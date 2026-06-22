import numpy as np
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger("train_regimes")

# Add paths to sys.path if needed
sys.path.append("/Users/diegocordoba/diegocordoba")
sys.path.append("/Users/diegocordoba/diegocordoba/PRIME-Kernel")

try:
    from hjb_solver_fortified import HJBSolver, HJBDynamics
    from prime_kernel.hopfield import HopfieldValueMemory
except ImportError as e:
    logger.error(f"Failed to import PRIME-Kernel modules: {e}")
    sys.exit(1)

from typing import List, Tuple

class PortfolioDynamics(HJBDynamics):
    """
    Portfolio State Dynamics for Mathematical Optimal Rebalancing.
    State: [SNDK_price, SNXX_price, VIX, cash_ratio]
    Control: u = allocation weight shift rate (rebalancing policy into SCHD/Risk)
    """

    def __init__(self, 
                 mu_sndk=0.08, sigma_sndk=0.20,
                 mu_snxx=0.05, sigma_snxx=0.15,
                 kappa_vix=5.0, theta_vix=20.0, sigma_vix=2.0,
                 risk_free_rate=0.03):
        self.mu_sndk = mu_sndk
        self.sigma_sndk = sigma_sndk
        self.mu_snxx = mu_snxx
        self.sigma_snxx = sigma_snxx
        self.kappa_vix = kappa_vix
        self.theta_vix = theta_vix
        self.sigma_vix_val = sigma_vix
        self.r = risk_free_rate

    def state_dims(self) -> int: return 4

    def state_bounds(self) -> List[Tuple[float, float]]:
        # Using a very coarse grid to make 4D solving fast for Hopfield Memory
        return [
            (10.0, 300.0),   # SNDK
            (10.0, 300.0),   # SNXX
            (10.0, 80.0),    # VIX
            (0.0, 1.0)       # cash_ratio
        ]

    def control_bounds(self) -> Tuple[float, float]:
        return (-0.5, 0.5)

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        sndk, snxx, vix, cash = state
        
        dsndk = sndk * self.mu_sndk
        dsnxx = snxx * self.mu_snxx
        dvix = self.kappa_vix * (self.theta_vix - vix)
        dcash = control
        
        new_sndk = np.clip(sndk + dsndk * dt, 10.0, 300.0)
        new_snxx = np.clip(snxx + dsnxx * dt, 10.0, 300.0)
        new_vix  = np.clip(vix + dvix * dt, 10.0, 80.0)
        new_cash = np.clip(cash + dcash * dt, 0.0, 1.0)
        
        return np.array([new_sndk, new_snxx, new_vix, new_cash])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        sndk, snxx, vix, _ = state
        vix_scale = max(1.0, vix / 20.0)
        return np.array([
            sndk * self.sigma_sndk * vix_scale,
            snxx * self.sigma_snxx * vix_scale,
            self.sigma_vix_val,
            0.0
        ])

    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        sndk, snxx, vix, cash = state
        tx_cost = 0.05 * abs(control)
        risk_penalty = max(0.0, (vix - 25.0)) * (1.0 - cash)
        opp_cost = max(0.0, (20.0 - vix)) * cash
        return tx_cost + 5.0 * risk_penalty + 2.0 * opp_cost

    def terminal_cost(self, state: np.ndarray) -> float:
        sndk, snxx, vix, cash = state
        return 50.0 * (1.0 - cash) * (vix / 20.0)


def train_regimes():
    memory_bank = HopfieldValueMemory(beta=2.0)
    
    regimes = [
        {
            "name": "LOW VIX Bull Run",
            "vix": 12.0,
            "mu_sndk": 0.15,
            "mu_snxx": 0.30
        },
        {
            "name": "HIGH VIX Crash",
            "vix": 35.0,
            "mu_sndk": -0.20,
            "mu_snxx": -0.40
        },
        {
            "name": "Decay Spiral (Chop)",
            "vix": 20.0,
            "mu_sndk": -0.05,
            "mu_snxx": -0.15
        }
    ]
    
    grid_points = [5, 5, 5, 5]  # Very coarse to run quickly for 4D
    
    for regime in regimes:
        logger.info(f"--- Training Regime: {regime['name']} ---")
        
        # Configure the dynamics
        dyn = PortfolioDynamics(
            mu_sndk=regime["mu_sndk"], 
            mu_snxx=regime["mu_snxx"],
            theta_vix=regime["vix"]
        )
        
        # The query vector representing this regime for the memory bank
        query_vector = np.array([regime["vix"], regime["mu_sndk"], regime["mu_snxx"]])
        
        # Initialize the HJB solver
        solver = HJBSolver(
            dynamics=dyn,
            total_time=100.0,
            dt=2.0,
            grid_points=grid_points,
            n_controls=5,
            max_sweeps=4,  # Just 4 sweeps to train fast
            stochastic=False,
            hopfield_memory=memory_bank,
            config_vector=query_vector
        )
        
        # We manually call solve() and then we manually store it 
        # (HJBSolver.simulate auto-stores, but we just want to train the V function)
        solver.solve()
        
        # Use a dummy total_cost or metric for storing
        # Lower cost is better in HJB
        avg_cost = np.mean(solver.V)
        metric = -avg_cost 
        
        memory_bank.store(query_vector, solver.V.copy(), metric=metric)
        logger.info(f"Stored {regime['name']} into HopfieldMemory.")
    
    # Save the memory bank
    save_path = "/Users/diegocordoba/diegocordoba/market_memory.pkl"
    memory_bank.save(save_path)
    logger.info(f"Training complete! Saved to {save_path}")

if __name__ == "__main__":
    train_regimes()
