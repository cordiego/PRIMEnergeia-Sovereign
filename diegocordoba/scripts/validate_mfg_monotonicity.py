import sys
import os
import numpy as np
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from granas_module.kernel_mfg_ev import KernelMMD_MFG_Solver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MFG Monotonicity] - %(message)s')
logger = logging.getLogger(__name__)

def validate_monotonicity(num_tests=100):
    logger.info("Initializing KernelMMD_MFG_Solver to validate Lasry-Lions monotonicity condition.")
    solver = KernelMMD_MFG_Solver(num_evs=100, grid_capacity_mw=5.0)
    K = solver._gaussian_kernel(solver.soc_grid, solver.soc_grid)
    
    violations = 0
    min_val = np.inf
    
    logger.info(f"Running {num_tests} randomized tests on empirical density measures.")
    for i in range(num_tests):
        # Generate two random valid probability densities
        rho1 = np.random.dirichlet(np.ones(solver.state_grid_size))
        rho2 = np.random.dirichlet(np.ones(solver.state_grid_size))
        
        # Calculate functional derivative F(rho) = 2 * K @ (rho - rho_target)
        # Note: We omit lambda_mmd as it's a positive scalar
        F_rho1 = 2 * K @ (rho1 - solver.rho_target)
        F_rho2 = 2 * K @ (rho2 - solver.rho_target)
        
        # Lasry-Lions Monotonicity Condition:
        # < F(rho1) - F(rho2), rho1 - rho2 > >= 0
        diff_F = F_rho1 - F_rho2
        diff_rho = rho1 - rho2
        
        inner_product = np.dot(diff_rho, diff_F)
        
        if inner_product < 0:
            if np.isclose(inner_product, 0, atol=1e-10):
                # Within floating point tolerance
                pass
            else:
                violations += 1
                
        if inner_product < min_val:
            min_val = inner_product
            
    logger.info(f"Tests Completed. Violations: {violations}")
    logger.info(f"Minimum inner product observed: {min_val:.6e}")
    
    if violations == 0:
        logger.info("SUCCESS: The Kernel-MMD penalty satisfies the Lasry-Lions monotonicity condition.")
        logger.info("The Mean Field Game admits a UNIQUE solution under this coupling cost.")
    else:
        logger.error("FAILURE: Monotonicity condition violated. Uniqueness is not guaranteed.")

if __name__ == "__main__":
    validate_monotonicity()
