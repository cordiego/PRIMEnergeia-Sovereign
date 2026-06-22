import numpy as np
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("prime.kernel_mfg_ev")

class KernelMMD_MFG_Solver:
    """
    Kernel-based Potential Mean Field Games (MFG) with Electric Vehicle (EV) Charging Coordination.
    Uses Kernel-Maximum Mean Discrepancy (MMD) penalties + Schrödinger bridge framework
    to manage distributed EV charging under grid congestion.
    """
    
    def __init__(
        self,
        num_evs: int = 100,
        grid_capacity_mw: float = 5.0,
        time_horizon: int = 24, # 24 hours
        kernel_bandwidth: float = 1.0,
        mmd_penalty_weight: float = 50.0
    ):
        self.num_evs = num_evs
        self.grid_capacity_mw = grid_capacity_mw
        self.T = time_horizon
        self.sigma = kernel_bandwidth
        self.lambda_mmd = mmd_penalty_weight
        
        # State: SOC (State of Charge) [0, 1]
        self.state_grid_size = 50
        self.soc_grid = np.linspace(0.0, 1.0, self.state_grid_size)
        
        # Mean field distribution: rho(t, x) -> probability density of EVs at SOC x at time t
        self.rho = np.ones((self.T, self.state_grid_size)) / self.state_grid_size
        
        # Target distribution: ideally we want all EVs to be fully charged at T
        self.rho_target = np.zeros(self.state_grid_size)
        self.rho_target[-1] = 1.0 

    def _gaussian_kernel(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """RBF / Gaussian kernel for MMD."""
        diff = x[:, None] - y[None, :]
        return np.exp(-(diff**2) / (2 * self.sigma**2))

    def compute_mmd_penalty(self, current_rho: np.ndarray, target_rho: np.ndarray) -> float:
        """
        Computes the Maximum Mean Discrepancy (MMD) between the current distribution
        and the target distribution using the Gaussian kernel.
        """
        K = self._gaussian_kernel(self.soc_grid, self.soc_grid)
        
        # MMD^2 = rho^T K rho - 2 rho^T K target + target^T K target
        term1 = current_rho @ K @ current_rho
        term2 = 2 * current_rho @ K @ target_rho
        term3 = target_rho @ K @ target_rho
        
        return float(term1 - term2 + term3)
        
    def solve_schrodinger_bridge(self, max_iters: int = 50) -> Dict[str, Any]:
        """
        Solves the Schrödinger bridge problem via Sinkhorn-like iterations or 
        Forward-Backward sweep to find optimal charging policies that shift
        the initial distribution to the target distribution while respecting
        grid capacity and MMD penalties.
        """
        logger.info(f"Solving Kernel-MMD Schrödinger Bridge for {self.num_evs} EVs...")
        
        # Transition cost matrix C(x, y) = (x - y)^2
        C = (self.soc_grid[:, None] - self.soc_grid[None, :])**2
        
        # Entropic regularization parameter
        epsilon = 0.05
        K = np.exp(-C / epsilon)
        
        # Initialize Schrödinger variables
        phi = np.ones((self.T, self.state_grid_size))
        phi_hat = np.ones((self.T, self.state_grid_size))
        
        # For simplicity in this adaptation, we approximate the forward-backward 
        # system across the time horizon.
        
        # Initial distribution (e.g. EVs start with low SOC)
        rho_0 = np.exp(-((self.soc_grid - 0.2)**2) / 0.05)
        rho_0 /= np.sum(rho_0)
        
        for iteration in range(max_iters):
            # 1. Forward sweep (Fokker-Planck approximation via transition matrix)
            phi_hat[0] = rho_0 / np.maximum(phi[0], 1e-10)
            for t in range(1, self.T):
                # Congestion factor: if expected load > capacity, increase transition cost
                expected_load = np.sum(self.rho[t]) * 10.0 # dummy load metric
                congestion_penalty = max(0.0, expected_load - self.grid_capacity_mw)
                
                # Dynamic transition kernel
                K_dyn = K * np.exp(-congestion_penalty * 0.1)
                phi_hat[t] = K_dyn.T @ phi_hat[t-1]
                
            # 2. Backward sweep (HJB approximation)
            # Terminal condition incorporates the MMD penalty explicitly
            K_mmd = self._gaussian_kernel(self.soc_grid, self.soc_grid)
            grad_mmd = 2 * K_mmd @ (phi_hat[-1] * phi[-1] - self.rho_target)
            
            terminal_cost = self.lambda_mmd * grad_mmd
            phi[-1] = np.exp(-terminal_cost / epsilon)
            
            for t in range(self.T - 2, -1, -1):
                expected_load = np.sum(self.rho[t]) * 10.0
                congestion_penalty = max(0.0, expected_load - self.grid_capacity_mw)
                K_dyn = K * np.exp(-congestion_penalty * 0.1)
                
                phi[t] = K_dyn @ phi[t+1]
                
            # Update density
            new_rho = phi_hat * phi
            # Normalize
            for t in range(self.T):
                new_rho[t] /= np.maximum(np.sum(new_rho[t]), 1e-12)
                
            # Check convergence
            diff = np.max(np.abs(new_rho - self.rho))
            self.rho = new_rho
            
            if diff < 1e-4:
                logger.info(f"Schrödinger Bridge converged at iteration {iteration+1}")
                break
                
        final_mmd = self.compute_mmd_penalty(self.rho[-1], self.rho_target)
        logger.info(f"Final MMD penalty at T: {final_mmd:.6f}")
        
        return {
            "density_evolution": self.rho,
            "final_mmd_penalty": final_mmd,
            "convergence_diff": diff
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    solver = KernelMMD_MFG_Solver()
    solver.solve_schrodinger_bridge(max_iters=100)
