#!/usr/bin/env python3
import time
import numpy as np
import logging

from hjb_solver_fortified import GridFrequencyDynamics, HJBSolver
from prime_kernel.hopfield import HopfieldValueMemory
from granas_vza400_dynamics import GranasVZA400Dynamics
from uncertainty_layer import UncertaintyQuantifier

def run_benchmark():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    print("\n" + "="*70)
    print(" PRIME-Kernel Benchmark: Hopfield Warm-Start vs Cold-Start")
    print("="*70 + "\n")

    dynamics_grid = GridFrequencyDynamics()
    grid_points = [25, 25]
    
    # -------------------------------------------------------------------------
    # 1. PURE COLD START
    # -------------------------------------------------------------------------
    print("\n--- Running Cold-Start Baseline ---")
    solver_cold = HJBSolver(dynamics_grid, grid_points=grid_points, max_sweeps=10, tol=0.01)
    solver_cold.solve()
    
    cold_sweeps = solver_cold._n_sweeps
    cold_time = solver_cold._solve_time
    
    # -------------------------------------------------------------------------
    # 2. POPULATE HOPFIELD MEMORY
    # -------------------------------------------------------------------------
    print("\n--- Populating Hopfield Memory ---")
    memory = HopfieldValueMemory(beta=1.0)
    solver_initial = HJBSolver(dynamics_grid, grid_points=grid_points, max_sweeps=10, tol=0.01, hopfield_memory=memory)
    initial_state = np.array([-0.02, 0.0])
    solver_initial.simulate(initial_state)
    
    # -------------------------------------------------------------------------
    # 3. WARM START
    # -------------------------------------------------------------------------
    print("\n--- Running Warm-Start ---")
    solver_warm = HJBSolver(dynamics_grid, grid_points=grid_points, max_sweeps=10, tol=0.01, hopfield_memory=memory)
    solver_warm.solve()
    
    warm_sweeps = solver_warm._n_sweeps
    warm_time = solver_warm._solve_time

    # -------------------------------------------------------------------------
    # 4. BAYESIAN UQ REPORT (30.3% PCE)
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" Validated UQ Layer for 30.3% PCE + Hydrogen Back Contact")
    print("="*70)

    dynamics_vza400 = GranasVZA400Dynamics()
    grid_points_vza400 = [4, 4, 4, 4]

    print("\n🧠 Solving Central HJB Optimal Control (Stochastic)...")
    solver_vza400 = HJBSolver(
        dynamics_vza400, 
        dt=2.0, 
        total_time=60.0, 
        grid_points=grid_points_vza400, 
        max_sweeps=3,
        stochastic=True
    )
    solver_vza400.solve()

    print("\n📈 Initializing Uncertainty Quantifier...")
    uq = UncertaintyQuantifier(solver_vza400)

    # High PV output (80 MW), Temp 400C, Pressure 200 bar, 50% H2 buffer
    initial_state_vza = np.array([80.0, 400.0, 200.0, 0.5])

    print("\nGenerating UQ Report (Monte Carlo + Robust HJB Bounds)...")
    report = uq.generate_report(initial_state_vza, epsilon=0.0035, n_paths=2000)

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" DUE DILIGENCE REPORT: PERFORMANCE & UQ")
    print("="*70)
    print(f"{'Metric':<20} | {'Cold-Start':<15} | {'Warm-Start (Hopfield)':<25}")
    print("-" * 70)
    print(f"{'Sweeps to converge':<20} | {cold_sweeps:<15} | {warm_sweeps:<25}")
    print(f"{'Solve Time (s)':<20} | {cold_time:<15.4f} | {warm_time:<25.4f}")
    
    speedup = cold_time / warm_time if warm_time > 0 else 0
    print("-" * 70)
    print(f"Speedup Factor: {speedup:.2f}x faster with Hopfield memory!")
    print("\n")
    print(report)

if __name__ == "__main__":
    run_benchmark()
