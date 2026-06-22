import numpy as np
import matplotlib.pyplot as plt
import time
from simulate_grid_disturbance import SPDEGridSolver

def run_sweep():
    # Sweep from 1.0 down to 0.0
    amps = np.linspace(1.0, 0.0, 40)
    n_scenarios = 100
    p_cascade = []
    
    disturbance = lambda x: -0.55 * np.exp(-((x - 50)**2) / 10)
    
    print("Starting BESS amplitude sweep...")
    start_time = time.time()
    
    for amp in amps:
        cascades = 0
        for s in range(n_scenarios):
            solver = SPDEGridSolver(damping=0.2)
            
            # Run simulation
            hist = solver.simulate(disturbance, use_stochastic_bess=True, bess_noise_amp=amp)
            
            # Check cascade condition: early break or hit limit
            if len(hist) < solver.nt + 1 or np.any(hist[-1] < -10.0) or np.any(np.isnan(hist[-1])):
                cascades += 1
                
        p_cascade.append(cascades / n_scenarios)
        print(f"Amp: {amp:.3f} | P(cascade): {p_cascade[-1]:.2f}")
        
    print(f"Sweep completed in {time.time() - start_time:.2f} seconds.")
    
    plt.figure(figsize=(8, 5))
    plt.plot(amps, p_cascade, 'ro-', linewidth=2)
    plt.axvline(0, color='k', linestyle='--', label='σ → 0 (Zero Noise)')
    
    # Invert x-axis to show the approach to 0 clearly from left to right
    plt.xlim(1.05, -0.05)
    
    plt.title('Phase 4: BESS Noise Regularization Gap\n(Singular vs Smooth Limit)')
    plt.xlabel('BESS Noise Amplitude (σ)')
    plt.ylabel('P(cascade)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    output_file = 'bess_bifurcation_pcascade.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {output_file}")

if __name__ == '__main__':
    run_sweep()
