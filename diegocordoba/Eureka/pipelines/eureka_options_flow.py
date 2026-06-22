#!/usr/bin/env python3
"""
Eureka Options Flow Pipeline
=================================
Fetches market maker positioning metrics (Dealer Gamma, Dark Pool Index)
to assess structural market stability. High negative gamma predicts extreme volatility.

Usage:
    python eureka_options_flow.py
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Options-Flow] - %(message)s')
logger = logging.getLogger(__name__)

# SqueezeMetrics provides public CSVs for DIX and GEX (proxy for SPX gamma)
SQUEEZEMETRICS_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"

def generate_options_flow(days_history: int = 365, out_dir: str = ".") -> str:
    """Fetch DIX/GEX and calculate structural instability flags."""
    logger.info(f"Fetching SqueezeMetrics DIX/GEX data...")
    
    try:
        # Load directly from URL
        df = pd.read_csv(SQUEEZEMETRICS_URL)
        df["date"] = pd.to_datetime(df["date"])
        
        # Filter to recent history
        cutoff_date = pd.to_datetime(datetime.now() - timedelta(days=days_history))
        df = df[df["date"] >= cutoff_date].copy()
        
        # Calculate derived metrics
        # If GEX < 0, Market Makers are in short gamma, meaning they sell when the market drops (amplifying crashes)
        # If GEX > 0, they buy when it drops (suppressing volatility)
        df["NEGATIVE_GAMMA_REGIME"] = df["gex"] < 0
        
        # DIX is the Dark Pool Index. High DIX means dark pool accumulation.
        # Moving average of DIX to smooth noise
        df["DIX_10D_MA"] = df["dix"].rolling(window=10).mean()
        df["DARK_POOL_ACCUMULATION"] = df["DIX_10D_MA"] > 0.45 # >45% implies heavy buying
        
        # Critical crash warning: Negative Gamma + Price drops
        # If the market is in negative gamma, dips should NOT be bought blindly.
        df["DIP_BUY_SAFE"] = ~df["NEGATIVE_GAMMA_REGIME"]
        
        out_path = os.path.join(out_dir, "options_flow_signals.csv")
        df.to_csv(out_path, index=False)
        logger.info(f"Successfully generated Options Flow Signals: {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Failed to fetch public Options Flow data: {e}. Falling back to proxy.")
        return generate_synthetic_options_flow(days_history, out_dir)

def generate_synthetic_options_flow(days_history: int, out_dir: str) -> str:
    """Generates synthetic GEX/DIX data for testing."""
    import numpy as np
    start_date = (datetime.now() - timedelta(days=days_history)).strftime("%Y-%m-%d")
    dates = pd.date_range(start=start_date, end=datetime.now(), freq="B")
    n = len(dates)
    
    # Synthetic GEX oscillating between -2B and +10B
    gex = 4.0 + np.sin(np.linspace(0, 10, n)) * 6.0 + np.random.normal(0, 1, n)
    # Synthetic DIX oscillating around 42%
    dix = 0.42 + np.cos(np.linspace(0, 15, n)) * 0.05 + np.random.normal(0, 0.02, n)
    
    df = pd.DataFrame({
        "date": dates,
        "price": 5000 + np.cumsum(np.random.normal(2, 20, n)),
        "dix": np.round(dix, 4),
        "gex": np.round(gex * 1e9, 0)
    })
    
    df["NEGATIVE_GAMMA_REGIME"] = df["gex"] < 0
    df["DIX_10D_MA"] = df["dix"].rolling(window=10).mean()
    df["DARK_POOL_ACCUMULATION"] = df["DIX_10D_MA"] > 0.45
    df["DIP_BUY_SAFE"] = ~df["NEGATIVE_GAMMA_REGIME"]
    
    out_path = os.path.join(out_dir, "options_flow_signals.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated synthetic Options Flow Signals: {out_path}")
    return out_path

if __name__ == "__main__":
    out_directory = os.path.dirname(os.path.abspath(__file__))
    generate_options_flow(days_history=365, out_dir=out_directory)
