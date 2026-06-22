#!/usr/bin/env python3
"""
Eureka Macro Liquidity Pipeline
=================================
Calculates Central Bank Net Liquidity based on the formula:
Net Liquidity = Fed Balance Sheet (WALCL) - Treasury General Account (WTREGEN) - Reverse Repo (RRPONTSYD)

Usage:
    export FRED_API_KEY="your_api_key_here"
    python eureka_macro_liquidity.py
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Macro-Liquidity] - %(message)s')
logger = logging.getLogger(__name__)

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

def fetch_fred_series(series_id: str, api_key: str, start_date: str) -> pd.Series:
    """Fetch a data series from FRED API."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "frequency": "w" if series_id == "WALCL" else "d" # WALCL is weekly
    }
    
    response = requests.get(FRED_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    
    observations = data.get("observations", [])
    if not observations:
        logger.warning(f"No observations returned for {series_id}")
        return pd.Series(dtype=float)
        
    dates = []
    values = []
    for obs in observations:
        val = obs.get("value", ".")
        if val != ".":
            dates.append(obs["date"])
            # FRED values are in millions or billions depending on series.
            # WALCL: Millions of Dollars
            # WTREGEN: Billions of Dollars (Wait, WTREGEN is millions)
            # RRPONTSYD: Billions of Dollars
            # Let's standardize everything to Billions.
            
            raw_val = float(val)
            if series_id in ["WALCL", "WTREGEN"]:
                values.append(raw_val / 1000.0) # Convert Millions to Billions
            else:
                values.append(raw_val) # Already in Billions
                
    df = pd.DataFrame({"date": pd.to_datetime(dates), series_id: values})
    df.set_index("date", inplace=True)
    return df[series_id]

def generate_net_liquidity(days_history: int = 365, out_dir: str = ".") -> str:
    """Calculate Net Liquidity and save to CSV."""
    api_key = os.environ.get("FRED_API_KEY")
    
    start_date = (datetime.now() - timedelta(days=days_history)).strftime("%Y-%m-%d")
    
    if not api_key:
        logger.warning("FRED_API_KEY environment variable not set. Generating synthetic proxy data for demonstration.")
        return generate_synthetic_liquidity(start_date, out_dir)
        
    logger.info(f"Fetching macro liquidity data from {start_date}...")
    
    try:
        walcl = fetch_fred_series("WALCL", api_key, start_date)
        wtregen = fetch_fred_series("WTREGEN", api_key, start_date)
        rrpontsyd = fetch_fred_series("RRPONTSYD", api_key, start_date)
        
        # Merge all series. Forward fill weekly WALCL to daily
        df = pd.DataFrame({"WALCL": walcl, "WTREGEN": wtregen, "RRPONTSYD": rrpontsyd})
        df.sort_index(inplace=True)
        df.ffill(inplace=True) # Forward fill weekly data
        df.dropna(inplace=True) # Drop early rows missing data
        
        # Calculate Net Liquidity
        df["NET_LIQUIDITY_B"] = df["WALCL"] - df["WTREGEN"] - df["RRPONTSYD"]
        
        # Calculate Rate of Change (Liquidity Momentum)
        df["LIQ_MOMENTUM_4W"] = df["NET_LIQUIDITY_B"].diff(20) # Approx 4 weeks
        
        # Risk Signal: True if Liquidity is expanding (Momentum > 0)
        df["RISK_ON_LIQUIDITY"] = df["LIQ_MOMENTUM_4W"] > 0
        
        out_path = os.path.join(out_dir, "macro_liquidity.csv")
        df.reset_index().to_csv(out_path, index=False)
        logger.info(f"Successfully generated Net Liquidity: {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Failed to fetch real FRED data: {e}. Falling back to proxy.")
        return generate_synthetic_liquidity(start_date, out_dir)

def generate_synthetic_liquidity(start_date: str, out_dir: str) -> str:
    """Generates synthetic data for testing if no API key is present."""
    import numpy as np
    dates = pd.date_range(start=start_date, end=datetime.now(), freq="B")
    n = len(dates)
    
    # Synthetic realistic base values in Billions
    walcl = 7500.0 + np.cumsum(np.random.normal(-5, 10, n))
    wtregen = 700.0 + np.cumsum(np.random.normal(0, 20, n))
    rrpontsyd = 400.0 + np.cumsum(np.random.normal(-2, 15, n))
    
    # Bound to realistic constraints
    wtregen = np.clip(wtregen, 100, 1000)
    rrpontsyd = np.clip(rrpontsyd, 0, 2500)
    
    df = pd.DataFrame({
        "date": dates,
        "WALCL": np.round(walcl, 2),
        "WTREGEN": np.round(wtregen, 2),
        "RRPONTSYD": np.round(rrpontsyd, 2)
    })
    
    df["NET_LIQUIDITY_B"] = df["WALCL"] - df["WTREGEN"] - df["RRPONTSYD"]
    df["LIQ_MOMENTUM_4W"] = df["NET_LIQUIDITY_B"].diff(20)
    df["RISK_ON_LIQUIDITY"] = df["LIQ_MOMENTUM_4W"] > 0
    
    out_path = os.path.join(out_dir, "macro_liquidity.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated synthetic Net Liquidity: {out_path}")
    return out_path

if __name__ == "__main__":
    out_directory = os.path.dirname(os.path.abspath(__file__))
    generate_net_liquidity(days_history=365, out_dir=out_directory)
