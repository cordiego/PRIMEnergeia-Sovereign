#!/usr/bin/env python3
"""
EUREKA SOVEREIGN — Pre-Market Signal Backtester
=================================================
Backtests the pre-market Markov chain + sector momentum strategy
against ALL available SNDK/SNXX history.

Measures:
  - Direction hit rate
  - Strategy return vs buy-and-hold SNXX
  - Decay savings from avoiding choppy regimes
  - Sharpe ratio and max drawdown comparisons

Usage:
    python backtest_premarket_signals.py
    python backtest_premarket_signals.py --years 3 --output reports/backtest.csv

PRIMEnergeia S.A.S.
"""

import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

# Add parent directory for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.eureka_markov import MarkovDayChain, GREEN, RED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Backtest] - %(message)s'
)
logger = logging.getLogger("eureka.backtest")

# ============================================================
#  CONFIGURATION
# ============================================================
DECAY_LAMBDA = 0.002250
LOOKBACK_MIN = 60  # minimum days to fit Markov chain

SIGNAL_KELLY_MAP = {
    "STRONG_BUY": 1.00,
    "BUY":        0.85,
    "HOLD":       0.50,
    "SELL":       0.25,
    "AVOID":      0.00,
}

# ============================================================
#  DATA
# ============================================================

def download_full_history(years: int = 0) -> pd.DataFrame:
    """
    Download SNDK + sector proxies (MU, SMH, QQQ) + VIX.
    years=0 means all available history.
    """
    if yf is None:
        logger.error("yfinance not installed.")
        return pd.DataFrame()

    tickers = ["SNDK", "MU", "SMH", "QQQ", "^VIX"]

    if years > 0:
        start = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
        logger.info(f"Downloading {years} years of data...")
        df = yf.download(tickers, start=start, progress=False)
    else:
        logger.info("Downloading ALL available history...")
        df = yf.download(tickers, period="max", progress=False)

    if df.empty:
        logger.error("No data returned from yfinance.")
        return pd.DataFrame()

    # Extract OHLC
    if isinstance(df.columns, pd.MultiIndex):
        closes = df["Close"].copy()
        opens = df["Open"].copy()
    else:
        closes = df[["Close"]].copy()
        opens = df[["Open"]].copy()

    result = pd.DataFrame(index=closes.index)
    for col in closes.columns:
        result[f"{col}_close"] = closes[col]
    for col in opens.columns:
        result[f"{col}_open"] = opens[col]

    result = result.dropna(subset=["SNDK_close"])
    logger.info(f"Data range: {result.index[0].strftime('%Y-%m-%d')} to "
                f"{result.index[-1].strftime('%Y-%m-%d')} ({len(result)} days)")
    return result


def simulate_snxx_returns(sndk_returns: pd.Series) -> pd.Series:
    """Simulate SNXX as 2x daily reset of SNDK returns."""
    return sndk_returns * 2.0


# ============================================================
#  BACKTEST ENGINE
# ============================================================

def backtest_premarket_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """
    For each trading day, simulate the pre-market signal using
    data available up to that point, and track performance.
    """
    sndk_close = data["SNDK_close"]
    sndk_open = data.get("SNDK_open", sndk_close)
    sndk_returns = sndk_close.pct_change()
    snxx_returns = simulate_snxx_returns(sndk_returns)

    # Sector proxy returns (close-to-close as proxy for pre-market in backtest)
    mu_returns  = data.get("MU_close",  pd.Series(dtype=float)).pct_change()
    smh_returns = data.get("SMH_close", pd.Series(dtype=float)).pct_change()
    qqq_returns = data.get("QQQ_close", pd.Series(dtype=float)).pct_change()

    results = []
    chain = MarkovDayChain()

    for i in range(LOOKBACK_MIN + 1, len(data)):
        date = data.index[i]

        # Fit Markov chain on all data up to yesterday
        past_returns = sndk_returns.iloc[1:i]  # skip first NaN
        chain.fit(past_returns, min_periods=30)

        # Overnight gap: (today's open - yesterday's close) / yesterday's close
        prev_close = float(sndk_close.iloc[i - 1])
        today_open = float(sndk_open.iloc[i])
        gap_pct = (today_open - prev_close) / prev_close if prev_close != 0 else 0

        # Sector momentum proxy (using yesterday's returns as stand-in for pre-market)
        # In live mode we'd use actual pre-market data; in backtest we use
        # prior-day returns as the best available proxy
        weights = {"SNDK": 0.40, "MU": 0.25, "SMH": 0.20, "QQQ": 0.15}
        sector_sum = 0.0
        total_w = 0.0

        for ticker, w in weights.items():
            if ticker == "SNDK":
                ret = gap_pct  # use actual gap for SNDK
            else:
                col_ret = {"MU": mu_returns, "SMH": smh_returns, "QQQ": qqq_returns}.get(ticker)
                if col_ret is not None and i < len(col_ret) and not pd.isna(col_ret.iloc[i - 1]):
                    ret = float(col_ret.iloc[i - 1])
                else:
                    continue
            sector_sum += w * ret
            total_w += w

        sector_score = np.clip((sector_sum / total_w) / 0.03, -1, 1) if total_w > 0 else 0

        # Markov prediction
        prediction = chain.predict_next_day()
        regime = prediction["regime"]

        # Gap signal
        gap_signal = float(np.clip(gap_pct / 0.03, -1, 1))

        # Markov trend
        markov_trend = (prediction["p_green"] - 0.5) * 2.0

        # Decay risk
        if i >= 6:
            vol_5d = float(sndk_returns.iloc[i - 5:i].std())
        else:
            vol_5d = 0.01
        regime_mult = {"CHOPPY": 3.0, "TRENDING": 0.5, "NEUTRAL": 1.0}.get(regime, 1.0)
        decay_risk = DECAY_LAMBDA * (vol_5d ** 2) * regime_mult * 100
        decay_risk_norm = float(np.clip(decay_risk / 0.5, 0, 1))

        # Conviction
        conviction = (
            0.35 * sector_score +
            0.25 * gap_signal +
            0.25 * markov_trend -
            0.15 * decay_risk_norm
        )

        # Signal
        if conviction > 0.5:
            signal = "STRONG_BUY"
        elif conviction > 0.2:
            signal = "BUY"
        elif conviction > -0.2:
            signal = "HOLD"
        elif conviction > -0.5:
            signal = "SELL"
        else:
            signal = "AVOID"

        kelly = SIGNAL_KELLY_MAP[signal]
        if regime == "CHOPPY":
            kelly = min(kelly, 0.50)

        # Actual SNXX return for the day
        actual_snxx = float(snxx_returns.iloc[i]) if i < len(snxx_returns) else 0

        # Strategy return = kelly fraction * SNXX return
        strat_return = kelly * actual_snxx

        # Was the direction call correct?
        if signal in ("STRONG_BUY", "BUY"):
            direction_correct = actual_snxx >= 0
        elif signal in ("SELL", "AVOID"):
            direction_correct = actual_snxx < 0
        else:
            direction_correct = None  # HOLD = no directional call

        results.append({
            "date": date,
            "signal": signal,
            "conviction": float(conviction),
            "kelly": kelly,
            "regime": regime,
            "gap_pct": gap_pct * 100,
            "sector_score": sector_score,
            "p_green": prediction["p_green"],
            "decay_risk": decay_risk,
            "actual_snxx_return": actual_snxx * 100,
            "strat_return": strat_return * 100,
            "bh_return": actual_snxx * 100,
            "direction_correct": direction_correct,
        })

    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    # Cumulative returns
    df["strat_cumret"] = (1 + df["strat_return"] / 100).cumprod()
    df["bh_cumret"] = (1 + df["bh_return"] / 100).cumprod()

    return df


# ============================================================
#  STATISTICS
# ============================================================

def compute_backtest_stats(results: pd.DataFrame) -> dict:
    """Compute comprehensive backtest statistics."""
    n_days = len(results)

    # Direction hit rate (excluding HOLDs)
    directional = results[results["direction_correct"].notna()]
    hit_rate = directional["direction_correct"].mean() * 100 if len(directional) > 0 else 0

    # Returns
    strat_total = (results["strat_cumret"].iloc[-1] - 1) * 100 if len(results) > 0 else 0
    bh_total = (results["bh_cumret"].iloc[-1] - 1) * 100 if len(results) > 0 else 0
    alpha = strat_total - bh_total

    # Sharpe ratios (annualized, assuming 252 trading days)
    strat_daily = results["strat_return"] / 100
    bh_daily = results["bh_return"] / 100
    strat_sharpe = (strat_daily.mean() / strat_daily.std() * np.sqrt(252)) if strat_daily.std() > 0 else 0
    bh_sharpe = (bh_daily.mean() / bh_daily.std() * np.sqrt(252)) if bh_daily.std() > 0 else 0

    # Max drawdown
    def max_drawdown(cumret):
        peak = cumret.cummax()
        dd = (cumret - peak) / peak
        return float(dd.min() * 100)

    strat_mdd = max_drawdown(results["strat_cumret"])
    bh_mdd = max_drawdown(results["bh_cumret"])

    # Decay savings: loss avoided on AVOID/SELL days that were red
    avoid_sell = results[results["signal"].isin(["AVOID", "SELL"])]
    red_avoided = avoid_sell[avoid_sell["actual_snxx_return"] < 0]
    n_avoided = len(red_avoided)
    loss_avoided = float(red_avoided["actual_snxx_return"].sum() * (1 - 0.125))  # avg reduced exposure

    # Conviction analysis
    correct = directional[directional["direction_correct"] == True]
    wrong = directional[directional["direction_correct"] == False]
    avg_conv_correct = float(correct["conviction"].abs().mean()) if len(correct) > 0 else 0
    avg_conv_wrong = float(wrong["conviction"].abs().mean()) if len(wrong) > 0 else 0

    # Regime breakdown
    regime_stats = {}
    for regime in ["TRENDING", "CHOPPY", "NEUTRAL"]:
        subset = results[results["regime"] == regime]
        if len(subset) > 0:
            regime_stats[regime] = {
                "days": len(subset),
                "total_return": float(subset["strat_return"].sum()),
            }
        else:
            regime_stats[regime] = {"days": 0, "total_return": 0.0}

    return {
        "n_days": n_days,
        "start": str(results.index[0].date()) if len(results) > 0 else "",
        "end": str(results.index[-1].date()) if len(results) > 0 else "",
        "strat_total": strat_total,
        "bh_total": bh_total,
        "alpha": alpha,
        "strat_sharpe": strat_sharpe,
        "bh_sharpe": bh_sharpe,
        "strat_mdd": strat_mdd,
        "bh_mdd": bh_mdd,
        "hit_rate": hit_rate,
        "avg_conv_correct": avg_conv_correct,
        "avg_conv_wrong": avg_conv_wrong,
        "n_avoided": n_avoided,
        "loss_avoided": loss_avoided,
        "regime_stats": regime_stats,
    }


def print_backtest_report(stats: dict, results: pd.DataFrame):
    """Print a formatted backtest report to console."""
    rs = stats.get("regime_stats", {})

    print()
    print("=" * 59)
    print("\U0001f4ca  EUREKA PRE-MARKET BACKTEST RESULTS")
    print("=" * 59)
    print(f"Period: {stats['start']} to {stats['end']} ({stats['n_days']} trading days)")
    print()

    print("STRATEGY PERFORMANCE:")
    print(f"  Total Return:      {stats['strat_total']:+.2f}%")
    print(f"  Buy & Hold SNXX:   {stats['bh_total']:+.2f}%")
    print(f"  Alpha:             {stats['alpha']:+.2f}%")
    print(f"  Sharpe (Strategy): {stats['strat_sharpe']:.2f}")
    print(f"  Sharpe (B&H):      {stats['bh_sharpe']:.2f}")
    print(f"  Max Drawdown:      {stats['strat_mdd']:.2f}% vs {stats['bh_mdd']:.2f}%")
    print()

    print("SIGNAL ACCURACY:")
    print(f"  Direction Hit Rate: {stats['hit_rate']:.1f}%")
    print(f"  Avg Conviction (Correct): {stats['avg_conv_correct']:.3f}")
    print(f"  Avg Conviction (Wrong):   {stats['avg_conv_wrong']:.3f}")
    print()

    print("DECAY SAVINGS:")
    print(f"  Red days avoided (AVOID/SELL signals): {stats['n_avoided']}")
    print(f"  Total loss avoided: {stats['loss_avoided']:+.2f}%")
    print()

    print("REGIME BREAKDOWN:")
    for regime in ["TRENDING", "CHOPPY", "NEUTRAL"]:
        r = rs.get(regime, {})
        print(f"  {regime:>10}: {r.get('total_return', 0):+.2f}% ({r.get('days', 0)} days)")
    print()

    # Signal distribution
    print("SIGNAL DISTRIBUTION:")
    if len(results) > 0:
        dist = results["signal"].value_counts()
        for sig, count in dist.items():
            pct = count / len(results) * 100
            print(f"  {sig:>12}: {count:4d} ({pct:.1f}%)")
    print("=" * 59)


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Eureka Pre-Market Signal Backtester")
    parser.add_argument("--years", type=int, default=0,
                        help="Years of history (0 = all available)")
    parser.add_argument("--output", type=str,
                        default=os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            "..", "reports", "premarket_backtest.csv"),
                        help="Output CSV path")
    args = parser.parse_args()

    print("\n[*] Eureka Sovereign — Pre-Market Signal Backtester")
    print(f"    History: {'ALL' if args.years == 0 else f'{args.years} years'}")
    print()

    # Download data
    data = download_full_history(years=args.years)
    if data.empty:
        print("[!] No data available. Exiting.")
        sys.exit(1)

    # Run backtest
    print("[*] Running backtest (this may take a moment)...")
    results = backtest_premarket_strategy(data)

    if results.empty:
        print("[!] Backtest produced no results. Exiting.")
        sys.exit(1)

    # Compute stats
    stats = compute_backtest_stats(results)

    # Print report
    print_backtest_report(stats, results)

    # Save CSV
    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    results.to_csv(out_path)
    print(f"\n[OK] Results saved to {out_path}")
    print(f"     {len(results)} daily records")


if __name__ == "__main__":
    main()
