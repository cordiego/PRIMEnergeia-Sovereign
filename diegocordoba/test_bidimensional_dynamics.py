import numpy as np
import sys
import os

sys.path.append(os.path.abspath('/Users/diegocordoba/diegocordoba'))
from hjb_solver_fortified import BidimensionalSovereignDynamics

def run_test():
    dyn = BidimensionalSovereignDynamics()
    state = np.array([0.0, 50.0, 0.284])  # df=0, P=50, PCE=28.4%
    control = 5.0  # MW/s
    dt = 2.0
    
    new_state = dyn.step(state, control, dt)
    print("New state:", new_state)
    
    diff = dyn.diffusion(state)
    print("Diffusion:", diff)
    
    cost = dyn.running_cost(state, control)
    print("Running cost:", cost)
    
    # Test terminal cost with PCE below threshold
    term_cost_low = dyn.terminal_cost(state)
    print("Terminal cost (low PCE):", term_cost_low)
    
    # Test terminal cost with PCE above threshold (e.g. 50%)
    state_high = np.array([0.0, 50.0, 0.50])
    term_cost_high = dyn.terminal_cost(state_high)
    print("Terminal cost (high PCE):", term_cost_high)
    print("Success!")

if __name__ == '__main__':
    run_test()
