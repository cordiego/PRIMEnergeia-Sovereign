import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import time
import warnings

try:
    from scipy.optimize import minimize as scipy_minimize
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

warnings.filterwarnings("ignore")

# ============================================================
#  EUREKA SOVEREIGN — 6-Ticker Portfolio Engine
#  VTIP Core | GEV · IAU · VGSH · KMLM · AGQ | Cash Tracking
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
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0, 209, 255, 0.04);
}
div[data-testid="stMetricValue"] {
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 36px;
    font-weight: 700;
    text-shadow: 0 0 12px rgba(0,209,255,0.3);
}
div[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace; color: #c8d6e5; }
div[data-testid="stMetricLabel"] {
    color: #c8d6e5;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

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
.math-block {
    background: #0a0f1a; border-left: 3px solid #00d1ff;
    padding: 16px 20px; font-family: 'JetBrains Mono', monospace;
    font-size: 14px; color: #e2e8f0; border-radius: 0 6px 6px 0; margin: 12px 0;
}
.kpi-highlight {
    background: linear-gradient(135deg, #001a33, #002244);
    border: 1px solid #003366; border-radius: 10px; padding: 24px; text-align: center;
}
.kpi-value { font-size: 38px; font-weight: 700; color: #00ff88; font-family: 'JetBrains Mono'; }
.kpi-label { font-size: 12px; color: #94a3b8; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }

.regime-card {
    background: linear-gradient(135deg, #0d1520, #111b2a);
    border: 1px solid #1a2744; border-radius: 10px; padding: 16px 20px; margin-bottom: 10px;
}
.stMarkdown, .stMarkdown p { color: #e2e8f0 !important; font-size: 15px; }
div[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  SIDEBAR — Cash Input & Configuration
# ============================================================
with st.sidebar:
    st.markdown("### 💰 Cash & Configuration")
    st.markdown("---")
    platform_cash = st.number_input(
        "Platform Cash ($)", min_value=0.0, value=0.0, step=100.0,
        help="Enter your uninvested brokerage purchasing power"
    )
    vgsh_floor = st.number_input(
        "VGSH Life-Support Floor ($)", min_value=0.0, value=50000.0, step=5000.0,
        help="Minimum VGSH balance for PRIME deal liquidity"
    )
    sweep_retention = st.slider(
        "VTIP Growth Retention (%)", 5, 50, 20, step=5,
        help="Percentage of daily VTIP gains retained for compounding"
    )
    st.markdown("---")
    st.caption("🏦 VGSH = Cash equivalent for multi-million PRIME deals")
    st.caption(f"📈 VTIP sweeps {100 - sweep_retention}% of daily gains")


# ============================================================
#  UNIVERSE
# ============================================================

EUREKA_CORE = ["VTIP"]
GAINS_SATELLITES = ["GEV", "IAU", "VGSH", "KMLM", "AGQ"]
GROWTH_SATELLITES = ["GEV", "IAU", "KMLM", "AGQ"]
CASH_EQUIVALENT = "VGSH"
FULL_UNIVERSE = EUREKA_CORE + GAINS_SATELLITES
BENCHMARK = "SPY"
VIX_TICKER = "^VIX"
ALL_TICKERS = FULL_UNIVERSE + [BENCHMARK, VIX_TICKER]

TARGET_WEIGHTS = {"VTIP": 1.0}

ASSET_META = {
    "VTIP": {"desc": "TIPS Bond",           "category": "Core Anchor",   "color": "#a78bfa"},
    "GEV":  {"desc": "Nuclear Energy",       "category": "Growth",        "color": "#00ff88"},
    "IAU":  {"desc": "Gold",                 "category": "Growth",        "color": "#FFD700"},
    "VGSH": {"desc": "Short Treasury",       "category": "Cash Equiv.",   "color": "#00d1ff"},
    "KMLM": {"desc": "Managed Futures",      "category": "Growth",        "color": "#ff6b6b"},
    "AGQ":  {"desc": "2× Silver",            "category": "Growth (2×)",   "color": "#C0C0C0"},
}


def classify_vix(vix_level):
    if vix_level < 18:
        return "LOW"
    elif vix_level <= 28:
        return "ELEVATED"
    else:
        return "HIGH"


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


# ============================================================
#  LIVE DATA ENGINE
# ============================================================
@st.cache_data(ttl=300)
def load_market_data(sweep_retention_val=20):
    sweep_retention = sweep_retention_val
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

    vix_series = prices[VIX_TICKER]
    port_returns = returns["VTIP"].copy()
    cum_returns = (1 + port_returns).cumprod()
    spy_cum = (1 + returns[BENCHMARK]).cumprod()

    # ── Growth Satellite Optimization (GEV, IAU, KMLM, AGQ) — Max Sharpe ──
    growth_tickers = [tk for tk in GROWTH_SATELLITES if tk in returns.columns]
    n_growth = len(growth_tickers)
    ew_growth_weights = {tk: 1.0 / n_growth for tk in growth_tickers} if n_growth > 0 else {}

    if n_growth >= 2:
        ret_matrix = returns[growth_tickers]
        mu = ret_matrix.mean().values * 252
        cov = ret_matrix.cov().values * 252
        rf = 0.045

        def neg_sharpe(w):
            port_ret = np.dot(w, mu)
            port_vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            return -(port_ret - rf) / port_vol if port_vol > 1e-10 else 1e6

        x0 = np.array([1.0 / n_growth] * n_growth)

        if HAS_SCIPY:
            constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
            bounds = tuple((0.01, 0.80) for _ in range(n_growth))
            try:
                result = scipy_minimize(neg_sharpe, x0, method='SLSQP',
                                        bounds=bounds, constraints=constraints,
                                        options={'maxiter': 1000, 'ftol': 1e-12})
                opt_w = result.x if result.success else x0
            except Exception:
                opt_w = x0
        else:
            np.random.seed(42)
            best_sharpe = 1e6
            opt_w = x0.copy()
            for _ in range(20000):
                w = np.random.dirichlet(np.ones(n_growth))
                s = neg_sharpe(w)
                if s < best_sharpe:
                    best_sharpe = s
                    opt_w = w.copy()

        growth_opt_weights = {tk: float(w) for tk, w in zip(growth_tickers, opt_w)}
    elif n_growth == 1:
        growth_opt_weights = {growth_tickers[0]: 1.0}
    else:
        growth_opt_weights = {}

    # Full satellite weights (growth + VGSH cash equiv)
    # 85% of swept gains → growth, 15% → VGSH
    sweep_retention_pct = sweep_retention / 100.0
    sweep_ratio = 1.0 - sweep_retention_pct
    growth_share = 0.85
    vgsh_share = 0.15

    sat_opt_weights = {}
    for tk, w in growth_opt_weights.items():
        sat_opt_weights[tk] = w * growth_share
    sat_opt_weights["VGSH"] = vgsh_share

    opt_weights = {"VTIP": 1.0}
    opt_weights.update(sat_opt_weights)

    # ── Daily Gains Sweep Simulation ──
    vtip_base = 1.0
    sat_values = {tk: 0.0 for tk in GAINS_SATELLITES if tk in returns.columns}
    composite_values = [1.0]
    vtip_values = [1.0]
    sat_total_values = [0.0]

    for i in range(len(returns)):
        vtip_daily_ret = returns["VTIP"].iloc[i]
        vtip_base *= (1 + vtip_daily_ret)

        for tk in sat_values:
            if sat_values[tk] > 0:
                sat_values[tk] *= (1 + returns[tk].iloc[i])

        # Daily sweep: if VTIP gained, sweep portion to satellites
        if vtip_daily_ret > 0.0001:  # min threshold
            daily_gain = vtip_base * vtip_daily_ret / (1 + vtip_daily_ret)
            sweep_amount = daily_gain * sweep_ratio
            for tk in sat_values:
                w = sat_opt_weights.get(tk, 0)
                sat_values[tk] += sweep_amount * w
            vtip_base -= sweep_amount

        total_sat = sum(sat_values.values())
        vtip_values.append(vtip_base)
        sat_total_values.append(total_sat)
        composite_values.append(vtip_base + total_sat)

    composite_idx = [returns.index[0] - pd.Timedelta(days=1)] + list(returns.index)
    composite_series = pd.Series(composite_values, index=composite_idx, name="Composite")
    vtip_sim_series = pd.Series(vtip_values, index=composite_idx, name="VTIP Base")
    sat_sim_series = pd.Series(sat_total_values, index=composite_idx, name="Satellite Gains")

    full_port_returns = composite_series.pct_change().dropna()
    full_cum_returns = composite_series / composite_series.iloc[0]

    # ── Rolling analytics ──
    rolling_vol_20 = port_returns.rolling(20).std() * np.sqrt(252)
    rolling_vol_60 = port_returns.rolling(60).std() * np.sqrt(252)
    rolling_sharpe = (port_returns.rolling(60).mean() * 252) / (port_returns.rolling(60).std() * np.sqrt(252))

    full_rolling_vol_20 = full_port_returns.rolling(20).std() * np.sqrt(252)
    full_rolling_vol_60 = full_port_returns.rolling(60).std() * np.sqrt(252)
    full_rolling_sharpe = (full_port_returns.rolling(60).mean() * 252) / (full_port_returns.rolling(60).std() * np.sqrt(252))

    # ── Key metrics ──
    total_return = float((cum_returns.iloc[-1] - 1) * 100)
    spy_return = float((spy_cum.iloc[-1] - 1) * 100)
    max_dd = float((cum_returns / cum_returns.cummax() - 1).min() * 100)
    ann_vol = float(port_returns.std() * np.sqrt(252) * 100)
    ann_return = float(port_returns.mean() * 252)
    sharpe = float(ann_return / (port_returns.std() * np.sqrt(252))) if port_returns.std() > 0 else 0.0
    alpha = float(total_return - spy_return)

    full_total_return = float((full_cum_returns.iloc[-1] - 1) * 100)
    full_max_dd = float((full_cum_returns / full_cum_returns.cummax() - 1).min() * 100)
    full_ann_vol = float(full_port_returns.std() * np.sqrt(252) * 100)
    full_ann_return = float(full_port_returns.mean() * 252)
    full_sharpe = float(full_ann_return / (full_port_returns.std() * np.sqrt(252))) if full_port_returns.std() > 0 else 0.0
    full_alpha = float(full_total_return - spy_return)

    drawdown_series = (cum_returns / cum_returns.cummax() - 1) * 100
    full_drawdown_series = (full_cum_returns / full_cum_returns.cummax() - 1) * 100

    var_95 = float(np.percentile(port_returns, 5) * 100)
    cvar_95 = float(port_returns[port_returns <= np.percentile(port_returns, 5)].mean() * 100) if len(port_returns[port_returns <= np.percentile(port_returns, 5)]) > 0 else var_95

    full_var_95 = float(np.percentile(full_port_returns, 5) * 100)
    full_cvar_95 = float(full_port_returns[full_port_returns <= np.percentile(full_port_returns, 5)].mean() * 100) if len(full_port_returns[full_port_returns <= np.percentile(full_port_returns, 5)]) > 0 else full_var_95

    sat_breakdown = {tk: float(sat_values.get(tk, 0)) for tk in GAINS_SATELLITES if tk in sat_values}
    total_sat_value = float(sum(sat_breakdown.values()))

    current_vix = float(vix_series.iloc[-1])
    vix_label = classify_vix(current_vix)

    # Per-ticker RSI signals
    ticker_signals = {}
    for tk in FULL_UNIVERSE:
        if tk in prices.columns and len(prices[tk].dropna()) >= 52:
            closes = prices[tk].dropna()
            rsi = compute_rsi(closes, 14)
            current_rsi = float(rsi.iloc[-1]) if not rsi.empty and pd.notna(rsi.iloc[-1]) else 50.0
            ema_20 = float(compute_ema(closes, 20).iloc[-1])
            ema_50 = float(compute_ema(closes, 50).iloc[-1])
            ema_trend = "BULLISH" if ema_20 > ema_50 else "BEARISH"

            if current_rsi < 30:
                signal = "BUY"
            elif current_rsi > 70:
                signal = "SELL"
            else:
                signal = "HOLD"

            ticker_signals[tk] = {
                "rsi": current_rsi,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "ema_trend": ema_trend,
                "signal": signal,
            }

    # Individual asset stats
    asset_stats = {}
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

    corr_matrix = returns[[tk for tk in FULL_UNIVERSE if tk in returns.columns]].corr()

    return {
        "prices": prices, "returns": returns,
        "port_returns": port_returns, "cum_returns": cum_returns, "spy_cum": spy_cum,
        "rolling_vol_20": rolling_vol_20, "rolling_vol_60": rolling_vol_60,
        "rolling_sharpe": rolling_sharpe,
        "drawdown_series": drawdown_series,
        "total_return": total_return, "spy_return": spy_return,
        "max_dd": max_dd, "ann_vol": ann_vol, "sharpe": sharpe, "alpha": alpha,
        "var_95": var_95, "cvar_95": cvar_95,
        "full_port_returns": full_port_returns, "full_cum_returns": full_cum_returns,
        "full_rolling_vol_20": full_rolling_vol_20, "full_rolling_vol_60": full_rolling_vol_60,
        "full_rolling_sharpe": full_rolling_sharpe,
        "full_drawdown_series": full_drawdown_series,
        "full_total_return": full_total_return,
        "full_max_dd": full_max_dd, "full_ann_vol": full_ann_vol, "full_sharpe": full_sharpe, "full_alpha": full_alpha,
        "full_var_95": full_var_95, "full_cvar_95": full_cvar_95,
        "opt_weights": opt_weights, "sat_opt_weights": sat_opt_weights,
        "growth_opt_weights": growth_opt_weights,
        "composite_series": composite_series,
        "vtip_sim_series": vtip_sim_series,
        "sat_sim_series": sat_sim_series,
        "sat_breakdown": sat_breakdown,
        "total_sat_value": total_sat_value,
        "vtip_base_value": vtip_base,
        "vix_series": vix_series, "current_vix": current_vix,
        "vix_label": vix_label,
        "corr_matrix": corr_matrix, "asset_stats": asset_stats,
        "ticker_signals": ticker_signals,
        "n_days": len(returns),
    }


# ============================================================
#  LOAD DATA
# ============================================================
data = load_market_data(sweep_retention_val=sweep_retention)
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
    st.caption("6-TICKER PORTFOLIO ENGINE — DAILY GAINS SWEEP")
with h2:
    vix_label = data["vix_label"]
    vix_color = {"LOW": "#00ff88", "ELEVATED": "#fbc02d", "HIGH": "#ff4b4b"}[vix_label]
    st.markdown(f"<p style='font-family: JetBrains Mono; font-size:18px; font-weight:700; color:{vix_color}; margin-top:20px;'>VIX: {vix_label}</p>", unsafe_allow_html=True)
    st.caption("VTIP → GEV · IAU · VGSH · KMLM · AGQ")
with h3:
    st.markdown(f"<p style='font-family: JetBrains Mono; color: #6b7fa3; margin-top:20px; font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} CST</p>", unsafe_allow_html=True)
    cash_display = f"${platform_cash:,.0f}" if platform_cash > 0 else "—"
    st.caption(f"Cash: {cash_display} | Sats: {len(GAINS_SATELLITES)}")

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
st.markdown("<div class='section-header'>VTIP CORE (100% ALLOCATION)</div>", unsafe_allow_html=True)
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("VIX LEVEL", f"{data['current_vix']:.2f}", f"{data['vix_label']}")
k2.metric("VTIP RETURN", f"{data['total_return']:+.2f}%", f"vs SPY {data['spy_return']:+.1f}%")
k3.metric("MAX DRAWDOWN", f"{data['max_dd']:.2f}%", "Peak-to-Trough")
k4.metric("SHARPE", f"{data['sharpe']:.3f}", "Annualized")
rv20_last = data['rolling_vol_20'].iloc[-1]
k5.metric("ROLLING VOL", f"{float(rv20_last)*100:.1f}%" if pd.notna(rv20_last) else "N/A", "20d Ann.")
k6.metric("α vs SPY", f"{data['alpha']:+.2f}%", "Excess Return")

# ============================================================
#  GAINS ALLOCATION CARDS
# ============================================================
st.markdown("")
st.markdown("<div class='section-header'>GAINS ALLOCATION — DAILY SWEEP → SATELLITES (MAX SHARPE OPTIMIZED)</div>", unsafe_allow_html=True)

sat_w = data["sat_opt_weights"]
all_display = [("VTIP", 1.0)] + list(sat_w.items())
if platform_cash > 0:
    all_display.append(("CASH", 0))

ow_cols = st.columns(len(all_display))
for i, (tk, w) in enumerate(all_display):
    meta = ASSET_META.get(tk, {"color": "#94a3b8"})
    color = meta.get("color", "#94a3b8")
    with ow_cols[i]:
        if tk == "VTIP":
            label, sublabel = "100%", "CAPITAL BASE"
        elif tk == "CASH":
            label, sublabel = f"${platform_cash:,.0f}", "PLATFORM CASH"
            color = "#94a3b8"
        else:
            label, sublabel = f"{w*100:.1f}%", "OF GAINS"
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid {color}44;
                    border-radius: 8px; padding: 10px 14px; text-align: center;'>
            <div style='font-family:JetBrains Mono; font-size:13px; font-weight:700; color:{color};'>{tk}</div>
            <div style='font-family:JetBrains Mono; font-size:24px; font-weight:700; color:#e0e6ed; margin: 2px 0;'>{label}</div>
            <div style='font-size:10px; color:#94a3b8;'>{sublabel}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")
fk1, fk2, fk3, fk4, fk5 = st.columns(5)
fk1.metric("SAT VALUE", f"${data['total_sat_value']:.4f}", "Per $1 Invested")
fk2.metric("COMPOSITE", f"{data['full_total_return']:+.2f}%", f"vs SPY {data['spy_return']:+.1f}%")
fk3.metric("MAX DD", f"{data['full_max_dd']:.2f}%", "Composite")
fk4.metric("SHARPE", f"{data['full_sharpe']:.3f}", "Composite")
fk5.metric("α vs SPY", f"{data['full_alpha']:+.2f}%", "Composite")

st.markdown("")

# ============================================================
#  TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 PERFORMANCE",
    "🎯 TICKER SIGNALS",
    "⚡ SWEEP ENGINE",
    "🛡️ RISK",
    "🔬 DEEP-DIVE",
    "🏦 CASH & LIQUIDITY",
    "📋 AUDIT LOG"
])


# ═══════════════════════════════════════════════
#  TAB 1: PERFORMANCE
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>CUMULATIVE PERFORMANCE — FULL UNIVERSE</div>", unsafe_allow_html=True)

    # Per-Ticker Table
    st.markdown("<div class='section-header'>PER-TICKER SUMMARY</div>", unsafe_allow_html=True)
    ticker_rows = []
    for tk in FULL_UNIVERSE:
        stats = data["asset_stats"].get(tk, {})
        sig = data["ticker_signals"].get(tk, {})
        if stats:
            ticker_rows.append({
                "Ticker": tk,
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
            if val == "BUY":
                return "color: #00ff88; font-weight: 700"
            elif val == "SELL":
                return "color: #ff4b4b; font-weight: 700"
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
        st.dataframe(
            styled,
            use_container_width=True, hide_index=True, height=280
        )

    st.markdown("")

    # Performance chart
    fig_perf = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("VTIP Capital + Daily Swept Gains → Satellite Growth", "Daily Returns"),
        row_heights=[0.65, 0.35]
    )

    fig_perf.add_trace(go.Scatter(
        x=data["full_cum_returns"].index, y=data["full_cum_returns"].values,
        name="⚡ Composite", line=dict(color="#a78bfa", width=3.5),
        fill='tozeroy', fillcolor='rgba(167,139,250,0.06)'
    ), row=1, col=1)

    fig_perf.add_trace(go.Scatter(
        x=data["sat_sim_series"].index, y=data["sat_sim_series"].values,
        name="💰 Satellite Value", line=dict(color="#00ff88", width=1.5),
        fill='tozeroy', fillcolor='rgba(0,255,136,0.08)'
    ), row=1, col=1)

    fig_perf.add_trace(go.Scatter(
        x=data["cum_returns"].index, y=data["cum_returns"].values,
        name="VTIP Core", line=dict(color="#F1C40F", width=2.5)
    ), row=1, col=1)

    fig_perf.add_trace(go.Scatter(
        x=data["spy_cum"].index, y=data["spy_cum"].values,
        name="SPY", line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dot")
    ), row=1, col=1)

    # Individual satellites
    for tk in GAINS_SATELLITES:
        if tk in data["returns"].columns:
            sat_cum = (1 + data["returns"][tk]).cumprod()
            fig_perf.add_trace(go.Scatter(
                x=sat_cum.index, y=sat_cum.values,
                name=f"{tk} ({ASSET_META[tk]['desc']})",
                line=dict(color=ASSET_META[tk]["color"], width=1.5, dash="dash"), opacity=0.8,
            ), row=1, col=1)

    fig_perf.add_hline(y=1.0, line_dash="dash", line_color="#333", row=1, col=1)

    # Daily returns
    vtip_colors = ["rgba(241,196,15,0.33)" if r > 0 else "rgba(255,75,75,0.33)" for r in data["port_returns"].values]
    fig_perf.add_trace(go.Bar(
        x=data["port_returns"].index, y=data["port_returns"].values * 100,
        name="VTIP Daily (%)", marker_color=vtip_colors, opacity=0.4
    ), row=2, col=1)

    fig_perf.update_layout(
        template="plotly_dark", height=850, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
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

    st.markdown("""
    <div class='math-block'>
    <strong>RSI(14):</strong>&nbsp;&nbsp; < 30 → BUY (oversold) | > 70 → SELL (overbought)<br>
    <strong>EMA:</strong>&nbsp;&nbsp; 20d vs 50d — Golden Cross → BUY | Death Cross → SELL<br>
    <strong>Each ticker is evaluated independently.</strong>
    </div>
    """, unsafe_allow_html=True)

    for tk in FULL_UNIVERSE:
        sig = data["ticker_signals"].get(tk, {})
        stats = data["asset_stats"].get(tk, {})
        if not sig or not stats:
            continue

        signal = sig["signal"]
        rsi = sig["rsi"]
        ema_trend = sig["ema_trend"]
        color = ASSET_META[tk]["color"]
        signal_color = "#00ff88" if signal == "BUY" else ("#ff4b4b" if signal == "SELL" else "#6b7fa3")
        signal_emoji = "🟢" if signal == "BUY" else ("🔴" if signal == "SELL" else "⚪")
        ret_color = "#00ff88" if stats["return"] > 0 else "#ff4b4b"

        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid {color}44;
                    border-left: 4px solid {signal_color}; border-radius: 8px; padding: 16px 20px; margin-bottom: 10px;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <span style='font-family:JetBrains Mono; font-size:18px; font-weight:700; color:{color};'>{tk}</span>
                    <span style='font-size:12px; color:#94a3b8; margin-left:12px;'>{ASSET_META[tk]["desc"]} · {ASSET_META[tk]["category"]}</span>
                </div>
                <span style='font-family:JetBrains Mono; font-size:22px; font-weight:700; color:{signal_color};'>
                    {signal_emoji} {signal}
                </span>
            </div>
            <div style='display:flex; gap:28px; margin-top:12px; font-family:JetBrains Mono; font-size:13px;'>
                <span>Price: <b style='color:#00d1ff;'>${stats["last_price"]:.2f}</b></span>
                <span>Return: <b style='color:{ret_color};'>{stats["return"]:+.2f}%</b></span>
                <span>RSI: <b style='color:{"#ff4b4b" if rsi > 70 else ("#00ff88" if rsi < 30 else "#fbc02d")}';>{rsi:.1f}</b></span>
                <span>EMA: <b style='color:{"#00ff88" if ema_trend == "BULLISH" else "#ff4b4b"};'>{ema_trend}</b></span>
                <span>Vol: <b style='color:#fbc02d;'>{stats["vol"]:.1f}%</b></span>
                <span>MaxDD: <b style='color:#ff4b4b;'>{stats["max_dd"]:.1f}%</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  TAB 3: SWEEP ENGINE
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>DAILY GAINS SWEEP ENGINE</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='math-block'>
    <strong>Strategy:</strong>&nbsp;&nbsp; 100% capital in VTIP<br>
    <strong>Daily Sweep:</strong>&nbsp;&nbsp; {100 - sweep_retention}% of VTIP gains → satellites<br>
    <strong>Retention:</strong>&nbsp;&nbsp; {sweep_retention}% of gains stay in VTIP for compounding<br>
    <strong>Growth Bucket:</strong>&nbsp;&nbsp; GEV · IAU · KMLM · AGQ (Max Sharpe optimized)<br>
    <strong>Cash Bucket:</strong>&nbsp;&nbsp; VGSH 15% priority (PRIME deal liquidity)
    </div>
    """, unsafe_allow_html=True)

    # Growth bucket weights
    st.markdown("<div class='section-header'>GROWTH BUCKET OPTIMIZATION (OF SWEPT GAINS × 85%)</div>", unsafe_allow_html=True)
    gc = st.columns(len(data["growth_opt_weights"]))
    for i, (tk, w) in enumerate(data["growth_opt_weights"].items()):
        color = ASSET_META.get(tk, {}).get("color", "#fff")
        with gc[i]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid {color}44;
                        border-radius: 8px; padding: 12px 16px; text-align: center;'>
                <div style='font-family:JetBrains Mono; font-size:14px; font-weight:700; color:{color};'>{tk}</div>
                <div style='font-family:JetBrains Mono; font-size:28px; font-weight:700; color:#e0e6ed;'>{w*100:.1f}%</div>
                <div style='font-size:10px; color:#94a3b8;'>OF GROWTH</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # Sweep simulation chart
    fig_sweep = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
        subplot_titles=("VTIP Base vs Satellite Accumulated Value", "Composite Portfolio Growth"),
        row_heights=[0.5, 0.5]
    )

    fig_sweep.add_trace(go.Scatter(
        x=data["vtip_sim_series"].index, y=data["vtip_sim_series"].values,
        name="VTIP Base", line=dict(color="#a78bfa", width=2.5),
        fill='tozeroy', fillcolor='rgba(167,139,250,0.08)'
    ), row=1, col=1)

    fig_sweep.add_trace(go.Scatter(
        x=data["sat_sim_series"].index, y=data["sat_sim_series"].values,
        name="Satellite Total", line=dict(color="#00ff88", width=2),
        fill='tozeroy', fillcolor='rgba(0,255,136,0.08)'
    ), row=1, col=1)

    fig_sweep.add_trace(go.Scatter(
        x=data["composite_series"].index, y=data["composite_series"].values,
        name="Composite", line=dict(color="#00d1ff", width=3)
    ), row=2, col=1)

    fig_sweep.add_trace(go.Scatter(
        x=data["spy_cum"].index, y=data["spy_cum"].values,
        name="SPY", line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dot")
    ), row=2, col=1)

    fig_sweep.update_layout(
        template="plotly_dark", height=700, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_sweep.update_xaxes(gridcolor="#1a2744")
    fig_sweep.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_sweep, use_container_width=True)

    # Satellite breakdown
    st.markdown("<div class='section-header'>SATELLITE VALUE BREAKDOWN (per $1 VTIP invested)</div>", unsafe_allow_html=True)
    breakdown_rows = []
    for tk, val in data["sat_breakdown"].items():
        pct_of_total = (val / data["total_sat_value"] * 100) if data["total_sat_value"] > 0 else 0
        breakdown_rows.append({
            "Ticker": tk,
            "Role": ASSET_META.get(tk, {}).get("category", "SAT"),
            "Value": f"${val:.6f}",
            "% of Sats": f"{pct_of_total:.1f}%",
            "Opt Weight": f"{data['sat_opt_weights'].get(tk, 0)*100:.1f}%",
        })
    if breakdown_rows:
        st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════
#  TAB 4: RISK
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>RISK ANALYTICS — VTIP CORE vs COMPOSITE</div>", unsafe_allow_html=True)

    rk1, rk2, rk3, rk4 = st.columns(4)
    rk1.metric("VTIP VOL", f"{data['ann_vol']:.2f}%", "Annualized")
    rk2.metric("VTIP VaR(95)", f"{data['var_95']:.3f}%", "Daily")
    rk3.metric("COMP VOL", f"{data['full_ann_vol']:.2f}%", "Annualized")
    rk4.metric("COMP VaR(95)", f"{data['full_var_95']:.3f}%", "Daily")

    fig_risk = make_subplots(
        rows=2, cols=2, vertical_spacing=0.18, horizontal_spacing=0.08,
        subplot_titles=("Rolling 60d Volatility", "Rolling 60d Sharpe", "Drawdown", "Return Distribution")
    )

    rv = data["rolling_vol_60"].dropna()
    fig_risk.add_trace(go.Scatter(
        x=rv.index, y=rv.values * 100, name="VTIP 60d Vol",
        line=dict(color="#fbc02d", width=2.5), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'
    ), row=1, col=1)
    frv = data["full_rolling_vol_60"].dropna()
    fig_risk.add_trace(go.Scatter(
        x=frv.index, y=frv.values * 100, name="Composite 60d Vol",
        line=dict(color="#a78bfa", width=2.5, dash="dash")
    ), row=1, col=1)

    rs = data["rolling_sharpe"].dropna().clip(-3, 5)
    fig_risk.add_trace(go.Scatter(x=rs.index, y=rs.values, name="VTIP Sharpe", line=dict(color="#00d1ff", width=2.5)), row=1, col=2)
    frs = data["full_rolling_sharpe"].dropna().clip(-3, 5)
    fig_risk.add_trace(go.Scatter(x=frs.index, y=frs.values, name="Composite Sharpe", line=dict(color="#a78bfa", width=2.5, dash="dash")), row=1, col=2)
    fig_risk.add_hline(y=0, line_dash="dash", line_color="#ff4b4b", row=1, col=2)

    dd = data["drawdown_series"]
    fig_risk.add_trace(go.Scatter(x=dd.index, y=dd.values, name="VTIP DD", line=dict(color="#ff4b4b", width=2), fill='tozeroy', fillcolor='rgba(255,75,75,0.12)'), row=2, col=1)
    fdd = data["full_drawdown_series"]
    fig_risk.add_trace(go.Scatter(x=fdd.index, y=fdd.values, name="Composite DD", line=dict(color="#a78bfa", width=2, dash="dash")), row=2, col=1)

    fig_risk.add_trace(go.Histogram(x=data["port_returns"].values * 100, nbinsx=60, name="VTIP", marker_color="#00d1ff", opacity=0.5), row=2, col=2)
    fig_risk.add_trace(go.Histogram(x=data["full_port_returns"].values * 100, nbinsx=60, name="Composite", marker_color="#a78bfa", opacity=0.4), row=2, col=2)

    fig_risk.update_layout(
        template="plotly_dark", height=850, showlegend=True, barmode='overlay',
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", font=dict(size=10)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3")
    )
    fig_risk.update_xaxes(gridcolor="#1a2744")
    fig_risk.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_risk, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 5: ASSET DEEP-DIVE
# ═══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>INDIVIDUAL ASSET ANALYTICS</div>", unsafe_allow_html=True)

    for i in range(0, len(FULL_UNIVERSE), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(FULL_UNIVERSE):
                tk = FULL_UNIVERSE[i + j]
                stats = data["asset_stats"].get(tk, {})
                if not stats:
                    continue
                ret_color = "#00ff88" if stats["return"] > 0 else "#ff4b4b"
                color = ASSET_META[tk]["color"]
                with col:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #1a2744;
                                border-left: 4px solid {color}; border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <span style='font-family:JetBrains Mono; font-size:16px; font-weight:700; color:{color};'>{tk}</span>
                            <span style='font-family:JetBrains Mono; font-size:18px; color:#00d1ff;'>${stats["last_price"]:.2f}</span>
                        </div>
                        <div style='font-size:11px; color:#94a3b8; margin-top:4px;'>{ASSET_META[tk]["desc"]} · {ASSET_META[tk]["category"]}</div>
                        <div style='display:flex; gap:16px; margin-top:10px; font-family:JetBrains Mono; font-size:12px;'>
                            <span>Ret: <b style='color:{ret_color};'>{stats["return"]:+.2f}%</b></span>
                            <span>Vol: <b style='color:#fbc02d;'>{stats["vol"]:.1f}%</b></span>
                            <span>SR: <b style='color:#00d1ff;'>{stats["sharpe"]:.2f}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # Correlation heatmap
    st.markdown("<div class='section-header'>CROSS-ASSET CORRELATION MATRIX</div>", unsafe_allow_html=True)
    corr = data["corr_matrix"]
    fig_corr = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale=[[0, "#ff4b4b"], [0.5, "#0a0f1a"], [1, "#00d1ff"]],
        zmid=0, text=np.round(corr.values, 2), texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=12, color="#e0e6ed"),
        colorbar=dict(title="ρ")
    ))
    fig_corr.update_layout(
        template="plotly_dark", height=450,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=12, color="#6b7fa3"),
        xaxis=dict(side="bottom"), yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig_corr, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 6: CASH & LIQUIDITY
# ═══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>CASH & LIQUIDITY MANAGEMENT — PRIME DEAL SUPPORT</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='math-block'>
    <strong>Platform Cash:</strong>&nbsp;&nbsp; ${platform_cash:,.2f} (uninvested purchasing power)<br>
    <strong>VGSH Target Floor:</strong>&nbsp;&nbsp; ${vgsh_floor:,.0f} (PRIME deal liquidity minimum)<br>
    <strong>VGSH Role:</strong>&nbsp;&nbsp; Cash equivalent — support multi-million dollar PRIME energy deals
    </div>
    """, unsafe_allow_html=True)

    # VGSH status
    vgsh_stats = data["asset_stats"].get("VGSH", {})
    vgsh_price = vgsh_stats.get("last_price", 0) if vgsh_stats else 0

    cl1, cl2, cl3, cl4 = st.columns(4)
    cl1.metric("PLATFORM CASH", f"${platform_cash:,.0f}", "Purchasing Power")
    cl2.metric("VGSH PRICE", f"${vgsh_price:.2f}", f"{vgsh_stats.get('return', 0):+.2f}%" if vgsh_stats else "—")
    cl3.metric("VGSH FLOOR", f"${vgsh_floor:,.0f}", "PRIME Liquidity Min")
    total_liquid = platform_cash + (data["total_sat_value"] * (data["sat_opt_weights"].get("VGSH", 0)))
    cl4.metric("TOTAL LIQUID", f"${total_liquid:,.0f}", "Cash + VGSH Alloc")

    st.markdown("")
    if platform_cash < 1000:
        st.warning("⚠️ Low platform cash — consider maintaining purchasing power for opportunities.")
    if vgsh_floor > 0:
        st.info(f"🏦 VGSH floor set at ${vgsh_floor:,.0f} for PRIME deal support. Gains sweep prioritizes VGSH at 15% of swept amount.")


# ═══════════════════════════════════════════════
#  TAB 7: AUDIT LOG
# ═══════════════════════════════════════════════
with tab7:
    st.markdown("<div class='section-header'>SYSTEM AUDIT LOG</div>", unsafe_allow_html=True)

    audit_events = [
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": "Dashboard initialized — 6-ticker universe", "Severity": "INFO", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"VIX: {data['vix_label']}", "Severity": "REGIME", "VIX": f"{data['current_vix']:.2f}"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"VTIP return: {data['total_return']:+.2f}%", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Composite return: {data['full_total_return']:+.2f}%", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Sharpe: {data['sharpe']:.3f} (VTIP) / {data['full_sharpe']:.3f} (Composite)", "Severity": "FINANCIAL", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Sweep config: {100-sweep_retention}% out, {sweep_retention}% retained", "Severity": "CONFIG", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"Platform cash: ${platform_cash:,.0f}", "Severity": "CASH", "VIX": "—"},
        {"Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "Event": f"VGSH floor: ${vgsh_floor:,.0f}", "Severity": "CASH", "VIX": "—"},
    ]

    # Add per-ticker signal events
    for tk in FULL_UNIVERSE:
        sig = data["ticker_signals"].get(tk, {})
        if sig and sig.get("signal") != "HOLD":
            audit_events.append({
                "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "Event": f"{sig['signal']} signal: {tk} (RSI={sig['rsi']:.1f}, {sig['ema_trend']})",
                "Severity": "SIGNAL",
                "VIX": "—",
            })

    df_audit = pd.DataFrame(audit_events)
    def color_severity(val):
        colors = {
            "INFO": "color: #6b7fa3", "WARNING": "color: #fbc02d",
            "FINANCIAL": "color: #00ff88", "REGIME": "color: #F1C40F",
            "CONFIG": "color: #a78bfa", "CASH": "color: #00d1ff",
            "SIGNAL": "color: #ff6b6b",
        }
        return colors.get(val, "color: white")
    try:
        audit_styled = df_audit.style.map(color_severity, subset=["Severity"])
    except AttributeError:
        audit_styled = df_audit.style.applymap(color_severity, subset=["Severity"])
    st.dataframe(audit_styled, use_container_width=True, height=500, hide_index=True)


# ============================================================
#  FOOTER
# ============================================================
st.divider()
fc1, fc2, fc3 = st.columns([2, 3, 2])
with fc1:
    st.caption("Eureka Sovereign Portfolio System")
    st.caption("6-Ticker Daily Sweep Engine")
with fc2:
    st.caption("Architect: Diego Córdoba Urrutia")
    st.caption("VTIP Core → GEV · IAU · VGSH · KMLM · AGQ")
with fc3:
    st.caption("Soberanía Financiera 🇲🇽")
    st.caption(f"Build: EUREKA-v3.0-6TK | {now.strftime('%Y')}")
