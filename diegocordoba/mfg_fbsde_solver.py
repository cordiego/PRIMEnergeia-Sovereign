import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from typing import Tuple, Dict

logger = logging.getLogger("prime_kernel.mfg_fbsde")

class Z_Network(nn.Module):
    """
    Neural network parameterizing Z_t = ∇_x V(x,t)
    Inputs: [t, Δf, ROCOF]
    Outputs: [Z_1, Z_2]
    """
    def __init__(self, state_dim: int = 2, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim + 1, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, state_dim)
        )
        
        # Initialize weights to avoid early explosions
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, t: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        # t is shape (batch_size, 1), x is shape (batch_size, state_dim)
        tx = torch.cat([t, x], dim=-1)
        return self.net(tx)


class MFG_FBSDE_System:
    """
    Deep FBSDE Picard solver for Mean-Field Game frequency regulation.
    Resolves the Nash equilibrium for N->∞ providers competing for regulation.
    """
    def __init__(self,
                 T: float = 1.0,         # 1 second horizon (or 1 hour scaled)
                 num_steps: int = 50,
                 batch_size: int = 256,
                 state_dim: int = 2,
                 lambda_mfg: float = 150.0):
        
        self.T = T
        self.num_steps = num_steps
        self.dt = T / num_steps
        self.batch_size = batch_size
        self.state_dim = state_dim
        self.lambda_mfg = lambda_mfg
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Grid/Physics Parameters (CENACE-like)
        self.H = 4.8
        self.D = 1.1
        self.sigma_ou = 0.01483
        
        # Cost weights
        self.q1 = 100.0   # Frequency deviation penalty
        self.q2 = 10.0    # ROCOF penalty
        self.r = 0.1      # Control effort penalty
        
        self.u_max = 50.0 # MW max regulation capacity
        
        # Trainable parameters
        self.Y0 = nn.Parameter(torch.tensor([1.0], device=self.device))
        self.Z_net = Z_Network(state_dim=state_dim).to(self.device)
        self.optimizer = optim.Adam([{'params': self.Y0, 'lr': 1e-2},
                                     {'params': self.Z_net.parameters(), 'lr': 1e-3}])
                                     
    def _optimal_control(self, Z: torch.Tensor) -> torch.Tensor:
        """
        Calculates optimal control u* = argmin_u { r u^2 + Z_2 * (-u / 2H) }
        => u* = Z_2 / (4 r H)
        """
        Z_2 = Z[:, 1:2]
        u_star = Z_2 / (4.0 * self.r * self.H)
        # Clip control to physical boundaries
        u_star = torch.clamp(u_star, -self.u_max, self.u_max)
        return u_star
        
    def _drift(self, X: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        """
        f(X, u) = [X_2, (-D*X_1 - u) / 2H]
        """
        X_1 = X[:, 0:1]
        X_2 = X[:, 1:2]
        dX_1 = X_2
        dX_2 = (-self.D * X_1 - u) / (2.0 * self.H)
        return torch.cat([dX_1, dX_2], dim=-1)

    def _running_cost_and_mfg(self, X: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        """
        L(X,u) + F(X, m_t)
        F(X, m_t) = λ * (E[Δf] - Δf)
        """
        X_1 = X[:, 0:1]
        X_2 = X[:, 1:2]
        
        # Base running cost
        L = self.q1 * X_1**2 + self.q2 * X_2**2 + self.r * u**2
        
        # Mean Field Game Penalty (Interaction)
        # E_{m_t}[Δf] is approximated by the batch mean of X_1
        mean_f = torch.mean(X_1).detach() # detachment stabilizes training
        F_mfg = self.lambda_mfg * (mean_f - X_1)
        
        return L + F_mfg

    def forward_pass(self) -> torch.Tensor:
        """
        Simulates the forward pass of the FBSDE.
        Returns the terminal loss |Y_T - Φ(X_T)|^2.
        """
        # Initial state (e.g. slight deviation or 0)
        X = torch.zeros(self.batch_size, self.state_dim, device=self.device)
        # Add some initial variance to help the network learn
        X[:, 0] = torch.randn(self.batch_size, device=self.device) * 0.05
        
        Y = self.Y0.expand(self.batch_size, 1)
        
        for step in range(self.num_steps):
            t_tensor = torch.full((self.batch_size, 1), step * self.dt, device=self.device)
            
            # Forward pass through Z network
            Z = self.Z_net(t_tensor, X)
            
            # Compute optimal control
            u_star = self._optimal_control(Z)
            
            # Compute drift and cost
            drift = self._drift(X, u_star)
            cost = self._running_cost_and_mfg(X, u_star)
            
            # Generate Brownian noise (only on frequency dimension)
            dW = torch.randn(self.batch_size, self.state_dim, device=self.device) * np.sqrt(self.dt)
            dW_scaled = dW.clone()
            dW_scaled[:, 0] *= self.sigma_ou
            dW_scaled[:, 1] = 0.0 # No direct noise on ROCOF
            
            # BSDE Update: dY_t = -f_bsde dt + Z_t dW_t
            # f_bsde = L(X,u) + Z * f(X,u) + F_mfg
            Z_dot_drift = torch.sum(Z * drift, dim=-1, keepdim=True)
            f_bsde = cost + Z_dot_drift
            
            Z_dot_dW = torch.sum(Z * dW_scaled, dim=-1, keepdim=True)
            
            Y = Y - f_bsde * self.dt + Z_dot_dW
            
            # State Update: dX_t = drift dt + σ dW_t
            X = X + drift * self.dt + dW_scaled
            
        # Terminal condition Φ(X_T) = 200 * Δf^2
        Y_T_target = 200.0 * X[:, 0:1]**2
        
        loss = torch.mean((Y - Y_T_target)**2)
        return loss

    def train(self, epochs: int = 1000):
        logger.info(f"Starting Deep FBSDE MFG Solver for {epochs} epochs...")
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            loss = self.forward_pass()
            loss.backward()
            
            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(self.Z_net.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            if epoch % 100 == 0:
                logger.info(f"Epoch {epoch} | Loss: {loss.item():.6f} | Y0 (Price): {self.Y0.item():.4f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MFG FBSDE] - %(message)s')
    solver = MFG_FBSDE_System(num_steps=50, batch_size=512, lambda_mfg=200.0)
    solver.train(epochs=1000)
    print(f"Final Contract Equilibrium Price (Y0): {solver.Y0.item():.4f}")
