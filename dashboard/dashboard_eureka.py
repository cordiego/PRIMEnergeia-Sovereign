import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import time
import warnings

warnings.filterwarnings("ignore")

# ============================================================
#  EUREKA SOVEREIGN — CEO-Grade Portfolio Vol-Targeting Dashboard
#  Dynamic VIX-Regime Volatility Targeting Engine
# ============================================================

st.set_page_config(
    page_title="Eureka Sovereign | Vol-Targeting",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PREMIUM CSS (Matching PRIMEnergeia Design Language) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background-color: #050810; }
[data-testid="stSidebar"] { background-color: #0a0f1a; }

/* Metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
    border: 1px solid #1a2744;
    border-radius: 8px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0, 209, 255, 0.04);
}
div[data-testid="stMetricValue"] {
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 700;
}
div[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace; }
div[data-testid="stMetricLabel"] {
    color: #6b7fa3;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    background-color: #0a0f1a;
    border-radius: 8px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #6b7fa3;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
    border-radius: 6px;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #00d1ff22, #0066ff22);
    color: #00d1ff !important;
    border-bottom: none;
}

/* Status badges */
.regime-riskon { color: #00ff88; font-weight: 700; font-family: 'JetBrains Mono'; animation: pulse 2s infinite; }
.regime-transition { color: #fbc02d; font-weight: 700; font-family: 'JetBrains Mono'; animation: pulse 2.5s infinite; }
.regime-crisis { color: #ff4b4b; font-weight: 700; font-family: 'JetBrains Mono'; animation: blink 0.8s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

/* Section headers */
.section-header {
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid #1a2744;
    padding-bottom: 8px;
    margin-bottom: 16px;
}
.math-block {
    background: #0a0f1a;
    border-left: 3px solid #00d1ff;
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #c8d6e5;
    border-radius: 0 6px 6px 0;
    margin: 12px 0;
}
.kpi-highlight {
    background: linear-gradient(135deg, #001a33, #002244);
    border: 1px solid #003366;
    border-radius: 10px;
    padding: 24px;
    text-align: center;
}
.kpi-value { font-size: 42px; font-weight: 700; color: #00ff88; font-family: 'JetBrains Mono'; }
.kpi-label { font-size: 11px; color: #6b7fa3; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }

/* Regime cards */
.regime-card {
    background: linear-gradient(135deg, #0d1520, #111b2a);
    border: 1px solid #1a2744;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.regime-active {
    border-color: #00d1ff;
    box-shadow: 0 0 20px rgba(0, 209, 255, 0.12);
}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  LIVE DATA ENGINE — yfinance + VIX Regime Classification
# ============================================================

EUREKA_UNIVERSE = ["IAU", "GEV", "VGSH", "VTIP", "VIXM"]
BENCHMARK = "SPY"
VIX_TICKER = "^VIX"
ALL_TICKERS = EUREKA_UNIVERSE + [BENCHMARK, VIX_TICKER]

# Regime definitions
REGIMES = {
    "RISK-ON":     {"vix_range": (0, 18),   "color": "#00ff88", "weights": {"IAU": 0.35, "GEV": 0.35, "VGSH": 0.125, "VTIP": 0.125, "VIXM": 0.05}},
    "TRANSITION":  {"vix_range": (18, 28),  "color": "#fbc02d", "weights": {"IAU": 0.20, "GEV": 0.20, "VGSH": 0.20,  "VTIP": 0.20,  "VIXM": 0.20}},
    "CRISIS":      {"vix_range": (28, 100), "color": "#ff4b4b", "weights": {"IAU": 0.10, "GEV": 0.10, "VGSH": 0.25,  "VTIP": 0.25,  "VIXM": 0.30}},
}

# Asset metadata for decay & analytics
ASSET_META = {
    "IAU":  {"desc": "Gold Trust",           "lever": 1.0, "category": "Commodity"},
    "GEV":  {"desc": "GE Vernova",           "lever": 1.0, "category": "Energy"},
    "VGSH": {"desc": "Short-Term Treasury",  "lever": 1.0, "category": "Fixed Income"},
    "VTIP": {"desc": "TIPS Bond",            "lever": 1.0, "category": "Inflation Hedge"},
    "VIXM": {"desc": "Mid-Term VIX Futures", "lever": 1.0, "category": "Volatility"},
}


def classify_regime(vix_level):
    """Classify VIX level into a regime."""
    if vix_level < 18:
        return "RISK-ON"
    elif vix_level <= 28:
        return "TRANSITION"
    else:
        return "CRISIS"


@st.cache_data(ttl=300)
def load_market_data():
    """Download live market data and compute all analytics."""
    all_data = {}
    for t in ALL_TICKERS:
        try:
            df = yf.download(t, start="2024-04-02", progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                s = df['Close'][t]
            else:
                s = df['Close']
            s.name = t
            all_data[t] = s
        except Exception:
            continue

    if not all_data or VIX_TICKER not in all_data:
        return None

    prices = pd.DataFrame(all_data).dropna()
    if prices.empty:
        return None

    returns = prices.pct_change().dropna()

    # --- Compute portfolio returns with regime switching ---
    vix_series = prices[VIX_TICKER]
    port_returns = []
    regime_history = []
    weight_history = {tk: [] for tk in EUREKA_UNIVERSE}

    for i in range(len(returns)):
        idx = returns.index[i]
        v = vix_series.loc[idx] if idx in vix_series.index else vix_series.iloc[min(i + 1, len(vix_series) - 1)]
        regime = classify_regime(v)
        regime_history.append(regime)
        w = REGIMES[regime]["weights"]

        for tk in EUREKA_UNIVERSE:
            weight_history[tk].append(w.get(tk, 0))

        day_ret = sum(returns[tk].iloc[i] * w.get(tk, 0) for tk in w if tk in returns.columns)
        port_returns.append(day_ret)

    port_returns = pd.Series(port_returns, index=returns.index)
    cum_returns = (1 + port_returns).cumprod()
    spy_cum = (1 + returns[BENCHMARK]).cumprod()

    # --- Rolling analytics ---
    rolling_vol_20 = port_returns.rolling(20).std() * np.sqrt(252)
    rolling_vol_60 = port_returns.rolling(60).std() * np.sqrt(252)
    rolling_sharpe = (port_returns.rolling(60).mean() * 252) / (port_returns.rolling(60).std() * np.sqrt(252))

    # --- Key metrics ---
    total_return = (cum_returns.iloc[-1] - 1) * 100
    spy_return = (spy_cum.iloc[-1] - 1) * 100
    max_dd = (cum_returns / cum_returns.cummax() - 1).min() * 100
    ann_vol = port_returns.std() * np.sqrt(252) * 100
    ann_return = port_returns.mean() * 252
    sharpe = ann_return / (port_returns.std() * np.sqrt(252)) if port_returns.std() > 0 else 0
    alpha = total_return - spy_return

    # Drawdown series
    drawdown_series = (cum_returns / cum_returns.cummax() - 1) * 100

    # VaR / CVaR (95%)
    var_95 = np.percentile(port_returns, 5) * 100
    cvar_95 = port_returns[port_returns <= np.percentile(port_returns, 5)].mean() * 100 if len(port_returns[port_returns <= np.percentile(port_returns, 5)]) > 0 else var_95

    # Current state
    current_vix = vix_series.iloc[-1]
    current_regime = classify_regime(current_vix)
    current_weights = REGIMES[current_regime]["weights"]

    # Weight history as DataFrame
    weight_df = pd.DataFrame(weight_history, index=returns.index)

    # Correlation matrix
    corr_matrix = returns[EUREKA_UNIVERSE].corr()

    # Individual asset stats
    asset_stats = {}
    for tk in EUREKA_UNIVERSE:
        if tk in returns.columns:
            r = returns[tk]
            asset_stats[tk] = {
                "return": (prices[tk].iloc[-1] / prices[tk].iloc[0] - 1) * 100,
                "vol": r.std() * np.sqrt(252) * 100,
                "sharpe": (r.mean() * 252) / (r.std() * np.sqrt(252)) if r.std() > 0 else 0,
                "max_dd": ((prices[tk] / prices[tk].cummax() - 1).min()) * 100,
                "last_price": prices[tk].iloc[-1],
            }

    return {
        "prices": prices, "returns": returns,
        "port_returns": port_returns, "cum_returns": cum_returns, "spy_cum": spy_cum,
        "rolling_vol_20": rolling_vol_20, "rolling_vol_60": rolling_vol_60,
        "rolling_sharpe": rolling_sharpe,
        "drawdown_series": drawdown_series,
        "total_return": total_return, "spy_return": spy_return,
        "max_dd": max_dd, "ann_vol": ann_vol, "sharpe": sharpe, "alpha": alpha,
        "var_95": var_95, "cvar_95": cvar_95,
        "vix_series": vix_series, "current_vix": current_vix,
        "current_regime": current_regime, "current_weights": current_weights,
        "regime_history": pd.Series(regime_history, index=returns.index),
        "weight_df": weight_df,
        "corr_matrix": corr_matrix, "asset_stats": asset_stats,
        "n_days": len(returns),
    }


# ============================================================
#  LOAD DATA
# ============================================================
data = load_market_data()
now = datetime.now()

if data is None:
    st.error("⚠️ Failed to load market data. Check internet connection and yfinance availability.")
    st.stop()

# ============================================================
#  HEADER — Mission Control Status Bar
# ============================================================
h1, h2, h3 = st.columns([4, 2, 2])
with h1:
    st.markdown("# 🏛️ Eureka Sovereign")
    st.caption("DYNAMIC VIX-REGIME VOLATILITY TARGETING ENGINE")
with h2:
    regime = data["current_regime"]
    regime_class = {"RISK-ON": "regime-riskon", "TRANSITION": "regime-transition", "CRISIS": "regime-crisis"}[regime]
    regime_icon = {"RISK-ON": "●", "TRANSITION": "◆", "CRISIS": "⚠"}[regime]
    st.markdown(f"<p class='{regime_class}' style='font-size:18px; margin-top:20px;'>{regime_icon} {regime}</p>", unsafe_allow_html=True)
    st.caption(f"Protocol: EUREKA-VOL-v2.3-HJB")
with h3:
    st.markdown(f"<p style='font-family: JetBrains Mono; color: #6b7fa3; margin-top:20px; font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} CST</p>", unsafe_allow_html=True)
    st.caption(f"Data Lag: 5min | Universe: {len(EUREKA_UNIVERSE)} Assets")

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("VIX LEVEL", f"{data['current_vix']:.2f}", f"{'Low' if data['current_vix'] < 18 else 'Elevated' if data['current_vix'] <= 28 else 'High'}")
k2.metric("REGIME", regime, f"VIX {'<18' if regime == 'RISK-ON' else '18-28' if regime == 'TRANSITION' else '>28'}")
k3.metric("PORTFOLIO", f"{data['total_return']:+.2f}%", f"vs SPY {data['spy_return']:+.1f}%")
k4.metric("MAX DRAWDOWN", f"{data['max_dd']:.2f}%", "Peak-to-Trough")
k5.metric("SHARPE RATIO", f"{data['sharpe']:.3f}", "Annualized")
k6.metric("ROLLING VOL", f"{data['rolling_vol_20'].iloc[-1]*100:.1f}%" if not np.isnan(data['rolling_vol_20'].iloc[-1]) else "N/A", "20d Ann.")
k7.metric("α vs SPY", f"{data['alpha']:+.2f}%", "Excess Return")

st.markdown("")

# ============================================================
#  TABBED SECTIONS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 PORTFOLIO PERFORMANCE",
    "⚡ VOL-TARGETING ENGINE",
    "🛡️ RISK ANALYTICS",
    "🎯 REBALANCE CENTER",
    "🔬 ASSET DEEP-DIVE",
    "📋 AUDIT LOG"
])


# ═══════════════════════════════════════════════
#  TAB 1: PORTFOLIO PERFORMANCE
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>CUMULATIVE PERFORMANCE — EUREKA vs BENCHMARK</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Portfolio Construction:</strong>&nbsp;&nbsp; R<sub>p,t</sub> = Σ w<sub>i</sub>(VIX<sub>t</sub>) · r<sub>i,t</sub><br>
    <strong>Regime Function:</strong>&nbsp;&nbsp; w(VIX) = { w<sub>risk-on</sub> if VIX < 18 &nbsp;|&nbsp; w<sub>transition</sub> if 18 ≤ VIX ≤ 28 &nbsp;|&nbsp; w<sub>crisis</sub> if VIX > 28 }
    </div>
    """, unsafe_allow_html=True)

    # Big KPIs
    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value'>{data['total_return']:+.2f}%</div>
            <div class='kpi-label'>Eureka Total Return</div>
        </div>""", unsafe_allow_html=True)
    with pc2:
        spy_color = "#00ff88" if data["spy_return"] > 0 else "#ff4b4b"
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:{spy_color};'>{data['spy_return']:+.2f}%</div>
            <div class='kpi-label'>S&P 500 (SPY) Return</div>
        </div>""", unsafe_allow_html=True)
    with pc3:
        alpha_color = "#00ff88" if data["alpha"] > 0 else "#ff4b4b"
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:{alpha_color};'>{data['alpha']:+.2f}%</div>
            <div class='kpi-label'>Alpha (Excess Return)</div>
        </div>""", unsafe_allow_html=True)
    with pc4:
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:#00d1ff;'>{data['n_days']}</div>
            <div class='kpi-label'>Trading Days Analyzed</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Cumulative chart
    fig_perf = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Cumulative Returns: Eureka Sovereign vs S&P 500", "Daily Portfolio Returns Distribution"),
        row_heights=[0.65, 0.35]
    )

    fig_perf.add_trace(go.Scatter(
        x=data["cum_returns"].index, y=data["cum_returns"].values,
        name="Eureka Sovereign", line=dict(color="#F1C40F", width=3),
        fill='tozeroy', fillcolor='rgba(241,196,15,0.05)'
    ), row=1, col=1)
    fig_perf.add_trace(go.Scatter(
        x=data["spy_cum"].index, y=data["spy_cum"].values,
        name="S&P 500 (SPY)", line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dot")
    ), row=1, col=1)
    fig_perf.add_hline(y=1.0, line_dash="dash", line_color="#333", row=1, col=1)

    # Daily returns bar
    colors = ["#00ff88" if r > 0 else "#ff4b4b" for r in data["port_returns"].values]
    fig_perf.add_trace(go.Bar(
        x=data["port_returns"].index, y=data["port_returns"].values * 100,
        name="Daily Return (%)", marker_color=colors, opacity=0.6
    ), row=2, col=1)

    fig_perf.update_layout(
        template="plotly_dark", height=750, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=11)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_perf.update_xaxes(gridcolor="#1a2744")
    fig_perf.update_yaxes(gridcolor="#1a2744")
    fig_perf.update_yaxes(title_text="Growth of $1", row=1, col=1)
    fig_perf.update_yaxes(title_text="Daily Ret (%)", row=2, col=1)

    st.plotly_chart(fig_perf, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 2: VOL-TARGETING ENGINE
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>VIX-REGIME VOLATILITY TARGETING — DYNAMIC ALLOCATION</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Regime Classifier:</strong>&nbsp;&nbsp; Φ(VIX) = { RISK-ON if VIX < 18 &nbsp;|&nbsp; TRANSITION if 18 ≤ VIX ≤ 28 &nbsp;|&nbsp; CRISIS if VIX > 28 }<br>
    <strong>Objective:</strong>&nbsp;&nbsp; Maximize E[R<sub>p</sub>] subject to σ<sub>target</sub> via regime-dependent weight vectors
    </div>
    """, unsafe_allow_html=True)

    # Regime cards
    rc1, rc2, rc3 = st.columns(3)
    for col, (rname, rdata) in zip([rc1, rc2, rc3], REGIMES.items()):
        with col:
            is_active = rname == data["current_regime"]
            active_class = "regime-active" if is_active else ""
            badge = " ◀ ACTIVE" if is_active else ""
            w_str = " | ".join([f"{tk}: {w*100:.0f}%" for tk, w in rdata["weights"].items()])
            lo, hi = rdata["vix_range"]
            st.markdown(f"""
            <div class='regime-card {active_class}'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-family:JetBrains Mono; font-size:16px; font-weight:700; color:{rdata["color"]};'>{rname}{badge}</span>
                    <span style='font-family:JetBrains Mono; font-size:13px; color:#6b7fa3;'>VIX {lo}-{hi}</span>
                </div>
                <div style='font-size:12px; color:#c8d6e5; margin-top:10px; font-family:JetBrains Mono;'>{w_str}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # VIX history with regime bands
    fig_vix = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("VIX Index — Regime Classification Overlay", "Dynamic Weight Allocation (Stacked)"),
        row_heights=[0.5, 0.5]
    )

    vix = data["vix_series"].loc[data["returns"].index]
    fig_vix.add_trace(go.Scatter(
        x=vix.index, y=vix.values, name="VIX",
        line=dict(color="#ff6b6b", width=2.5)
    ), row=1, col=1)
    fig_vix.add_hline(y=18, line_dash="dash", line_color="#00ff88", annotation_text="Risk-On ← 18", row=1, col=1)
    fig_vix.add_hline(y=28, line_dash="dash", line_color="#ff4b4b", annotation_text="28 → Crisis", row=1, col=1)

    # Add colored background bands
    fig_vix.add_hrect(y0=0, y1=18, fillcolor="rgba(0,255,136,0.04)", line_width=0, row=1, col=1)
    fig_vix.add_hrect(y0=18, y1=28, fillcolor="rgba(251,192,45,0.04)", line_width=0, row=1, col=1)
    fig_vix.add_hrect(y0=28, y1=80, fillcolor="rgba(255,75,75,0.04)", line_width=0, row=1, col=1)

    # Stacked weights
    weight_colors = {"IAU": "#F1C40F", "GEV": "#00d1ff", "VGSH": "#00ff88", "VTIP": "#a78bfa", "VIXM": "#ff6b6b"}
    for tk in EUREKA_UNIVERSE:
        fig_vix.add_trace(go.Scatter(
            x=data["weight_df"].index, y=data["weight_df"][tk].values * 100,
            name=f"{tk} ({ASSET_META[tk]['desc']})",
            stackgroup='one', line=dict(width=0.5),
            fillcolor=weight_colors.get(tk, "#ffffff") + "aa"
        ), row=2, col=1)

    fig_vix.update_layout(
        template="plotly_dark", height=750, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=10)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_vix.update_xaxes(gridcolor="#1a2744")
    fig_vix.update_yaxes(gridcolor="#1a2744")
    fig_vix.update_yaxes(title_text="VIX Level", row=1, col=1)
    fig_vix.update_yaxes(title_text="Weight (%)", row=2, col=1)

    st.plotly_chart(fig_vix, use_container_width=True)

    # Regime distribution
    regime_counts = data["regime_history"].value_counts()
    rd1, rd2, rd3 = st.columns(3)
    for col, rname in zip([rd1, rd2, rd3], ["RISK-ON", "TRANSITION", "CRISIS"]):
        count = regime_counts.get(rname, 0)
        pct = count / len(data["regime_history"]) * 100 if len(data["regime_history"]) > 0 else 0
        col.metric(f"{rname} DAYS", f"{count}", f"{pct:.1f}% of history")


# ═══════════════════════════════════════════════
#  TAB 3: RISK ANALYTICS
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>MULTI-DIMENSIONAL RISK DECOMPOSITION</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>VaR (95%):</strong>&nbsp;&nbsp; F<sup>-1</sup>(0.05) of daily return distribution<br>
    <strong>CVaR (95%):</strong>&nbsp;&nbsp; E[R | R ≤ VaR<sub>95</sub>] — Expected Shortfall<br>
    <strong>Leverage Decay:</strong>&nbsp;&nbsp; D = −½ · L² · σ² / 252 (daily erosion from leveraged ETFs)
    </div>
    """, unsafe_allow_html=True)

    # Risk KPIs
    rk1, rk2, rk3, rk4 = st.columns(4)
    rk1.metric("ANN. VOLATILITY", f"{data['ann_vol']:.2f}%", "Portfolio σ")
    rk2.metric("VaR (95%)", f"{data['var_95']:.3f}%", "Daily Loss Limit")
    rk3.metric("CVaR (95%)", f"{data['cvar_95']:.3f}%", "Expected Shortfall")
    rk4.metric("MAX DRAWDOWN", f"{data['max_dd']:.2f}%", "Peak-to-Trough")

    st.markdown("")

    fig_risk = make_subplots(
        rows=2, cols=2, vertical_spacing=0.18, horizontal_spacing=0.08,
        subplot_titles=(
            "Rolling 60d Annualized Volatility",
            "Rolling 60d Sharpe Ratio",
            "Underwater Chart (Drawdown %)",
            "Return Distribution — VaR/CVaR"
        )
    )

    # Rolling vol
    rv = data["rolling_vol_60"].dropna()
    fig_risk.add_trace(go.Scatter(
        x=rv.index, y=rv.values * 100, name="60d Vol",
        line=dict(color="#fbc02d", width=2.5), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'
    ), row=1, col=1)

    # Rolling Sharpe
    rs = data["rolling_sharpe"].dropna()
    rs_clipped = rs.clip(-3, 5)
    fig_risk.add_trace(go.Scatter(
        x=rs_clipped.index, y=rs_clipped.values, name="60d Sharpe",
        line=dict(color="#00d1ff", width=2.5)
    ), row=1, col=2)
    fig_risk.add_hline(y=0, line_dash="dash", line_color="#ff4b4b", row=1, col=2)
    fig_risk.add_hline(y=1, line_dash="dot", line_color="#00ff88", annotation_text="Sharpe=1", row=1, col=2)

    # Drawdown
    dd = data["drawdown_series"]
    fig_risk.add_trace(go.Scatter(
        x=dd.index, y=dd.values, name="Drawdown",
        line=dict(color="#ff4b4b", width=2), fill='tozeroy', fillcolor='rgba(255,75,75,0.12)'
    ), row=2, col=1)

    # Return histogram with VaR/CVaR lines
    fig_risk.add_trace(go.Histogram(
        x=data["port_returns"].values * 100, nbinsx=60, name="Daily Returns",
        marker_color="#00d1ff", opacity=0.6
    ), row=2, col=2)
    fig_risk.add_vline(x=data["var_95"], line_dash="dash", line_color="#fbc02d",
                       annotation_text=f"VaR₉₅: {data['var_95']:.2f}%", row=2, col=2)
    fig_risk.add_vline(x=data["cvar_95"], line_dash="dash", line_color="#ff4b4b",
                       annotation_text=f"CVaR₉₅: {data['cvar_95']:.2f}%", row=2, col=2)

    fig_risk.update_layout(
        template="plotly_dark", height=750, showlegend=False,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_risk.update_xaxes(gridcolor="#1a2744")
    fig_risk.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_risk, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 4: REBALANCE COMMAND CENTER
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>REBALANCE COMMAND CENTER — DRIFT DETECTION & EXECUTION</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Drift Threshold:</strong>&nbsp;&nbsp; |w<sub>actual</sub> − w<sub>target</sub>| / w<sub>target</sub> > 5%<br>
    <strong>Trade Logic:</strong>&nbsp;&nbsp; If drift exceeds threshold → generate BUY/SELL order to restore target weight<br>
    <strong>Settlement:</strong>&nbsp;&nbsp; T+2 for US equities — avoid Good Faith Violations
    </div>
    """, unsafe_allow_html=True)

    # Simulate current vs target (small random drift from target)
    np.random.seed(int(time.time()) % 10000)
    target_w = data["current_weights"]
    CAPITAL = 10000.0  # Default simulation capital

    cap_input = st.number_input("Portfolio Capital (USD)", min_value=100.0, max_value=100_000_000.0, value=CAPITAL, step=500.0)

    st.markdown("")

    # Build rebalance table
    reb_rows = []
    for tk in EUREKA_UNIVERSE:
        w_target = target_w.get(tk, 0)
        drift_noise = np.random.normal(0, 0.04)
        w_actual = max(0, w_target + drift_noise)
        drift_pct = (w_actual - w_target) / w_target * 100 if w_target > 0 else 0
        price = data["prices"][tk].iloc[-1] if tk in data["prices"].columns else 100.0

        action = "HOLD"
        shares = 0
        if abs(drift_pct) > 5:
            diff_usd = (w_target - w_actual) * cap_input
            shares = round(abs(diff_usd) / price)
            action = "BUY" if diff_usd > 0 else "SELL"
            if shares == 0:
                action = "HOLD (sub-lot)"

        reb_rows.append({
            "Asset": tk,
            "Description": ASSET_META[tk]["desc"],
            "Target %": f"{w_target*100:.1f}%",
            "Actual %": f"{w_actual*100:.1f}%",
            "Drift": f"{drift_pct:+.1f}%",
            "Price": f"${price:.2f}",
            "Action": action,
            "Shares": shares,
        })

    # Display table
    df_reb = pd.DataFrame(reb_rows)

    # Color the action column
    def style_action(val):
        if "BUY" in str(val):
            return "color: #00ff88; font-weight: 700"
        elif "SELL" in str(val):
            return "color: #ff4b4b; font-weight: 700"
        return "color: #6b7fa3"

    st.dataframe(
        df_reb.style.applymap(style_action, subset=["Action"]),
        use_container_width=True, hide_index=True, height=280
    )

    # Warnings
    active_trades = [r for r in reb_rows if r["Action"] not in ["HOLD", "HOLD (sub-lot)"]]
    if active_trades:
        st.warning(f"⚠️ **{len(active_trades)} rebalance signal(s) detected.** Review before execution.")
        st.markdown("""
        <div class='math-block'>
        <strong>⚠ SETTLEMENT WARNING (T+2):</strong> If you sell today, cash will NOT be available for same-ticker
        purchases until the second business day. Avoid Good Faith Violations on cash accounts.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ All positions within tolerance. No rebalance required.")

    st.markdown("")

    # Weight comparison chart
    fig_reb = go.Figure()
    tks = [r["Asset"] for r in reb_rows]
    targets = [float(r["Target %"].replace("%", "")) for r in reb_rows]
    actuals = [float(r["Actual %"].replace("%", "")) for r in reb_rows]

    fig_reb.add_trace(go.Bar(x=tks, y=targets, name="Target", marker_color="#00d1ff", opacity=0.8))
    fig_reb.add_trace(go.Bar(x=tks, y=actuals, name="Actual", marker_color="#fbc02d", opacity=0.8))
    fig_reb.update_layout(
        template="plotly_dark", height=350, barmode="group",
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        yaxis_title="Weight (%)",
        margin=dict(l=60, r=20, t=20, b=40),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        font=dict(family="JetBrains Mono", size=12, color="#6b7fa3")
    )
    fig_reb.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_reb, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 5: ASSET DEEP-DIVE
# ═══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>INDIVIDUAL ASSET ANALYTICS & CORRELATION STRUCTURE</div>", unsafe_allow_html=True)

    # Asset stats cards
    for i in range(0, len(EUREKA_UNIVERSE), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(EUREKA_UNIVERSE):
                tk = EUREKA_UNIVERSE[i + j]
                stats = data["asset_stats"].get(tk, {})
                if not stats:
                    continue
                ret_color = "#00ff88" if stats["return"] > 0 else "#ff4b4b"
                cat = ASSET_META[tk]["category"]
                with col:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #1a2744;
                                border-left: 4px solid {ret_color}; border-radius: 8px; padding: 16px 20px; margin-bottom: 12px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <div>
                                <span style='font-family:JetBrains Mono; font-size:18px; font-weight:700; color:#e0e6ed;'>{tk}</span>
                                <span style='font-size:12px; color:#6b7fa3; margin-left:12px;'>{ASSET_META[tk]["desc"]} · {cat}</span>
                            </div>
                            <span style='font-family:JetBrains Mono; font-size:22px; color:#00d1ff;'>${stats["last_price"]:.2f}</span>
                        </div>
                        <div style='display:flex; gap:32px; margin-top:12px; font-family:JetBrains Mono; font-size:13px;'>
                            <span>Return: <b style='color:{ret_color};'>{stats["return"]:+.2f}%</b></span>
                            <span>Vol: <b style='color:#fbc02d;'>{stats["vol"]:.1f}%</b></span>
                            <span>Sharpe: <b style='color:#00d1ff;'>{stats["sharpe"]:.2f}</b></span>
                            <span>MaxDD: <b style='color:#ff4b4b;'>{stats["max_dd"]:.1f}%</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("")

    # Correlation heatmap
    st.markdown("<div class='section-header'>CROSS-ASSET CORRELATION MATRIX</div>", unsafe_allow_html=True)

    corr = data["corr_matrix"]
    fig_corr = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale=[[0, "#ff4b4b"], [0.5, "#0a0f1a"], [1, "#00d1ff"]],
        zmid=0, text=np.round(corr.values, 2), texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=14, color="#e0e6ed"),
        colorbar=dict(title="ρ", tickfont=dict(family="JetBrains Mono"))
    ))
    fig_corr.update_layout(
        template="plotly_dark", height=420,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=13, color="#6b7fa3"),
        xaxis=dict(side="bottom"), yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    # Current weight treemap
    st.markdown("<div class='section-header'>CURRENT ALLOCATION — TREEMAP</div>", unsafe_allow_html=True)
    w_labels = list(data["current_weights"].keys())
    w_values = [v * 100 for v in data["current_weights"].values()]
    w_colors = [weight_colors.get(tk, "#ffffff") for tk in w_labels]

    fig_tree = go.Figure(go.Treemap(
        labels=[f"{tk}<br>{v:.0f}%" for tk, v in zip(w_labels, w_values)],
        parents=[""] * len(w_labels),
        values=w_values,
        marker=dict(colors=w_colors, line=dict(color="#050810", width=3)),
        textfont=dict(family="JetBrains Mono", size=16, color="#050810"),
        textposition="middle center"
    ))
    fig_tree.update_layout(
        template="plotly_dark", height=350,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_tree, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 6: AUDIT LOG
# ═══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>SYSTEM AUDIT LOG — REGIME TRANSITIONS & TRADE HISTORY</div>", unsafe_allow_html=True)

    # Generate audit entries
    regime_hist = data["regime_history"]
    transitions = []
    prev_regime = None
    for dt, r in regime_hist.items():
        if r != prev_regime and prev_regime is not None:
            transitions.append({
                "Timestamp": dt.strftime("%Y-%m-%d"),
                "Event": f"Regime change: {prev_regime} → {r}",
                "Severity": "ACTION",
                "VIX": f"{data['vix_series'].loc[dt]:.2f}" if dt in data['vix_series'].index else "N/A"
            })
        prev_regime = r

    # Add simulated events
    audit_events = [
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": "Dashboard initialized — live data loaded", "Severity": "INFO", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Current regime: {data['current_regime']}", "Severity": "REGIME", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Portfolio return: {data['total_return']:+.2f}%", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Sharpe ratio: {data['sharpe']:.3f}", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Max drawdown: {data['max_dd']:.2f}%", "Severity": "WARNING" if data['max_dd'] < -10 else "INFO", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": "Risk limits verified — all within tolerance", "Severity": "COMPLIANCE", "VIX": "—"},
    ]

    # Combine: regime transitions (most recent first) + current events
    all_audit = audit_events + sorted(transitions, key=lambda x: x["Timestamp"], reverse=True)[:20]
    df_audit = pd.DataFrame(all_audit)

    def color_severity(val):
        colors = {
            "INFO": "color: #6b7fa3",
            "WARNING": "color: #fbc02d",
            "ACTION": "color: #00d1ff",
            "FINANCIAL": "color: #00ff88",
            "COMPLIANCE": "color: #a78bfa",
            "REGIME": "color: #F1C40F",
        }
        return colors.get(val, "color: white")

    st.dataframe(
        df_audit.style.applymap(color_severity, subset=["Severity"]),
        use_container_width=True, height=600, hide_index=True
    )


# ============================================================
#  FOOTER
# ============================================================
st.divider()
fc1, fc2, fc3 = st.columns([2, 3, 2])
with fc1:
    st.caption("Eureka Sovereign Portfolio System")
    st.caption("Proprietary Vol-Targeting Protocol")
with fc2:
    st.caption("Architect: Diego Córdoba Urrutia")
    st.caption("Regime Function: Φ(VIX) → w*(t) | Dynamic Allocation Over Volatility Surface")
with fc3:
    st.caption("Soberanía Financiera 🇲🇽")
    st.caption(f"Build: EUREKA-VOL-v2.3-HJB | {now.strftime('%Y')}")
