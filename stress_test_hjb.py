import numpy as np
import logging
import time
from lib.prime_kernel.hjb_solver import (
    GridFrequencyDynamics,
    HJBSolver,
    RobustHJBSolver,
    ISOMarket
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger("hjb_stress_test")

def run_stress_test():
    logger.info("Starting HJB Boundary Conditions Stress Test")
    
    # Initialize basic grid dynamics
    dynamics = GridFrequencyDynamics(market=ISOMarket.CENACE)
    
    # Initialize Solvers with small grid for fast tests
    base_solver = HJBSolver(dynamics, grid_points=[10, 10], stochastic=True, max_sweeps=2)
    robust_solver = RobustHJBSolver(dynamics, epsilon=0.00346, grid_points=[10, 10], max_sweeps=2)
    
    logger.info("Solving base solver...")
    base_solver.solve()
    
    logger.info("Solving robust solver...")
    robust_solver.solve()
    
    test_states = {
        "Inside Bounds (Normal)": np.array([0.0, 50.0]),
        "Lower Bound Exact": np.array([-2.0, 0.0]),
        "Upper Bound Exact": np.array([2.0, 100.0]),
        "Far Outside Lower Bound": np.array([-10.0, -50.0]),
        "Far Outside Upper Bound": np.array([10.0, 500.0]),
        "NaN State": np.array([np.nan, np.nan]),
        "Inf State": np.array([np.inf, -np.inf]),
    }
    
    solvers = {
        "HJBSolver": base_solver,
        "RobustHJBSolver": robust_solver
    }
    
    for solver_name, solver in solvers.items():
        logger.info("=" * 50)
        logger.info(f"Testing {solver_name}")
        logger.info("=" * 50)
        
        for case_name, state in test_states.items():
            logger.info(f"--- Case: {case_name} (State: {state}) ---")
            
            try:
                # 1. Test interpolation
                v_val = solver._interpolate_V(state)
                logger.info(f"  Interpolated V(x) = {v_val:.4f}")
                
                # 2. Test optimal control
                u_opt = solver.optimal_control(state)
                logger.info(f"  Optimal Control u*(x) = {u_opt:.4f}")
                
                # 3. Test simulation (only if no NaN/Inf)
                if not np.any(np.isnan(state)) and not np.any(np.isinf(state)):
                    t0 = time.perf_counter()
                    res = solver.simulate(state)
                    sim_time = time.perf_counter() - t0
                    
                    # Verify bounds in simulation trajectory
                    df_traj = res.state_trajectory[:, 0]
                    p_traj = res.state_trajectory[:, 1]
                    
                    df_min, df_max = np.min(df_traj), np.max(df_traj)
                    p_min, p_max = np.min(p_traj), np.max(p_traj)
                    
                    logger.info(f"  Simulation completed in {sim_time:.3f}s. Total Cost: {res.total_cost:.2f}")
                    logger.info(f"  Trajectory Bounds -> df: [{df_min:.3f}, {df_max:.3f}], P: [{p_min:.3f}, {p_max:.3f}]")
                    
                    if df_min < -2.0 or df_max > 2.0 or p_min < 0.0 or p_max > 100.0:
                        logger.warning(f"  ⚠️ BOUNDARY VIOLATION IN TRAJECTORY!")
                else:
                    logger.info("  Skipping simulation for NaN/Inf state.")
                
            except Exception as e:
                logger.error(f"  ❌ FAILED: {str(e)}")

if __name__ == "__main__":
    run_stress_test()
