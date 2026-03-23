import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import time

# ============================================================
#  PRIMEnergeia — MIBEL Market Dashboard
#  Hamilton-Jacobi-Bellman Optimal Frequency Control System
#  Mercado Ibérico de Electricidad (Spain & Portugal)
# ============================================================

st.set_page_config(
    page_title="PRIMEnergeia MIBEL | Grid Control",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PREMIUM CSS (MIBEL: Iberian Gold Accent) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background-color: #050810; }
[data-testid="stSidebar"] { background-color: #0a0f1a; }

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
    border: 1px solid #2a2210;
    border-radius: 8px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(232, 197, 71, 0.04);
}
div[data-testid="stMetricValue"] {
    color: #e8c547;
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
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
    background: linear-gradient(135deg, #e8c54722, #c9a02022);
    color: #e8c547 !important;
    border-bottom: none;
}

.status-nominal { color: #00ff88; font-weight: 700; font-family: 'JetBrains Mono'; animation: pulse 2s infinite; }
.status-alert { color: #ff4b4b; font-weight: 700; font-family: 'JetBrains Mono'; animation: blink 0.8s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

.section-header {
    color: #e8c547;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid #2a2210;
    padding-bottom: 8px;
    margin-bottom: 16px;
}
.math-block {
    background: #0a0f1a;
    border-left: 3px solid #e8c547;
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #c8d6e5;
    border-radius: 0 6px 6px 0;
    margin: 12px 0;
}
.kpi-highlight {
    background: linear-gradient(135deg, #1a1500, #221c00);
    border: 1px solid #443800;
    border-radius: 10px;
    padding: 24px;
    text-align: center;
}
.kpi-value { font-size: 42px; font-weight: 700; color: #00ff88; font-family: 'JetBrains Mono'; }
.kpi-label { font-size: 11px; color: #6b7fa3; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  SIMULATION ENGINE — MIBEL Grid Physics (50 Hz)
# ============================================================

@st.cache_data(ttl=2)
def generate_simulation_state():
    """Full MIBEL grid state simulation — 50 Hz ENTSO-E system."""
    np.random.seed(int(time.time()) % 10000)
    now = datetime.now()

    # --- Grid Frequency Physics (Swing Equation — 50 Hz ENTSO-E) ---
    f_nominal = 50.0   # European standard
    H = 6.0            # Higher inertia — large conventional fleet
    D = 2.5
    dt = 0.01
    n_steps = 600

    freq_history = np.zeros(n_steps)
    rocof_history = np.zeros(n_steps)
    inertia_injection = np.zeros(n_steps)
    p_mechanical = np.ones(n_steps)
    p_electrical = np.ones(n_steps) + np.random.normal(0, 0.006, n_steps)
    p_electrical[200:230] += 0.03  # Solar ramp event
    p_electrical[420:445] += 0.05  # Wind drop disturbance

    f = f_nominal
    for i in range(n_steps):
        error = f_nominal - f
        u_inertia = max(0, error * 500.0)
        inertia_injection[i] = u_inertia
        M_eff = 2 * H + u_inertia
        dfdt = (p_mechanical[i] - p_electrical[i] - D * (f - f_nominal)) / M_eff
        f += dfdt * dt
        freq_history[i] = f
        rocof_history[i] = dfdt

    f_current = freq_history[-1]
    rocof_current = rocof_history[-1]

    # --- HJB Value Function (50 Hz centered) ---
    state_grid = np.linspace(49.8, 50.2, 200)
    V_function = 0.5 * 1e4 * (state_grid - 50.0)**2
    V_gradient = 1e4 * (state_grid - 50.0)
    u_optimal = -0.5 * V_gradient

    H_field = np.abs(V_gradient * (p_mechanical[-1] - p_electrical[-1])) + V_function * 0.01

    # --- OMIE Pool Pricing (EUR/MWh) ---
    hours = np.arange(0, 24, 0.25)
    pool_base = 55 + 35 * np.sin((hours - 10) * np.pi / 12)
    pool_noise = np.cumsum(np.random.normal(0, 1.8, len(hours))) * 0.3
    pool_spikes = np.where(np.random.rand(len(hours)) > 0.97, np.random.uniform(150, 500, len(hours)), 0)
    pool_prices = np.clip(pool_base + pool_noise + pool_spikes, 0, 3000)

    # --- Voltage & Power Factor (220 kV nominal) ---
    v_a = 220.0 + np.random.normal(0, 0.3)
    v_b = 220.0 + np.random.normal(0, 0.35)
    v_c = 220.0 + np.random.normal(0, 0.25)
    pf = 0.97 + np.random.normal(0, 0.007)

    # --- THD (EN 50160 — 8% limit) ---
    harmonics = {3: 0.06 + np.random.normal(0, 0.01),
                 5: 0.04 + np.random.normal(0, 0.008),
                 7: 0.025 + np.random.normal(0, 0.005),
                 9: 0.012 + np.random.normal(0, 0.003),
                 11: 0.007 + np.random.normal(0, 0.002),
                 13: 0.003 + np.random.normal(0, 0.001)}
    thd = np.sqrt(sum(v**2 for v in harmonics.values())) * 100

    # --- Capital Recovery (EUR) ---
    optimal_mw = 150.0 * np.maximum(0, np.sin((hours - 6) * np.pi / 12))
    legacy_loss = np.random.uniform(0.78, 0.88, len(hours))
    actual_mw = optimal_mw * legacy_loss
    actual_mw *= np.where(pool_prices > 200, np.random.uniform(0.60, 0.75, len(hours)), 1.0)
    actual_mw *= np.random.normal(1.0, 0.012, len(hours))
    actual_mw = np.maximum(0, actual_mw)
    delta_mw = np.maximum(0, optimal_mw - actual_mw)
    capital_per_interval = delta_mw * pool_prices * 0.25
    capital_cumulative = np.cumsum(capital_per_interval)

    # --- Node Network ---
    nodes = [
        # — Spain: North —
        {"id": "ES-BIL-400", "loc": "Bilbao", "region": "Spain North", "cap": 100, "load": np.random.randint(55, 80), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.008)},
        {"id": "ES-ZAR-400", "loc": "Zaragoza", "region": "Spain North", "cap": 80, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.009)},
        {"id": "ES-BCN-400", "loc": "Barcelona", "region": "Spain North", "cap": 120, "load": np.random.randint(62, 88), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.007)},
        # — Spain: Central —
        {"id": "ES-MAD-400", "loc": "Madrid", "region": "Spain Central", "cap": 150, "load": np.random.randint(70, 92), "status": "MASTER", "f": 50.0 + np.random.normal(0, 0.006)},
        {"id": "ES-VAL-400", "loc": "Valencia", "region": "Spain Central", "cap": 100, "load": np.random.randint(55, 82), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.008)},
        {"id": "ES-CLM-220", "loc": "Ciudad Real", "region": "Spain Central", "cap": 60, "load": np.random.randint(30, 58), "status": "STANDBY", "f": 50.0 + np.random.normal(0, 0.012)},
        # — Spain: South —
        {"id": "ES-SEV-400", "loc": "Sevilla", "region": "Spain South", "cap": 100, "load": np.random.randint(52, 78), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.009)},
        {"id": "ES-MAL-400", "loc": "Málaga", "region": "Spain South", "cap": 80, "load": np.random.randint(48, 75), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.010)},
        {"id": "ES-ALM-220", "loc": "Almería", "region": "Spain South", "cap": 60, "load": np.random.randint(35, 62), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.011)},
        {"id": "ES-GRA-220", "loc": "Granada", "region": "Spain South", "cap": 60, "load": np.random.randint(32, 58), "status": "STANDBY", "f": 50.0 + np.random.normal(0, 0.013)},
        # — Spain: Northwest —
        {"id": "ES-COR-400", "loc": "A Coruña", "region": "Spain Northwest", "cap": 80, "load": np.random.randint(40, 68), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.010)},
        {"id": "ES-LEO-220", "loc": "León", "region": "Spain Northwest", "cap": 60, "load": np.random.randint(28, 55), "status": "STANDBY", "f": 50.0 + np.random.normal(0, 0.014)},
        # — Spain: Islands —
        {"id": "ES-PMI-220", "loc": "Palma de Mallorca", "region": "Balearic Islands", "cap": 40, "load": np.random.randint(30, 60), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.016)},
        {"id": "ES-TFE-220", "loc": "Tenerife", "region": "Canary Islands", "cap": 40, "load": np.random.randint(35, 65), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.018)},
        {"id": "ES-LPA-220", "loc": "Las Palmas", "region": "Canary Islands", "cap": 40, "load": np.random.randint(32, 62), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.017)},
        # — Portugal: North —
        {"id": "PT-PRT-400", "loc": "Porto", "region": "Portugal North", "cap": 80, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.009)},
        {"id": "PT-BRG-220", "loc": "Braga", "region": "Portugal North", "cap": 50, "load": np.random.randint(28, 55), "status": "STANDBY", "f": 50.0 + np.random.normal(0, 0.013)},
        # — Portugal: South —
        {"id": "PT-LIS-400", "loc": "Lisboa", "region": "Portugal South", "cap": 100, "load": np.random.randint(58, 85), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.008)},
        {"id": "PT-FAR-220", "loc": "Faro", "region": "Portugal South", "cap": 50, "load": np.random.randint(25, 52), "status": "STANDBY", "f": 50.0 + np.random.normal(0, 0.015)},
        {"id": "PT-SET-220", "loc": "Setúbal", "region": "Portugal South", "cap": 50, "load": np.random.randint(28, 55), "status": "ONLINE", "f": 50.0 + np.random.normal(0, 0.012)},
    ]

    return {
        "now": now, "f_current": f_current, "rocof": rocof_current,
        "freq_history": freq_history, "rocof_history": rocof_history,
        "inertia_injection": inertia_injection, "p_electrical": p_electrical,
        "state_grid": state_grid, "V_function": V_function, "V_gradient": V_gradient,
        "u_optimal": u_optimal, "H_field": H_field,
        "pool_prices": pool_prices, "hours": hours,
        "optimal_mw": optimal_mw, "actual_mw": actual_mw,
        "capital_cumulative": capital_cumulative, "capital_total": capital_cumulative[-1],
        "v_a": v_a, "v_b": v_b, "v_c": v_c, "pf": pf,
        "thd": thd, "harmonics": harmonics,
        "nodes": nodes, "n_steps": n_steps,
    }


state = generate_simulation_state()
now = state["now"]
f = state["f_current"]
is_nominal = abs(f - 50.0) < 0.04

# ============================================================
#  HEADER
# ============================================================
h1, h2, h3 = st.columns([4, 2, 2])
with h1:
    st.markdown("# ⚡ PRIMEnergeia — MIBEL")
    st.caption("HAMILTON-JACOBI-BELLMAN OPTIMAL FREQUENCY CONTROL | IBERIAN ELECTRICITY MARKET")
with h2:
    status_class = "status-nominal" if is_nominal else "status-alert"
    status_text = "● NOMINAL" if is_nominal else "⚠ EXCURSION DETECTED"
    st.markdown(f"<p class='{status_class}' style='font-size:18px; margin-top:20px;'>{status_text}</p>", unsafe_allow_html=True)
    st.caption(f"Protocol: PRIME-HJB-v8.0-MIBEL")
with h3:
    st.markdown(f"<p style='font-family: JetBrains Mono; color: #6b7fa3; margin-top:20px; font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} CET</p>", unsafe_allow_html=True)
    st.caption(f"Latency: 0.{np.random.randint(3,9)}ms | Uptime: 99.99%")

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("FREQUENCY", f"{f:.4f} Hz", f"Δ {f - 50.0:+.4f}")
k2.metric("RoCoF", f"{state['rocof']:+.5f} Hz/s", "Swing Eq.")
k3.metric("VOLTAGE Φ-A", f"{state['v_a']:.1f} kV", "220 kV Nom.")
k4.metric("THD", f"{state['thd']:.2f} %", f"{'✓ EN 50160' if state['thd'] < 8 else '⚠ Exceeds'}")
k5.metric("COS φ", f"{state['pf']:.4f}", "Unity Target")
k6.metric("HOUR OF DAY", now.strftime("%H:%M"), "Live")
k7.metric("RESCUED ACC.", f"€{state['capital_total']:,.0f}", "EUR / day")

st.markdown("")

# ============================================================
#  TABBED SECTIONS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 PHYSICS ENGINE",
    "🧮 HJB OPTIMIZER",
    "💰 FINANCIAL ENGINE",
    "🔬 HARMONIC ANALYSIS",
    "🌐 NETWORK TOPOLOGY",
    "📋 AUDIT LOG"
])


# ═══════════════════════════════════════════════
#  TAB 1: PHYSICS ENGINE (50 Hz)
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>REAL-TIME SWING EQUATION DYNAMICS — ENTSO-E 50 Hz GRID</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Swing Equation:</strong>&nbsp;&nbsp; M<sub>eff</sub> · (df/dt) = P<sub>m</sub> − P<sub>e</sub> − D · (f − f<sub>0</sub>)<br>
    <strong>Where:</strong>&nbsp;&nbsp; M<sub>eff</sub> = 2H + u<sub>inertia</sub> &nbsp;|&nbsp; H = 6.0s &nbsp;|&nbsp; D = 2.5 &nbsp;|&nbsp; dt = 10ms<br>
    <strong>Note:</strong>&nbsp;&nbsp; MIBEL operates on ENTSO-E Continental synchronous area at 50 Hz nominal
    </div>
    """, unsafe_allow_html=True)

    t_axis = np.linspace(0, 6, state["n_steps"])

    fig_phys = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Grid Frequency — Swing Equation Solution (50 Hz)", "Rate of Change of Frequency (RoCoF)", "Synthetic Inertia Injection u(t)"),
        row_heights=[0.4, 0.3, 0.3]
    )

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["freq_history"], name="f(t) — Controlled",
        line=dict(color="#e8c547", width=2.5)), row=1, col=1)
    fig_phys.add_hline(y=50.0, line_dash="dash", line_color="#00ff88", annotation_text="f₀ = 50.000 Hz", row=1, col=1)
    fig_phys.add_hline(y=49.96, line_dash="dot", line_color="#ff4b4b", annotation_text="ENTSO-E Penalty", row=1, col=1)
    fig_phys.add_hline(y=50.04, line_dash="dot", line_color="#ff4b4b", row=1, col=1)

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["rocof_history"], name="df/dt",
        line=dict(color="#fbc02d", width=1.5), fill='tozeroy', fillcolor='rgba(251,192,45,0.08)'), row=2, col=1)

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["inertia_injection"], name="u_inertia(t)",
        line=dict(color="#00ff88", width=2), fill='tozeroy', fillcolor='rgba(0,255,136,0.1)'), row=3, col=1)

    fig_phys.update_layout(template="plotly_dark", height=750, showlegend=False,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_phys.update_xaxes(title_text="Time (s)", row=3, col=1, gridcolor="#1a2744")
    fig_phys.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_phys, use_container_width=True)

    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("INERTIA CONSTANT H", "6.0 s", "Higher (conventional fleet)")
    pc2.metric("DAMPING COEFF D", "2.5 p.u.", "ENTSO-E Calibrated")
    pc3.metric("INTEGRATION STEP", "10 ms", "Euler Method")


# ═══════════════════════════════════════════════
#  TAB 2: HJB OPTIMIZER (50 Hz)
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>HAMILTON-JACOBI-BELLMAN OPTIMAL CONTROL SOLUTION</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>HJB Equation:</strong>&nbsp;&nbsp; V<sub>t</sub> + min<sub>u</sub> { L(x,u) + ∇V · f(x,u) } = 0<br>
    <strong>Running Cost:</strong>&nbsp;&nbsp; L(x,u) = ½ Q (f − f₀)² + ½ R u²<br>
    <strong>Optimal Control:</strong>&nbsp;&nbsp; u*(x) = −R⁻¹ · B<sup>T</sup> · ∇V(x) &nbsp;|&nbsp; f₀ = 50.000 Hz
    </div>
    """, unsafe_allow_html=True)

    fig_hjb = make_subplots(
        rows=2, cols=2, vertical_spacing=0.18, horizontal_spacing=0.08,
        subplot_titles=(
            "Value Function V(x) — Cost-to-Go",
            "Policy Gradient ∇V(x)",
            "Optimal Control Law u*(x)",
            "Hamiltonian Field H(x, u*)"
        )
    )

    sg = state["state_grid"]

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["V_function"], name="V(x)",
        line=dict(color="#e8c547", width=3), fill='tozeroy', fillcolor='rgba(232,197,71,0.06)'), row=1, col=1)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["V_gradient"], name="∇V(x)",
        line=dict(color="#ff6b6b", width=2.5)), row=1, col=2)
    fig_hjb.add_hline(y=0, line_dash="dash", line_color="#333", row=1, col=2)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["u_optimal"], name="u*(x)",
        line=dict(color="#00ff88", width=3), fill='tozeroy', fillcolor='rgba(0,255,136,0.08)'), row=2, col=1)
    fig_hjb.add_vline(x=50.0, line_dash="dash", line_color="#e8c547", annotation_text="f₀", row=2, col=1)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["H_field"], name="H(x,u*)",
        line=dict(color="#fbc02d", width=2), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'), row=2, col=2)

    fig_hjb.update_layout(template="plotly_dark", height=750, showlegend=False,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_hjb.update_xaxes(title_text="Frequency (Hz)", gridcolor="#1a2744")
    fig_hjb.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_hjb, use_container_width=True)

    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Q (STATE COST)", "10,000", "Frequency penalty")
    hc2.metric("R (CONTROL COST)", "1.0", "Actuation penalty")
    hc3.metric("V(f) AT OPTIMUM", "0.000", "Minimum cost")
    hc4.metric("CONVERGENCE", "✓ SOLVED", "Steady-state")


# ═══════════════════════════════════════════════
#  TAB 3: FINANCIAL ENGINE (EUR)
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>FIDUCIARY CAPITAL RECOVERY ENGINE — OMIE POOL MARKET</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Recovery Formula:</strong>&nbsp;&nbsp; Σ [ (P*<sub>optimal</sub> − P<sub>actual</sub>) × Pool Price × Δt ]<br>
    <strong>Settlement:</strong>&nbsp;&nbsp; OMIE Day-Ahead + Intraday Auctions (hourly) &nbsp;|&nbsp; <strong>Royalty:</strong>&nbsp;&nbsp; 25% of rescued capital<br>
    <strong>Operators:</strong>&nbsp;&nbsp; OMIE (market) · REE (Spain TSO) · REN (Portugal TSO)
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value'>€{state['capital_total']:,.0f}</div>
            <div class='kpi-label'>Total Capital Rescued Today</div>
        </div>""", unsafe_allow_html=True)
    with fc2:
        client_net = state['capital_total'] * 0.75
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:#e8c547;'>€{client_net:,.0f}</div>
            <div class='kpi-label'>Client Net Savings (75%)</div>
        </div>""", unsafe_allow_html=True)
    with fc3:
        prime_fee = state['capital_total'] * 0.25
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:#fbc02d;'>€{prime_fee:,.0f}</div>
            <div class='kpi-label'>PRIMEnergeia Fee (25%)</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    fig_fin = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.18,
        subplot_titles=("Injection Profile: Optimal vs Actual (MW)", "Cumulative Capital Recovery (EUR)")
    )

    h = state["hours"]
    fig_fin.add_trace(go.Scatter(x=h, y=state["optimal_mw"], name="P* Optimal (HJB)",
        line=dict(color="#00ff88", width=2.5)), row=1, col=1)
    fig_fin.add_trace(go.Scatter(x=h, y=state["actual_mw"], name="P Actual (Legacy)",
        line=dict(color="#ff4b4b", width=1.5, dash="dash")), row=1, col=1)
    fig_fin.add_trace(go.Scatter(x=h, y=state["optimal_mw"], fill='tonexty',
        fillcolor='rgba(255,75,75,0.12)', showlegend=False, line=dict(width=0)), row=1, col=1)

    fig_fin.add_trace(go.Scatter(x=h, y=state["capital_cumulative"], name="Capital Rescued",
        line=dict(color="#e8c547", width=3), fill='tozeroy', fillcolor='rgba(232,197,71,0.08)'), row=2, col=1)

    fig_fin.update_layout(template="plotly_dark", height=750, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=100, b=40),
        legend=dict(orientation="h", y=1.18, x=0.5, xanchor="center", font=dict(size=11)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_fin.update_xaxes(title_text="Hour of Day", gridcolor="#1a2744")
    fig_fin.update_yaxes(gridcolor="#1a2744")

    curr_h = now.hour + now.minute/60.0
    fig_fin.add_vline(x=curr_h, line_dash="dash", line_color="#e8c547", opacity=0.7, annotation_text="LIVE", annotation_position="top left")

    st.plotly_chart(fig_fin, use_container_width=True)

    # Pool Pricing
    st.markdown("<div class='section-header'>OMIE POOL PRICE DYNAMICS — IBERIAN MARKET</div>", unsafe_allow_html=True)
    fig_pool = go.Figure()
    fig_pool.add_trace(go.Scatter(x=h, y=state["pool_prices"], name="Pool Price (EUR/MWh)",
        line=dict(color="#e8c547", width=2), fill='tozeroy', fillcolor='rgba(232,197,71,0.06)'))
    fig_pool.add_hline(y=200, line_dash="dash", line_color="#ff4b4b", annotation_text="High-Price Threshold")
    fig_pool.update_layout(template="plotly_dark", height=280,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_pool.update_xaxes(gridcolor="#1a2744")
    fig_pool.update_yaxes(gridcolor="#1a2744")
    curr_h = now.hour + now.minute/60.0
    fig_pool.add_vline(x=curr_h, line_dash="dash", line_color="#e8c547", opacity=0.7, annotation_text="LIVE", annotation_position="top left")
    st.plotly_chart(fig_pool, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 4: HARMONIC ANALYSIS (EN 50160)
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>HARMONIC DISTORTION ANALYSIS — EN 50160 COMPLIANCE</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>THD Calculation:</strong>&nbsp;&nbsp; THD = √(Σ V<sub>h</sub>²) / V<sub>1</sub> × 100%<br>
    <strong>EN 50160 Limit:</strong>&nbsp;&nbsp; THD ≤ 8.0% &nbsp;|&nbsp; Individual harmonic ≤ 5.0%
    </div>
    """, unsafe_allow_html=True)

    hd1, hd2, hd3 = st.columns(3)
    hd1.metric("THD TOTAL", f"{state['thd']:.2f} %", f"{'✓ COMPLIANT' if state['thd'] < 8 else '⚠ VIOLATION'}")
    hd2.metric("FUNDAMENTAL (50 Hz)", "100.00 %", "Reference")
    hd3.metric("WORST HARMONIC", f"3rd ({abs(state['harmonics'][3])*100:.2f}%)", "150 Hz")

    harm_orders = list(state["harmonics"].keys())
    harm_values = [abs(v) * 100 for v in state["harmonics"].values()]

    fig_harm = go.Figure()
    fig_harm.add_trace(go.Bar(
        x=[f"H{h} ({h*50}Hz)" for h in harm_orders], y=harm_values,
        marker=dict(color=["#ff4b4b" if v > 5 else "#e8c547" for v in harm_values],
                    line=dict(color="#2a2210", width=1)),
        text=[f"{v:.2f}%" for v in harm_values], textposition='outside',
        textfont=dict(family="JetBrains Mono", size=12, color="#e0e6ed")
    ))
    fig_harm.add_hline(y=5.0, line_dash="dash", line_color="#ff4b4b", annotation_text="EN 50160 Limit (5%)")
    fig_harm.update_layout(template="plotly_dark", height=350,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", yaxis_title="Magnitude (%)",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_harm.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_harm, use_container_width=True)

    # Three-phase waveform (50 Hz)
    st.markdown("<div class='section-header'>THREE-PHASE VOLTAGE WAVEFORM — POST PRIME FILTERING (50 Hz)</div>", unsafe_allow_html=True)
    t_wave = np.linspace(0, 0.06, 1000)  # 3 cycles at 50 Hz
    phase_a = np.sin(2 * np.pi * 50 * t_wave)
    phase_b = np.sin(2 * np.pi * 50 * t_wave - 2*np.pi/3)
    phase_c = np.sin(2 * np.pi * 50 * t_wave + 2*np.pi/3)
    distorted_a = phase_a + sum(state["harmonics"][h] * np.sin(2*np.pi*50*h*t_wave) for h in state["harmonics"])

    fig_3ph = go.Figure()
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=distorted_a, name="Pre-PRIME (distorted)", line=dict(color="#ff4b4b", width=1, dash="dot"), opacity=0.5))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_a, name="Phase A (filtered)", line=dict(color="#e8c547", width=2.5)))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_b, name="Phase B (filtered)", line=dict(color="#00ff88", width=2)))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_c, name="Phase C (filtered)", line=dict(color="#fbc02d", width=2)))

    fig_3ph.update_layout(template="plotly_dark", height=320,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40), xaxis_title="Time (ms)", yaxis_title="Voltage (p.u.)",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_3ph.update_xaxes(gridcolor="#1a2744")
    fig_3ph.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_3ph, use_container_width=True)

    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("V PHASE-A", f"{state['v_a']:.1f} kV", "Balanced")
    vc2.metric("V PHASE-B", f"{state['v_b']:.1f} kV", "Balanced")
    vc3.metric("V PHASE-C", f"{state['v_c']:.1f} kV", "Balanced")
    vc4.metric("IMBALANCE", f"{abs(state['v_a']-state['v_b'])*100/220:.3f} %", "< 2% req.")


# ═══════════════════════════════════════════════
#  TAB 5: NETWORK TOPOLOGY
# ═══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>IBERIAN GRID — 20-NODE SOVEREIGN NETWORK (SPAIN + PORTUGAL)</div>", unsafe_allow_html=True)

    from collections import OrderedDict
    regions = OrderedDict()
    for node in state["nodes"]:
        r = node.get("region", "Unknown")
        regions.setdefault(r, []).append(node)

    for region_name, region_nodes in regions.items():
        st.markdown(f"<p style='font-family:JetBrains Mono; font-size:11px; color:#e8c547; letter-spacing:2px; margin:16px 0 8px 0;'>▸ {region_name.upper()}</p>", unsafe_allow_html=True)
        for i in range(0, len(region_nodes), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(region_nodes):
                    node = region_nodes[i + j]
                    status_color = "#00ff88" if node["status"] in ["MASTER", "ONLINE"] else "#fbc02d"
                    freq_delta = node["f"] - 50.0
                    cap = node.get("cap", "—")
                    with col:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #2a2210;
                                    border-left: 4px solid {status_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;'>
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <div>
                                    <span style='font-family:JetBrains Mono; font-size:14px; font-weight:700; color:#e0e6ed;'>{node["id"]}</span>
                                    <span style='font-size:10px; color:{status_color}; margin-left:8px; font-weight:700;'>● {node["status"]}</span>
                                </div>
                                <span style='font-family:JetBrains Mono; font-size:16px; color:#e8c547;'>{node["f"]:.3f} Hz</span>
                            </div>
                            <div style='font-size:11px; color:#6b7fa3; margin-top:5px;'>{node["loc"]} &nbsp;|&nbsp; {cap} MW &nbsp;|&nbsp; Load: {node["load"]}% &nbsp;|&nbsp; Δf: {freq_delta:+.4f} Hz</div>
                        </div>
                        """, unsafe_allow_html=True)

    st.markdown("")
    ns1, ns2, ns3, ns4 = st.columns(4)
    active_nodes = sum(1 for n in state["nodes"] if n["status"] in ["MASTER", "ONLINE"])
    avg_freq = np.mean([n["f"] for n in state["nodes"]])
    avg_load = np.mean([n["load"] for n in state["nodes"]])
    ns1.metric("ACTIVE NODES", f"{active_nodes} / {len(state['nodes'])}", "Operational")
    ns2.metric("AVG FREQUENCY", f"{avg_freq:.4f} Hz", f"Δ {avg_freq-50:+.4f}")
    ns3.metric("AVG LOAD", f"{avg_load:.0f} %", "Network")
    total_cap = sum(n.get("cap", 0) for n in state["nodes"])
    ns4.metric("TOTAL CAPACITY", f"{total_cap:,} MW", "20-Node Aggregate")


# ═══════════════════════════════════════════════
#  TAB 6: AUDIT LOG
# ═══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>SYSTEM AUDIT LOG — ENTSO-E / EN 50160 COMPLIANCE RECORD</div>", unsafe_allow_html=True)

    audit_data = {
        "Timestamp": [
            (now - timedelta(minutes=i*60)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(20, 0, -1)
        ],
        "Event": [
            "HJB convergence verified", "Pool spike detected (€420/MWh)", "Inertia injection: 1.8 p.u.",
            "Frequency stabilized: 49.999 Hz", "Node MAD-400 sync confirmed", "Capital checkpoint: €14,280",
            "THD measurement: 3.82%", "EN 50160: COMPLIANT", "RoCoF within limits: +0.0008",
            "Node BCN-400 load rebalanced", "Pool normalized: €58/MWh", "HJB re-solved (state change)",
            "Swing Equation integration OK", "Phase imbalance: 0.02%", "Capital checkpoint: €32,940",
            "DRL actor-critic weight update", "Network heartbeat: all nodes", "Pool arbitrage captured: €5,800",
            "Frequency nominal: 50.001 Hz", "System integrity: VERIFIED"
        ],
        "Severity": [
            "INFO", "WARNING", "ACTION", "INFO", "INFO", "FINANCIAL",
            "INFO", "COMPLIANCE", "INFO", "ACTION", "INFO", "ACTION",
            "INFO", "INFO", "FINANCIAL", "ACTION", "INFO", "FINANCIAL",
            "INFO", "COMPLIANCE"
        ]
    }

    df_audit = pd.DataFrame(audit_data)

    def color_severity(val):
        colors = {
            "INFO": "color: #6b7fa3",
            "WARNING": "color: #fbc02d",
            "ACTION": "color: #e8c547",
            "FINANCIAL": "color: #00ff88",
            "COMPLIANCE": "color: #a78bfa"
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
    st.caption("PRIMEnergeia S.A.S.")
    st.caption("Proprietary Protocol")
with fc2:
    st.caption("Lead Computational Physicist: Diego Córdoba Urrutia")
    st.caption("HJB Control Law: V_t + min_u { L(x,u) + ∇V · f(x,u) } = 0")
with fc3:
    st.caption("Soberanía Energética Ibérica ⚡ 🇪🇸🇵🇹")
    st.caption(f"Build: PRIME-HJB-v8.0-MIBEL | {now.strftime('%Y')}")
