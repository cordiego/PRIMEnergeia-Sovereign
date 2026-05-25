import numpy as np
import logging
from typing import Dict, Tuple
from hjb_solver_fortified import HJBSolver, RobustHJBSolver, HJBDynamics

logger = logging.getLogger("prime_kernel.uncertainty")

class UncertaintyQuantifier:
    """
    Validated Uncertainty Quantification (UQ) Layer for the PRIME-Kernel.
    Provides Empirical UQ (Monte Carlo SDE) and Structural UQ (Robust HJB).
    """

    def __init__(self, solver: HJBSolver):
        if not solver._solved:
            raise RuntimeError("HJBSolver must be solved before initializing UQ.")
        self.solver = solver
        self.dynamics = solver.dynamics
        self.dt = solver.dt
        self.total_time = solver.total_time
        
    def empirical_uq(self, initial_state: np.ndarray, n_paths: int = 1000) -> Dict[str, float]:
        """
        Forward SDE Monte Carlo evaluation of the optimal policy.
        Simulates n_paths and collects the total cost/revenue distribution.
        """
        logger.info(f"Running Empirical UQ: {n_paths} Monte Carlo SDE paths...")
        n_steps = int(self.total_time / self.dt)
        n_dims = self.dynamics.state_dims()
        t_grid = np.linspace(0, self.total_time, n_steps + 1)
        
        path_costs = np.zeros(n_paths)
        
        for p in range(n_paths):
            state = initial_state.copy()
            cost = 0.0
            
            for i in range(n_steps):
                t = t_grid[i]
                u = self.solver.optimal_control(state, t)
                
                # Accumulate deterministic running cost
                cost += self.dynamics.running_cost(state, u, t) * self.dt
                
                # Deterministic step
                state = self.dynamics.step(state, u, self.dt)
                
                # Stochastic Itô injection (Brownian noise)
                if self.solver.stochastic:
                    g = self.dynamics.diffusion(state)
                    dW = np.random.normal(0.0, np.sqrt(self.dt), size=n_dims)
                    state += g * dW
                    
            cost += self.dynamics.terminal_cost(state)
            path_costs[p] = cost
            
        # Cost is inverted for revenue metrics if necessary, but we treat it as cost here.
        # We assume the user wants confidence bounds on the Total Value (-Cost).
        path_values = -path_costs
        
        p10 = float(np.percentile(path_values, 10))
        p50 = float(np.percentile(path_values, 50))
        p90 = float(np.percentile(path_values, 90))
        
        # 95% Value at Risk (VaR) and Expected Shortfall (CVaR)
        var_95 = float(np.percentile(path_values, 5)) 
        cvar_95 = float(np.mean(path_values[path_values <= var_95]))
        
        logger.info(f"Empirical UQ Results (n={n_paths}):")
        logger.info(f" P90 Value: {p90:,.2f}")
        logger.info(f" P50 Value: {p50:,.2f}")
        logger.info(f" P10 Value: {p10:,.2f}")
        logger.info(f" VaR(95%):  {var_95:,.2f}")
        logger.info(f" CVaR(95%): {cvar_95:,.2f}")
        
        return {
            "P10": p10,
            "P50": p50,
            "P90": p90,
            "VaR_95": var_95,
            "CVaR_95": cvar_95,
            "raw_values": path_values
        }

    def structural_uq(self, initial_state: np.ndarray, epsilon: float = 0.005) -> Dict[str, float]:
        """
        Robust HJB Value Bounds (Structural UQ).
        Evaluates the worst-case robust HJB under ambiguity radius epsilon.
        """
        logger.info(f"Running Structural UQ: Robust HJB with epsilon={epsilon}...")
        
        # Worst-case (Adversarial) HJB
        robust_solver = RobustHJBSolver(
            self.dynamics,
            epsilon=epsilon,
            total_time=self.solver.total_time,
            dt=self.solver.dt,
            grid_points=[len(g) for g in self.solver.state_grids],
            n_controls=self.solver.n_controls,
            max_sweeps=self.solver.max_sweeps,
            tol=self.solver.tol,
            stochastic=self.solver.stochastic
        )
        robust_solver.solve()
        v_robust = -robust_solver._interpolate_V(initial_state)
        
        # Central-case (Already solved)
        v_central = -self.solver._interpolate_V(initial_state)
        
        logger.info(f"Structural UQ Results (ε={epsilon}):")
        logger.info(f" Central Value: {v_central:,.2f}")
        logger.info(f" Robust (Worst-case) Value: {v_robust:,.2f}")
        
        return {
            "V_central": v_central,
            "V_robust": v_robust,
            "epsilon": epsilon
        }

    def generate_report(self, initial_state: np.ndarray, epsilon: float = 0.005, n_paths: int = 1000) -> str:
        """
        Generates a validated UQ report for licensing/buyers.
        """
        emp = self.empirical_uq(initial_state, n_paths=n_paths)
        struc = self.structural_uq(initial_state, epsilon=epsilon)
        
        confidence_score = max(0.0, min(100.0, 100.0 * (emp["VaR_95"] / struc["V_central"])))
        
        report = (
            "============================================================\n"
            "       VALIDATED UNCERTAINTY QUANTIFICATION (UQ) REPORT     \n"
            "============================================================\n"
            f"Model Confidence Score: {confidence_score:.1f}/100\n\n"
            "--- EMPIRICAL UQ (Monte Carlo SDE) ---\n"
            f" Simulated Paths: {n_paths}\n"
            f" P90 Value (Optimistic):  {emp['P90']:>12,.2f}\n"
            f" P50 Value (Expected):    {emp['P50']:>12,.2f}\n"
            f" P10 Value (Pessimistic): {emp['P10']:>12,.2f}\n"
            f" 95% Value at Risk (VaR): {emp['VaR_95']:>12,.2f}\n"
            f" Expected Shortfall:      {emp['CVaR_95']:>12,.2f}\n\n"
            "--- STRUCTURAL UQ (Robust HJB) ---\n"
            f" Ambiguity Radius (ε):    {struc['epsilon']:.5f}\n"
            f" Central HJB Value:       {struc['V_central']:>12,.2f}\n"
            f" Worst-Case Robust Value: {struc['V_robust']:>12,.2f}\n"
            "============================================================"
        )
        return report
