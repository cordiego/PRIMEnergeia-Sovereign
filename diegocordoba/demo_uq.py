#!/usr/bin/env python3
import sys
import numpy as np
import logging

from hjb_solver_fortified import HJBSolver
from granas_dynamics import GranasDynamics
from uncertainty_layer import UncertaintyQuantifier

logging.basicConfig(level=logging.INFO, format="%(message)s")

def main():
    np.random.seed(20462)
    print("🚀 Initializing Validated UQ Layer for 30.3% PCE + Hydrogen Back Contact...")

    # Initialize dynamics for PV-HB integration
    dynamics = GranasDynamics()

    # To keep the demo fast, we use a coarse grid (4D state space)
    # E_PV, T_r, P_r, S_H2
    grid_points = [4, 4, 4, 4]

    print("\n🧠 Solving Central HJB Optimal Control (Stochastic)...")
    solver = HJBSolver(
        dynamics, 
        dt=2.0, 
        total_time=60.0,  # Short horizon for quick demo
        grid_points=grid_points, 
        max_sweeps=3,
        stochastic=True
    )
    solver.solve()

    print("\n📈 Initializing Uncertainty Quantifier...")
    uq = UncertaintyQuantifier(solver)

    # Initial state representing the 30.3% PCE operational point:
    # High PV output (e.g. 80 MW), nominal Temp 400C, Pressure 200 bar, 50% H2 buffer
    initial_state = np.array([80.0, 400.0, 200.0, 0.5])

    # Generate the Validated UQ Report
    print("\n" + "="*60)
    print("Generating UQ Report (Monte Carlo + Robust HJB Bounds)...")
    report = uq.generate_report(initial_state, epsilon=0.0035, n_paths=2000)
    
    print("\n" + report)

if __name__ == "__main__":
    main()
