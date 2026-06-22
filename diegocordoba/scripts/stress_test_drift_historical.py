import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.eureka_math import compute_dynamic_regime_weights

EUREKA_UNIVERSE = ["SNXX", "SNDK", "SCHD"]
CRISIS_ANCHOR = "SCHD"
DEADBAND_THRESHOLDS = [0.01, 0.025, 0.05, 0.10]

kelly_weights = {"SNXX": 0.4, "SNDK": 0.4, "SCHD": 0.2}

def stress_test_historical():
    print("--- EUREKA DRIFT LOGIC STRESS TEST (HISTORICAL MID/HIGH VIX) ---")
    
    df = yf.download("^VIX", start="2020-02-01", end="2020-06-01", progress=False)
    
    # Handle multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        vix_series = df['Close']['^VIX']
    else:
        vix_series = df['Close']
        
    print(f"Period: 2020-02-01 to 2020-06-01 (Trading Days: {len(vix_series)})")
    print(f"VIX Range: {float(vix_series.min()):.2f} - {float(vix_series.max()):.2f}\n")
    
    for deadband in DEADBAND_THRESHOLDS:
        trades_triggered = 0
        total_turnover = 0.0
        
        current_weights = compute_dynamic_regime_weights(15.0, kelly_weights, EUREKA_UNIVERSE, CRISIS_ANCHOR)
        
        for vix_val in vix_series:
            vix = float(vix_val)
            target_weights = compute_dynamic_regime_weights(vix, kelly_weights, EUREKA_UNIVERSE, CRISIS_ANCHOR)
            
            drifts = {tk: abs(target_weights[tk] - current_weights[tk]) for tk in EUREKA_UNIVERSE}
            max_drift = max(drifts.values())
            
            if max_drift > deadband:
                trades_triggered += 1
                total_turnover += sum(drifts.values()) / 2.0
                current_weights = target_weights.copy()
                
        print(f"Deadband: {deadband*100:5.1f}% | Trades: {trades_triggered:3d} | Total Turnover: {total_turnover:6.2%}")

if __name__ == '__main__':
    stress_test_historical()
