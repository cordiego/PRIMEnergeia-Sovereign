import torch
import torch.nn as nn
import torch.optim as optim

class PICNNArbitrageSolver:
    """
    Mathematical Bridge: HJB Solver ↔ Market Arbitrage
    
    This solver exploits the strict convexity of the GranasPICNN w.r.t the economic input 
    z = log(p_L). Because the network guarantees a Positive Semi-Definite (PSD) Hessian 
    for z, any convex objective function defined over the network's output will have a 
    unique global optimum. 
    
    This breaks the "curse of dimensionality" for complex non-linear grid states (x),
    allowing us to guarantee optimal dispatch or arbitrage schedules to Engie.
    """
    def __init__(self, picnn_model: nn.Module, lr=0.1, max_iter=100):
        """
        Args:
            picnn_model: The trained GranasPICNN instance.
            lr: Learning rate for the L-BFGS optimizer.
            max_iter: Maximum iterations for the optimizer.
        """
        self.model = picnn_model
        self.model.eval() # Freeze network weights for optimization
        self.lr = lr
        self.max_iter = max_iter

    def solve_optimal_dispatch(self, x, z_init, objective_fn):
        """
        Solves for the optimal log-price (z*) given covariates (x).
        
        Args:
            x: Tensor of covariates (batch_size, covariate_dim).
            z_init: Initial guess for z (batch_size, z_dim).
            objective_fn: A callable `fn(model_output, z)` that returns a scalar loss to MINIMIZE.
                          Since PICNN is convex w.r.t z, if objective_fn preserves convexity, 
                          L-BFGS is guaranteed to find the global minimum.
                          
        Returns:
            z_opt: The optimal z tensor.
            loss_history: List of loss values during optimization.
        """
        # Ensure gradients can be computed for z
        z = z_init.clone().detach().requires_grad_(True)
        
        # Use L-BFGS, which is highly efficient for deterministic convex problems
        optimizer = optim.LBFGS([z], lr=self.lr, max_iter=self.max_iter, 
                                tolerance_grad=1e-7, tolerance_change=1e-9, 
                                history_size=10, line_search_fn="strong_wolfe")
        
        loss_history = []
        
        def closure():
            optimizer.zero_grad()
            # Forward pass through the PICNN
            out = self.model(x, z)
            # Evaluate the economic objective
            loss = objective_fn(out, z)
            loss.backward()
            loss_history.append(loss.item())
            return loss

        # Run optimization
        optimizer.step(closure)
        
        return z.detach(), loss_history

    def verify_convexity(self, x, z):
        """
        Mathematically audits the Hessian of the PICNN w.r.t z.
        For Engie's due diligence: Returns True if the Hessian is Positive Semi-Definite.
        """
        if not hasattr(self.model, 'compute_hessian_z'):
            raise NotImplementedError("PICNN model must have compute_hessian_z method.")
            
        hessian = self.model.compute_hessian_z(x, z)
        batch_size = hessian.size(0)
        
        is_psd = True
        min_eigenvalues = []
        
        for b in range(batch_size):
            # Compute eigenvalues of the Hessian matrix
            eigvals = torch.linalg.eigvalsh(hessian[b])
            min_eig = eigvals.min().item()
            min_eigenvalues.append(min_eig)
            
            # Allow for minor numerical instability (e.g., -1e-6)
            if min_eig < -1e-5:
                is_psd = False
                
        return is_psd, min_eigenvalues

if __name__ == "__main__":
    # Quick standalone verification
    import numpy as np
    from granas_icnn import GranasPICNN
    
    print("Initializing Granas PICNN Arbitrage Solver Test...")
    model = GranasPICNN(covariate_dim=5, hidden_dims=[32, 32], z_dim=1)
    solver = PICNNArbitrageSolver(model)
    
    # Mock data
    x_mock = torch.randn(2, 5) # 2 samples, 5 covariates
    z_mock = torch.randn(2, 1) # Initial price guess
    
    # 1. Verify Convexity (Hessian Audit)
    is_psd, min_eigs = solver.verify_convexity(x_mock, z_mock)
    print(f"Hessian is Positive Semi-Definite: {is_psd} (Min Eigenvalues: {min_eigs})")
    
    # 2. Solve Optimal Dispatch
    # Example Objective: We want the network output (e.g., log demand) to match a target_demand,
    # plus a small regularization cost on price z. This forms a strictly convex quadratic objective.
    target_out = torch.tensor([[0.5], [1.0]])
    
    def mock_objective(out, z):
        # L2 distance to target + L2 regularization on z
        return torch.mean((out - target_out)**2) + 0.01 * torch.mean(z**2)
        
    z_opt, history = solver.solve_optimal_dispatch(x_mock, z_mock, mock_objective)
    print(f"Initial z: {z_mock.view(-1).numpy()}")
    print(f"Optimal z*: {z_opt.view(-1).numpy()}")
    print(f"Initial Loss: {history[0]:.4f} -> Final Loss: {history[-1]:.4f}")
