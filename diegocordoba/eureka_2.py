import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import sys

# Suppress annoying warnings
import warnings
warnings.filterwarnings("ignore")

def main():
    print("\n" + "="*50)
    print("   EUREKA 2.0: DYNAMIC VOLATILITY-TARGETING   ")
    print("="*50)
    
    tickers = ["SNDK", "SNXX", "CASH", "SPY", "^VIX"]
    print(f"[*] Downloading: {', '.join(tickers)}...")
    
    # We download individually to avoid the multi-ticker 'Download Failed' bug
    all_data = {}
    for t in tickers:
        try:
            # We add 'auto_adjust=True' to handle the FutureWarning you saw
            d = yf.download(t, start="2022-01-01", progress=False, auto_adjust=True)
            if d.empty:
                print(f"[!] Warning: No data for {t}")
                continue
            all_data[t] = d['Close'] # We explicitly take 'Close'
        except Exception as e:
            print(f"[!] Error on {t}: {e}")

    if not all_data:
        print("[!!] FATAL: No data was downloaded. Check your internet/VPN."); sys.exit(1)

    data = pd.DataFrame(all_data).dropna()
    returns = data.pct_change().dropna()
    vix = data['^VIX']
    
    port_returns = []
    for i in range(len(returns)):
        v = vix.iloc[i]
        if v < 18:
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        elif 18 <= v <= 28:
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        else:
            w = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        
        # Calculate day return based on weight mapping
        day_ret = sum(returns[tk].iloc[i] * w[tk] for tk in w if tk in returns.columns)
        port_returns.append(day_ret)

    port_returns = pd.Series(port_returns, index=returns.index)
    cum_returns = (1 + port_returns).cumprod()
    
    print(f"\n[RESULTS]")
    print(f"Current VIX: {vix.iloc[-1]:.2f}")
    print(f"Portfolio Final Value: ${cum_returns.iloc[-1]:.2f}")
    print(f"Max Drawdown: {(cum_returns / cum_returns.cummax() - 1).min():.2%}")
    
    plt.style.use('ggplot') # Use standard style if dark_background fails
    cum_returns.plot(title="Eureka 2.0 (Dynamic VIXM)")
    plt.savefig('eureka_results.png') # Automatically save so you don't need a window
    print("\n[*] Analysis complete. Plot saved as 'eureka_results.png'.")

if __name__ == "__main__":
    main()
