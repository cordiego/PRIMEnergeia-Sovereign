import numpy as np
import matplotlib.pyplot as plt
import time

class TrueSPDEGridSolver:
    def __init__(self, nx=100, nt=300, synch_coeff=0.02, damping=0.1, length=100.0, t_max=5.0):
        self.nx = nx
        self.nt = nt
        self.dx = length / (nx - 1)
        self.dt = t_max / nt
        self.synch_coeff = synch_coeff
        self.damping = damping
        self.x = np.linspace(0, length, nx)
        self.f_dev = np.zeros(nx)
        
    def step(self, f_dev_prev, use_stochastic_bess=False, bess_noise_amp=0.0):
        f_next = np.zeros_like(f_dev_prev)
        # Multiplicative Itô noise: bess_noise_amp * f * dW
        # The Itô-Stratonovich correction effectively adds damping: -0.5 * sigma^2 * f
        dW = np.random.normal(0, np.sqrt(self.dt), self.nx)
        bess_action = bess_noise_amp * f_dev_prev * dW if use_stochastic_bess else np.zeros(self.nx)
            
        for i in range(1, self.nx - 1):
            diffusion = self.synch_coeff * (f_dev_prev[i+1] - 2*f_dev_prev[i] + f_dev_prev[i-1]) / (self.dx**2)
            damp = -self.damping * f_dev_prev[i]
            cascade_force = 0
            if f_dev_prev[i] < -0.5:
                cascade_force = -0.5 * (f_dev_prev[i]**2)
                # REMOVED: if use_stochastic_bess: cascade_force *= 0.2
                
            f_next[i] = f_dev_prev[i] + self.dt * (diffusion + damp + cascade_force) + bess_action[i]
            
        f_next[0], f_next[-1] = f_next[1], f_next[-2]
        return f_next

    def simulate(self, disturbance, use_stochastic_bess=False, bess_noise_amp=0.0):
        self.f_dev = disturbance(self.x)
        history = [self.f_dev.copy()]
        for _ in range(self.nt):
            self.f_dev = self.step(self.f_dev, use_stochastic_bess, bess_noise_amp)
            if np.any(self.f_dev < -10.0) or np.any(np.isnan(self.f_dev)): break
            history.append(self.f_dev.copy())
        return np.array(history)

def run_sweep():
    # We want to see if noise can prevent the cascade (P -> 0 at high amp)
    # and if P -> 1 as amp -> 0 (Singular limit)
    amps = np.linspace(3.0, 0.0, 40)
    n_scenarios = 100
    p_cascade = []
    
    disturbance = lambda x: -0.55 * np.exp(-((x - 50)**2) / 10)
    
    print("Starting TRUE BESS amplitude sweep (no artificial suppression)...")
    start_time = time.time()
    
    for amp in amps:
        cascades = 0
        for s in range(n_scenarios):
            solver = TrueSPDEGridSolver(damping=0.1)
            hist = solver.simulate(disturbance, use_stochastic_bess=True, bess_noise_amp=amp)
            
            if len(hist) < solver.nt + 1 or np.any(hist[-1] < -10.0) or np.any(np.isnan(hist[-1])):
                cascades += 1
                
        p_cascade.append(cascades / n_scenarios)
        print(f"Amp: {amp:.3f} | P(cascade): {p_cascade[-1]:.2f}")
        
    print(f"Sweep completed in {time.time() - start_time:.2f} seconds.")

if __name__ == '__main__':
    run_sweep()
