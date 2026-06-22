#!/usr/bin/env python3
"""
EUREKA SOVEREIGN — Precision Execution & Dynamic Allocation Engine
====================================================================
Runs during the final hour of trading (3:00 PM - 4:00 PM ET) or ad-hoc.
Fetches daily prices for Kelly Optimization + VIX continuous scaling.
Fetches 5m intraday prices for VWAP and RSI to pinpoint exact entry/exit.
"""

import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings

# New imports for layers 2, 3, 4
from hmmlearn.hmm import GaussianHMM
import pandas_market_calendars as mcal
try:
    import pandas_datareader.data as web
except ImportError:
    web = None

# Add parent directory to path to import core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../Eureka/pipelines')))
from core.eureka_math import (
    compute_kelly_weights, compute_dynamic_regime_weights, 
    compute_rsi, compute_vwap, compute_tail_dependence_copula, compute_cointegration_zscore
)
from eureka_options_flow import generate_options_flow
from eureka_microstructure import generate_microstructure_signals
from eureka_execution_rl import train_and_execute_rl

# Pre-market integration (AM -> PM feedback loop)
try:
    from eureka_premarket import PREMARKET_HISTORY_PATH
    import json as _json
    _PREMARKET_AVAILABLE = True
except ImportError:
    _PREMARKET_AVAILABLE = False

warnings.filterwarnings("ignore")

# ============================================================
#  CONFIGURATION
# ============================================================
EUREKA_UNIVERSE = ["SNXX", "SNDK", "SCHD"]
VIX_TICKER = "^VIX"
BENCHMARK = "SPY"
CRISIS_ANCHOR = "SCHD"
DEADBAND_THRESHOLD = 0.025  # 2.5% minimum drift to trigger a trade

# ============================================================
#  DATA FETCHING
# ============================================================
def fetch_daily_data(lookback_days=252):
    tickers = EUREKA_UNIVERSE + [VIX_TICKER, BENCHMARK]
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    
    df = yf.download(tickers, start=start_date, progress=False)
    if df.empty:
        return None
    
    if isinstance(df.columns, pd.MultiIndex):
        closes = df['Close']
    else:
        closes = df
    return closes.dropna()

def fetch_intraday_data():
    data = {}
    for t in EUREKA_UNIVERSE:
        try:
            # Layer 1: 5d period for better VWAP & Gap Context
            df = yf.download(t, period="5d", interval="5m", progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                data[t] = df
        except Exception as e:
            pass
    return data

def fetch_sndk_options_skew():
    """
    Layer 3: Fetch nearest expiry options for SNDK and compute IV Put/Call Skew.
    """
    try:
        sndk = yf.Ticker("SNDK")
        expirations = sndk.options
        if not expirations:
            return 1.0  # Default neutral
        
        # Nearest expiry
        opts = sndk.option_chain(expirations[0])
        iv_calls = opts.calls['impliedVolatility'].mean()
        iv_puts  = opts.puts['impliedVolatility'].mean()
        
        if pd.isna(iv_calls) or pd.isna(iv_puts) or iv_calls == 0:
            return 1.0
            
        skew = iv_puts / iv_calls
        return float(skew)
    except Exception as e:
        return 1.0

def fetch_macro_pulse():
    """
    Layer 4: Fetch 2Y-10Y spread (FRED) and FOMC/Macro day flag.
    """
    spread = 1.0  # Default positive (normal curve)
    if web is not None:
        try:
            end = datetime.now()
            start = end - timedelta(days=30)
            df = web.DataReader('T10Y2Y', 'fred', start, end)
            if not df.empty:
                spread = float(df.iloc[-1].values[0])
        except Exception as e:
            pass
            
    is_high_impact = False
    macro_event_name = ""
    
    import requests
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            events = resp.json()
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            for event in events:
                if event.get("country") == "USD" and event.get("impact") == "High":
                    event_date_str = event.get("date", "")[:10]
                    if event_date_str:
                        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                        if event_date == today or event_date == tomorrow:
                            is_high_impact = True
                            macro_event_name = event.get("title", "High Impact USD Event")
                            try:
                                from transformers import pipeline
                                classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert")
                                res = classifier(macro_event_name)[0]
                                sentiment_score = 1.0 if res['label'] == 'positive' else -1.0 if res['label'] == 'negative' else 0.0
                            except Exception:
                                sentiment_score = 0.0
                            break
    except Exception as e:
        pass
        
    return spread, is_high_impact, macro_event_name, locals().get('sentiment_score', 0.0)

# ============================================================
#  EUREKA ENGINE
# ============================================================
def classify_regime_hmm(vix_closes: pd.Series) -> str:
    """
    Layer 2: HMM Regime Detection using VIX returns.
    """
    if len(vix_closes) < 30:
        return "NEUTRAL"
        
    returns = vix_closes.pct_change().dropna().values.reshape(-1, 1)
    try:
        model = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
        model.fit(returns)
        # Predict hidden states
        states = model.predict(returns)
        current_state = states[-1]
        
        # Map states based on their average VIX return (highest mean return = BEAR)
        means = model.means_.flatten()
        sorted_states = np.argsort(means)
        
        state_map = {}
        state_map[sorted_states[0]] = "BULL"
        state_map[sorted_states[1]] = "NEUTRAL"
        state_map[sorted_states[2]] = "BEAR"
        
        return state_map.get(current_state, "NEUTRAL")
    except Exception as e:
        return "NEUTRAL"

def run_precision_eureka():
    daily_closes = fetch_daily_data(252)
    if daily_closes is None or daily_closes.empty:
        return {"error": "Failed to fetch daily data"}

    intraday_data = fetch_intraday_data()
    iv_skew = fetch_sndk_options_skew()
    macro_spread, is_macro_day, macro_event, sentiment_score = fetch_macro_pulse()

    # Calculate returns for historical stats
    returns = daily_closes.pct_change().dropna()
    spy_returns = returns[BENCHMARK] if BENCHMARK in returns.columns else pd.Series(0, index=returns.index)
    
    kelly_weights = compute_kelly_weights(returns[EUREKA_UNIVERSE], kelly_fraction=0.5)
    
    # Identify Regime via HMM
    vix_series = daily_closes[VIX_TICKER]
    current_regime = classify_regime_hmm(vix_series)
    # Mock history of regimes to prevent breaking existing formatting
    regime_history = ["UNKNOWN"] * (len(returns) - 1) + [current_regime]
    
    # Portfolio historical reconstruction (approximate)
    port_returns = []
    
    for i in range(len(returns)):
        idx = returns.index[i]
        vix_val = float(vix_series.loc[idx] if idx in vix_series.index else 20.0)
        # Using the same fixed kelly weights for the history to approximate
        w = compute_dynamic_regime_weights(
            vix_val, kelly_weights, EUREKA_UNIVERSE, crisis_anchor=CRISIS_ANCHOR,
            hmm_regime=current_regime, iv_skew=1.0, macro_spread=1.0, is_macro_day=False # history defaults
        )
        day_ret = sum(float(returns[tk].iloc[i]) * w.get(tk, 0) for tk in EUREKA_UNIVERSE if tk in returns.columns)
        port_returns.append(day_ret)

    port_returns = pd.Series(port_returns, index=returns.index)
    cum_returns = (1 + port_returns).cumprod()
    spy_cum = (1 + spy_returns).cumprod()

    # Current stats
    current_vix = float(vix_series.iloc[-1])
    prev_regime = regime_history[-2] if len(regime_history) > 1 else current_regime
    regime_changed = (current_regime != prev_regime)
    
    # New Elite Metrics
    copula_penalty = compute_tail_dependence_copula(returns[EUREKA_UNIVERSE])
    
    out_dir = os.path.dirname(os.path.abspath(__file__))
    generate_options_flow(days_history=10, out_dir=out_dir)
    generate_microstructure_signals(ticker=BENCHMARK, days_history=10, out_dir=out_dir)
    
    try:
        df_opt = pd.read_csv(os.path.join(out_dir, "options_flow_signals.csv"))
        negative_gamma = bool(df_opt["NEGATIVE_GAMMA_REGIME"].iloc[-1])
    except Exception:
        negative_gamma = False
        
    try:
        df_mic = pd.read_csv(os.path.join(out_dir, f"microstructure_{BENCHMARK}.csv"))
        high_toxicity = bool(df_mic["HIGH_TOXICITY_FLAG"].iloc[-1])
    except Exception:
        high_toxicity = False

    if negative_gamma and high_toxicity:
        copula_penalty = max(copula_penalty, 3.0)
    
    # Recalculate Kelly weights for today utilizing the dynamic copula_penalty cap
    kelly_weights = compute_kelly_weights(returns[EUREKA_UNIVERSE], copula_penalty=copula_penalty, kelly_fraction=0.5)

    target_weights = compute_dynamic_regime_weights(
        current_vix, kelly_weights, EUREKA_UNIVERSE, crisis_anchor=CRISIS_ANCHOR,
        hmm_regime=current_regime, iv_skew=iv_skew, macro_spread=macro_spread, is_macro_day=is_macro_day,
        copula_penalty=copula_penalty
    )

    # % Changes
    daily_pct = float(port_returns.iloc[-1]) * 100 if len(port_returns) >= 1 else 0.0
    weekly_pct = float((cum_returns.iloc[-1] / cum_returns.iloc[-6] - 1) * 100) if len(cum_returns) >= 6 else daily_pct
    monthly_pct = float((cum_returns.iloc[-1] / cum_returns.iloc[-22] - 1) * 100) if len(cum_returns) >= 22 else weekly_pct

    ytd_start = cum_returns.index[cum_returns.index >= f"{datetime.now().year}-01-01"]
    ytd_pct = float((cum_returns.iloc[-1] / cum_returns.loc[ytd_start[0]] - 1) * 100) if len(ytd_start) > 0 else 0.0

    spy_daily = float(spy_returns.iloc[-1]) * 100 if len(spy_returns) >= 1 else 0.0
    spy_ytd_start = spy_cum.index[spy_cum.index >= f"{datetime.now().year}-01-01"]
    spy_ytd = float((spy_cum.iloc[-1] / spy_cum.loc[spy_ytd_start[0]] - 1) * 100) if len(spy_ytd_start) > 0 else 0.0

    spy_price = float(daily_closes[BENCHMARK].iloc[-1])

    actions = []
    
    for tk in EUREKA_UNIVERSE:
        w_target = target_weights.get(tk, 0)
        asset_daily = float(returns[tk].iloc[-1]) if tk in returns.columns else 0.0
        
        df_5m = intraday_data.get(tk)
        intraday_signal = "HOLD"
        reason = ""
        current_price = float(daily_closes[tk].iloc[-1])
        gap_pct = 0.0
        
        if df_5m is not None and not df_5m.empty and len(df_5m) > 1:
            current_price = float(df_5m['Close'].iloc[-1])
            df_5m['VWAP'] = compute_vwap(df_5m)
            df_5m['RSI'] = compute_rsi(df_5m['Close'], period=14)
            
            # Layer 1: Intraday Opening Gap
            # Try to grab the close from yesterday and open from today
            # Given we have 5d of 5m data, we can just grab the open of the current day
            # This is a basic proxy for the gap: (Today's Open - Yesterday's Close) / Yesterday's Close
            # We'll just look for index jumps to find day splits
            day_changes = df_5m.index.day != pd.Series(df_5m.index.day).shift(1).fillna(df_5m.index.day[0])
            day_start_indices = np.where(day_changes)[0]
            if len(day_start_indices) > 0:
                last_day_start = day_start_indices[-1]
                if last_day_start > 0:
                    yest_close = df_5m['Close'].iloc[last_day_start - 1]
                    today_open = df_5m['Open'].iloc[last_day_start]
                    gap_pct = (today_open - yest_close) / yest_close
            
            last_vwap = float(df_5m['VWAP'].iloc[-1])
            last_rsi = float(df_5m['RSI'].iloc[-1])
            
            stat_arb_reason = ""
            if tk in ["SNXX", "SNDK"]:
                other_tk = "SNDK" if tk == "SNXX" else "SNXX"
                if other_tk in returns.columns and tk in returns.columns:
                    z_score = compute_cointegration_zscore(returns[tk], returns[other_tk])
                    if z_score < -2.0:
                        stat_arb_reason = "STATARB BUY"
                        intraday_signal = "BUY"
                    elif z_score > 2.0:
                        stat_arb_reason = "STATARB SELL"
                        intraday_signal = "SELL"
                        
            if stat_arb_reason:
                reason = stat_arb_reason
            elif current_price < last_vwap and gap_pct < -0.01 and last_rsi < 35:
                if negative_gamma and high_toxicity:
                    intraday_signal = "HOLD"
                    reason = "TOXIC AVOID"
                else:
                    intraday_signal = "BUY"
                    reason = "GAP+DIP"
            elif current_price < last_vwap and last_rsi < 35:
                if negative_gamma and high_toxicity:
                    intraday_signal = "HOLD"
                    reason = "TOXIC AVOID"
                else:
                    intraday_signal = "BUY"
                    reason = "DIP"
            elif current_price > last_vwap and last_rsi > 65:
                intraday_signal = "SELL"
                reason = "PEAK"
            elif gap_pct > 0.02 and current_price < last_vwap:
                intraday_signal = "SELL"
                reason = "FADE GAP"
            else:
                intraday_signal = "HOLD"
                reason = "FLAT"
                
            rl_exec_pct = w_target * 100
            if intraday_signal != "HOLD" and w_target > 0:
                rl_exec_pct, _ = train_and_execute_rl(w_target * 100, current_price, df_5m)
        else:
            reason = "MOC"
            rl_exec_pct = w_target * 100
            
        # ── Discretized Trade Conviction (25, 50, 75, 100) ──
        max_w = 0.35
        if intraday_signal == "BUY":
            conviction = min(1.0, w_target / max_w)
        elif intraday_signal == "SELL":
            conviction = min(1.0, (max_w - w_target) / max_w)
        else:
            conviction = 0.0
            
        if conviction > 0.75: trade_pct = 100
        elif conviction > 0.50: trade_pct = 75
        elif conviction > 0.25: trade_pct = 50
        else: trade_pct = 25

        actions.append({
            "ticker": tk,
            "price": current_price,
            "target_pct": w_target * 100,
            "asset_daily_pct": asset_daily * 100,
            "intraday_signal": intraday_signal,
            "reason": reason,
            "gap_pct": gap_pct,
            "rl_exec_pct": rl_exec_pct,
            "trade_pct": trade_pct
        })

    # ── Load Pre-Market State (AM feedback loop) ──
    premarket_state = None
    if _PREMARKET_AVAILABLE:
        try:
            import os as _os
            if _os.path.exists(PREMARKET_HISTORY_PATH):
                with open(PREMARKET_HISTORY_PATH, 'r') as _f:
                    _pm_hist = _json.load(_f)
                today_key = datetime.now().strftime("%Y-%m-%d")
                if today_key in _pm_hist:
                    premarket_state = _pm_hist[today_key]
                    # Fill in actual SNXX return for feedback
                    for a in actions:
                        if a["ticker"] == "SNXX":
                            premarket_state["actual_snxx_close_pct"] = a["asset_daily_pct"]
                            pm_sig = premarket_state.get("pm_signal", "HOLD")
                            actual = a["asset_daily_pct"]
                            if pm_sig in ("STRONG_BUY", "BUY"):
                                premarket_state["signal_correct"] = actual >= 0
                            elif pm_sig in ("SELL", "AVOID"):
                                premarket_state["signal_correct"] = actual < 0
                            else:
                                premarket_state["signal_correct"] = None
                    # Save updated state back
                    _pm_hist[today_key] = premarket_state
                    with open(PREMARKET_HISTORY_PATH, 'w') as _f:
                        _json.dump(_pm_hist, _f, indent=2, default=str)
        except Exception:
            pass

    return {
        "current_vix": current_vix,
        "current_regime": current_regime,
        "prev_regime": prev_regime,
        "regime_changed": regime_changed,
        "iv_skew": iv_skew,
        "macro_spread": macro_spread,
        "is_macro_day": is_macro_day,
        "macro_event": macro_event,
        "sentiment_score": sentiment_score,
        "negative_gamma": negative_gamma,
        "high_toxicity": high_toxicity,
        "copula_penalty": copula_penalty,
        "daily_pct": daily_pct,
        "weekly_pct": weekly_pct,
        "monthly_pct": monthly_pct,
        "ytd_pct": ytd_pct,
        "spy_daily": spy_daily,
        "spy_ytd": spy_ytd,
        "spy_price": spy_price,
        "actions": actions,
        "premarket_state": premarket_state,
    }

# ============================================================
#  MESSAGE FORMATTING
# ============================================================
def format_message(perf):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []

    lines.append("=" * 55)
    lines.append("🏛️  EUREKA SOVEREIGN — DAILY DISPATCH")
    lines.append("=" * 55)
    lines.append(f"📅  {ts}")
    lines.append(f"📊  VIX: {perf['current_vix']:.2f}  |  REGIME (HMM): {perf['current_regime']}")
    
    # Layer 3/4 Data
    skew_alert = "⚠️ RISK" if perf['iv_skew'] > 1.1 else "✅ NORM"
    spread_alert = "⚠️ INVERTED" if perf['macro_spread'] < 0 else "✅ NORM"
    lines.append(f"📈  SNDK IV SKEW: {perf['iv_skew']:.2f} [{skew_alert}]")
    lines.append(f"🏦  2Y-10Y SPREAD: {perf['macro_spread']:+.2f} [{spread_alert}]")
    
    if perf['is_macro_day']:
        lines.append(f"🚨 MACRO ALERT: {perf['macro_event']} detected in < 48hrs (Sentiment: {perf['sentiment_score']}). Moving to Cash/Safety.")
        
    lines.append(f"🔮  COPULA TAIL RISK: {perf['copula_penalty']:.2f}X")
    lines.append(f"🩸  DARK POOL / GEX: {'⚠️ TOXIC/NEGATIVE GAMMA' if (perf['negative_gamma'] and perf['high_toxicity']) else '✅ NORM'}")
    lines.append(f"📉  SPY: ${perf['spy_price']:.2f}")
    lines.append("")

    # ── Portfolio % Change ──
    lines.append("─" * 55)
    lines.append("📊  EUREKA PORTFOLIO % CHANGE")
    lines.append("─" * 55)

    def arrow(val):
        return "▲" if val > 0 else "▼" if val < 0 else "─"

    lines.append(f"  Today:   {arrow(perf['daily_pct'])} {perf['daily_pct']:+.2f}%   (SPY: {perf['spy_daily']:+.2f}%)")
    lines.append(f"  5-Day:   {arrow(perf['weekly_pct'])} {perf['weekly_pct']:+.2f}%")
    lines.append(f"  30-Day:  {arrow(perf['monthly_pct'])} {perf['monthly_pct']:+.2f}%")
    lines.append(f"  YTD:     {arrow(perf['ytd_pct'])} {perf['ytd_pct']:+.2f}%   (SPY: {perf['spy_ytd']:+.2f}%)")
    alpha = perf['ytd_pct'] - perf['spy_ytd']
    lines.append(f"  α (YTD): {arrow(alpha)} {alpha:+.2f}%")
    lines.append("")

    if perf["regime_changed"]:
        lines.append("⚡ REGIME CHANGE DETECTED ⚡")
        lines.append(f"   {perf['prev_regime']} → {perf['current_regime']}")
        lines.append("")

    lines.append("─" * 55)
    lines.append("💰  OPTIMAL PORTFOLIO ALLOCATION (FRACTIONAL KELLY)")
    lines.append("─" * 55)
    for a in perf['actions']:
        role = "(Crisis Anchor/Cash)" if a['ticker'] == CRISIS_ANCHOR else "(Risk-adjusted Kelly)"
        lines.append(f"  ➜ {a['ticker']:<6}: {a['target_pct']:5.1f}% of total portfolio {role}")
    lines.append("")

    # ── Asset Daily Moves & Trade Orders ──
    lines.append("─" * 55)
    lines.append(f"🎯  ASSETS ({perf['current_regime']}) — Precision Timing")
    lines.append("─" * 55)
    lines.append(f"{'TICKER':<6} {'TARGET':<8} {'GAP %':>7} {'TIMING':>16}")
    lines.append("─" * 55)
    for a in perf['actions']:
        timing_str = f"{a['intraday_signal']} ({a['reason']})"
        lines.append(f"  {a['ticker']:<6} {a['target_pct']:5.1f}%   {a['gap_pct']*100:+5.2f}%  {timing_str:>17}")
    lines.append("")

    lines.append("─" * 55)
    lines.append("⚡  EXECUTION ORDERS")
    lines.append("─" * 55)
    trade_recommended = False
    for a in perf['actions']:
        if a['intraday_signal'] != "HOLD":
            trade_recommended = True
            emoji = "🟢" if a['intraday_signal'] == "BUY" else "🔴"
            lines.append(f"  {emoji} {a['intraday_signal']} {a['trade_pct']}% OF USUAL BLOCK — Target {a['target_pct']:.1f}% for {a['ticker']} | RL Exec: {a['rl_exec_pct']:.2f}% @ ${a['price']:.2f} ({a['reason']})")
    
    if not trade_recommended:
         lines.append("  ⏳  All assets neutrally priced intraday (No exact entry/exit moments).")
         lines.append("      Hold or use Market-On-Close/TWAP to hit target allocations.")
         
    # ── Pre-Market Feedback Loop ──
    pm = perf.get("premarket_state")
    if pm:
        lines.append("")
        lines.append("\u2500" * 55)
        lines.append("\U0001f305  PRE-MARKET FEEDBACK (AM \u2192 PM)")
        lines.append("\u2500" * 55)
        am_signal = pm.get('pm_signal', '?')
        am_conv = pm.get('pm_conviction', 0)
        actual = pm.get('actual_snxx_close_pct', 0) or 0
        correct = pm.get('signal_correct')
        verdict = "\u2705 CORRECT" if correct is True else "\u274c WRONG" if correct is False else "\u26aa N/A"
        lines.append(f"  AM Signal: {am_signal} (conviction: {am_conv:+.3f})")
        lines.append(f"  SNXX Actual:  {actual:+.2f}%")
        lines.append(f"  Verdict:  {verdict}")

    lines.append("=" * 55)
    return "\n".join(lines)

# ============================================================
#  MAIN
# ============================================================
def send_telegram(message):
    try:
        from core.alerts import PRIMAlerts
        alerts = PRIMAlerts()
        return alerts._send_telegram(message)
    except Exception as e:
        print(f"[!] Alert failed: {e}")
        return False

def main():
    print("\n[*] Eureka Sovereign — Precision Execution Engine")
    results = run_precision_eureka()
    
    if "error" in results:
        print(f"[!] {results['error']}")
        sys.exit(1)
        
    message = format_message(results)
    print(message)
    
    # Send Notification
    print("\n[*] Sending Telegram Notification...")
    success = send_telegram(message)
    if success:
        print("[✓] Notification delivered successfully.")
    else:
        print("[!] Failed to send notification or Telegram not configured.")

if __name__ == "__main__":
    main()
