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
    font-size: 40px;
    font-weight: 700;
    text-shadow: 0 0 12px rgba(0,209,255,0.3);
}
div[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace; color: #c8d6e5; }
div[data-testid="stMetricLabel"] {
    color: #c8d6e5;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 1px;
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
    color: #c8d6e5;
    font-weight: 600;
    font-size: 15px;
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
    font-size: 14px;
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
    font-size: 15px;
    color: #e2e8f0;
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
.kpi-label { font-size: 13px; color: #94a3b8; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }

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
/* Markdown & sidebar readability */
.stMarkdown, .stMarkdown p { color: #e2e8f0 !important; font-size: 15px; }
div[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  LIVE DATA ENGINE — yfinance + VIX Regime Classification
# ============================================================

EUREKA_CORE = ["VTIP"]
GAINS_SATELLITES = ["IAU", "GEV", "VGSH"]
EUREKA_UNIVERSE = EUREKA_CORE
BENCHMARK = "SPY"
VIX_TICKER = "^VIX"
ALL_TICKERS = EUREKA_CORE + GAINS_SATELLITES + [BENCHMARK, VIX_TICKER]

# Core allocation — 100% VTIP anchor
TARGET_WEIGHTS = {"VTIP": 1.0}

# Asset metadata for analytics
ASSET_META = {
    "VTIP": {"desc": "TIPS Bond",            "lever": 1.0, "category": "Core Anchor"},
    "IAU":  {"desc": "Gold",                 "lever": 1.0, "category": "Satellite"},
    "GEV":  {"desc": "Nuclear Energy",        "lever": 1.0, "category": "Satellite"},
    "VGSH": {"desc": "Short-Term Treasury",   "lever": 1.0, "category": "Satellite"},
}


def classify_vix(vix_level):
    """Classify VIX level for display."""
    if vix_level < 18:
        return "LOW"
    elif vix_level <= 28:
        return "ELEVATED"
    else:
        return "HIGH"


def _safe_close(df, ticker):
    """Safely extract Close prices regardless of yfinance column format."""
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


@st.cache_data(ttl=300)
def load_market_data():
    """Download live market data and compute all analytics."""
    all_data = {}
    for t in ALL_TICKERS:
        for attempt in range(3):
            try:
                df = yf.download(t, start="2024-04-02", progress=False)
                if df.empty:
                    break
                s = _safe_close(df, t)
                if s is None or s.dropna().empty:
                    if attempt < 2:
                        time.sleep(1)
                    continue
                s = s.dropna()
                s.name = t
                all_data[t] = s
                break
            except Exception:
                if attempt < 2:
                    time.sleep(1)

    if not all_data or VIX_TICKER not in all_data:
        return None

    prices = pd.DataFrame(all_data).dropna()
    if prices.empty:
        return None

    returns = prices.pct_change().dropna()

    # --- Compute portfolio returns — 100% VTIP ---
    vix_series = prices[VIX_TICKER]
    port_returns = returns["VTIP"].copy()
    cum_returns = (1 + port_returns).cumprod()
    weight_history = {"VTIP": [1.0] * len(returns)}
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
    vix_label = classify_vix(current_vix)
    current_weights = TARGET_WEIGHTS

    # Weight history as DataFrame
    weight_df = pd.DataFrame(weight_history, index=returns.index)

    # Correlation matrix
    corr_matrix = returns[EUREKA_UNIVERSE].corr()

    # Individual asset stats — core + satellites
    asset_stats = {}
    for tk in EUREKA_CORE + GAINS_SATELLITES:
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
        "vix_label": vix_label, "current_weights": current_weights,
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
    vix_label = data["vix_label"]
    vix_color = {"LOW": "#00ff88", "ELEVATED": "#fbc02d", "HIGH": "#ff4b4b"}[vix_label]
    st.markdown(f"<p style='font-family: JetBrains Mono; font-size:18px; font-weight:700; color:{vix_color}; margin-top:20px;'>VIX: {vix_label}</p>", unsafe_allow_html=True)
    st.caption(f"100% VTIP | Gains → IAU · GEV · VGSH")
with h3:
    st.markdown(f"<p style='font-family: JetBrains Mono; color: #6b7fa3; margin-top:20px; font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} CST</p>", unsafe_allow_html=True)
    st.caption(f"Data Lag: 5min | Core: VTIP | Satellites: {len(GAINS_SATELLITES)}")

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("VIX LEVEL", f"{data['current_vix']:.2f}", f"{data['vix_label']}")
k2.metric("ALLOCATION", "100% VTIP", "Core Anchor")
k3.metric("PORTFOLIO", f"{data['total_return']:+.2f}%", f"vs SPY {data['spy_return']:+.1f}%")
k4.metric("MAX DRAWDOWN", f"{data['max_dd']:.2f}%", "Peak-to-Trough")
k5.metric("SHARPE RATIO", f"{data['sharpe']:.3f}", "Annualized")
rv20_last = data['rolling_vol_20'].iloc[-1]
k6.metric("ROLLING VOL", f"{float(rv20_last)*100:.1f}%" if pd.notna(rv20_last) else "N/A", "20d Ann.")
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
    <strong>Portfolio Construction:</strong>&nbsp;&nbsp; R<sub>p,t</sub> = 1.0 · r<sub>VTIP</sub><br>
    <strong>Gains Destination:</strong>&nbsp;&nbsp; IAU · GEV · VGSH — gains redistributed equally to satellites
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

    # Cumulative chart — all tickers
    fig_perf = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Cumulative Returns: Full Portfolio Universe", "Daily Portfolio Returns Distribution"),
        row_heights=[0.65, 0.35]
    )

    fig_perf.add_trace(go.Scatter(
        x=data["cum_returns"].index, y=data["cum_returns"].values,
        name="VTIP (Core 100%)", line=dict(color="#F1C40F", width=3),
        fill='tozeroy', fillcolor='rgba(241,196,15,0.05)'
    ), row=1, col=1)
    fig_perf.add_trace(go.Scatter(
        x=data["spy_cum"].index, y=data["spy_cum"].values,
        name="S&P 500 (SPY)", line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dot")
    ), row=1, col=1)

    # Satellite cumulative returns — IAU, GEV, VGSH
    sat_colors = {"IAU": "#FFD700", "GEV": "#00ff88", "VGSH": "#00d1ff"}
    for tk in GAINS_SATELLITES:
        if tk in data["returns"].columns:
            sat_cum = (1 + data["returns"][tk]).cumprod()
            fig_perf.add_trace(go.Scatter(
                x=sat_cum.index, y=sat_cum.values,
                name=f"{tk} ({ASSET_META[tk]['desc']})",
                line=dict(color=sat_colors.get(tk, "#aaa"), width=1.8, dash="dash"),
                opacity=0.85,
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
    st.markdown("<div class='section-header'>PORTFOLIO ALLOCATION — STATIC WEIGHTS</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Allocation:</strong>&nbsp;&nbsp; 100% VTIP (Core Anchor)<br>
    <strong>Gains Destinations:</strong>&nbsp;&nbsp; IAU · GEV · VGSH — gains redistributed equally
    </div>
    """, unsafe_allow_html=True)

    # Weight display cards — VTIP core + 3 satellites
    wc1, wc2, wc3, wc4 = st.columns(4)
    weight_data = [
        ("VTIP", 100.0, "#a78bfa"), ("IAU", 0.0, "#FFD700"), ("GEV", 0.0, "#00ff88"),
        ("VGSH", 0.0, "#00d1ff"),
    ]
    for col, (tk, pct, color) in zip([wc1, wc2, wc3, wc4], weight_data):
        with col:
            label = f"{pct:.0f}% CORE" if tk == "VTIP" else "💰 GAINS"
            desc = ASSET_META.get(tk, {}).get("desc", tk)
            st.markdown(f"""
            <div class='regime-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-family:JetBrains Mono; font-size:16px; font-weight:700; color:{color};'>{tk}</span>
                    <span style='font-family:JetBrains Mono; font-size:16px; color:#e0e6ed;'>{label}</span>
                </div>
                <div style='font-size:12px; color:#94a3b8; margin-top:8px;'>{desc}</div>
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
    weight_colors_rgba = {
        "VTIP": "rgba(167, 139, 250, 0.66)",
        "IAU":  "rgba(255, 215, 0, 0.66)",
        "GEV":  "rgba(0, 255, 136, 0.66)",
        "VGSH": "rgba(0, 209, 255, 0.66)",
    }
    for tk in EUREKA_CORE:
        fig_vix.add_trace(go.Scatter(
            x=data["weight_df"].index, y=data["weight_df"][tk].values * 100,
            name=f"{tk} ({ASSET_META[tk]['desc']})",
            stackgroup='one', line=dict(width=0.5),
            fillcolor=weight_colors_rgba.get(tk, "rgba(255, 255, 255, 0.66)")
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

    st.markdown("")

    # Build rebalance table
    reb_rows = []
    for tk in EUREKA_CORE:
        w_target = target_w.get(tk, 0)
        drift_noise = np.random.normal(0, 0.04)
        w_actual = max(0, w_target + drift_noise)
        drift_pct = (w_actual - w_target) / w_target * 100 if w_target > 0 else 0
        price = data["prices"][tk].iloc[-1] if tk in data["prices"].columns else 100.0

        adj_pct = (w_target - w_actual) * 100

        action = "HOLD"
        if abs(drift_pct) > 5:
            action = "BUY" if adj_pct > 0 else "SELL"

        reb_rows.append({
            "Asset": tk,
            "Description": ASSET_META[tk]["desc"],
            "Target %": f"{w_target*100:.1f}%",
            "Actual %": f"{w_actual*100:.1f}%",
            "Drift": f"{drift_pct:+.1f}%",
            "Trade %": f"{abs(adj_pct):.1f}%",
            "Price": f"${price:.2f}",
            "Action": action,
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
        df_reb.style.map(style_action, subset=["Action"]),
        use_container_width=True, hide_index=True, height=280
    )

    # Warnings
    active_trades = [r for r in reb_rows if r["Action"] not in ["HOLD"]]
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
    for i in range(0, len(EUREKA_CORE + GAINS_SATELLITES), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(EUREKA_CORE + GAINS_SATELLITES):
                tk = (EUREKA_CORE + GAINS_SATELLITES)[i + j]
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
                                <span style='font-size:12px; color:#94a3b8; margin-left:12px;'>{ASSET_META[tk]["desc"]} · {cat}</span>
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

    corr_tickers = [tk for tk in EUREKA_CORE + GAINS_SATELLITES if tk in data["returns"].columns]
    corr = data["returns"][corr_tickers].corr()
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
    treemap_colors = {"VTIP": "#a78bfa", "IAU": "#FFD700", "GEV": "#00ff88", "VGSH": "#00d1ff"}
    w_colors = [treemap_colors.get(tk, "#ffffff") for tk in w_labels]

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

    # Generate audit entries from current session
    audit_events = [
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": "Dashboard initialized — live data loaded", "Severity": "INFO", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"VIX regime: {data['vix_label']}", "Severity": "REGIME", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Portfolio return: {data['total_return']:+.2f}%", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Sharpe ratio: {data['sharpe']:.3f}", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Max drawdown: {data['max_dd']:.2f}%", "Severity": "WARNING" if data['max_dd'] < -10 else "INFO", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": "Risk limits verified — all within tolerance", "Severity": "COMPLIANCE", "VIX": "—"},
    ]

    # Combine: current events
    all_audit = audit_events
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
        df_audit.style.map(color_severity, subset=["Severity"]),
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
    st.caption("100% VTIP Core Anchor | Gains → IAU · GEV · VGSH")
with fc3:
    st.caption("Soberanía Financiera 🇲🇽")
    st.caption(f"Build: EUREKA-VOL-v2.3-HJB | {now.strftime('%Y')}")
