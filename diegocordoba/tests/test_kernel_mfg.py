import unittest
import numpy as np

# Adjust path to import from the workspace root
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from granas_module.kernel_mfg_ev import KernelMMD_MFG_Solver

class TestKernelMMD_MFG(unittest.TestCase):
    
    def setUp(self):
        # Small horizon and grid for fast tests
        self.solver = KernelMMD_MFG_Solver(
            num_evs=10,
            grid_capacity_mw=2.0,
            time_horizon=5,
            kernel_bandwidth=1.0,
            mmd_penalty_weight=10.0
        )
        # Reduce state grid size to speed up
        self.solver.state_grid_size = 10
        self.solver.soc_grid = np.linspace(0.0, 1.0, 10)
        self.solver.rho = np.ones((5, 10)) / 10
        self.solver.rho_target = np.zeros(10)
        self.solver.rho_target[-1] = 1.0 
        
    def test_mmd_penalty(self):
        """Test MMD calculation."""
        current_rho = np.zeros(10)
        current_rho[0] = 1.0 # Far from target
        
        penalty_far = self.solver.compute_mmd_penalty(current_rho, self.solver.rho_target)
        
        current_rho_near = np.zeros(10)
        current_rho_near[-2] = 1.0 # Near target
        
        penalty_near = self.solver.compute_mmd_penalty(current_rho_near, self.solver.rho_target)
        
        self.assertGreater(penalty_far, penalty_near, "MMD penalty should be higher when distributions are further apart.")
        
    def test_schrodinger_bridge(self):
        """Test the Schrödinger bridge convergence."""
        results = self.solver.solve_schrodinger_bridge(max_iters=10)
        
        self.assertIn("final_mmd_penalty", results)
        self.assertIn("density_evolution", results)
        self.assertIn("convergence_diff", results)
        
        # Verify density constraints
        for t in range(self.solver.T):
            density_sum = np.sum(results["density_evolution"][t])
            self.assertAlmostEqual(density_sum, 1.0, places=4, msg=f"Density at t={t} does not sum to 1")

if __name__ == '__main__':
    unittest.main()
