import os
import sys
import tempfile
import pytest

# Add PRIME-Kernel to path for testing
PRIME_KERNEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../PRIME-Kernel'))
if PRIME_KERNEL_PATH not in sys.path:
    sys.path.append(PRIME_KERNEL_PATH)

SOVEREIGN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SOVEREIGN_PATH not in sys.path:
    sys.path.append(SOVEREIGN_PATH)

from optimization.mfg_bridge import GranasMFGBridge

def test_mfg_bridge_initialization():
    """Test that the bridge initializes correctly with default params."""
    bridge = GranasMFGBridge()
    assert bridge.bayesian_calls == 50
    assert bridge.optuna_trials == 10
    assert bridge.output_dir == "granas_results"

def test_mfg_bridge_execution():
    """
    Test the full end-to-end execution of the bridge.
    We use very small trial counts (2 and 2) to ensure the test runs quickly.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize bridge with minimal trials for testing
        bridge = GranasMFGBridge(bayesian_calls=2, optuna_trials=2, output_dir=temp_dir)
        
        # Execute the bridge
        results = bridge.execute_bridge()
        
        # Verify the Bayesian optimizer produced the CSV
        csv_path = os.path.join(temp_dir, "granas_experiment_log.csv")
        assert os.path.exists(csv_path)
        
        # Verify Optuna returned a valid pareto front
        assert "pareto_front" in results
        assert isinstance(results["pareto_front"], list)
        
        # Verify the structure of the pareto front items if any were returned
        if len(results["pareto_front"]) > 0:
            first_policy = results["pareto_front"][0]
            assert "params" in first_policy
            assert "stability_score" in first_policy
            assert "defect_density" in first_policy
            
            # Verify the parameters include the expected keys
            expected_keys = {"molar_conc", "solvent_ratio", "spin_speed", "additive_pct", "anneal_temp", "anneal_time"}
            assert set(first_policy["params"].keys()) == expected_keys
