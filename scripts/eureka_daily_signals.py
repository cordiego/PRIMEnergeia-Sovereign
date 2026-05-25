#!/usr/bin/env python3
"""
EUREKA SOVEREIGN — Daily Portfolio % Change + Trade Signal Generator
====================================================================
Runs daily via GitHub Actions at 3:45 PM ET (15 min before close).
Fetches live prices, computes VIX-regime target percentages,
calculates Eureka portfolio % change (daily / weekly / monthly / YTD),
and emits BUY/SELL/HOLD recommendations based on regime transitions.

Notification channels:
  - Telegram (via bot API)
  - Email (via SMTP / Gmail App Password)
  - Console output (for GitHub Actions logs)

Required GitHub Secrets:
  TELEGRAM_BOT_TOKEN    — Telegram bot token
  TELEGRAM_CHAT_ID      — Telegram chat ID
  EMAIL_ADDRESS         — Gmail address for sending
  EMAIL_APP_PASSWORD    — Gmail App Password
  EMAIL_TO              — Recipient email address
"""

import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# ============================================================
#  CONFIGURATION
# ============================================================

EUREKA_UNIVERSE = ["VTIP", "IAU", "GEV", "VGSH"]
GAINS_DESTINATION = "VGSH"
VIX_TICKER = "^VIX"
BENCHMARK = "SPY"

# Static allocation — Vol≤5% optimal
TARGET_WEIGHTS = {"VTIP": 1.0}

# Thresholds for momentum signals
TAKE_PROFIT_THRESHOLD = 0.01   # daily return > +1% → take profit window
DIP_BUY_THRESHOLD = -0.02      # daily return < -2% → opportunistic buy window


def classify_regime(vix_level):
    if vix_level < 18:
        return "RISK-ON"
    elif vix_level <= 28:
        return "TRANSITION"
    else:
        return "CRISIS"


# ============================================================
#  DATA FETCHING — historical for % change computation
# ============================================================

def fetch_historical_data(lookback_days=90):
    """Download price history for the Eureka universe to compute % changes."""
    tickers = EUREKA_UNIVERSE + [VIX_TICKER, BENCHMARK]
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    all_data = {}

    for t in tickers:
        try:
            df = yf.download(t, start=start_date, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                s = df['Close'][t]
            else:
                s = df['Close']
            s.name = t
            all_data[t] = s
        except Exception as e:
            print(f"[!] Failed to fetch {t}: {e}")

    if not all_data or VIX_TICKER not in all_data:
        return None

    prices = pd.DataFrame(all_data).dropna()
    return prices


# ============================================================
#  EUREKA PORTFOLIO % CHANGE ENGINE
# ============================================================

def compute_eureka_performance(prices):
    """
    Compute Eureka portfolio performance using regime-adaptive weights.
    Returns daily portfolio returns series and summary metrics.
    """
    if prices is None or prices.empty:
        return None

    returns = prices.pct_change().dropna()
    vix_series = prices[VIX_TICKER]

    # Build portfolio returns using regime-driven weights each day
    port_returns = []
    regime_history = []

    for i in range(len(returns)):
        idx = returns.index[i]
        vix_val = vix_series.loc[idx] if idx in vix_series.index else 20.0
        regime = classify_regime(vix_val)
        regime_history.append(regime)
        w = REGIMES[regime]["weights"]
        day_ret = sum(returns[tk].iloc[i] * w.get(tk, 0) for tk in w if tk in returns.columns)
        port_returns.append(day_ret)

    port_returns = pd.Series(port_returns, index=returns.index)
    cum_returns = (1 + port_returns).cumprod()

    # SPY benchmark
    spy_returns = returns[BENCHMARK] if BENCHMARK in returns.columns else pd.Series(0, index=returns.index)
    spy_cum = (1 + spy_returns).cumprod()

    # Current state
    current_vix = float(vix_series.iloc[-1])
    current_regime = classify_regime(current_vix)
    current_weights = REGIMES[current_regime]["weights"]

    # Percentage changes at different horizons
    daily_pct = float(port_returns.iloc[-1]) * 100 if len(port_returns) >= 1 else 0.0
    weekly_pct = float((cum_returns.iloc[-1] / cum_returns.iloc[-6] - 1) * 100) if len(cum_returns) >= 6 else daily_pct
    monthly_pct = float((cum_returns.iloc[-1] / cum_returns.iloc[-22] - 1) * 100) if len(cum_returns) >= 22 else weekly_pct

    # YTD: from first trading day of current year
    ytd_start = cum_returns.index[cum_returns.index >= f"{datetime.now().year}-01-01"]
    if len(ytd_start) > 0:
        ytd_pct = float((cum_returns.iloc[-1] / cum_returns.loc[ytd_start[0]] - 1) * 100)
    else:
        ytd_pct = float((cum_returns.iloc[-1] - 1) * 100)

    # SPY comparisons
    spy_daily = float(spy_returns.iloc[-1]) * 100 if len(spy_returns) >= 1 else 0.0
    spy_ytd_start = spy_cum.index[spy_cum.index >= f"{datetime.now().year}-01-01"]
    if len(spy_ytd_start) > 0:
        spy_ytd = float((spy_cum.iloc[-1] / spy_cum.loc[spy_ytd_start[0]] - 1) * 100)
    else:
        spy_ytd = float((spy_cum.iloc[-1] - 1) * 100)

    # Previous regime (yesterday) for transition detection
    prev_regime = regime_history[-2] if len(regime_history) >= 2 else current_regime

    # Latest prices and per-asset daily returns
    latest_prices = {tk: float(prices[tk].iloc[-1]) for tk in EUREKA_UNIVERSE if tk in prices.columns}
    spy_price = float(prices[BENCHMARK].iloc[-1]) if BENCHMARK in prices.columns else 0.0
    asset_daily_returns = {tk: float(returns[tk].iloc[-1]) for tk in EUREKA_UNIVERSE if tk in returns.columns}

    return {
        "current_vix": current_vix,
        "current_regime": current_regime,
        "prev_regime": prev_regime,
        "regime_changed": prev_regime != current_regime,
        "current_weights": current_weights,
        "prev_weights": REGIMES[prev_regime]["weights"],
        "daily_pct": daily_pct,
        "weekly_pct": weekly_pct,
        "monthly_pct": monthly_pct,
        "ytd_pct": ytd_pct,
        "spy_daily": spy_daily,
        "spy_ytd": spy_ytd,
        "spy_price": spy_price,
        "latest_prices": latest_prices,
        "asset_daily_returns": asset_daily_returns,
        "port_returns": port_returns,
        "cum_returns": cum_returns,
    }


# ============================================================
#  BUY / SELL RECOMMENDATION ENGINE
# ============================================================

BUY_THRESHOLD = -0.015    # asset down 1.5% → BUY the dip
SELL_THRESHOLD = 0.015    # asset up 1.5% → SELL / take profit


def generate_recommendations(perf):
    """
    Generate BUY/SELL/HOLD recommendations based on each asset's
    daily % change. Assumes portfolio is at target weights.
    Includes trade_pct: exact % of portfolio to trade.
    """
    actions = []
    port_daily_ret = perf["daily_pct"] / 100.0

    for tk in EUREKA_UNIVERSE:
        w_now = perf["current_weights"].get(tk, 0)
        price = perf["latest_prices"].get(tk, 0)
        asset_daily = perf["asset_daily_returns"].get(tk, 0)
        asset_daily_pct = asset_daily * 100

        # Drift: weight shift from target due to today's move
        denom = 1 + port_daily_ret
        new_weight = w_now * (1 + asset_daily) / denom if denom != 0 else w_now
        drift = new_weight - w_now
        trade_pct = abs(drift) * 100

        if asset_daily <= BUY_THRESHOLD:
            action = "BUY"
            reason = f"Down {asset_daily_pct:+.2f}% — buy the dip"
        elif asset_daily >= SELL_THRESHOLD:
            action = "SELL"
            reason = f"Up {asset_daily_pct:+.2f}% — take profit"
        else:
            action = "HOLD"
            reason = f"Within range ({asset_daily_pct:+.2f}%)"
            trade_pct = 0.0

        actions.append({
            "ticker": tk,
            "price": price,
            "target_pct": w_now * 100,
            "asset_daily_pct": asset_daily_pct,
            "trade_pct": trade_pct,
            "action": action,
            "reason": reason,
        })

    # Portfolio-level momentum signal
    daily_ret = perf["daily_pct"] / 100.0
    momentum_signal = None
    if daily_ret > TAKE_PROFIT_THRESHOLD:
        momentum_signal = f"📈 TAKE-PROFIT WINDOW: Eureka up {perf['daily_pct']:+.2f}% today. Consider trimming winners."
    elif daily_ret < DIP_BUY_THRESHOLD:
        momentum_signal = f"📉 OPPORTUNISTIC BUY WINDOW: Eureka down {perf['daily_pct']:+.2f}% today. Consider adding to core positions."

    return actions, momentum_signal


# ============================================================
#  MESSAGE FORMATTING
# ============================================================

def format_message(perf, actions, momentum_signal):
    """Format the complete notification message."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []

    lines.append("=" * 50)
    lines.append("🏛️  EUREKA SOVEREIGN — DAILY DISPATCH")
    lines.append("=" * 50)
    lines.append(f"📅  {ts}")
    lines.append(f"📊  VIX: {perf['current_vix']:.2f}  |  REGIME: {perf['current_regime']}")
    lines.append(f"📈  SPY: ${perf['spy_price']:.2f}")
    lines.append("")

    # ── Portfolio % Change ──
    lines.append("─" * 50)
    lines.append("📊  EUREKA PORTFOLIO % CHANGE")
    lines.append("─" * 50)

    def arrow(val):
        return "▲" if val > 0 else "▼" if val < 0 else "─"

    lines.append(f"  Today:   {arrow(perf['daily_pct'])} {perf['daily_pct']:+.2f}%   (SPY: {perf['spy_daily']:+.2f}%)")
    lines.append(f"  5-Day:   {arrow(perf['weekly_pct'])} {perf['weekly_pct']:+.2f}%")
    lines.append(f"  30-Day:  {arrow(perf['monthly_pct'])} {perf['monthly_pct']:+.2f}%")
    lines.append(f"  YTD:     {arrow(perf['ytd_pct'])} {perf['ytd_pct']:+.2f}%   (SPY: {perf['spy_ytd']:+.2f}%)")
    alpha = perf['ytd_pct'] - perf['spy_ytd']
    lines.append(f"  α (YTD): {arrow(alpha)} {alpha:+.2f}%")
    lines.append("")

    # ── Regime Status ──
    if perf["regime_changed"]:
        lines.append("⚡ REGIME CHANGE DETECTED ⚡")
        lines.append(f"   {perf['prev_regime']} → {perf['current_regime']}")
        lines.append("")

    # ── Asset Daily Moves & Trade Orders ──
    lines.append("─" * 50)
    lines.append(f"🎯  ASSETS ({perf['current_regime']}) — Daily % Change")
    lines.append("─" * 50)
    lines.append(f"{'TICKER':<6} {'TARGET':<8} {'DAILY Δ':>8} {'TRADE %':>8} {'ACTION':>6}")
    lines.append("─" * 50)
    for a in actions:
        t_pct = f"{a['trade_pct']:.2f}%" if a['trade_pct'] > 0 else "  —"
        lines.append(f"  {a['ticker']:<6} {a['target_pct']:5.1f}%   {a['asset_daily_pct']:+6.2f}%  {t_pct:>7}  {a['action']}")
    lines.append("")

    # ── Trade Orders ──
    trade_actions = [a for a in actions if a["action"] != "HOLD"]
    if trade_actions:
        lines.append("─" * 50)
        lines.append("⚡  RECOMMENDED TRADE ORDERS")
        lines.append("─" * 50)
        for a in trade_actions:
            emoji = "🟢" if a["action"] == "BUY" else "🔴"
            lines.append(f"  {emoji} {a['action']}  {a['trade_pct']:.2f}% of portfolio  —  {a['ticker']} @ ${a['price']:.2f}")
            lines.append(f"     {a['reason']}")
        lines.append("")
        lines.append("⚠️  T+2 Settlement: Plan accordingly.")
    else:
        lines.append("✅  All assets within ±1.5% — no trades needed.")

    # ── Momentum Signal ──
    if momentum_signal:
        lines.append("")
        lines.append(momentum_signal)

    # ── Execution Window ──
    lines.append("")
    lines.append("─" * 50)
    lines.append("🕐  EXECUTION WINDOW: ~15 min to market close")
    lines.append("    Place percentage-based orders NOW to fill before 4:00 PM ET")
    lines.append("=" * 50)

    return "\n".join(lines)


# ============================================================
#  NOTIFICATION CHANNELS
# ============================================================

def send_telegram(message, token, chat_id, max_retries=3):
    """Send message via Telegram Bot API with retry logic."""
    import urllib.request
    import urllib.parse
    import time
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # NOTE: Do NOT use parse_mode='Markdown' — the message contains raw _+*
    # characters that break Telegram's Markdown parser and silently kill sends.
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
    }).encode()
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=15)
            print(f"[✓] Telegram notification sent (attempt {attempt}).")
            return True
        except Exception as e:
            print(f"[!] Telegram attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
    print("[!!] Telegram: ALL RETRIES EXHAUSTED — notification NOT delivered.")
    return False


def send_email(message, from_addr, app_password, to_addr):
    """Send message via Gmail SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = f"🏛️ Eureka Dispatch — {datetime.utcnow().strftime('%Y-%m-%d')}"
        msg["From"] = from_addr
        msg["To"] = to_addr
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_password)
            server.send_message(msg)
        print("[✓] Email notification sent.")
        return True
    except Exception as e:
        print(f"[!] Email failed: {e}")
        return False


# ============================================================
#  MAIN
# ============================================================

def main():
    print("\n[*] Eureka Sovereign — Daily Dispatch Generator")
    print(f"[*] Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

    # --- Fetch historical data ---
    print("[*] Fetching market data (90-day lookback)...")
    prices = fetch_historical_data(lookback_days=90)

    if prices is None:
        print("[!!] FATAL: Could not fetch required price data.")
        sys.exit(1)

    print(f"[*] Prices loaded: {list(prices.columns)}\n")

    # --- Compute Eureka portfolio performance ---
    perf = compute_eureka_performance(prices)
    if perf is None:
        print("[!!] FATAL: Could not compute portfolio performance.")
        sys.exit(1)

    # --- Generate BUY/SELL recommendations ---
    actions, momentum_signal = generate_recommendations(perf)

    # --- Format message ---
    message = format_message(perf, actions, momentum_signal)

    # --- Console output (always) ---
    print(message)

    # --- Track delivery ---
    any_sent = False
    any_channel = False

    # --- Telegram ---
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        any_channel = True
        if send_telegram(message, tg_token, tg_chat):
            any_sent = True
    else:
        print("[!!] WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set!")

    # --- Email ---
    email_addr = os.environ.get("EMAIL_ADDRESS")
    email_pass = os.environ.get("EMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", email_addr)
    if email_addr and email_pass:
        any_channel = True
        if send_email(message, email_addr, email_pass, email_to):
            any_sent = True

    if any_channel and not any_sent:
        print("\n[!!] CRITICAL: All notification channels FAILED.")
        sys.exit(1)

    print("\n[*] Dispatch complete.")


if __name__ == "__main__":
    main()
