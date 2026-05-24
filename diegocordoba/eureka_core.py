import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import time
import sys

# Set non-interactive backend for Mac Terminal
plt.switch_backend('Agg')

def main():
    print("\n" + "="*50)
    print("   EUREKA 2.3: MULTI-INDEX CORE ENGINE (IAU/GEV)   ")
    print("="*50)
    
    # Your specific universe + VIXM & SPY (Benchmark)
    tickers = ["SNDK", "SNXX", "CASH", "SPY", "^VIX"]
    all_data = []

    print("[*] Downloading Core Universe Assets (Staggered)...")
    
    for t in tickers:
        try:
            # GEV started in April 2024; we fetch from there
            df_tick = yf.download(t, start="2024-04-02", progress=False)
            
            if df_tick.empty:
                print(f" [!] Warning: No data for {t}")
                continue
            
            # 2026 FIX: Handle MultiIndex columns by selecting 'Close' and the Ticker
            # This flattens the Yahoo Finance 2026 data structure
            if isinstance(df_tick.columns, pd.MultiIndex):
                s = df_tick['Close'][t]
            else:
                s = df_tick['Close']
                
            s.name = t
            all_data.append(s)
            print(f" [+] {t} Loaded: {len(s)} days.")
            time.sleep(1.5) 
            
        except Exception as e:
            print(f" [!] Failed {t}: {e}")

    if not all_data:
        print("\n[!!] FATAL: All downloads failed. Check internet/yfinance version."); sys.exit(1)

    # Align assets into a single DataFrame
    df = pd.concat(all_data, axis=1).dropna()
    
    if df.empty or "^VIX" not in df.columns:
        print("\n[!!] FATAL: Zero overlapping trading days found. Check GEV/VIXM."); sys.exit(1)

    print(f"[*] Total overlapping trading days: {len(df)}")
    
    returns = df.pct_change().dropna()
    port_returns = []

    for i in range(len(returns)):
        # Classification based on VIX Level
        v = df['^VIX'].iloc[i+1]
        
        if v < 18:
            # Risk-On: Focus on IAU/GEV
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        elif 18 <= v <= 28:
            # Transition: Balanced
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        else:
            # Crisis: High VIXM/Cash protection
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        
        day_ret = sum(returns[tk].iloc[i] * w.get(tk, 0) for tk in w if tk in returns.columns)
        port_returns.append(day_ret)

    # Finalize Series and Benchmarks
    port_series = pd.Series(port_returns, index=returns.index)
    cum_returns = (1 + port_series).cumprod()
    spy_cum = (1 + returns['SPY']).cumprod()
    
    print("\n" + "-"*30)
    print(f"Current VIX:   {df['^VIX'].iloc[-1]:.2f}")
    print(f"Portfolio Return: {((cum_returns.iloc[-1]-1)*100):.2f}%")
    print(f"Max Drawdown:  {(cum_returns / cum_returns.cummax() - 1).min():.2%}")
    print("-"*30)
    
    # Visualization
    plt.style.use('dark_background')
    plt.figure(figsize=(10,6))
    plt.plot(cum_returns, label='Eureka 2.3 (Dynamic IAU/GEV Core)', color='#F1C40F', lw=2)
    plt.plot(spy_cum, label='S&P 500 (SPY)', color='white', alpha=0.3)
    plt.title("Eureka Universe Expansion: Volatility Targeting (2024-2026)")
    plt.legend()
    plt.grid(alpha=0.2)
    plt.savefig('eureka_final.png')
    print("[*] Success. Image: 'eureka_final.png'")

if __name__ == "__main__":
    main()
