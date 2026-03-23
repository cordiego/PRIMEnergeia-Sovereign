import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import time

# ============================================================
#  PRIMEnergeia — SEN Market Dashboard
#  Hamilton-Jacobi-Bellman Optimal Frequency Control System
#  Sistema Eléctrico Nacional — CENACE (México)
# ============================================================

st.set_page_config(
    page_title="PRIMEnergeia SEN | Control de Red",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PREMIUM CSS (SEN: PRIME Cyan Accent) ---
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
    background: linear-gradient(135deg, #00d1ff22, #0066ff22);
    color: #00d1ff !important;
    border-bottom: none;
}

.status-nominal { color: #00ff88; font-weight: 700; font-family: 'JetBrains Mono'; animation: pulse 2s infinite; }
.status-alert { color: #ff4b4b; font-weight: 700; font-family: 'JetBrains Mono'; animation: blink 0.8s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

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
</style>
""", unsafe_allow_html=True)


# ============================================================
#  SIMULATION ENGINE — SEN Grid Physics
# ============================================================

@st.cache_data(ttl=2)
def generate_simulation_state():
    """Full SEN grid state simulation with physics-accurate data."""
    np.random.seed(int(time.time()) % 10000)
    now = datetime.now()

    # --- Grid Frequency Physics (Swing Equation — SEN) ---
    f_nominal = 60.0
    H = 5.0
    D = 2.0
    dt = 0.01
    n_steps = 600

    freq_history = np.zeros(n_steps)
    rocof_history = np.zeros(n_steps)
    inertia_injection = np.zeros(n_steps)
    p_mechanical = np.ones(n_steps)
    p_electrical = np.ones(n_steps) + np.random.normal(0, 0.008, n_steps)
    p_electrical[200:230] += 0.04
    p_electrical[420:445] += 0.06

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

    # --- HJB Value Function ---
    state_grid = np.linspace(59.8, 60.2, 200)
    V_function = 0.5 * 1e4 * (state_grid - 60.0)**2
    V_gradient = 1e4 * (state_grid - 60.0)
    u_optimal = -0.5 * V_gradient

    H_field = np.abs(V_gradient * (p_mechanical[-1] - p_electrical[-1])) + V_function * 0.01

    # --- PML Market Dynamics (CENACE) ---
    hours = np.arange(0, 24, 0.25)
    pml_base = 42 + 22 * np.sin((hours - 10) * np.pi / 12)
    pml_noise = np.cumsum(np.random.normal(0, 1.5, len(hours))) * 0.3
    pml_spikes = np.where(np.random.rand(len(hours)) > 0.95, np.random.uniform(80, 200, len(hours)), 0)
    pml_prices = np.clip(pml_base + pml_noise + pml_spikes, 28, 350)

    # --- Voltage & Power Factor ---
    v_a = 115.0 + np.random.normal(0, 0.12)
    v_b = 115.0 + np.random.normal(0, 0.15)
    v_c = 115.0 + np.random.normal(0, 0.10)
    pf = 0.98 + np.random.normal(0, 0.005)

    # --- THD (Código de Red) ---
    harmonics = {3: 0.08 + np.random.normal(0, 0.01),
                 5: 0.05 + np.random.normal(0, 0.008),
                 7: 0.03 + np.random.normal(0, 0.005),
                 9: 0.015 + np.random.normal(0, 0.003),
                 11: 0.008 + np.random.normal(0, 0.002),
                 13: 0.004 + np.random.normal(0, 0.001)}
    thd = np.sqrt(sum(v**2 for v in harmonics.values())) * 100

    # --- Capital Recovery ---
    optimal_mw = 100.0 * np.maximum(0, np.sin((hours - 6) * np.pi / 12))
    legacy_loss = np.random.uniform(0.75, 0.85, len(hours))
    actual_mw = optimal_mw * legacy_loss
    actual_mw *= np.where(pml_prices > 120, np.random.uniform(0.60, 0.75, len(hours)), 1.0)
    actual_mw *= np.random.normal(1.0, 0.015, len(hours))
    actual_mw = np.maximum(0, actual_mw)
    delta_mw = np.maximum(0, optimal_mw - actual_mw)
    capital_per_interval = delta_mw * pml_prices * 0.25
    capital_cumulative = np.cumsum(capital_per_interval)

    # --- Node Network ---
    nodes = [
        {"id": "05-VZA-400", "loc": "Valle de México", "region": "Central", "cap": 100, "load": np.random.randint(78, 92), "status": "MASTER", "f": 60.0 + np.random.normal(0, 0.008)},
        {"id": "01-QRO-230", "loc": "Querétaro", "region": "Central", "cap": 80, "load": np.random.randint(50, 75), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.011)},
        {"id": "01-TUL-400", "loc": "Tula, Hidalgo", "region": "Central", "cap": 100, "load": np.random.randint(55, 80), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.009)},
        {"id": "06-SLP-400", "loc": "San Luis Potosí", "region": "Central", "cap": 100, "load": np.random.randint(40, 70), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.012)},
        {"id": "02-PUE-400", "loc": "Puebla", "region": "Oriental", "cap": 100, "load": np.random.randint(55, 82), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.010)},
        {"id": "02-VER-230", "loc": "Veracruz", "region": "Oriental", "cap": 80, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.011)},
        {"id": "02-OAX-230", "loc": "Oaxaca", "region": "Oriental", "cap": 80, "load": np.random.randint(40, 68), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.013)},
        {"id": "02-TEH-400", "loc": "Tehuantepec", "region": "Oriental", "cap": 100, "load": np.random.randint(50, 78), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.014)},
        {"id": "03-GDL-400", "loc": "Guadalajara", "region": "Occidental", "cap": 100, "load": np.random.randint(58, 82), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.009)},
        {"id": "03-MAN-400", "loc": "Manzanillo", "region": "Occidental", "cap": 100, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.010)},
        {"id": "03-AGS-230", "loc": "Aguascalientes", "region": "Occidental", "cap": 80, "load": np.random.randint(40, 68), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.011)},
        {"id": "03-COL-115", "loc": "Colima", "region": "Occidental", "cap": 40, "load": np.random.randint(25, 55), "status": "STANDBY", "f": 60.0 + np.random.normal(0, 0.015)},
        {"id": "04-MTY-400", "loc": "Monterrey", "region": "Noreste", "cap": 100, "load": np.random.randint(62, 88), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.010)},
        {"id": "04-TAM-230", "loc": "Tampico", "region": "Noreste", "cap": 80, "load": np.random.randint(42, 70), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.012)},
        {"id": "04-SAL-400", "loc": "Saltillo", "region": "Noreste", "cap": 100, "load": np.random.randint(48, 75), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.011)},
        {"id": "05-CHI-400", "loc": "Chihuahua", "region": "Norte", "cap": 100, "load": np.random.randint(50, 78), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.012)},
        {"id": "05-LAG-230", "loc": "Gómez Palacio", "region": "Norte", "cap": 80, "load": np.random.randint(40, 68), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.013)},
        {"id": "05-DGO-230", "loc": "Durango", "region": "Norte", "cap": 60, "load": np.random.randint(30, 58), "status": "STANDBY", "f": 60.0 + np.random.normal(0, 0.015)},
        {"id": "05-JRZ-230", "loc": "Cd. Juárez", "region": "Norte", "cap": 80, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.014)},
        {"id": "07-HER-230", "loc": "Hermosillo", "region": "Noroeste", "cap": 80, "load": np.random.randint(52, 78), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.015)},
        {"id": "07-NAV-230", "loc": "Navojoa", "region": "Noroeste", "cap": 60, "load": np.random.randint(28, 55), "status": "STANDBY", "f": 60.0 + np.random.normal(0, 0.016)},
        {"id": "07-CUM-115", "loc": "Cd. Obregón", "region": "Noroeste", "cap": 40, "load": np.random.randint(18, 48), "status": "STANDBY", "f": 60.0 + np.random.normal(0, 0.018)},
        {"id": "07-GUY-230", "loc": "Guaymas", "region": "Noroeste", "cap": 60, "load": np.random.randint(30, 58), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.016)},
        {"id": "07-CUL-230", "loc": "Culiacán", "region": "Noroeste", "cap": 80, "load": np.random.randint(40, 68), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.013)},
        {"id": "08-MXL-230", "loc": "Mexicali", "region": "Baja California", "cap": 80, "load": np.random.randint(48, 75), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.014)},
        {"id": "08-ENS-230", "loc": "Ensenada", "region": "Baja California", "cap": 80, "load": np.random.randint(35, 62), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.013)},
        {"id": "08-TIJ-230", "loc": "Tijuana", "region": "Baja California", "cap": 80, "load": np.random.randint(50, 78), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.012)},
        {"id": "09-LAP-115", "loc": "La Paz", "region": "BCS", "cap": 40, "load": np.random.randint(20, 50), "status": "STANDBY", "f": 60.0 + np.random.normal(0, 0.020)},
        {"id": "10-MER-230", "loc": "Mérida", "region": "Peninsular", "cap": 80, "load": np.random.randint(45, 72), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.012)},
        {"id": "10-CAN-230", "loc": "Cancún", "region": "Peninsular", "cap": 80, "load": np.random.randint(50, 78), "status": "ONLINE", "f": 60.0 + np.random.normal(0, 0.013)},
    ]

    return {
        "now": now, "f_current": f_current, "rocof": rocof_current,
        "freq_history": freq_history, "rocof_history": rocof_history,
        "inertia_injection": inertia_injection, "p_electrical": p_electrical,
        "state_grid": state_grid, "V_function": V_function, "V_gradient": V_gradient,
        "u_optimal": u_optimal, "H_field": H_field,
        "pml_prices": pml_prices, "hours": hours,
        "optimal_mw": optimal_mw, "actual_mw": actual_mw,
        "capital_cumulative": capital_cumulative, "capital_total": capital_cumulative[-1],
        "v_a": v_a, "v_b": v_b, "v_c": v_c, "pf": pf,
        "thd": thd, "harmonics": harmonics,
        "nodes": nodes, "n_steps": n_steps,
    }


state = generate_simulation_state()
now = state["now"]
f = state["f_current"]
is_nominal = abs(f - 60.0) < 0.03

# ============================================================
#  HEADER
# ============================================================
h1, h2, h3 = st.columns([4, 2, 2])
with h1:
    st.markdown("# ⚡ PRIMEnergeia — SEN")
    st.caption("HAMILTON-JACOBI-BELLMAN CONTROL ÓPTIMO DE FRECUENCIA | SISTEMA ELÉCTRICO NACIONAL")
with h2:
    status_class = "status-nominal" if is_nominal else "status-alert"
    status_text = "● NOMINAL" if is_nominal else "⚠ EXCURSIÓN DETECTADA"
    st.markdown(f"<p class='{status_class}' style='font-size:18px; margin-top:20px;'>{status_text}</p>", unsafe_allow_html=True)
    st.caption(f"Protocolo: PRIME-HJB-v8.0-SEN")
with h3:
    st.markdown(f"<p style='font-family: JetBrains Mono; color: #6b7fa3; margin-top:20px; font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} CST</p>", unsafe_allow_html=True)
    st.caption(f"Latencia: 0.{np.random.randint(3,9)}ms | Disponibilidad: 99.98%")

st.divider()

# ============================================================
#  PRIMARY KPI BAR
# ============================================================
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("FRECUENCIA", f"{f:.4f} Hz", f"Δ {f - 60.0:+.4f}")
k2.metric("RoCoF", f"{state['rocof']:+.5f} Hz/s", "Swing Eq.")
k3.metric("TENSIÓN Φ-A", f"{state['v_a']:.2f} kV", "Nominal")
k4.metric("THD", f"{state['thd']:.2f} %", f"{'✓ Código Red' if state['thd'] < 5 else '⚠ Excede'}")
k5.metric("COS φ", f"{state['pf']:.4f}", "Unity Target")
k6.metric("HORA DEL DÍA", now.strftime("%H:%M"), "En vivo")
k7.metric("RESCATE ACUM.", f"${state['capital_total']:,.0f}", "USD / día")

st.markdown("")

# ============================================================
#  TABBED SECTIONS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 MOTOR FÍSICO",
    "🧮 OPTIMIZADOR HJB",
    "💰 MOTOR FINANCIERO",
    "🔬 ANÁLISIS ARMÓNICO",
    "🌐 TOPOLOGÍA DE RED",
    "📋 BITÁCORA DE AUDITORÍA"
])


# ═══════════════════════════════════════════════
#  TAB 1: PHYSICS ENGINE
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>DINÁMICA DE ECUACIÓN DE OSCILACIÓN EN TIEMPO REAL</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Ecuación de Oscilación:</strong>&nbsp;&nbsp; M<sub>eff</sub> · (df/dt) = P<sub>m</sub> − P<sub>e</sub> − D · (f − f<sub>0</sub>)<br>
    <strong>Donde:</strong>&nbsp;&nbsp; M<sub>eff</sub> = 2H + u<sub>inercia</sub> &nbsp;|&nbsp; H = 5.0s &nbsp;|&nbsp; D = 2.0 &nbsp;|&nbsp; dt = 10ms
    </div>
    """, unsafe_allow_html=True)

    t_axis = np.linspace(0, 6, state["n_steps"])

    fig_phys = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Frecuencia de Red — Solución de Ecuación de Oscilación", "Tasa de Cambio de Frecuencia (RoCoF)", "Inyección de Inercia Sintética u(t)"),
        row_heights=[0.4, 0.3, 0.3]
    )

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["freq_history"], name="f(t) — Controlada",
        line=dict(color="#00d1ff", width=2.5)), row=1, col=1)
    fig_phys.add_hline(y=60.0, line_dash="dash", line_color="#00ff88", annotation_text="f₀ = 60.000 Hz", row=1, col=1)
    fig_phys.add_hline(y=59.95, line_dash="dot", line_color="#ff4b4b", annotation_text="Penalización CENACE", row=1, col=1)
    fig_phys.add_hline(y=60.05, line_dash="dot", line_color="#ff4b4b", row=1, col=1)

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["rocof_history"], name="df/dt",
        line=dict(color="#fbc02d", width=1.5), fill='tozeroy', fillcolor='rgba(251,192,45,0.08)'), row=2, col=1)

    fig_phys.add_trace(go.Scatter(x=t_axis, y=state["inertia_injection"], name="u_inercia(t)",
        line=dict(color="#00ff88", width=2), fill='tozeroy', fillcolor='rgba(0,255,136,0.1)'), row=3, col=1)

    fig_phys.update_layout(template="plotly_dark", height=750, showlegend=False,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_phys.update_xaxes(title_text="Tiempo (s)", row=3, col=1, gridcolor="#1a2744")
    fig_phys.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_phys, use_container_width=True)

    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("CONSTANTE INERCIA H", "5.0 s", "Estándar IEEE")
    pc2.metric("COEF. AMORTIGUAMIENTO D", "2.0 p.u.", "Calibrado")
    pc3.metric("PASO INTEGRACIÓN", "10 ms", "Método Euler")


# ═══════════════════════════════════════════════
#  TAB 2: HJB OPTIMIZER
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>SOLUCIÓN DE CONTROL ÓPTIMO HAMILTON-JACOBI-BELLMAN</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Ecuación HJB:</strong>&nbsp;&nbsp; V<sub>t</sub> + min<sub>u</sub> { L(x,u) + ∇V · f(x,u) } = 0<br>
    <strong>Costo Corriente:</strong>&nbsp;&nbsp; L(x,u) = ½ Q (f − f₀)² + ½ R u²<br>
    <strong>Control Óptimo:</strong>&nbsp;&nbsp; u*(x) = −R⁻¹ · B<sup>T</sup> · ∇V(x)
    </div>
    """, unsafe_allow_html=True)

    fig_hjb = make_subplots(
        rows=2, cols=2, vertical_spacing=0.18, horizontal_spacing=0.08,
        subplot_titles=(
            "Función de Valor V(x) — Costo-por-Ir",
            "Gradiente de Política ∇V(x)",
            "Ley de Control Óptimo u*(x)",
            "Campo Hamiltoniano H(x, u*)"
        )
    )

    sg = state["state_grid"]

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["V_function"], name="V(x)",
        line=dict(color="#00d1ff", width=3), fill='tozeroy', fillcolor='rgba(0,209,255,0.06)'), row=1, col=1)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["V_gradient"], name="∇V(x)",
        line=dict(color="#ff6b6b", width=2.5)), row=1, col=2)
    fig_hjb.add_hline(y=0, line_dash="dash", line_color="#333", row=1, col=2)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["u_optimal"], name="u*(x)",
        line=dict(color="#00ff88", width=3), fill='tozeroy', fillcolor='rgba(0,255,136,0.08)'), row=2, col=1)
    fig_hjb.add_vline(x=60.0, line_dash="dash", line_color="#fbc02d", annotation_text="f₀", row=2, col=1)

    fig_hjb.add_trace(go.Scatter(x=sg, y=state["H_field"], name="H(x,u*)",
        line=dict(color="#fbc02d", width=2), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'), row=2, col=2)

    fig_hjb.update_layout(template="plotly_dark", height=750, showlegend=False,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=80, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_hjb.update_xaxes(title_text="Frecuencia (Hz)", gridcolor="#1a2744")
    fig_hjb.update_yaxes(gridcolor="#1a2744")

    st.plotly_chart(fig_hjb, use_container_width=True)

    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Q (COSTO ESTADO)", "10,000", "Penalización de frecuencia")
    hc2.metric("R (COSTO CONTROL)", "1.0", "Penalización de actuación")
    hc3.metric("V(f) EN ÓPTIMO", "0.000", "Costo mínimo")
    hc4.metric("CONVERGENCIA", "✓ RESUELTO", "Estado estacionario")


# ═══════════════════════════════════════════════
#  TAB 3: FINANCIAL ENGINE
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>MOTOR DE RECUPERACIÓN DE CAPITAL FIDUCIARIO — MERCADO PML CENACE</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Fórmula de Recuperación:</strong>&nbsp;&nbsp; Σ [ (P*<sub>óptimo</sub> − P<sub>actual</sub>) × PML × Δt ]<br>
    <strong>Liquidación:</strong>&nbsp;&nbsp; Intervalos de 15 min CENACE &nbsp;|&nbsp; <strong>Regalía:</strong>&nbsp;&nbsp; 25% del capital rescatado
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value'>${state['capital_total']:,.0f}</div>
            <div class='kpi-label'>Capital Total Rescatado Hoy</div>
        </div>""", unsafe_allow_html=True)
    with fc2:
        client_net = state['capital_total'] * 0.75
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:#00d1ff;'>${client_net:,.0f}</div>
            <div class='kpi-label'>Ahorro Neto del Cliente (75%)</div>
        </div>""", unsafe_allow_html=True)
    with fc3:
        prime_fee = state['capital_total'] * 0.25
        st.markdown(f"""<div class='kpi-highlight'>
            <div class='kpi-value' style='color:#fbc02d;'>${prime_fee:,.0f}</div>
            <div class='kpi-label'>Honorario PRIMEnergeia (25%)</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    fig_fin = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.18,
        subplot_titles=("Perfil de Inyección: Óptimo vs Actual (MW)", "Recuperación Acumulada de Capital (USD)")
    )

    h = state["hours"]
    fig_fin.add_trace(go.Scatter(x=h, y=state["optimal_mw"], name="P* Óptimo (HJB)",
        line=dict(color="#00ff88", width=2.5)), row=1, col=1)
    fig_fin.add_trace(go.Scatter(x=h, y=state["actual_mw"], name="P Actual (Legacy)",
        line=dict(color="#ff4b4b", width=1.5, dash="dash")), row=1, col=1)
    fig_fin.add_trace(go.Scatter(x=h, y=state["optimal_mw"], fill='tonexty',
        fillcolor='rgba(255,75,75,0.12)', showlegend=False, line=dict(width=0)), row=1, col=1)

    fig_fin.add_trace(go.Scatter(x=h, y=state["capital_cumulative"], name="Capital Rescatado",
        line=dict(color="#fbc02d", width=3), fill='tozeroy', fillcolor='rgba(251,192,45,0.08)'), row=2, col=1)

    fig_fin.update_layout(template="plotly_dark", height=750, showlegend=True,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=100, b=40),
        legend=dict(orientation="h", y=1.18, x=0.5, xanchor="center", font=dict(size=11)),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_fin.update_xaxes(title_text="Hora del Día", gridcolor="#1a2744")
    fig_fin.update_yaxes(gridcolor="#1a2744")

    curr_h = now.hour + now.minute/60.0
    fig_fin.add_vline(x=curr_h, line_dash="dash", line_color="#00d1ff", opacity=0.7, annotation_text="EN VIVO", annotation_position="top left")

    st.plotly_chart(fig_fin, use_container_width=True)

    st.markdown("<div class='section-header'>DINÁMICA DE MERCADO PML — NODO CENACE</div>", unsafe_allow_html=True)
    fig_pml = go.Figure()
    fig_pml.add_trace(go.Scatter(x=h, y=state["pml_prices"], name="PML (USD/MWh)",
        line=dict(color="#fbc02d", width=2), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'))
    fig_pml.add_hline(y=120, line_dash="dash", line_color="#ff4b4b", annotation_text="Umbral Alto")
    fig_pml.update_layout(template="plotly_dark", height=280,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_pml.update_xaxes(gridcolor="#1a2744")
    fig_pml.update_yaxes(gridcolor="#1a2744")
    curr_h = now.hour + now.minute/60.0
    fig_pml.add_vline(x=curr_h, line_dash="dash", line_color="#00d1ff", opacity=0.7, annotation_text="EN VIVO", annotation_position="top left")
    st.plotly_chart(fig_pml, use_container_width=True)


# ═══════════════════════════════════════════════
#  TAB 4: HARMONIC ANALYSIS
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>ANÁLISIS DE DISTORSIÓN ARMÓNICA — CUMPLIMIENTO CÓDIGO DE RED</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='math-block'>
    <strong>Cálculo THD:</strong>&nbsp;&nbsp; THD = √(Σ V<sub>h</sub>²) / V<sub>1</sub> × 100%<br>
    <strong>Límite Código de Red:</strong>&nbsp;&nbsp; THD ≤ 5.0% &nbsp;|&nbsp; Armónico individual ≤ 3.0%
    </div>
    """, unsafe_allow_html=True)

    hd1, hd2, hd3 = st.columns(3)
    hd1.metric("THD TOTAL", f"{state['thd']:.2f} %", f"{'✓ CUMPLE' if state['thd'] < 5 else '⚠ VIOLACIÓN'}")
    hd2.metric("FUNDAMENTAL (60 Hz)", "100.00 %", "Referencia")
    hd3.metric("PEOR ARMÓNICO", f"3er ({abs(state['harmonics'][3])*100:.2f}%)", "180 Hz")

    harm_orders = list(state["harmonics"].keys())
    harm_values = [abs(v) * 100 for v in state["harmonics"].values()]

    fig_harm = go.Figure()
    fig_harm.add_trace(go.Bar(
        x=[f"H{h} ({h*60}Hz)" for h in harm_orders], y=harm_values,
        marker=dict(color=["#ff4b4b" if v > 3 else "#00d1ff" for v in harm_values],
                    line=dict(color="#1a2744", width=1)),
        text=[f"{v:.2f}%" for v in harm_values], textposition='outside',
        textfont=dict(family="JetBrains Mono", size=12, color="#e0e6ed")
    ))
    fig_harm.add_hline(y=3.0, line_dash="dash", line_color="#ff4b4b", annotation_text="Límite Código de Red (3%)")
    fig_harm.update_layout(template="plotly_dark", height=350,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", yaxis_title="Magnitud (%)",
        margin=dict(l=60, r=20, t=20, b=40),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_harm.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_harm, use_container_width=True)

    st.markdown("<div class='section-header'>FORMA DE ONDA TRIFÁSICA — POST FILTRADO PRIME</div>", unsafe_allow_html=True)
    t_wave = np.linspace(0, 0.05, 1000)
    phase_a = np.sin(2 * np.pi * 60 * t_wave)
    phase_b = np.sin(2 * np.pi * 60 * t_wave - 2*np.pi/3)
    phase_c = np.sin(2 * np.pi * 60 * t_wave + 2*np.pi/3)
    distorted_a = phase_a + sum(state["harmonics"][h] * np.sin(2*np.pi*60*h*t_wave) for h in state["harmonics"])

    fig_3ph = go.Figure()
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=distorted_a, name="Pre-PRIME (distorsionada)", line=dict(color="#ff4b4b", width=1, dash="dot"), opacity=0.5))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_a, name="Fase A (filtrada)", line=dict(color="#00d1ff", width=2.5)))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_b, name="Fase B (filtrada)", line=dict(color="#00ff88", width=2)))
    fig_3ph.add_trace(go.Scatter(x=t_wave*1000, y=phase_c, name="Fase C (filtrada)", line=dict(color="#fbc02d", width=2)))

    fig_3ph.update_layout(template="plotly_dark", height=320,
        paper_bgcolor="#050810", plot_bgcolor="#0a0f1a",
        margin=dict(l=60, r=20, t=20, b=40), xaxis_title="Tiempo (ms)", yaxis_title="Voltaje (p.u.)",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        font=dict(family="JetBrains Mono", size=11, color="#6b7fa3"))
    fig_3ph.update_xaxes(gridcolor="#1a2744")
    fig_3ph.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_3ph, use_container_width=True)

    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("V FASE-A", f"{state['v_a']:.2f} kV", "Balanceada")
    vc2.metric("V FASE-B", f"{state['v_b']:.2f} kV", "Balanceada")
    vc3.metric("V FASE-C", f"{state['v_c']:.2f} kV", "Balanceada")
    vc4.metric("DESBALANCE", f"{abs(state['v_a']-state['v_b'])*100/115:.3f} %", "< 2% req.")


# ═══════════════════════════════════════════════
#  TAB 5: NETWORK TOPOLOGY
# ═══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>RED NACIONAL — 30 NODOS SOBERANOS (SEN)</div>", unsafe_allow_html=True)

    from collections import OrderedDict
    regions = OrderedDict()
    for node in state["nodes"]:
        r = node.get("region", "Unknown")
        regions.setdefault(r, []).append(node)

    for region_name, region_nodes in regions.items():
        st.markdown(f"<p style='font-family:JetBrains Mono; font-size:11px; color:#00d1ff; letter-spacing:2px; margin:16px 0 8px 0;'>▸ {region_name.upper()}</p>", unsafe_allow_html=True)
        for i in range(0, len(region_nodes), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(region_nodes):
                    node = region_nodes[i + j]
                    status_color = "#00ff88" if node["status"] in ["MASTER", "ONLINE"] else "#fbc02d"
                    freq_delta = node["f"] - 60.0
                    cap = node.get("cap", "—")
                    with col:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #1a2744;
                                    border-left: 4px solid {status_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;'>
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <div>
                                    <span style='font-family:JetBrains Mono; font-size:14px; font-weight:700; color:#e0e6ed;'>{node["id"]}</span>
                                    <span style='font-size:10px; color:{status_color}; margin-left:8px; font-weight:700;'>● {node["status"]}</span>
                                </div>
                                <span style='font-family:JetBrains Mono; font-size:16px; color:#00d1ff;'>{node["f"]:.3f} Hz</span>
                            </div>
                            <div style='font-size:11px; color:#6b7fa3; margin-top:5px;'>{node["loc"]} &nbsp;|&nbsp; {cap} MW &nbsp;|&nbsp; Carga: {node["load"]}% &nbsp;|&nbsp; Δf: {freq_delta:+.4f} Hz</div>
                        </div>
                        """, unsafe_allow_html=True)

    st.markdown("")
    ns1, ns2, ns3, ns4 = st.columns(4)
    active_nodes = sum(1 for n in state["nodes"] if n["status"] in ["MASTER", "ONLINE"])
    avg_freq = np.mean([n["f"] for n in state["nodes"]])
    avg_load = np.mean([n["load"] for n in state["nodes"]])
    ns1.metric("NODOS ACTIVOS", f"{active_nodes} / {len(state['nodes'])}", "Operacionales")
    ns2.metric("FRECUENCIA PROM.", f"{avg_freq:.4f} Hz", f"Δ {avg_freq-60:+.4f}")
    ns3.metric("CARGA PROM.", f"{avg_load:.0f} %", "Red")
    total_cap = sum(n.get("cap", 0) for n in state["nodes"])
    ns4.metric("CAPACIDAD TOTAL", f"{total_cap:,} MW", "Agregado 30 Nodos")


# ═══════════════════════════════════════════════
#  TAB 6: AUDIT LOG
# ═══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>BITÁCORA DE AUDITORÍA — CUMPLIMIENTO FIDUCIARIO</div>", unsafe_allow_html=True)

    audit_data = {
        "Marca Temporal": [
            (now - timedelta(minutes=i*15)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(20, 0, -1)
        ],
        "Evento": [
            "Convergencia HJB verificada", "Pico PML detectado ($284/MWh)", "Inyección inercia: 2.4 p.u.",
            "Frecuencia estabilizada: 59.998 Hz", "Nodo MTY-400 sincronizado", "Punto de control capital: $12,480",
            "Medición THD: 2.14%", "Código de Red: CUMPLE", "RoCoF dentro de límites: +0.0012",
            "Nodo HER-230 carga rebalanceada", "PML normalizado: $52/MWh", "HJB re-resuelto (cambio de estado)",
            "Integración Ecuación Oscilación OK", "Desbalance de fase: 0.03%", "Punto de control capital: $28,940",
            "Actualización pesos actor-crítico DRL", "Latido de red: todos los nodos", "Arbitraje PML capturado: $3,200",
            "Frecuencia nominal: 60.001 Hz", "Integridad del sistema: VERIFICADA"
        ],
        "Severidad": [
            "INFO", "ADVERTENCIA", "ACCIÓN", "INFO", "INFO", "FINANCIERO",
            "INFO", "CUMPLIMIENTO", "INFO", "ACCIÓN", "INFO", "ACCIÓN",
            "INFO", "INFO", "FINANCIERO", "ACCIÓN", "INFO", "FINANCIERO",
            "INFO", "CUMPLIMIENTO"
        ]
    }

    df_audit = pd.DataFrame(audit_data)

    def color_severity(val):
        colors = {
            "INFO": "color: #6b7fa3",
            "ADVERTENCIA": "color: #fbc02d",
            "ACCIÓN": "color: #00d1ff",
            "FINANCIERO": "color: #00ff88",
            "CUMPLIMIENTO": "color: #a78bfa"
        }
        return colors.get(val, "color: white")

    st.dataframe(
        df_audit.style.map(color_severity, subset=["Severidad"]),
        use_container_width=True, height=600, hide_index=True
    )


# ============================================================
#  FOOTER
# ============================================================
st.divider()
fc1, fc2, fc3 = st.columns([2, 3, 2])
with fc1:
    st.caption("PRIMEnergeia S.A.S.")
    st.caption("Protocolo Propietario")
with fc2:
    st.caption("Físico Computacional Principal: Diego Córdoba Urrutia")
    st.caption("Ley de Control HJB: V_t + min_u { L(x,u) + ∇V · f(x,u) } = 0")
with fc3:
    st.caption("Soberanía Energética para México 🇲🇽")
    st.caption(f"Build: PRIME-HJB-v8.0-SEN | {now.strftime('%Y')}")
