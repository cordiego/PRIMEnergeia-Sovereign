#!/usr/bin/env python3
"""
Eureka Insider Tracker Pipeline
=================================
Fetches and aggregates corporate insider trading (Form 4) open market buys.
Highlights "cluster buying" where multiple executives buy stock concurrently.

Usage:
    export FINNHUB_API_KEY="your_api_key_here"
    python eureka_insider_tracker.py
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Insider-Tracker] - %(message)s')
logger = logging.getLogger(__name__)

FINNHUB_URL = "https://finnhub.io/api/v1/stock/insider-transactions"

def generate_insider_signals(tickers: list, days_history: int = 30, out_dir: str = ".") -> str:
    """Fetch insider trades for a list of tickers and aggregate signals."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    start_date = (datetime.now() - timedelta(days=days_history)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    if not api_key:
        logger.warning("FINNHUB_API_KEY not set. Generating synthetic proxy data.")
        return generate_synthetic_insider_data(tickers, start_date, out_dir)
        
    all_trades = []
    
    for ticker in tickers:
        try:
            params = {
                "symbol": ticker,
                "from": start_date,
                "to": end_date,
                "token": api_key
            }
            res = requests.get(FINNHUB_URL, params=params)
            res.raise_for_status()
            data = res.json().get("data", [])
            
            for trade in data:
                # We only care about Open Market BUYS
                if trade.get("transactionCode") == "P": # P = Purchase
                    all_trades.append({
                        "date": trade.get("transactionDate"),
                        "ticker": ticker,
                        "name": trade.get("name"),
                        "shares": trade.get("change"),
                        "price": trade.get("transactionPrice")
                    })
        except Exception as e:
            logger.error(f"Failed fetching insider data for {ticker}: {e}")
            
    if not all_trades:
        logger.info("No open market buys found for the specified tickers in the timeframe.")
        df = pd.DataFrame(columns=["date", "ticker", "unique_buyers", "total_buy_volume_usd", "CLUSTER_BUY_SIGNAL"])
    else:
        df = pd.DataFrame(all_trades)
        df["date"] = pd.to_datetime(df["date"])
        df["volume_usd"] = df["shares"] * df["price"]
        
        # Aggregate by date and ticker
        agg_df = df.groupby(["date", "ticker"]).agg(
            unique_buyers=("name", "nunique"),
            total_buy_volume_usd=("volume_usd", "sum")
        ).reset_index()
        
        # A cluster buy is when 3 or more unique insiders buy on the same day
        agg_df["CLUSTER_BUY_SIGNAL"] = agg_df["unique_buyers"] >= 3
        df = agg_df
        
    out_path = os.path.join(out_dir, "insider_signals.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"Successfully generated Insider Signals: {out_path}")
    return out_path

def generate_synthetic_insider_data(tickers: list, start_date: str, out_dir: str) -> str:
    """Generates synthetic cluster buying data for demonstration."""
    import numpy as np
    dates = pd.date_range(start=start_date, end=datetime.now(), freq="B")
    
    synthetic_records = []
    for date in dates:
        for ticker in tickers:
            # 5% chance of an insider buying event on any given day for a ticker
            if np.random.random() < 0.05:
                unique_buyers = np.random.randint(1, 5)
                volume_usd = np.random.randint(50_000, 2_000_000)
                synthetic_records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "unique_buyers": unique_buyers,
                    "total_buy_volume_usd": volume_usd,
                    "CLUSTER_BUY_SIGNAL": unique_buyers >= 3
                })
                
    df = pd.DataFrame(synthetic_records)
    if df.empty:
        df = pd.DataFrame(columns=["date", "ticker", "unique_buyers", "total_buy_volume_usd", "CLUSTER_BUY_SIGNAL"])
        
    out_path = os.path.join(out_dir, "insider_signals.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated synthetic Insider Signals: {out_path}")
    return out_path

if __name__ == "__main__":
    out_directory = os.path.dirname(os.path.abspath(__file__))
    # Assuming standard portfolio based on earlier PRiME conversations
    target_tickers = ["SPY", "QQQ", "SCHD", "AXP", "AAPL"]
    generate_insider_signals(tickers=target_tickers, days_history=30, out_dir=out_directory)
