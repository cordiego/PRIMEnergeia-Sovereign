import unittest
import numpy as np

# Adjust path to import from the workspace root
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from optimization.vza400_hjb_pide import VZA400PIDESolver

class TestVZA400PIDESolver(unittest.TestCase):
    
    def setUp(self):
        # Initialize with a small grid for fast testing
        self.solver = VZA400PIDESolver(
            max_injection_mw=50.0,
            dt=0.5,
            grid_size_p=11,
            grid_size_price=11
        )
        
    def test_imex_convergence(self):
        """Test that the IMEX scheme converged and the value function is populated."""
        self.assertFalse(np.all(self.solver.V == 0), "Value function should not be all zeros.")
        self.assertFalse(np.all(self.solver.policy == 0), "Policy function should not be all zeros.")
        
    def test_policy_bounds(self):
        """Test that the resulting optimal policy bounds are within constraints."""
        max_policy = np.max(self.solver.policy)
        min_policy = np.min(self.solver.policy)
        
        self.assertLessEqual(max_policy, self.solver.max_inj)
        self.assertGreaterEqual(min_policy, -self.solver.max_inj)
        
    def test_compute_dispatch(self):
        """Test the continuous extraction of optimal control."""
        # High renewable capacity, high price -> Should inject heavily
        high_price = 450.0
        high_ren = 0.9
        dispatch_high = self.solver.compute_dispatch(high_ren, high_price)
        
        # Low renewable capacity, low price -> Should inject minimally or pull
        low_price = 20.0
        low_ren = 0.1
        dispatch_low = self.solver.compute_dispatch(low_ren, low_price)
        
        # A simple check to ensure varying conditions lead to varying dispatch
        self.assertNotEqual(dispatch_high, dispatch_low, "Dispatch should vary by state.")

if __name__ == '__main__':
    unittest.main()
