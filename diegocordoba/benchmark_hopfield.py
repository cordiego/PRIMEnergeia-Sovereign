import time
import numpy as np
import logging
from hjb_solver_fortified import GridFrequencyDynamics, HJBSolver
from prime_kernel.hopfield import HopfieldValueMemory

def run_benchmark():
    # Setup logging to see solver logs
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
    logger = logging.getLogger("prime_benchmark")
    
    print("\n" + "="*70)
    print(" PRIME-Kernel Benchmark: Hopfield Warm-Start vs Cold-Start")
    print("="*70 + "\n")

    dynamics = GridFrequencyDynamics()
    grid_points = [25, 25]  # Slightly larger grid to make the timing difference more obvious
    
    # -------------------------------------------------------------------------
    # 1. PURE COLD START
    # -------------------------------------------------------------------------
    print("\n--- Running Cold-Start Baseline ---")
    solver_cold = HJBSolver(dynamics, grid_points=grid_points, max_sweeps=10, tol=0.01)
    solver_cold.solve()
    
    cold_sweeps = solver_cold._n_sweeps
    cold_time = solver_cold._solve_time
    
    # -------------------------------------------------------------------------
    # 2. POPULATE HOPFIELD MEMORY
    # -------------------------------------------------------------------------
    print("\n--- Populating Hopfield Memory ---")
    memory = HopfieldValueMemory(beta=1.0)
    solver_initial = HJBSolver(dynamics, grid_points=grid_points, max_sweeps=10, tol=0.01, hopfield_memory=memory)
    # Simulate will solve and then store the result into the memory
    initial_state = np.array([-0.02, 0.0])
    solver_initial.simulate(initial_state)
    
    # -------------------------------------------------------------------------
    # 3. WARM START
    # -------------------------------------------------------------------------
    print("\n--- Running Warm-Start ---")
    # We create a new solver instance but pass the populated memory
    solver_warm = HJBSolver(dynamics, grid_points=grid_points, max_sweeps=10, tol=0.01, hopfield_memory=memory)
    solver_warm.solve()
    
    warm_sweeps = solver_warm._n_sweeps
    warm_time = solver_warm._solve_time
    
    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" Benchmark Results Summary")
    print("="*70)
    print(f"{'Metric':<20} | {'Cold-Start':<15} | {'Warm-Start (Hopfield)':<25}")
    print("-" * 70)
    print(f"{'Sweeps to converge':<20} | {cold_sweeps:<15} | {warm_sweeps:<25}")
    print(f"{'Solve Time (s)':<20} | {cold_time:<15.4f} | {warm_time:<25.4f}")
    
    speedup = cold_time / warm_time if warm_time > 0 else 0
    print("-" * 70)
    print(f"Speedup Factor: {speedup:.2f}x faster with Hopfield memory!")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_benchmark()
