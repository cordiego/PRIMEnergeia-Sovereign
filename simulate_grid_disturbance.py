#!/usr/bin/env python3
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('lib')
from prime_kernel.hjb_solver import HJBSolver, RobustHJBSolver, GridFrequencyDynamics, ISOMarket

def main():
    print("Initializing solvers...")
    dynamics = GridFrequencyDynamics(market=ISOMarket.CENACE)
    # Smaller grid and fewer sweeps for faster evaluation in pure Python
    grid_points = [15, 12]
    
    # Overwrite xi_grid in robust solver dynamically to be in MW instead of Hz/sqrt(s)
    # +/- 30 MW disturbances
    base_solver = HJBSolver(dynamics, grid_points=grid_points, max_sweeps=5)
    robust_solver = RobustHJBSolver(dynamics, epsilon=0.00346, grid_points=grid_points, max_sweeps=5)
    robust_solver.xi_grid = np.linspace(-30.0, 30.0, 7)
    
    print("Solving Deterministic HJB...")
    base_solver.solve()
    
    print("Solving Minimax Robust HJB...")
    robust_solver.solve()
    
    print("Running 500 Quantum-Seeded Simulations...")
    rng = np.random.default_rng(62697)
    
    n_scenarios = 500
    dt = 0.5  # fine dt for simulation
    horizon = 300.0  # 5 minutes
    n_steps = int(horizon / dt)
    
    rec_time_det = np.zeros(n_scenarios)
    rec_time_rob = np.zeros(n_scenarios)
    nadir_det = np.zeros(n_scenarios)
    nadir_rob = np.zeros(n_scenarios)
    cost_det = np.zeros(n_scenarios)
    cost_rob = np.zeros(n_scenarios)
    
    initial_state = np.array([-1.5, 0.0])  # Initial shock: -1.5 Hz
    
    def fast_optimal_control(solver, state):
        idx = tuple(
            np.abs(g - s).argmin() for g, s in zip(solver.state_grids, state)
        )
        return solver.control_grid[solver.policy[idx]]

    def simulate_policy(solver, state0, noise_path):
        state = state0.copy()
        nadir = state[0]
        cost = 0.0
        recovered_time = horizon
        
        for i in range(n_steps):
            df = state[0]
            nadir = min(nadir, df)
            
            # Check recovery condition (within +/- 0.5 Hz)
            if abs(df) <= 0.5 and recovered_time == horizon:
                recovered_time = i * dt
            elif abs(df) > 0.5:
                # Reset if it falls out again (optional, we'll keep strict first-touch recovery for simplicity)
                pass
            
            u = fast_optimal_control(solver, state)
            cost += abs(u) * dt
            
            xi = noise_path[i]
            state = dynamics.step(state, u, dt, xi=xi)
            
        return recovered_time, nadir, cost

    start_sim = time.time()
    for s in range(n_scenarios):
        # Generate the quantum-seeded stochastic path (MW disturbance)
        # Using a base volatility of 10 MW + some heavy tails
        noise_path = rng.normal(0, 10.0, n_steps)
        
        # 2% chance of a massive jump at any second (-40 to -10 MW drop)
        jumps = rng.uniform(0, 1, n_steps) < (0.02 * dt)
        noise_path[jumps] += rng.uniform(-40.0, -10.0, np.sum(jumps))
        
        t_det, n_det, c_det = simulate_policy(base_solver, initial_state, noise_path)
        t_rob, n_rob, c_rob = simulate_policy(robust_solver, initial_state, noise_path)
        
        rec_time_det[s] = t_det
        rec_time_rob[s] = t_rob
        
        nadir_det[s] = n_det
        nadir_rob[s] = n_rob
        
        cost_det[s] = c_det
        cost_rob[s] = c_rob

    print(f"Simulation completed in {time.time() - start_sim:.2f} seconds.")
    print("\n--- RESULTS ---")
    print(f"Deterministic HJB | Mean Recovery Time: {np.mean(rec_time_det):.2f} s | Worst Nadir: {np.min(nadir_det):.4f} Hz | Mean Cost: {np.mean(cost_det):.2f}")
    print(f"Minimax Robust HJB| Mean Recovery Time: {np.mean(rec_time_rob):.2f} s | Worst Nadir: {np.min(nadir_rob):.4f} Hz | Mean Cost: {np.mean(cost_rob):.2f}")
    
    plt.figure(figsize=(10, 6))
    
    x_det = np.sort(rec_time_det)
    y_det = np.arange(1, len(x_det)+1) / len(x_det)
    
    x_rob = np.sort(rec_time_rob)
    y_rob = np.arange(1, len(x_rob)+1) / len(x_rob)
    
    plt.plot(x_det, y_det, label='Deterministic HJB', linewidth=2, color='coral')
    plt.plot(x_rob, y_rob, label='Minimax Robust HJB', linewidth=2, color='teal')
    
    plt.title('CDF of Grid Frequency Recovery Time (Target: ±0.5 Hz)', fontsize=14)
    plt.xlabel('Recovery Time (seconds)', fontsize=12)
    plt.ylabel('Cumulative Probability', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    textstr = '\\n'.join((
        r'Worst Nadir (Det): %.3f Hz' % (np.min(nadir_det), ),
        r'Worst Nadir (Rob): %.3f Hz' % (np.min(nadir_rob), ),
        r'Mean Cost (Det): %.1f' % (np.mean(cost_det), ),
        r'Mean Cost (Rob): %.1f' % (np.mean(cost_rob), )))
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    plt.gca().text(0.65, 0.45, textstr, transform=plt.gca().transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
            
    plt.savefig('robust_vs_deterministic_cdf.png', dpi=300, bbox_inches='tight')
    print("Saved plot to robust_vs_deterministic_cdf.png")

if __name__ == "__main__":
    main()
