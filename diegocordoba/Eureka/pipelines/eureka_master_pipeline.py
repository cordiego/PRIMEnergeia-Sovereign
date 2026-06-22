#!/usr/bin/env python3
"""
Eureka Master Orchestrator Pipeline
===================================
Runs all Eureka Advanced Intelligence modules and merges their outputs
into a single master signal file for `Eureka.R` to consume.

Usage:
    python eureka_master_pipeline.py
"""

import os
import sys
import pandas as pd
import logging
from datetime import datetime

# Import the specific module functions
from eureka_macro_liquidity import generate_net_liquidity
from eureka_insider_tracker import generate_insider_signals
from eureka_options_flow import generate_options_flow
from eureka_microstructure import generate_microstructure_signals

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Master-Pipeline] - %(message)s')
logger = logging.getLogger(__name__)

def run_all_pipelines():
    """Execute all pipelines and merge the resulting signals into a master CSV."""
    out_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info("Starting Eureka Master Pipeline Execution...")
    
    # 1. Run Macro Liquidity
    liq_file = generate_net_liquidity(days_history=365, out_dir=out_dir)
    
    # 2. Run Options Flow
    opt_file = generate_options_flow(days_history=365, out_dir=out_dir)
    
    # 3. Run Microstructure for SPY
    mic_file = generate_microstructure_signals(ticker="SPY", days_history=60, out_dir=out_dir)
    
    # 4. Run Insider Tracker (for SPY / target portfolio)
    target_tickers = ["SPY", "QQQ", "SCHD", "AXP", "AAPL"]
    ins_file = generate_insider_signals(tickers=target_tickers, days_history=60, out_dir=out_dir)
    
    logger.info("All individual pipelines completed. Merging signals...")
    
    # Load all generated CSVs
    try:
        df_liq = pd.read_csv(liq_file)
        df_opt = pd.read_csv(opt_file)
        df_mic = pd.read_csv(mic_file)
        df_ins = pd.read_csv(ins_file)
        
        # Ensure 'date' columns are datetime objects for merging
        for df in [df_liq, df_opt, df_mic, df_ins]:
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime('%Y-%m-%d')
                
        # To merge insider data (which has 'ticker'), we'll aggregate it to a daily macro level
        # E.g., How many total cluster buys happened across our target universe today?
        df_ins_agg = df_ins.groupby("date")["CLUSTER_BUY_SIGNAL"].sum().reset_index()
        df_ins_agg.rename(columns={"CLUSTER_BUY_SIGNAL": "TOTAL_CLUSTER_BUYS"}, inplace=True)
        
        # We use Options Flow as the base, since it usually runs every business day
        master_df = df_opt.copy()
        
        # Merge Liquidity
        master_df = pd.merge(master_df, df_liq[["date", "NET_LIQUIDITY_B", "RISK_ON_LIQUIDITY"]], on="date", how="left")
        
        # Merge Microstructure
        master_df = pd.merge(master_df, df_mic[["date", "VPIN_PROXY", "HIGH_TOXICITY_FLAG"]], on="date", how="left")
        
        # Merge Insider Tracker
        master_df = pd.merge(master_df, df_ins_agg, on="date", how="left")
        master_df["TOTAL_CLUSTER_BUYS"].fillna(0, inplace=True)
        
        # Forward fill any missing macro metrics (e.g. if liquidity hasn't updated today)
        master_df.ffill(inplace=True)
        
        # Generate the Eureka Master "Rock Solid" Recommendation
        # 1. Do NOT buy if we are in negative gamma and highly toxic
        # 2. DO NOT sell the dip if liquidity is expanding and negative gamma is false
        master_df["EUREKA_AVOID_CRASH_FLAG"] = (master_df["NEGATIVE_GAMMA_REGIME"] == True) & (master_df["HIGH_TOXICITY_FLAG"] == True)
        master_df["EUREKA_BUY_THE_DIP_FLAG"] = (master_df["DIP_BUY_SAFE"] == True) & (master_df["RISK_ON_LIQUIDITY"] == True) & (master_df["TOTAL_CLUSTER_BUYS"] > 0)
        
        master_out = os.path.join(out_dir, "eureka_master_signals.csv")
        master_df.to_csv(master_out, index=False)
        logger.info(f"Successfully generated MASTER signal file: {master_out}")
        
    except Exception as e:
        logger.error(f"Failed to merge master pipeline: {e}")
        sys.exit(1)
        
    logger.info("Eureka Master Pipeline Execution Complete.")

if __name__ == "__main__":
    run_all_pipelines()
