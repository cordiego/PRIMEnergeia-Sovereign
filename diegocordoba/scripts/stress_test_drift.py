import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.eureka_math import compute_dynamic_regime_weights

EUREKA_UNIVERSE = ["SNXX", "SNDK", "SCHD"]
CRISIS_ANCHOR = "SCHD"
DEADBAND_THRESHOLD = 0.025

# Baseline Kelly weights (assuming equal weight for testing if not calculated)
kelly_weights = {"SNXX": 0.4, "SNDK": 0.4, "SCHD": 0.2}

def stress_test():
    print("--- EUREKA DRIFT LOGIC STRESS TEST ---")
    print(f"Deadband Threshold: {DEADBAND_THRESHOLD * 100}%\n")
    
    # Simulate VIX moving from 15 (Risk-On) to 35 (Crisis)
    vix_scenarios = np.linspace(15, 35, 21)
    
    # Initial portfolio matches Kelly exactly (VIX=15)
    current_weights = compute_dynamic_regime_weights(15.0, kelly_weights, EUREKA_UNIVERSE, CRISIS_ANCHOR)
    
    trades_triggered = 0
    total_turnover = 0.0
    
    print(f"{'VIX':<6} | {'SNXX Wgt':<10} | {'SNDK Wgt':<10} | {'SCHD Wgt':<10} | {'Max Drift':<10} | {'Trade?':<6}")
    print("-" * 70)
    
    for vix in vix_scenarios:
        target_weights = compute_dynamic_regime_weights(vix, kelly_weights, EUREKA_UNIVERSE, CRISIS_ANCHOR)
        
        # Calculate max drift
        drifts = {tk: abs(target_weights[tk] - current_weights[tk]) for tk in EUREKA_UNIVERSE}
        max_drift = max(drifts.values())
        
        trade = max_drift > DEADBAND_THRESHOLD
        
        if trade:
            trades_triggered += 1
            # Rebalance to target
            total_turnover += sum(drifts.values()) / 2.0  # one-way turnover
            current_weights = target_weights.copy()
            
        trade_str = "YES" if trade else "NO"
        
        print(f"{vix:<6.1f} | {target_weights['SNXX']:<10.3f} | {target_weights['SNDK']:<10.3f} | {target_weights['SCHD']:<10.3f} | {max_drift:<10.3f} | {trade_str:<6}")

    print("-" * 70)
    print(f"Total Rebalances Triggered: {trades_triggered}")
    print(f"Total Portfolio Turnover: {total_turnover:.2%}")

if __name__ == '__main__':
    stress_test()
