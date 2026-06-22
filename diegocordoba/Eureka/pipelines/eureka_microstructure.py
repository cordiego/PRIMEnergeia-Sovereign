#!/usr/bin/env python3
"""
Eureka Microstructure Pipeline
=================================
Calculates a proxy for Volume-Synchronized Probability of Informed Trading (VPIN).
High VPIN indicates informed institutional traders are aggressively taking liquidity.

Usage:
    python eureka_microstructure.py
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

try:
    import yfinance as yf
except ImportError:
    yf = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Microstructure] - %(message)s')
logger = logging.getLogger(__name__)

def generate_microstructure_signals(ticker: str = "SPY", days_history: int = 60, out_dir: str = ".") -> str:
    """Fetch recent OHLCV data and estimate VPIN (Toxicity)."""
    
    if not yf:
        logger.warning("yfinance not installed. Generating synthetic microstructure data.")
        return generate_synthetic_microstructure(ticker, days_history, out_dir)
        
    start_date = (datetime.now() - timedelta(days=days_history)).strftime("%Y-%m-%d")
    logger.info(f"Fetching OHLCV data for {ticker}...")
    
    try:
        # Download hourly data to get better microstructure approximations
        df = yf.download(ticker, start=start_date, interval="1h", progress=False)
        
        if df.empty:
            raise ValueError(f"No data returned from yfinance for {ticker}")
            
        # Standardize columns
        # Depending on yfinance version, columns might be multi-index
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Calculate simplified VPIN proxy (Order Flow Toxicity)
        # We estimate Buy Volume vs Sell Volume based on where the Close is relative to High/Low
        df["PRICE_RANGE"] = df["High"] - df["Low"]
        
        # Avoid division by zero
        df["PRICE_RANGE"] = df["PRICE_RANGE"].replace(0, 0.001)
        
        # Proportion of volume that was "buy" volume (rough proxy)
        df["BUY_VOL_RATIO"] = (df["Close"] - df["Low"]) / df["PRICE_RANGE"]
        df["BUY_VOL"] = df["Volume"] * df["BUY_VOL_RATIO"]
        df["SELL_VOL"] = df["Volume"] * (1 - df["BUY_VOL_RATIO"])
        
        # Aggregate to Daily
        daily_df = df.groupby(df.index.date).agg({
            "Close": "last",
            "Volume": "sum",
            "BUY_VOL": "sum",
            "SELL_VOL": "sum"
        }).reset_index()
        daily_df.rename(columns={"index": "date"}, inplace=True)
        
        # VPIN proxy: Absolute Order Imbalance / Total Volume
        daily_df["ORDER_IMBALANCE"] = abs(daily_df["BUY_VOL"] - daily_df["SELL_VOL"])
        daily_df["VPIN_PROXY"] = daily_df["ORDER_IMBALANCE"] / daily_df["Volume"]
        
        # Smooth VPIN
        daily_df["VPIN_5D_MA"] = daily_df["VPIN_PROXY"].rolling(window=5).mean()
        
        # High Toxicity Flag (If VPIN is higher than its 20-day mean + 1 standard deviation)
        vpin_mean = daily_df["VPIN_PROXY"].rolling(window=20).mean()
        vpin_std = daily_df["VPIN_PROXY"].rolling(window=20).std()
        
        daily_df["HIGH_TOXICITY_FLAG"] = daily_df["VPIN_PROXY"] > (vpin_mean + vpin_std)
        
        out_path = os.path.join(out_dir, f"microstructure_{ticker}.csv")
        daily_df.to_csv(out_path, index=False)
        logger.info(f"Successfully generated Microstructure Signals: {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"Failed to calculate VPIN from market data: {e}. Falling back to proxy.")
        return generate_synthetic_microstructure(ticker, days_history, out_dir)

def generate_synthetic_microstructure(ticker: str, days_history: int, out_dir: str) -> str:
    """Generates synthetic order flow toxicity data."""
    start_date = (datetime.now() - timedelta(days=days_history)).strftime("%Y-%m-%d")
    dates = pd.date_range(start=start_date, end=datetime.now(), freq="B")
    n = len(dates)
    
    # Synthetic VPIN oscillating between 0.1 and 0.4
    vpin = 0.25 + np.sin(np.linspace(0, 20, n)) * 0.1 + np.random.normal(0, 0.05, n)
    vpin = np.clip(vpin, 0.05, 0.6)
    
    df = pd.DataFrame({
        "date": dates,
        "Close": 500 + np.cumsum(np.random.normal(0, 5, n)),
        "Volume": np.random.randint(40_000_000, 100_000_000, n),
        "VPIN_PROXY": np.round(vpin, 3)
    })
    
    df["VPIN_5D_MA"] = df["VPIN_PROXY"].rolling(window=5).mean()
    
    vpin_mean = df["VPIN_PROXY"].rolling(window=20).mean()
    vpin_std = df["VPIN_PROXY"].rolling(window=20).std()
    df["HIGH_TOXICITY_FLAG"] = df["VPIN_PROXY"] > (vpin_mean + vpin_std)
    
    out_path = os.path.join(out_dir, f"microstructure_{ticker}.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated synthetic Microstructure Signals: {out_path}")
    return out_path

if __name__ == "__main__":
    out_directory = os.path.dirname(os.path.abspath(__file__))
    generate_microstructure_signals(ticker="SPY", days_history=60, out_dir=out_directory)
