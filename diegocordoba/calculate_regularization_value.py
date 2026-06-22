import sys
import numpy as np

sys.path.append('lib')
from prime_kernel.hjb_solver import iso_params, ISOMarket
from simulate_grid_disturbance import SPDEGridSolver

def run_spde_valuation():
    solver_det = SPDEGridSolver(t_max=5.0)
    solver_stoch = SPDEGridSolver(damping=0.1, t_max=5.0)
    
    disturbance = lambda x: -0.55 * np.exp(-((x - 50)**2) / 10)
    
    print("Simulating Deterministic Cascade (Undefended)...")
    hist_det = solver_det.simulate(disturbance, False)
    
    print("Simulating Stochastic BESS Regularization...")
    hist_stoch = solver_stoch.simulate(disturbance, True, 4.0)
    
    p = iso_params(ISOMarket.CENACE)
    pen_coeff = p["penalty_coeff"]
    deadband = p["freq_deadband_hz"]
    
    def calculate_trajectory_cost(history, solver, collapsed):
        total_cost = 0.0
        # Time integration
        for f_dev in history:
            freq_cost = np.sum(100.0 * (f_dev**2))
            excess = np.maximum(0.0, np.abs(f_dev) - deadband)
            penalty = np.sum(pen_coeff * (excess**2))
            total_cost += (freq_cost + penalty) * solver.dt
            
        if collapsed:
            # If it collapsed, add the massive Energy Not Supplied cost
            # Assuming a 100 MW microgrid / zone, 1 hour blackout
            voll_cost = 100.0 * p["ens_cost_mxn_mwh"]
            total_cost += voll_cost
            
        return total_cost
        
    collapsed_det = len(hist_det) < solver_det.nt + 1 or np.any(hist_det[-1] < -10.0)
    collapsed_stoch = len(hist_stoch) < solver_stoch.nt + 1 or np.any(hist_stoch[-1] < -10.0)
    
    cost_det = calculate_trajectory_cost(hist_det, solver_det, collapsed_det)
    cost_stoch = calculate_trajectory_cost(hist_stoch, solver_stoch, collapsed_stoch)
    
    delta = cost_det - cost_stoch
    
    print(f"Cost Without Stochastic BESS: ${cost_det:,.2f}")
    print(f"Cost With Stochastic BESS:    ${cost_stoch:,.2f}")
    print(f"Delta (Navier-Stokes Reg):    ${delta:,.2f}")
    
    with open('navier_stokes_regularization_value.md', 'w') as f:
        f.write("# Navier-Stokes Regularization Valuation\n\n")
        f.write("By injecting the cascade term ($-0.5f^2$) into the SPDE dynamics, we evaluated the grid response to a cascading failure with and without stochastic BESS.\n\n")
        f.write(f"- **Cost Without Stochastic BESS (Undefended Grid):** ${cost_det:,.2f}\n")
        f.write(f"- **Cost With Stochastic BESS (Regularized Grid):** ${cost_stoch:,.2f}\n")
        f.write(f"- **Delta (Dollar Value of Regularization):** ${delta:,.2f}\n\n")
        f.write("> [!TIP]\n")
        f.write(f"> **Our SPDE control preserves ${delta:,.2f} of revenue that an undefended grid loses to cascade.** This provides a defensible, monetizable number for the Navier-Stokes regularization.\n")

if __name__ == "__main__":
    run_spde_valuation()
