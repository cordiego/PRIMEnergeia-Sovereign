#!/usr/bin/env python3
"""
EUREKA SOVEREIGN — Daily Trade Signal Generator
================================================
Runs daily via GitHub Actions. Fetches live prices, computes
VIX-regime-based target weights, compares to your current holdings,
and outputs exact BUY/SELL share counts.

Notification channels:
  - Telegram (via bot API)
  - Email (via SMTP / Gmail App Password)
  - Console output (for GitHub Actions logs)

Required GitHub Secrets:
  EUREKA_CAPITAL        — Total portfolio capital in USD (e.g. 10000)
  EUREKA_HOLDINGS       — JSON of current share counts, e.g. {"IAU":10,"GEV":5,...}
  TELEGRAM_BOT_TOKEN    — Telegram bot token
  TELEGRAM_CHAT_ID      — Telegram chat ID
  EMAIL_ADDRESS         — Gmail address for sending
  EMAIL_APP_PASSWORD    — Gmail App Password
  EMAIL_TO              — Recipient email address
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# ============================================================
#  CONFIGURATION
# ============================================================

EUREKA_UNIVERSE = ["IAU", "GEV", "VGSH", "VTIP", "VIXM"]
VIX_TICKER = "^VIX"
BENCHMARK = "SPY"
DRIFT_THRESHOLD = 0.05  # 5% drift triggers rebalance

REGIMES = {
    "RISK-ON":    {"vix_range": (0, 18),   "weights": {"IAU": 0.35, "GEV": 0.35, "VGSH": 0.125, "VTIP": 0.125, "VIXM": 0.05}},
    "TRANSITION": {"vix_range": (18, 28),  "weights": {"IAU": 0.20, "GEV": 0.20, "VGSH": 0.20,  "VTIP": 0.20,  "VIXM": 0.20}},
    "CRISIS":     {"vix_range": (28, 100), "weights": {"IAU": 0.10, "GEV": 0.10, "VGSH": 0.25,  "VTIP": 0.25,  "VIXM": 0.30}},
}


def classify_regime(vix_level):
    if vix_level < 18:
        return "RISK-ON"
    elif vix_level <= 28:
        return "TRANSITION"
    else:
        return "CRISIS"


# ============================================================
#  DATA FETCHING
# ============================================================

def fetch_prices():
    """Download latest prices for the Eureka universe."""
    tickers = EUREKA_UNIVERSE + [VIX_TICKER, BENCHMARK]
    prices = {}

    for t in tickers:
        try:
            df = yf.download(t, period="5d", progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                price = float(df['Close'][t].iloc[-1])
            else:
                price = float(df['Close'].iloc[-1])
            prices[t] = price
        except Exception as e:
            print(f"[!] Failed to fetch {t}: {e}")

    return prices


# ============================================================
#  SIGNAL GENERATION
# ============================================================

def generate_signals(capital, holdings, prices):
    """
    Given capital, current holdings (shares), and latest prices,
    compute exact BUY/SELL orders per asset.
    """
    vix = prices.get(VIX_TICKER, 20.0)
    regime = classify_regime(vix)
    target_weights = REGIMES[regime]["weights"]

    # Compute current portfolio value from holdings
    portfolio_value = sum(holdings.get(tk, 0) * prices.get(tk, 0) for tk in EUREKA_UNIVERSE)

    # If holdings are empty/zero, use provided capital
    if portfolio_value < 1:
        portfolio_value = capital

    spy_price = prices.get(BENCHMARK, 0)

    signals = []
    total_target_value = 0
    total_actual_value = 0

    for tk in EUREKA_UNIVERSE:
        price = prices.get(tk, 0)
        if price <= 0:
            continue

        current_shares = holdings.get(tk, 0)
        current_value = current_shares * price
        w_actual = current_value / portfolio_value if portfolio_value > 0 else 0
        w_target = target_weights.get(tk, 0)

        target_value = w_target * portfolio_value
        target_shares = int(target_value / price)
        delta_shares = target_shares - current_shares
        delta_value = delta_shares * price

        drift = (w_actual - w_target) / w_target if w_target > 0 else 0

        action = "HOLD"
        if abs(drift) > DRIFT_THRESHOLD:
            action = "BUY" if delta_shares > 0 else "SELL"

        total_target_value += target_value
        total_actual_value += current_value

        signals.append({
            "ticker": tk,
            "price": price,
            "current_shares": current_shares,
            "current_value": current_value,
            "w_actual": w_actual,
            "w_target": w_target,
            "target_shares": target_shares,
            "delta_shares": delta_shares,
            "delta_value": delta_value,
            "drift": drift,
            "action": action,
        })

    return {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "vix": vix,
        "regime": regime,
        "portfolio_value": portfolio_value,
        "spy_price": spy_price,
        "signals": signals,
    }


# ============================================================
#  MESSAGE FORMATTING
# ============================================================

def format_message(result):
    """Format the signal result into a clean text message."""
    lines = []
    lines.append("=" * 50)
    lines.append("🏛️  EUREKA SOVEREIGN — DAILY TRADE SIGNAL")
    lines.append("=" * 50)
    lines.append(f"📅  {result['timestamp']}")
    lines.append(f"📊  VIX: {result['vix']:.2f}  |  REGIME: {result['regime']}")
    lines.append(f"💰  Portfolio: ${result['portfolio_value']:,.2f}")
    lines.append(f"📈  SPY: ${result['spy_price']:.2f}")
    lines.append("-" * 50)
    lines.append(f"{'TICKER':<6} {'ACTION':<6} {'Δ SHARES':>9} {'Δ VALUE':>10} {'DRIFT':>7}")
    lines.append("-" * 50)

    for s in result["signals"]:
        action_str = s["action"]
        delta_str = f"{s['delta_shares']:+d}" if s["action"] != "HOLD" else "—"
        value_str = f"${s['delta_value']:+,.0f}" if s["action"] != "HOLD" else "—"
        drift_str = f"{s['drift']*100:+.1f}%"

        lines.append(f"{s['ticker']:<6} {action_str:<6} {delta_str:>9} {value_str:>10} {drift_str:>7}")

    lines.append("-" * 50)

    # Action summary
    actions = [s for s in result["signals"] if s["action"] != "HOLD"]
    if actions:
        lines.append(f"\n⚡ {len(actions)} TRADE(S) REQUIRED:")
        for s in actions:
            emoji = "🟢" if s["action"] == "BUY" else "🔴"
            lines.append(f"  {emoji} {s['action']} {abs(s['delta_shares'])} shares of {s['ticker']} @ ${s['price']:.2f} (${abs(s['delta_value']):,.0f})")
        lines.append("\n⚠️  T+2 Settlement: Plan accordingly to avoid Good Faith Violations.")
    else:
        lines.append("\n✅  ALL POSITIONS WITHIN TOLERANCE — No trades needed.")

    lines.append(f"\n{'=' * 50}")
    lines.append(f"Regime Weights ({result['regime']}):")
    w = REGIMES[result['regime']]['weights']
    lines.append("  " + " | ".join(f"{tk}: {v*100:.0f}%" for tk, v in w.items()))
    lines.append("=" * 50)

    return "\n".join(lines)


# ============================================================
#  NOTIFICATION CHANNELS
# ============================================================

def send_telegram(message, token, chat_id):
    """Send message via Telegram Bot API."""
    import urllib.request
    import urllib.parse
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        print("[✓] Telegram notification sent.")
    except Exception as e:
        print(f"[!] Telegram failed: {e}")


def send_email(message, from_addr, app_password, to_addr):
    """Send message via Gmail SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = f"🏛️ Eureka Signal — {datetime.utcnow().strftime('%Y-%m-%d')}"
        msg["From"] = from_addr
        msg["To"] = to_addr
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_password)
            server.send_message(msg)
        print("[✓] Email notification sent.")
    except Exception as e:
        print(f"[!] Email failed: {e}")


# ============================================================
#  MAIN
# ============================================================

def main():
    print("\n[*] Eureka Sovereign — Daily Signal Generator")
    print(f"[*] Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

    # --- Read config from environment / secrets ---
    capital = float(os.environ.get("EUREKA_CAPITAL", "10000"))
    holdings_str = os.environ.get("EUREKA_HOLDINGS", "{}")
    try:
        holdings = json.loads(holdings_str)
    except json.JSONDecodeError:
        print("[!] Invalid EUREKA_HOLDINGS JSON. Using empty holdings.")
        holdings = {}

    # --- Fetch live prices ---
    print("[*] Fetching live market data...")
    prices = fetch_prices()

    if not prices or VIX_TICKER not in prices:
        print("[!!] FATAL: Could not fetch required price data.")
        sys.exit(1)

    print(f"[*] Prices loaded for {len(prices)} tickers.\n")

    # --- Generate signals ---
    result = generate_signals(capital, holdings, prices)
    message = format_message(result)

    # --- Console output (always) ---
    print(message)

    # --- Telegram ---
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        send_telegram(message, tg_token, tg_chat)

    # --- Email ---
    email_addr = os.environ.get("EMAIL_ADDRESS")
    email_pass = os.environ.get("EMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", email_addr)
    if email_addr and email_pass:
        send_email(message, email_addr, email_pass, email_to)

    print("\n[*] Signal generation complete.")


if __name__ == "__main__":
    main()
