"""
PRIMEnergeia — Granas SDL Dashboard
=====================================
Self-Driving Lab Command Center

Separate product from Granas Optics:
  - Optics HJB → optimizes panel design (radius, density, thickness)
  - SDL HJB → optimizes fabrication recipe (spin rpm, anneal temp, concentration)

Tabs: HJB Fabrication | SDL Campaign | Lab Telemetry | Architecture

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    st.error("Plotly required. Install with: pip install plotly")
    st.stop()

# Import SDL-specific modules
try:
    from sdl.hjb_sdl import SDLHJBController, FabricationState, FabricationModel
    from sdl.sdl_engine import SDLCampaign
    SDL_AVAILABLE = True
except ImportError:
    try:
        from hjb_sdl import SDLHJBController, FabricationState, FabricationModel
        from sdl_engine import SDLCampaign
        SDL_AVAILABLE = True
    except ImportError:
        SDL_AVAILABLE = False

st.set_page_config(
    page_title="Granas SDL | Self-Driving Lab",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .stApp {
        background: linear-gradient(145deg, #020608 0%, #0a1020 50%, #020608 100%);
        font-family: 'Inter', sans-serif;
    }
    .sdl-header {
        background: linear-gradient(90deg, rgba(0,255,204,0.12) 0%, rgba(138,43,226,0.08) 100%);
        border: 1px solid rgba(0,255,204,0.3);
        border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
    }
    .sdl-header h1 {
        background: linear-gradient(90deg, #00ffcc, #8a2be2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.2rem; font-weight: 700; margin: 0;
    }
    .sdl-header p { color: #94a3b8; font-size: 1rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0f1a 0%, #020608 100%);
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 8px; padding: 16px 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #00ffcc; font-family: 'JetBrains Mono', monospace;
        font-size: 34px; font-weight: 700;
        text-shadow: 0 0 12px rgba(0,255,204,0.3);
    }
    div[data-testid="stMetricDelta"] { font-size: 13px; }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] {
        color: #00ffcc !important; border-bottom-color: #00ffcc !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="sdl-header">
    <h1>🧬 Granas SDL — Self-Driving Lab</h1>
    <p>HJB Fabrication Optimization + Closed-Loop Lab Automation &bull;
    AI Designs → Execute → Measure → Learn → Iterate</p>
</div>
""", unsafe_allow_html=True)

if not SDL_AVAILABLE:
    st.error("⚠️ SDL engine not found. Ensure `sdl/` folder exists.")
    st.stop()

# ─── Session State ───────────────────────────────────────────
for key in ["sdl_hjb_result", "sdl_campaign_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧬 SDL Controls")
    st.markdown("---")
    mode = st.radio("Mode", ["🧠 HJB Fabrication", "🧪 SDL Campaign"])

    if mode == "🧠 HJB Fabrication":
        st.markdown("#### Initial Recipe")
        init_rpm = st.slider("Spin RPM", 1000, 8000, 3000, step=250)
        init_temp = st.slider("Anneal Temp (°C)", 50, 200, 80, step=5)
        init_conc = st.slider("Concentration (M)", 0.5, 2.0, 0.8, step=0.1)
        st.markdown("#### Solver")
        n_iter = st.slider("Iterations", 5, 40, 20)
        n_grid = st.slider("Grid Resolution", 8, 20, 12)
        run_hjb = st.button("▶ Run HJB Optimizer", type="primary",
                            use_container_width=True)
    else:
        st.markdown("#### Campaign Settings")
        n_experiments = st.slider("Max Experiments", 3, 30, 8)
        run_sdl = st.button("▶ Run SDL Campaign", type="primary",
                            use_container_width=True)

    st.markdown("---")
    st.markdown("### 📐 Stack")
    st.markdown("""
    | Layer | Tech |
    |-------|------|
    | **Edge** | OPC-UA, MQTT, SiLA2 |
    | **Pipeline** | Kafka → InfluxDB |
    | **Orchestration** | PyLabRobot |
    | **AI** | HJB + Active Learning |
    """)

# ─── HJB Fabrication Mode ────────────────────────────────────
if mode == "🧠 HJB Fabrication":
    if run_hjb:
        with st.spinner("🧠 Solving SDL-HJB value function..."):
            ctrl = SDLHJBController(
                n_iterations=n_iter, n_rpm=n_grid,
                n_temp=n_grid, n_conc=max(6, n_grid - 4), n_control=5,
            )
            result = ctrl.optimize(FabricationState(
                spin_rpm=float(init_rpm),
                anneal_temp_C=float(init_temp),
                concentration_M=float(init_conc),
            ))
            st.session_state.sdl_hjb_result = (result, ctrl)
        st.toast("✅ HJB Fabrication Optimization Complete!", icon="🧠")

    res_pair = st.session_state.sdl_hjb_result
    if res_pair is None:
        st.markdown("""
        <div style="text-align: center; padding: 4rem;">
            <p style="font-size: 4rem; margin: 0;">🧠</p>
            <h2 style="color: #00ffcc;">HJB Fabrication Optimizer</h2>
            <p style="color: #94a3b8;">
                Optimizes fabrication recipe (spin speed, anneal temperature, concentration)
                to maximize PCE via Hamilton-Jacobi-Bellman dynamic programming.<br><br>
                <em>Different from Optics HJB which optimizes panel design (radius, density, thickness).</em>
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    result, hjb_ctrl = res_pair
    opt = result.optimal_recipe

    # Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🏆 PCE", f"{opt['pce_pct']:.2f}%")
    m2.metric("📈 Improvement", f"+{result.pce_improvement_pct:.1f}%")
    m3.metric("🌀 RPM", f"{opt['spin_rpm']:.0f}")
    m4.metric("🔥 Temp", f"{opt['anneal_temp_C']:.0f} °C")
    m5.metric("🧪 Conc", f"{opt['concentration_M']:.2f} M")
    m6.metric("💎 Grain", f"{opt['grain_nm']:.0f} nm")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Convergence", "🗺️ Value Function",
        "🔬 Recipe Evolution", "🏛️ Architecture"
    ])

    with tab1:
        fig = make_subplots(rows=2, cols=2, subplot_titles=[
            "PCE Convergence", "Grain Size",
            "RPM + Temperature", "Concentration"
        ])
        iters = result.iteration_grid

        fig.add_trace(go.Scatter(x=iters, y=result.pce_trajectory,
                                  line=dict(color="#00ffcc", width=3),
                                  name="PCE"), row=1, col=1)
        fig.add_trace(go.Scatter(x=iters, y=result.grain_trajectory,
                                  line=dict(color="#ffd700", width=2),
                                  name="Grain"), row=1, col=2)
        fig.add_trace(go.Scatter(x=iters, y=result.rpm_trajectory,
                                  line=dict(color="#00d1ff", width=2),
                                  name="RPM"), row=2, col=1)
        fig.add_trace(go.Scatter(x=iters, y=result.temp_trajectory,
                                  line=dict(color="#ff6b35", width=2),
                                  name="Temp"), row=2, col=1)
        fig.add_trace(go.Scatter(x=iters, y=result.conc_trajectory,
                                  line=dict(color="#8a2be2", width=3),
                                  name="Conc"), row=2, col=2)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=550, showlegend=False,
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        V = result.value_function
        fig_vf = go.Figure(go.Heatmap(
            z=-V,
            x=[f"{t:.0f}" for t in hjb_ctrl.temp_grid],
            y=[f"{r:.0f}" for r in hjb_ctrl.rpm_grid],
            colorscale=[[0, "#020608"], [0.3, "#0a2e1a"],
                        [0.6, "#00ffcc"], [0.8, "#8a2be2"], [1, "#ffd700"]],
            colorbar=dict(title="Value (-cost)"),
        ))
        fig_vf.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=500,
            title="V(RPM, Temperature) at mid-concentration",
            xaxis_title="Anneal Temp (°C)", yaxis_title="Spin RPM",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig_vf, use_container_width=True)

    with tab3:
        fig3d = go.Figure(go.Scatter3d(
            x=result.rpm_trajectory,
            y=result.temp_trajectory,
            z=result.conc_trajectory,
            mode="lines+markers",
            line=dict(color=result.pce_trajectory,
                      colorscale=[[0, "#ff6b35"], [1, "#00ffcc"]], width=5),
            marker=dict(size=4, color=result.pce_trajectory,
                        colorscale=[[0, "#ff6b35"], [1, "#00ffcc"]],
                        colorbar=dict(title="PCE %")),
        ))
        fig3d.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            scene=dict(
                xaxis=dict(title="RPM", backgroundcolor="#020608"),
                yaxis=dict(title="Temp (°C)", backgroundcolor="#020608"),
                zaxis=dict(title="Conc (M)", backgroundcolor="#020608"),
            ),
            title="HJB Recipe Trajectory in 3D State Space",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            height=600,
        )
        st.plotly_chart(fig3d, use_container_width=True)

    with tab4:
        st.markdown("""
### 🏛️ Self-Driving Lab Architecture

| Layer | Technology | Devices |
|-------|-----------|---------|
| **Edge** | OPC-UA, MQTT, SiLA 2 | Spin Coater, Hot Plate, UV-Vis, XRD, Solar Sim |
| **Pipeline** | Kafka → InfluxDB | FAIR-tagged time-series |
| **Orchestration** | PyLabRobot, FastAPI | Recipe → device commands |
| **AI** | **SDL-HJB** + Active Learning | Fabrication optimization |

**Key difference from Optics:**
- **Optics HJB** optimizes *panel design* (radius, density, thickness → Jsc)
- **SDL HJB** optimizes *fabrication recipe* (RPM, temp, concentration → PCE)

**FAIR Data**: All measurements tagged with experiment ID, sample ID, device ID.
**Active Learning**: Pause/Pivot/Accelerate/Terminate based on uncertainty + anomaly.
        """)

# ─── SDL Campaign Mode ───────────────────────────────────────
elif mode == "🧪 SDL Campaign":
    if run_sdl:
        with st.spinner("🧬 Running SDL Campaign..."):
            campaign = SDLCampaign("Dashboard_SDL")
            sdl_result = campaign.run_campaign(n_experiments=n_experiments)
            st.session_state.sdl_campaign_result = sdl_result
        st.toast("✅ SDL Campaign Complete!", icon="🧬")

    sdl_result = st.session_state.sdl_campaign_result
    if sdl_result is None:
        st.markdown("""
        <div style="text-align: center; padding: 4rem;">
            <p style="font-size: 4rem; margin: 0;">🧬</p>
            <h2 style="color: #00ffcc;">Self-Driving Lab Campaign</h2>
            <p style="color: #94a3b8;">
                Closed-loop optimization: AI designs experiments, hardware executes,
                data streams back, AI analyzes and iterates.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("🧪 Experiments", f"{sdl_result.experiments_run}")
    sm2.metric("🏆 Best PCE", f"{sdl_result.best_pce:.2f}%")
    sm3.metric("⏱️ Time", f"{sdl_result.total_time_s:.1f}s")
    sm4.metric("📊 Decisions", f"{len(sdl_result.active_learning_decisions)}")

    stab1, stab2 = st.tabs(["📈 PCE Convergence", "🧠 Active Learning"])

    with stab1:
        pces = [p["pce"] for p in sdl_result.pareto_front]
        exps = [p["experiment"] for p in sdl_result.pareto_front]
        preds = [p["predicted_pce"] for p in sdl_result.pareto_front]
        order = np.argsort(exps)

        fig_pce = go.Figure()
        fig_pce.add_trace(go.Scatter(
            x=[exps[i] for i in order], y=[pces[i] for i in order],
            mode="lines+markers", name="Measured PCE",
            line=dict(color="#00ffcc", width=3), marker=dict(size=10),
        ))
        fig_pce.add_trace(go.Scatter(
            x=[exps[i] for i in order], y=[preds[i] for i in order],
            mode="lines+markers", name="Predicted PCE",
            line=dict(color="#8a2be2", width=2, dash="dot"), marker=dict(size=6),
        ))
        fig_pce.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=450,
            title="PCE: Measured vs Predicted",
            xaxis_title="Experiment #", yaxis_title="PCE (%)",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig_pce, use_container_width=True)

    with stab2:
        decisions = sdl_result.active_learning_decisions
        if decisions:
            df_al = pd.DataFrame(decisions)
            st.dataframe(
                df_al[["experiment_id", "action", "measured_pce",
                        "predicted_pce", "anomaly_score"]],
                use_container_width=True, hide_index=True,
            )

# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Self-Driving Lab &bull;
    Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
