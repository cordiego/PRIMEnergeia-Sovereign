import os
import sys
import logging
from typing import Dict, Any, List

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MFG Bridge] - %(message)s')
logger = logging.getLogger(__name__)

# Add PRIME-Kernel to path
PRIME_KERNEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../PRIME-Kernel'))
if PRIME_KERNEL_PATH not in sys.path:
    sys.path.append(PRIME_KERNEL_PATH)

try:
    from optimization.granas_bayesian import GranasOptimizer as SovereignOptimizer
except ImportError:
    logger.error("Failed to import SovereignOptimizer. Ensure you are running from PRIMEnergeia-Sovereign root.")
    raise

try:
    from prime_kernel.granas_optimization import GranasOptimizer as KernelOptimizer
except ImportError:
    logger.error(f"Failed to import KernelOptimizer from PRIME-Kernel at {PRIME_KERNEL_PATH}.")
    raise

class GranasMFGBridge:
    """
    Bridge connecting PRIMEnergeia-Sovereign's fast surrogate Bayesian Optimizer 
    with PRIME-Kernel's rigorous HJB Mean Field Game (MFG) Optuna Optimizer.
    """
    
    def __init__(self, bayesian_calls: int = 50, optuna_trials: int = 10, output_dir: str = "granas_results"):
        self.bayesian_calls = bayesian_calls
        self.optuna_trials = optuna_trials
        self.output_dir = output_dir

    def execute_bridge(self) -> Dict[str, Any]:
        """
        Executes the bridged optimization pipeline:
        1. Surrogate-based Bayesian search
        2. Export CSV
        3. Multi-objective Optuna search with HJB MFG evaluation
        """
        logger.info("=====================================================")
        logger.info(" STEP 1: Sovereign Bayesian Optimizer (Surrogate)")
        logger.info("=====================================================")
        
        # 1. Run Bayesian Optimization
        sov_opt = SovereignOptimizer(
            n_calls=self.bayesian_calls,
            n_initial=max(2, min(8, self.bayesian_calls)), # reasonable initial points
            output_dir=self.output_dir
        )
        
        # Warm start logic could be added here if needed
        sov_opt.run()
        
        # The SovereignOptimizer automatically exports to 'granas_experiment_log.csv' 
        # in the specified output directory.
        csv_path = os.path.join(self.output_dir, "granas_experiment_log.csv")
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Expected surrogate results at {csv_path} but file was not created.")
            
        logger.info(f"Surrogate optimization completed. Results saved to {csv_path}.")
        
        logger.info("=====================================================")
        logger.info(" STEP 2: PRIME-Kernel Optuna Optimizer (MFG)")
        logger.info("=====================================================")
        
        # 2. Run MFG Optuna Multi-Objective Optimization
        kernel_opt = KernelOptimizer(log_path=csv_path)
        
        # Run Optuna using the historical points from the CSV as seeds
        results = kernel_opt.run_optimization(n_trials=self.optuna_trials)
        
        logger.info("=====================================================")
        logger.info(" BRIDGE EXECUTION COMPLETE")
        logger.info("=====================================================")
        
        return results

if __name__ == "__main__":
    # Example usage
    bridge = GranasMFGBridge(bayesian_calls=10, optuna_trials=5)
    pareto_front_results = bridge.execute_bridge()
    print("\n--- FINAL ROBUST PARETO FRONTIER ---")
    for i, res in enumerate(pareto_front_results.get('pareto_front', [])):
        print(f"Policy {i+1} | Stability: {res['stability_score']:.4f} | Defects: {res['defect_density']:.4f}")
        for k, v in res['params'].items():
            print(f"  {k}: {v:.4f}")
