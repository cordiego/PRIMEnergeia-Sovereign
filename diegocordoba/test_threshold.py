import numpy as np
from simulate_grid_disturbance import SPDEGridSolver

def test_sigma(sigma):
    solver = SPDEGridSolver(damping=0.1)
    disturbance = lambda x: -0.55 * np.exp(-((x - 50)**2) / 10)
    hist = solver.simulate(disturbance, True, sigma)
    # Check if blew up
    blew_up = np.any(hist[-1] < -10.0) or np.any(np.isnan(hist[-1]))
    return blew_up

# Test around 0.59
for sig in [0.0, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 1.0]:
    blowups = 0
    n_trials = 50
    for _ in range(n_trials):
        if test_sigma(sig):
            blowups += 1
    print(f"Sigma = {sig:.2f}: {blowups}/{n_trials} blowups")

