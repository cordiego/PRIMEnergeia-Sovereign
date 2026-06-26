#!/usr/bin/env python3
"""
EUREKA SOVEREIGN — Pre-Market Intelligence Engine
====================================================
Reads overnight gaps, sector proxy momentum, and Markov regime
to generate a pre-market conviction signal BEFORE the opening bell.

Designed to run at 7:30 AM ET, delivers Telegram alert at 8:00 AM ET.
Separate from the 3 PM daily dispatch — this is the MORNING read.

Usage:
    python eureka_premarket.py
    python eureka_premarket.py --dry-run

PRIMEnergeia S.A.S.
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

# Add parent directory for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.eureka_markov import MarkovDayChain, build_full_history_chain

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PreMarket] - %(message)s'
)
logger = logging.getLogger("eureka.premarket")

# ============================================================
#  CONFIGURATION
# ============================================================
MAIN_TICKER = "SCHD"
PROJ_TICKER = "SCHD"
VIX_TICKER = "^VIX"

SECTOR_PROXIES = {
    "SPY": 0.30,   # S"SPY":  0.25,   # Micron — semiconductor siblingP 500 Broad Market
    "DIA": 0.30,   # Dow Jones
}
MAIN_WEIGHT = 0.40  # SCHD itself is the primary signal

DECAY_LAMBDA = 0.002250  # Locked from decay_parameter_lock.json
PREMARKET_HISTORY_PATH = os.path.expanduser(
    "~/.quantum_portfolio/schd_premarket_history.json"
)

# ============================================================
#  DATA FETCHING
# ============================================================

import pytz

def get_yesterday_close(ticker: str) -> float:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period="5d", prepost=False)
        if h.empty:
            return None
        
        ny_tz = pytz.timezone("America/New_York")
        now_ny = datetime.now(ny_tz).date()
        last_date = h.index[-1].date()
        
        if last_date == now_ny:
            if len(h) >= 2:
                return float(h["Close"].iloc[-2])
            return None
        else:
            return float(h["Close"].iloc[-1])
    except Exception:
        return None

def fetch_premarket_data() -> dict:
    """
    Fetch pre-market / after-hours data for SCHD and sector proxies.
    Returns dict with overnight gap percentages and current prices.
    """
    if yf is None:
        logger.error("yfinance not installed.")
        return {"error": "yfinance not installed"}

    result = {"timestamp": datetime.utcnow().isoformat() + "Z"}
    tickers_to_fetch = [MAIN_TICKER] + list(SECTOR_PROXIES.keys()) + [VIX_TICKER]

    for ticker in tickers_to_fetch:
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            
            latest_price = info.get("preMarketPrice")
            if latest_price is None:
                latest_price = info.get("postMarketPrice")
            if latest_price is None:
                latest_price = info.get("currentPrice")
            if latest_price is None:
                latest_price = info.get("regularMarketPrice")
                
            yesterday_close = get_yesterday_close(ticker)
            
            if latest_price is None or yesterday_close is None:
                logger.warning(f"Missing info for {ticker}")
                result[ticker] = {"gap_pct": None, "price": None}
                continue
            
            latest_price = float(latest_price)
            yesterday_close = float(yesterday_close)
            
            if yesterday_close > 0:
                gap_pct = (latest_price - yesterday_close) / yesterday_close
            else:
                gap_pct = 0.0

            result[ticker] = {
                "gap_pct": float(gap_pct),
                "price": latest_price,
                "yesterday_close": yesterday_close,
            }

        except Exception as e:
            logger.warning(f"Failed to fetch {ticker}: {e}")
            result[ticker] = {"gap_pct": None, "price": None}

    # Project SCHD open from SCHD gap (2x leverage)
    sndk_data = result.get(MAIN_TICKER, {})
    sndk_gap = sndk_data.get("gap_pct")
    if sndk_gap is not None:
        result["snxx_projected_gap"] = sndk_gap * 2.0
    else:
        result["snxx_projected_gap"] = None

    return result


# ============================================================
#  SECTOR MOMENTUM
# ============================================================

def compute_sector_momentum(premarket_data: dict) -> float:
    """
    Weighted composite of pre-market changes across SCHD + sector proxies.
    Returns score in [-1, +1].
    """
    total_weight = 0.0
    weighted_sum = 0.0

    # SCHD primary signal
    sndk_gap = premarket_data.get(MAIN_TICKER, {}).get("gap_pct")
    if sndk_gap is not None:
        weighted_sum += MAIN_WEIGHT * sndk_gap
        total_weight += MAIN_WEIGHT

    # Sector proxies
    for ticker, weight in SECTOR_PROXIES.items():
        gap = premarket_data.get(ticker, {}).get("gap_pct")
        if gap is not None:
            weighted_sum += weight * gap
            total_weight += weight

    if total_weight == 0:
        return 0.0

    # Normalize by actual weight used (handles missing proxies)
    raw_score = weighted_sum / total_weight

    # Scale to [-1, +1] using 3% as a "full conviction" move
    score = np.clip(raw_score / 0.03, -1.0, 1.0)
    return float(score)


# ============================================================
#  DECAY RISK
# ============================================================

def compute_decay_risk(markov_chain: MarkovDayChain, daily_returns: pd.Series) -> float:
    """
    Estimate today's decay risk for SCHD based on recent realized
    volatility and the current Markov regime.
    Returns decay risk as a percentage.
    """
    if len(daily_returns) < 5:
        return 0.0

    # 5-day realized volatility (annualized daily stdev)
    realized_vol_5d = float(daily_returns.iloc[-5:].std())

    regime = markov_chain.get_regime()
    multiplier = {"CHOPPY": 3.0, "TRENDING": 0.5, "NEUTRAL": 1.0}.get(regime, 1.0)

    decay_risk = DECAY_LAMBDA * (realized_vol_5d ** 2) * multiplier
    return float(decay_risk * 100)  # as percentage


# ============================================================
#  MAIN SIGNAL GENERATOR
# ============================================================

def generate_premarket_signal() -> dict:
    """
    Master function: generates the complete pre-market intelligence signal.
    Combines gap analysis, sector momentum, Markov regime, and decay risk.
    """
    logger.info("Generating pre-market signal...")

    # 1. Fetch pre-market data
    pm_data = fetch_premarket_data()
    if "error" in pm_data:
        return pm_data

    # 2. Build Markov chain on full SCHD history
    logger.info("Building Markov chain on full SCHD history...")
    chain = build_full_history_chain(MAIN_TICKER)

    # 3. Compute components
    sector_score = compute_sector_momentum(pm_data)

    # Get SCHD daily returns for decay risk calc
    try:
        df = yf.download(MAIN_TICKER, period="30d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            closes = df["Close"].iloc[:, 0]
        else:
            closes = df["Close"]
        daily_returns = closes.pct_change().dropna()
    except Exception:
        daily_returns = pd.Series(dtype=float)

    decay_risk = compute_decay_risk(chain, daily_returns)

    # Markov prediction
    prediction = chain.predict_next_day()
    streaks = chain.streak_analysis()
    regime = prediction["regime"]

    # Gap signal: normalize SCHD gap to [-1, +1]
    sndk_gap = pm_data.get(MAIN_TICKER, {}).get("gap_pct", 0) or 0
    gap_signal = float(np.clip(sndk_gap / 0.03, -1.0, 1.0))

    # Markov trend: center P(green) around 0
    markov_trend = (prediction["p_green"] - 0.5) * 2.0

    # Decay risk normalized to [0, 1] using 0.5% as max
    decay_risk_normalized = float(np.clip(decay_risk / 0.5, 0.0, 1.0))

    # 4. Composite conviction score
    pm_conviction = (
        0.35 * sector_score +
        0.25 * gap_signal +
        0.25 * markov_trend -
        0.15 * decay_risk_normalized
    )

    # 5. Map conviction to signal
    if pm_conviction > 0.5:
        pm_signal = "STRONG_BUY"
        kelly_adj = 1.00
    elif pm_conviction > 0.2:
        pm_signal = "BUY"
        kelly_adj = 0.85
    elif pm_conviction > -0.2:
        pm_signal = "HOLD"
        kelly_adj = 0.50
    elif pm_conviction > -0.5:
        pm_signal = "SELL"
        kelly_adj = 0.25
    else:
        pm_signal = "AVOID"
        kelly_adj = 0.00

    # Choppy regime override: cap Kelly at 50% regardless of conviction
    if regime == "CHOPPY":
        kelly_adj = min(kelly_adj, 0.50)
        logger.info("CHOPPY regime detected — Kelly capped at 50%")

    # 6. Assemble full signal dict
    signal = {
        "timestamp": pm_data.get("timestamp"),
        "date": datetime.now().strftime("%Y-%m-%d"),

        # Pre-market data
        "sndk_gap_pct": sndk_gap * 100,
        "snxx_projected_gap_pct": (pm_data.get("snxx_projected_gap") or 0) * 100,
        "sndk_price": pm_data.get(MAIN_TICKER, {}).get("price"),

        # Sector proxies
        "sector_score": sector_score,
        "spy_gap_pct":  (pm_data.get("SPY", {}).get("gap_pct") or 0) * 100,
        "dia_gap_pct": (pm_data.get("DIA", {}).get("gap_pct") or 0) * 100,

        # VIX
        "vix_price": pm_data.get(VIX_TICKER, {}).get("price"),

        # Markov chain
        "markov_regime": regime,
        "p_green": prediction["p_green"],
        "p_red": prediction["p_red"],
        "current_state": prediction["current_state"],
        "current_streak_length": streaks["current_streak_length"],
        "current_streak_direction": streaks["current_streak_direction"],
        "p_gg": float(chain.transition_matrix[0, 0]),
        "p_rr": float(chain.transition_matrix[1, 1]),

        # Decay
        "decay_risk_pct": decay_risk,

        # Signal output
        "gap_signal": gap_signal,
        "markov_trend": markov_trend,
        "decay_risk_normalized": decay_risk_normalized,
        "pm_conviction": float(pm_conviction),
        "pm_signal": pm_signal,
        "kelly_adj": kelly_adj,

        # Feedback fields (filled by 3 PM dispatch)
        "actual_snxx_close_pct": None,
        "signal_correct": None,
    }

    logger.info(f"Pre-market signal: {pm_signal} (conviction={pm_conviction:+.3f}, "
                f"regime={regime}, kelly={kelly_adj:.0%})")
    return signal


# ============================================================
#  MESSAGE FORMATTING
# ============================================================

def format_premarket_message(signal: dict) -> str:
    """Format the pre-market signal as a Telegram-ready dispatch message."""
    ts = signal.get("timestamp", datetime.utcnow().isoformat())

    # Labels
    score = signal.get("sector_score", 0)
    if score > 0.3:
        sector_label = "BULLISH"
    elif score < -0.3:
        sector_label = "BEARISH"
    else:
        sector_label = "NEUTRAL"

    dr = signal.get("decay_risk_pct", 0)
    if dr < 0.05:
        decay_label = "LOW"
    elif dr < 0.15:
        decay_label = "MODERATE"
    elif dr < 0.30:
        decay_label = "HIGH"
    else:
        decay_label = "CRITICAL"

    sig = signal.get("pm_signal", "HOLD")
    emoji_map = {
        "STRONG_BUY": "\U0001f7e2\U0001f7e2",
        "BUY":        "\U0001f7e2",
        "HOLD":       "\u26aa",
        "SELL":       "\U0001f534",
        "AVOID":      "\U0001f534\U0001f534",
    }
    sig_emoji = emoji_map.get(sig, "\u26aa")

    exec_map = {
        "STRONG_BUY": "Buy at open or within first 15 min if SCHD opens within +/-0.5% of projected",
        "BUY":        "Scale in during first 30 min using TWAP",
        "HOLD":       "No action — wait for 3 PM Eureka dispatch",
        "SELL":       "Reduce exposure at open, target MOC for remainder",
        "AVOID":      "DO NOT trade SCHD today — choppy regime + negative setup",
    }
    exec_guidance = exec_map.get(sig, "Wait for confirmation")

    regime = signal.get("markov_regime", "NEUTRAL")
    streak_len = signal.get("current_streak_length", 0)
    streak_dir = signal.get("current_streak_direction", "?")

    lines = []
    lines.append("=" * 59)
    lines.append("\U0001f305  EUREKA PRE-MARKET INTELLIGENCE")
    lines.append("=" * 59)
    lines.append(f"\U0001f4c5  {ts}")
    lines.append(f"\U0001f4ca  SCHD Pre-Market: {signal.get('schd_gap_pct', signal.get('sndk_gap_pct', 0)):+.2f}%")

    lines.append(f"\U0001f52e  Sector Pulse: {sector_label} "
                 f"(SPY {signal.get('spy_gap_pct', 0):+.1f}%, "
                 f"DIA {signal.get('dia_gap_pct', 0):+.1f}%)")
    lines.append(f"\U0001f4c8  Markov Regime: {regime} "
                 f"(P(G\u2192G)={signal.get('p_gg', 0.5):.2f}, "
                 f"streak: {streak_len} {streak_dir})")

    lines.append(f"\u26a1  Decay Risk: {decay_label} ({dr:.3f}%)")

    if signal.get("vix_price"):
        lines.append(f"\U0001f4ca  VIX: {signal['vix_price']:.2f}")

    lines.append("")
    lines.append("\u2500" * 59)
    lines.append(f"\U0001f3af  PRE-MARKET SIGNAL: {sig_emoji} {sig}")
    lines.append(f"\U0001f4b0  Kelly Sizing: {signal.get('kelly_adj', 0.5) * 100:.0f}% of full block")
    lines.append(f"\U0001f4ca  Conviction: {signal.get('pm_conviction', 0):+.3f}")
    lines.append("\u2500" * 59)
    lines.append(f"\u23f0  EXECUTION WINDOW:")
    lines.append(f"    {exec_guidance}")
    lines.append("=" * 59)

    return "\n".join(lines)


# ============================================================
#  HISTORY PERSISTENCE
# ============================================================

def save_premarket_history(signal: dict):
    """Save today's pre-market signal to the history JSON file."""
    history = {}
    if os.path.exists(PREMARKET_HISTORY_PATH):
        try:
            with open(PREMARKET_HISTORY_PATH, 'r') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = {}

    date_key = signal.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Convert numpy types for JSON serialization
    clean_signal = {}
    for k, v in signal.items():
        if isinstance(v, (np.integer,)):
            clean_signal[k] = int(v)
        elif isinstance(v, (np.floating,)):
            clean_signal[k] = float(v)
        elif isinstance(v, np.ndarray):
            clean_signal[k] = v.tolist()
        else:
            clean_signal[k] = v

    history[date_key] = clean_signal

    os.makedirs(os.path.dirname(PREMARKET_HISTORY_PATH), exist_ok=True)
    with open(PREMARKET_HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2, default=str)

    logger.info(f"Saved pre-market signal to {PREMARKET_HISTORY_PATH}")


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Eureka Pre-Market Intelligence Engine")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print signal without sending Telegram")
    args = parser.parse_args()

    print("\n[*] Eureka Sovereign — Pre-Market Intelligence Engine")
    signal = generate_premarket_signal()

    if "error" in signal:
        print(f"[!] {signal['error']}")
        sys.exit(1)

    message = format_premarket_message(signal)
    print(message)

    # Send Telegram
    if not args.dry_run:
        print("\n[*] Sending Telegram Notification...")
        try:
            from core.alerts import PRIMAlerts
            alerts = PRIMAlerts()
            success = alerts._send_telegram(message)
            if success:
                print("[OK] Pre-market notification delivered.")
            else:
                print("[!] Telegram delivery failed.")
        except Exception as e:
            print(f"[!] Alert error: {e}")
    else:
        print("\n[DRY RUN] Telegram skipped.")

    # Save history
    try:
        save_premarket_history(signal)
        print("[OK] History saved.")
    except Exception as e:
        print(f"[!] History save failed: {e}")


if __name__ == "__main__":
    main()
