import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime
import time
import warnings
import os
import sys

# Add PRIME-Kernel path for HopfieldMemory
sys.path.insert(0, "/Users/diegocordoba/diegocordoba/lib")
from prime_kernel.hopfield import HopfieldValueMemory

warnings.filterwarnings("ignore")

# Try to import auto-refresh, but degrade gracefully
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, limit=None, key="live_refresh")  # Refresh every 60s
except ImportError:
    pass

# ============================================================
#  EUREKA SOVEREIGN — 3-Ticker Fixed Portfolio Engine
#  SNDK (20%) | SNXX (50%) | SCHD (30%)
# ============================================================

st.set_page_config(
    page_title="Eureka Sovereign | Portfolio Engine",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PREMIUM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background-color: #050810; }
[data-testid="stSidebar"] { background-color: #0a0f1a; }

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
    border: 1px solid #1a2744;
    border-radius: 8px;
    padding: 16px 14px;
    box-shadow: 0 4px 20px rgba(0, 209, 255, 0.04);
    overflow: visible;
    min-width: 0;
}
div[data-testid="stMetricValue"] {
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(18px, 2.2vw, 32px) !important;
    font-weight: 700;
    text-shadow: 0 0 12px rgba(0,209,255,0.3);
    white-space: nowrap;
}
div[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace;
    color: #c8d6e5;
    font-size: clamp(11px, 1.1vw, 14px) !important;
    white-space: nowrap;
}
div[data-testid="stMetricLabel"] {
    color: #c8d6e5;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: clamp(10px, 1vw, 13px) !important;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    white-space: nowrap;
}
[data-testid="stMetric"] > div { overflow: visible !important; }
[data-testid="stMetric"] label { overflow: visible !important; white-space: nowrap !important; }

.stTabs [data-baseweb="tab-list"] {
    gap: 0px; background-color: #0a0f1a; border-radius: 8px; padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #c8d6e5; font-weight: 600; font-size: 14px;
    letter-spacing: 0.5px; border-radius: 6px; padding: 10px 16px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #00d1ff22, #0066ff22);
    color: #00d1ff !important; border-bottom: none;
}

.section-header {
    color: #00d1ff; font-family: 'JetBrains Mono', monospace;
    font-size: 14px; letter-spacing: 2px; text-transform: uppercase;
    border-bottom: 1px solid #1a2744; padding-bottom: 8px; margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  UNIVERSE
# ============================================================

PORTFOLIO_WEIGHTS = {
    "SNDK": 0.20,
    "SNXX": 0.50,
    "SCHD": 0.30
}
FULL_UNIVERSE = list(PORTFOLIO_WEIGHTS.keys())
BENCHMARK = "SPY"
VIX_TICKER = "^VIX"
ALL_TICKERS = FULL_UNIVERSE + [BENCHMARK, VIX_TICKER]

ASSET_META = {
    "SNDK": {"desc": "Sandisk", "category": "Tech Growth", "color": "#00d1ff"},
    "SNXX": {"desc": "2× SNDK", "category": "Leveraged Growth", "color": "#ff4b4b"},
    "SCHD": {"desc": "US Dividend Equity", "category": "Yield", "color": "#a78bfa"}
}

def classify_vix(vix_level):
    if vix_level < 18: return "LOW"
    elif vix_level <= 28: return "ELEVATED"
    else: return "HIGH"

def _safe_close(df, ticker):
    try:
        if isinstance(df.columns, pd.MultiIndex):
            if ('Close', ticker) in df.columns:
                return df[('Close', ticker)]
            close_cols = df['Close']
            if ticker in close_cols.columns:
                return close_cols[ticker]
            if len(close_cols.columns) == 1:
                return close_cols.iloc[:, 0]
        elif 'Close' in df.columns:
            return df['Close']
    except Exception:
        pass
    return None

def compute_rsi(series, period=14):
    delta = series.diff().dropna()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def compute_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def compute_black_litterman(returns_df, prior_weights_dict, ticker_signals, tau=0.05, delta=2.5):
    tickers = list(prior_weights_dict.keys())
    ret = returns_df[tickers].dropna()
    if ret.empty:
        return {k: float(v) for k, v in prior_weights_dict.items()}
        
    Sigma = ret.cov() * 252
    W = np.array([prior_weights_dict[tk] for tk in tickers])
    Pi = delta * Sigma.dot(W)
    
    K = len(tickers)
    P = np.eye(K)
    Q = np.zeros(K)
    Omega = np.zeros((K, K))
    
    for i, tk in enumerate(tickers):
        sig_info = ticker_signals.get(tk, {})
        signal = sig_info.get("signal", "HOLD")
        if "BUY" in signal:
            sig_type = "BUY"
        elif "SELL" in signal:
            sig_type = "SELL"
        else:
            sig_type = "HOLD"
            
        conviction = sig_info.get("conviction", 50)
        
        shift = (conviction / 100.0) * 0.15
        if sig_type == "BUY":
            Q[i] = Pi.iloc[i] + shift
        elif sig_type == "SELL":
            Q[i] = Pi.iloc[i] - shift
        else:
            Q[i] = Pi.iloc[i]
            
        c = max(0.01, conviction / 100.0)
        base_var = tau * Sigma.iloc[i, i]
        Omega[i, i] = base_var * (1.1 - c)

    tau_Sigma = tau * Sigma
    tau_Sigma_inv = np.linalg.inv(tau_Sigma)
    Omega_inv = np.linalg.inv(Omega)
    
    M_inv = tau_Sigma_inv + P.T.dot(Omega_inv).dot(P)
    M = np.linalg.inv(M_inv)
    
    term1 = tau_Sigma_inv.dot(Pi)
    term2 = P.T.dot(Omega_inv).dot(Q)
    ER = M.dot(term1 + term2)
    
    delta_Sigma_inv = np.linalg.inv(delta * Sigma)
    w_BL = delta_Sigma_inv.dot(ER)
    
    w_BL = np.clip(w_BL, 0, None)
    if np.sum(w_BL) == 0:
        w_BL = W
    else:
        w_BL = w_BL / np.sum(w_BL)
        
    return {tk: float(w_BL[i]) for i, tk in enumerate(tickers)}

# ============================================================
#  LIVE DATA ENGINE
# ============================================================
@st.cache_resource
def load_neural_memory():
    try:
        mem_path = "/Users/diegocordoba/diegocordoba/market_memory.pkl"
        if os.path.exists(mem_path):
            return HopfieldValueMemory.load(mem_path)
    except Exception as e:
        pass
    return None

@st.cache_data(ttl=300)
def load_market_data():
    all_data = {}
    for t in ALL_TICKERS:
        for attempt in range(3):
            try:
                df = yf.download(t, start="2014-01-01", progress=False)
                if df.empty:
                    if attempt < 2: time.sleep(1)
                    continue
                s = _safe_close(df, t)
                if s is None or s.dropna().empty:
                    if attempt < 2: time.sleep(1)
                    continue
                s = s.dropna()
                s.name = t
                all_data[t] = s
                break
            except Exception:
                if attempt < 2: time.sleep(1)

    if not all_data or VIX_TICKER not in all_data:
        return None

    prices_full = pd.DataFrame(all_data).ffill().dropna()
    if prices_full.empty: return None

    # Fix: Ensure all columns are explicitly float64 to avoid DataError
    prices_full = prices_full.astype(np.float64)
    
    current_vix = float(prices_full[VIX_TICKER].iloc[-1])
    vix_label = classify_vix(current_vix)

    mom_crash_flags = {}
    for tk in FULL_UNIVERSE:
        if tk in prices_full.columns:
            closes_full = prices_full[tk].dropna()
            long_window = min(252, max(22, len(closes_full) - 1))
            short_window = max(1, int(long_window * (21/252)))
            mom_series = closes_full.shift(short_window) / closes_full.shift(long_window) - 1
            if not mom_series.dropna().empty:
                mom_decile = mom_series.quantile(0.90)
                current_mom = mom_series.iloc[-1]
                mom_crash_flags[tk] = pd.notna(current_mom) and (current_mom >= mom_decile)
            else:
                mom_crash_flags[tk] = False

    cut_date = "2024-04-02"
    prices = prices_full.loc[cut_date:] if cut_date in prices_full.index or pd.to_datetime(cut_date) in prices_full.index else prices_full
    if prices.empty: prices = prices_full

    returns = prices.pct_change().dropna()

    vix_series = prices[VIX_TICKER]
    
    # Portfolio Returns (Fixed Weights)
    # Rebalance daily back to target weights (simplest assumption)
    port_returns = pd.Series(0.0, index=returns.index)
    for tk, w in PORTFOLIO_WEIGHTS.items():
        if tk in returns.columns:
            port_returns += returns[tk] * w

    cum_returns = (1 + port_returns).cumprod()
    spy_cum = (1 + returns[BENCHMARK]).cumprod() if BENCHMARK in returns.columns else None

    # Rolling analytics
    rolling_vol_20 = port_returns.rolling(20).std() * np.sqrt(252)
    rolling_vol_60 = port_returns.rolling(60).std() * np.sqrt(252)
    rolling_sharpe = (port_returns.rolling(60).mean() * 252) / (port_returns.rolling(60).std() * np.sqrt(252))

    # Key metrics
    total_return = float((cum_returns.iloc[-1] - 1) * 100)
    spy_return = float((spy_cum.iloc[-1] - 1) * 100) if spy_cum is not None else 0.0
    max_dd = float((cum_returns / cum_returns.cummax() - 1).min() * 100)
    ann_vol = float(port_returns.std() * np.sqrt(252) * 100)
    ann_return = float(port_returns.mean() * 252)
    sharpe = float(ann_return / (port_returns.std() * np.sqrt(252))) if port_returns.std() > 0 else 0.0
    alpha = float(total_return - spy_return)

    current_vix = float(vix_series.iloc[-1])
    vix_label = classify_vix(current_vix)

    # Individual asset stats
    asset_stats = {}
    ticker_signals = {}
    for tk in FULL_UNIVERSE:
        if tk in returns.columns:
            r = returns[tk]
            asset_stats[tk] = {
                "return": float((prices[tk].iloc[-1] / prices[tk].iloc[0] - 1) * 100),
                "vol": float(r.std() * np.sqrt(252) * 100),
                "sharpe": float((r.mean() * 252) / (r.std() * np.sqrt(252))) if r.std() > 0 else 0.0,
                "max_dd": float(((prices[tk] / prices[tk].cummax() - 1).min()) * 100),
                "last_price": float(prices[tk].iloc[-1]),
            }
            
            closes = prices[tk].dropna()
            if len(closes) >= 52:
                rsi = compute_rsi(closes, 14)
                current_rsi = float(rsi.iloc[-1]) if not rsi.empty and pd.notna(rsi.iloc[-1]) else 50.0
                ema_20 = float(compute_ema(closes, 20).iloc[-1])
                ema_50 = float(compute_ema(closes, 50).iloc[-1])
                ema_trend = "BULLISH" if ema_20 > ema_50 else "BEARISH"

                high_20 = float(closes.rolling(20).max().iloc[-1])
                low_20 = float(closes.rolling(20).min().iloc[-1])

                if current_rsi < 30: 
                    signal = "BUY"
                    dist_to_trigger = "TRIGGERED"
                elif current_rsi > 70: 
                    if tk in ["SNDK", "SNXX"] and mom_crash_flags.get(tk, False):
                        signal = "HALVE POSITION"
                        dist_to_trigger = "MOM CRASH REGIME"
                    else:
                        signal = "SELL"
                        dist_to_trigger = "TRIGGERED"
                else: 
                    signal = "HOLD"
                    if ema_trend == "BULLISH":
                        dist = max(0.1, ((high_20 / float(prices[tk].iloc[-1])) - 1) * 100)
                        dist_to_trigger = f"Needs +{dist:.1f}% for MOM_TP"
                    else:
                        dist = max(0.1, ((float(prices[tk].iloc[-1]) / low_20) - 1) * 100)
                        dist_to_trigger = f"Needs -{dist:.1f}% for DIP_BUY"

                # Calculate conviction
                try:
                    import json
                    with open("/Users/diegocordoba/diegocordoba/Eureka-Sovereign/.snxx_hedge_state.json", "r") as f:
                        decay = json.load(f).get("decay_cumulative", 0.0)
                except Exception:
                    decay = 0.0

                rsi_dist = abs(current_rsi - 50)
                rsi_score = min(40, (rsi_dist / 20) * 40)
                ema_score = 30 if ema_trend == "BULLISH" else 10
                vix_score = 20 if vix_label == "LOW" else (10 if vix_label == "ELEVATED" else 0)
                decay_score = max(0, 10 - (decay * 100))
                conviction = min(100, int(rsi_score + ema_score + vix_score + decay_score))

                ticker_signals[tk] = {
                    "rsi": current_rsi,
                    "ema_20": ema_20,
                    "ema_50": ema_50,
                    "ema_trend": ema_trend,
                    "signal": signal,
                    "dist_to_trigger": dist_to_trigger,
                    "conviction": conviction
                }

    bl_weights = compute_black_litterman(returns, PORTFOLIO_WEIGHTS, ticker_signals)
    target_weights = {k: v for k, v in bl_weights.items()}

    return {
        "prices": prices, "returns": returns,
        "port_returns": port_returns, "cum_returns": cum_returns, "spy_cum": spy_cum,
        "rolling_vol_20": rolling_vol_20, "rolling_vol_60": rolling_vol_60,
        "rolling_sharpe": rolling_sharpe,
        "total_return": total_return, "spy_return": spy_return,
        "max_dd": max_dd, "ann_vol": ann_vol, "sharpe": sharpe, "alpha": alpha,
        "vix_series": vix_series, "current_vix": current_vix,
        "vix_label": vix_label,
        "asset_stats": asset_stats,
        "ticker_signals": ticker_signals,
        "target_weights": target_weights,
    }


# ============================================================
#  LOAD DATA
# ============================================================
data = load_market_data()
now = datetime.now()

if data is None:
    st.error("⚠️ Failed to load market data. Check internet connection.")
    st.stop()

# ============================================================
#  HEADER
# ============================================================
h1, h2, h3 = st.columns([4, 2, 2])
with h1:
    st.markdown("# 🏛️ Eureka Sovereign")
    st.caption("3-TICKER FIXED PORTFOLIO ENGINE — SNDK 20% | SNXX 50% | SCHD 30%")
with h2:
    vix_label = data["vix_label"]
    vix_color = {"LOW": "#00ff88", "ELEVATED": "#fbc02d", "HIGH": "#ff4b4b"}[vix_label]
    st.markdown(f"<p style='font-family: JetBrains Mono; font-size:18px; font-weight:700; color:{vix_color}; margin-top:20px;'>VIX: {vix_label}</p>", unsafe_allow_html=True)
with h3:
    avg_conviction = int(np.mean([s["conviction"] for s in data["ticker_signals"].values()])) if data["ticker_signals"] else 50
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #00d1ff;
                    border-radius: 8px; padding: 10px; text-align: center;'>
            <div style='font-family:Inter; font-size:11px; font-weight:600; color:#c8d6e5; letter-spacing:1px;'>EUREKA CONVICTION</div>
            <div style='font-family:JetBrains Mono; font-size:28px; font-weight:700; color:#00d1ff;'>{avg_conviction}<span style='font-size:16px;'>/100</span></div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ============================================================
#  NEURAL MARKET MEMORY (HOPFIELD NETWORK)
# ============================================================
memory_bank = load_neural_memory()
if memory_bank is not None:
    st.markdown("<div class='section-header'>🧠 NEURAL MARKET MEMORY (HOPFIELD ATTENTION)</div>", unsafe_allow_html=True)
    
    # Compute Query Vector: [vix, mu_sndk, mu_snxx]
    vix = data["current_vix"]
    sndk_ret = data["asset_stats"].get("SNDK", {}).get("return", 0) / 100.0 if "SNDK" in data["asset_stats"] else 0.08
    snxx_ret = data["asset_stats"].get("SNXX", {}).get("return", 0) / 100.0 if "SNXX" in data["asset_stats"] else 0.05
    query_vector = np.array([vix, sndk_ret, snxx_ret])
    
    scores = memory_bank.get_attention_scores(query_vector)
    if scores is not None:
        regime_names = ["LOW VIX Bull Run", "HIGH VIX Crash", "Decay Spiral (Chop)"]
        colors = ["#00ff88", "#ff4b4b", "#fbc02d"]
        
        cols = st.columns(len(regime_names))
        for i, (name, score, color) in enumerate(zip(regime_names, scores, colors)):
            opacity = max(0.1, score)
            border = f"2px solid {color}" if score == max(scores) else "1px solid #1a2744"
            with cols[i]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, {color}11, #0d1520); border: {border};
                            border-radius: 8px; padding: 14px; text-align: center; opacity: {opacity:.2f}; transition: 0.3s;'>
                    <div style='font-family:JetBrains Mono; font-size:13px; font-weight:700; color:{color};'>{name}</div>
                    <div style='font-family:JetBrains Mono; font-size:24px; font-weight:700; color:#e0e6ed; margin: 4px 0;'>{score*100:.1f}%</div>
                    <div style='font-size:10px; color:#94a3b8;'>Attention Weight</div>
                </div>
                """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
st.markdown("<div class='section-header'>PORTFOLIO METRICS</div>", unsafe_allow_html=True)
k1, k2, k3 = st.columns(3)
k1.metric("PORTFOLIO RETURN", f"{data['total_return']:+.2f}%", f"↑ vs SPY {data['spy_return']:+.1f}%")
k2.metric("MAX DRAWDOWN", f"{data['max_dd']:.2f}%", "↑ Peak-to-Trough")
k3.metric("SHARPE RATIO", f"{data['sharpe']:.3f}", "↑ Annualized")
k4, k5, k6 = st.columns(3)
k4.metric("ANNUALIZED VOL", f"{data['ann_vol']:.1f}%", "↑ Risk Profile")
rv20_last = data['rolling_vol_20'].iloc[-1]
k5.metric("ROLLING VOL (20d)", f"{float(rv20_last):.1f}%" if pd.notna(rv20_last) else "N/A", "↑ Recent Volatility")
k6.metric("α vs SPY", f"{data['alpha']:+.2f}%", "↑ Excess Return")

st.markdown("<div class='section-header'>TARGET ALLOCATION (BL POSTERIOR)</div>", unsafe_allow_html=True)
target_w = data.get("target_weights", PORTFOLIO_WEIGHTS)
ow_cols = st.columns(len(target_w))
for i, (tk, w) in enumerate(target_w.items()):
    color = ASSET_META[tk]["color"] if tk in ASSET_META else "#888888"
    desc = ASSET_META[tk]["desc"] if tk in ASSET_META else "Cash Reserve"
    with ow_cols[i]:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid {color}44;
                    border-radius: 8px; padding: 10px 14px; text-align: center;'>
            <div style='font-family:JetBrains Mono; font-size:13px; font-weight:700; color:{color};'>{tk}</div>
            <div style='font-family:JetBrains Mono; font-size:24px; font-weight:700; color:#e0e6ed; margin: 2px 0;'>{w*100:.0f}%</div>
            <div style='font-size:10px; color:#94a3b8;'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# ============================================================
#  TABS
# ============================================================
tab1, tab2, tab3 = st.tabs(["📈 PERFORMANCE", "🎯 TICKER SIGNALS", "❤️ LIVE MONITOR"])

# ═══════════════════════════════════════════════
#  TAB 1: PERFORMANCE
# ═══════════════════════════════════════════════
with tab1:
    # Per-Ticker Table
    st.markdown("<div class='section-header'>PER-TICKER SUMMARY</div>", unsafe_allow_html=True)
    ticker_rows = []
    for tk in FULL_UNIVERSE:
        stats = data["asset_stats"].get(tk, {})
        sig = data["ticker_signals"].get(tk, {})
        if stats:
            ticker_rows.append({
                "Ticker": tk,
                "Weight": f"{data['target_weights'].get(tk, 0)*100:.0f}%",
                "Description": ASSET_META[tk]["desc"],
                "Role": ASSET_META[tk]["category"],
                "Price": f"${stats['last_price']:.2f}",
                "Return": f"{stats['return']:+.2f}%",
                "Ann. Vol": f"{stats['vol']:.1f}%",
                "Sharpe": f"{stats['sharpe']:.2f}",
                "RSI(14)": f"{sig.get('rsi', 50):.1f}",
                "Signal": sig.get("signal", "—"),
                "Max DD": f"{stats['max_dd']:.1f}%",
            })
    if ticker_rows:
        df_tickers = pd.DataFrame(ticker_rows)
        def style_signal(val):
            if val == "BUY": return "color: #00ff88; font-weight: 700"
            elif val == "SELL": return "color: #ff4b4b; font-weight: 700"
            elif val == "HALVE POSITION": return "color: #fbc02d; font-weight: 700"
            return "color: #6b7fa3"
        def style_return(val):
            try:
                v = float(str(val).replace("%", "").replace("+", ""))
                return f"color: {'#00ff88' if v > 0 else '#ff4b4b'}; font-weight: 700"
            except:
                return ""
        styled = df_tickers.style
        try:
            styled = styled.map(style_signal, subset=["Signal"]).map(style_return, subset=["Return", "Max DD"])
        except AttributeError:
            styled = styled.applymap(style_signal, subset=["Signal"]).applymap(style_return, subset=["Return", "Max DD"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("")

    # Performance chart
    fig_perf = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Cumulative Portfolio Return vs SPY", "Daily Returns"),
        row_heights=[0.65, 0.35]
    )

    fig_perf.add_trace(go.Scatter(
        x=data["cum_returns"].index, y=data["cum_returns"].values,
        name="Eureka Portfolio", line=dict(color="#00d1ff", width=3.5),
        fill='tozeroy', fillcolor='rgba(0,209,255,0.06)'
    ), row=1, col=1)

    if data["spy_cum"] is not None:
        fig_perf.add_trace(go.Scatter(
            x=data["spy_cum"].index, y=data["spy_cum"].values,
            name="SPY", line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dot")
        ), row=1, col=1)

    for tk in FULL_UNIVERSE:
        if tk in data["returns"].columns:
            tk_cum = (1 + data["returns"][tk]).cumprod()
            fig_perf.add_trace(go.Scatter(
                x=tk_cum.index, y=tk_cum.values,
                name=f"{tk} ({data['target_weights'].get(tk, 0)*100:.0f}%)",
                line=dict(color=ASSET_META[tk]["color"], width=1.5, dash="dash"), opacity=0.8,
            ), row=1, col=1)

    fig_perf.add_hline(y=1.0, line_dash="dash", line_color="#333", row=1, col=1)

    # Daily returns
    port_colors = ["rgba(0,209,255,0.33)" if r > 0 else "rgba(255,75,75,0.33)" for r in data["port_returns"].values]
    fig_perf.add_trace(go.Bar(
        x=data["port_returns"].index, y=data["port_returns"].values * 100,
        name="Daily Return (%)", marker_color=port_colors, opacity=0.4
    ), row=2, col=1)

    fig_perf.update_layout(
        template="plotly_dark", height=700, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=60, b=40),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=10)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_perf.update_xaxes(gridcolor="#1a2744")
    fig_perf.update_yaxes(gridcolor="#1a2744")
    fig_perf.update_yaxes(title_text="Growth of $1", row=1, col=1)
    fig_perf.update_yaxes(title_text="Daily Ret (%)", row=2, col=1)

    st.plotly_chart(fig_perf, use_container_width=True)

# ═══════════════════════════════════════════════
#  TAB 2: PER-TICKER SIGNALS
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>PER-TICKER BUY / SELL / HOLD SIGNALS</div>", unsafe_allow_html=True)
    for tk in FULL_UNIVERSE:
        sig = data["ticker_signals"].get(tk, {})
        stats = data["asset_stats"].get(tk, {})
        if not sig or not stats:
            continue

        signal = sig["signal"]
        rsi = sig["rsi"]
        ema_trend = sig["ema_trend"]
        color = ASSET_META[tk]["color"]
        signal_color = "#00ff88" if signal == "BUY" else ("#ff4b4b" if signal == "SELL" else ("#fbc02d" if signal == "HALVE POSITION" else "#6b7fa3"))
        signal_emoji = "🟢" if signal == "BUY" else ("🔴" if signal == "SELL" else ("🟡" if signal == "HALVE POSITION" else "⚪"))
        ret_color = "#00ff88" if stats["return"] > 0 else "#ff4b4b"

        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid {color}44;
                    border-left: 4px solid {signal_color}; border-radius: 8px; padding: 16px 20px; margin-bottom: 10px;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <span style='font-family:JetBrains Mono; font-size:18px; font-weight:700; color:{color};'>{tk}</span>
                    <span style='font-size:12px; color:#94a3b8; margin-left:12px;'>{ASSET_META[tk]["desc"]} · {data['target_weights'].get(tk, 0)*100:.0f}% Target Weight</span>
                </div>
                <span style='font-family:JetBrains Mono; font-size:22px; font-weight:700; color:{signal_color};'>
                    {signal_emoji} {signal}
                </span>
            </div>
            <div style='display:flex; gap:28px; margin-top:12px; font-family:JetBrains Mono; font-size:13px;'>
                <span>Price: <b style='color:#00d1ff;'>${stats["last_price"]:.2f}</b></span>
                <span>Distance: <b style='color:#fbc02d;'>{sig.get("dist_to_trigger", "—")}</b></span>
                <span>Conviction: <b style='color:#00ff88;'>{sig.get("conviction", 50)}/100</b></span>
                <span>RSI: <b style='color:{"#ff4b4b" if rsi > 70 else ("#00ff88" if rsi < 30 else "#fbc02d")}';>{rsi:.1f}</b></span>
                <span>EMA: <b style='color:{"#00ff88" if ema_trend == "BULLISH" else "#ff4b4b"};'>{ema_trend}</b></span>
            </div>
            <div style='display:flex; gap:28px; margin-top:12px; font-family:JetBrains Mono; font-size:13px;'>
                <span>Vol: <b style='color:#fbc02d;'>{stats["vol"]:.1f}%</b></span>
                <span>MaxDD: <b style='color:#ff4b4b;'>{stats["max_dd"]:.1f}%</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  TAB 3: LIVE MONITOR (SNDK/SNXX)
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>LIVE MONITOR: SNDK/SNXX CORRELATION REGIME</div>", unsafe_allow_html=True)
    
    # Calculate rolling correlation and beta
    returns_daily = data["returns"]
    if "SNDK" in returns_daily.columns and "SNXX" in returns_daily.columns:
        corr_20 = returns_daily["SNDK"].rolling(window=20).corr(returns_daily["SNXX"])
        cov_20 = returns_daily["SNDK"].rolling(window=20).cov(returns_daily["SNXX"])
        var_20 = returns_daily["SNDK"].rolling(window=20).var()
        beta_20 = cov_20 / var_20
        
        target_beta = 2.0
        cum_base = (1 + returns_daily["SNDK"]).cumprod()
        cum_lev = (1 + returns_daily["SNXX"]).cumprod()
        returns_ideal_lev = returns_daily["SNDK"] * target_beta
        cum_ideal_lev = (1 + returns_ideal_lev).cumprod()
        decay_spread = (cum_lev / cum_ideal_lev) - 1
        
        current_corr = corr_20.iloc[-1] if not corr_20.empty and pd.notna(corr_20.iloc[-1]) else 0.0
        current_beta = beta_20.iloc[-1] if not beta_20.empty and pd.notna(beta_20.iloc[-1]) else 0.0
        current_decay = decay_spread.iloc[-1] if not decay_spread.empty and pd.notna(decay_spread.iloc[-1]) else 0.0
        
        if current_corr > 0.98 and abs(current_beta - target_beta) < 0.15:
            regime_state = "PERFECT SYNC 💑"
            regime_color = "#00ff88"
        elif current_corr > 0.90:
            regime_state = "SLIGHT DRIFT 🤔"
            regime_color = "#fbc02d"
        else:
            regime_state = "DECOUPLING ALERT 💔"
            regime_color = "#ff4b4b"

        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border-left: 5px solid {regime_color}; 
                    border-radius: 8px; padding: 15px 20px; margin-bottom: 25px;'>
            <div style='font-family: JetBrains Mono; font-size: 13px; color: #94a3b8; font-weight: 600;'>CURRENT REGIME STATE</div>
            <div style='font-family: JetBrains Mono; font-size: 28px; font-weight: 700; color: {regime_color}; margin-top: 5px;'>{regime_state}</div>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("20D Correlation", f"{current_corr:.4f}", "Target: 1.0000")
        m2.metric("20D Beta", f"{current_beta:.2f}x", f"Target: {target_beta}x")
        m3.metric("Cumulative Decay", f"{current_decay * 100:.2f}%", "Beta Slippage vs Ideal 2x")
        
        st.divider()
        
        fig_monitor = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
            subplot_titles=("Rolling 20-Day Pearson Correlation", "Rolling 20-Day Beta (SNXX vs SNDK)", "Cumulative Volatility Drag (Decay Spread)"),
            row_heights=[0.33, 0.33, 0.34]
        )

        fig_monitor.add_trace(go.Scatter(
            x=corr_20.index, y=corr_20.values,
            name="20D Correlation", line=dict(color="#ff4b4b", width=2.5),
            fill='tozeroy', fillcolor='rgba(255, 75, 75, 0.1)'
        ), row=1, col=1)
        fig_monitor.add_hline(y=1.0, line_dash="dash", line_color="#333", row=1, col=1)

        fig_monitor.add_trace(go.Scatter(
            x=beta_20.index, y=beta_20.values,
            name="20D Beta", line=dict(color="#00d1ff", width=2.5)
        ), row=2, col=1)
        fig_monitor.add_hline(y=target_beta, line_dash="dash", line_color="#00ff88", row=2, col=1)

        decay_colors = ["rgba(0, 209, 255, 0.5)" if val >= 0 else "rgba(255, 75, 75, 0.5)" for val in decay_spread.values]
        fig_monitor.add_trace(go.Bar(
            x=decay_spread.index, y=decay_spread.values * 100,
            name="Decay Spread (%)", marker_color=decay_colors
        ), row=3, col=1)

        fig_monitor.update_layout(
            template="plotly_dark", height=800, showlegend=False,
            paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
            margin=dict(l=40, r=40, t=60, b=40),
            font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
        )
        fig_monitor.update_xaxes(gridcolor="#1a2744")
        fig_monitor.update_yaxes(gridcolor="#1a2744")
        
        min_corr = corr_20.min() if not corr_20.empty and pd.notna(corr_20.min()) else 0.8
        fig_monitor.update_yaxes(title_text="Correlation", row=1, col=1, range=[min(0.8, min_corr), 1.01])
        fig_monitor.update_yaxes(title_text="Beta (x)", row=2, col=1)
        fig_monitor.update_yaxes(title_text="Decay (%)", row=3, col=1)

        st.plotly_chart(fig_monitor, use_container_width=True)
    else:
        st.warning("Data for SNDK or SNXX not found.")
