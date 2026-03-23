"""
PRIMEnergeia — Granas SDL Dashboard
=====================================
Self-Driving Lab Command Center with HJB-Optics Optimization

Tabs: HJB Optimizer | SDL Campaign | Lab Telemetry | Architecture

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import numpy as np
import pandas as pd
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    st.error("Plotly required. Install with: pip install plotly")
    st.stop()

from sdl.hjb_optics import HJBOpticsController, OpticalDesignState, FastOpticsModel
from sdl.sdl_engine import SDLCampaign, ExperimentDesign

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
        background: linear-gradient(90deg, rgba(0,255,136,0.12) 0%, rgba(138,43,226,0.08) 100%);
        border: 1px solid rgba(0,255,136,0.3);
        border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
    }
    .sdl-header h1 {
        background: linear-gradient(90deg, #00ff88, #8a2be2);
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
        color: #00ff88; font-family: 'JetBrains Mono', monospace;
        font-size: 26px; font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #6b7fa3; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] {
        color: #00ff88 !important; border-bottom-color: #00ff88 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="sdl-header">
    <h1>🧬 Granas SDL — Self-Driving Lab</h1>
    <p>HJB Optimal Control + Closed-Loop Lab Automation &bull;
    AI Designs → Execute → Measure → Learn → Iterate</p>
</div>
""", unsafe_allow_html=True)


# ─── Session State ───────────────────────────────────────────
for key in ["hjb_result", "sdl_result", "hjb_controller"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧬 SDL Controls")
    st.markdown("---")

    mode = st.radio("Mode", ["🔬 HJB Optimizer", "🧪 SDL Campaign"])

    if mode == "🔬 HJB Optimizer":
        st.markdown("#### Design Space")
        init_radius = st.slider("Initial Radius (nm)", 80, 500, 150, step=10)
        init_density = st.slider("Initial Density", 0.1, 0.7, 0.3, step=0.05)
        init_thickness = st.slider("Initial Thickness (nm)", 200, 2000, 500, step=50)

        st.markdown("#### Solver")
        n_iter = st.slider("Iterations", 5, 50, 20)
        n_radius = st.slider("Radius Grid", 8, 25, 15)
        n_density = st.slider("Density Grid", 6, 20, 12)
        n_thickness = st.slider("Thickness Grid", 6, 15, 10)

        run_hjb = st.button("▶ Run HJB Optimizer", type="primary",
                            use_container_width=True)

    else:
        st.markdown("#### Campaign Settings")
        n_experiments = st.slider("Max Experiments", 3, 30, 8)
        run_sdl = st.button("▶ Run SDL Campaign", type="primary",
                            use_container_width=True)

    st.markdown("---")
    st.markdown("### 📐 Architecture")
    st.markdown("""
    | Layer | Tech |
    |-------|------|
    | **Edge** | OPC-UA, MQTT, SiLA2 |
    | **Pipeline** | Kafka → InfluxDB |
    | **Orchestration** | PyLabRobot |
    | **AI** | HJB + Active Learning |
    """)


# ─── HJB Optimizer ───────────────────────────────────────────
if mode == "🔬 HJB Optimizer":
    if run_hjb:
        with st.spinner("🧠 Solving HJB value function..."):
            ctrl = HJBOpticsController(
                n_iterations=n_iter,
                n_radius=n_radius,
                n_density=n_density,
                n_thickness=n_thickness,
                n_control=5,
            )
            result = ctrl.optimize(OpticalDesignState(
                radius_nm=float(init_radius),
                packing_density=float(init_density),
                thickness_nm=float(init_thickness),
            ))
            st.session_state.hjb_result = result
            st.session_state.hjb_controller = ctrl
        st.toast("✅ HJB Optimization Complete!", icon="🧠")

    result = st.session_state.hjb_result
    if result is None:
        st.markdown("""
        <div style="text-align: center; padding: 4rem;">
            <p style="font-size: 4rem; margin: 0;">🧠</p>
            <h2 style="color: #00ff88;">HJB-Optics Optimizer</h2>
            <p style="color: #94a3b8;">
                Configure initial design parameters and click <strong>▶ Run</strong>
                to find the optimal granule configuration via Hamilton-Jacobi-Bellman.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Metrics
    opt = result.optimal_design
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("⚡ Jsc", f"{opt['jsc_mA_cm2']:.2f} mA/cm²")
    m2.metric("📈 Improvement", f"+{result.jsc_improvement_pct:.1f}%")
    m3.metric("🔵 Radius", f"{opt['radius_nm']:.0f} nm")
    m4.metric("📦 Density", f"{opt['packing_density']:.3f}")
    m5.metric("📏 Thickness", f"{opt['thickness_nm']:.0f} nm")
    m6.metric("🔆 Absorption", f"{opt['absorption_pct']:.1f}%")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Convergence", "🗺️ Value Function", "🎯 Design Trajectory",
        "📊 Spectral Impact"
    ])

    with tab1:
        fig = make_subplots(rows=2, cols=2, subplot_titles=[
            "Jsc Convergence", "Absorption Convergence",
            "Radius Evolution", "Density Evolution"
        ])
        iters = result.iteration_grid

        fig.add_trace(go.Scatter(x=iters, y=result.jsc_trajectory,
                                  line=dict(color="#00ff88", width=3),
                                  name="Jsc"), row=1, col=1)
        fig.add_trace(go.Scatter(x=iters, y=result.absorption_trajectory,
                                  line=dict(color="#8a2be2", width=3),
                                  name="Absorption"), row=1, col=2)
        fig.add_trace(go.Scatter(x=iters, y=result.radius_trajectory,
                                  line=dict(color="#00d1ff", width=3),
                                  name="Radius"), row=2, col=1)
        fig.add_trace(go.Scatter(x=iters, y=result.density_trajectory,
                                  line=dict(color="#ff6b35", width=3),
                                  name="Density"), row=2, col=2)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=550, showlegend=False,
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        V = result.value_function
        ctrl = st.session_state.hjb_controller
        fig_vf = go.Figure(go.Heatmap(
            z=-V,  # Negate: lower cost = better
            x=[f"{d:.2f}" for d in ctrl.density_grid],
            y=[f"{r:.0f}" for r in ctrl.radius_grid],
            colorscale=[[0, "#020608"], [0.3, "#0a2e1a"],
                        [0.6, "#00ff88"], [0.8, "#8a2be2"], [1, "#ffd700"]],
            colorbar=dict(title="Value (-cost)"),
        ))
        fig_vf.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=500,
            title="Value Function V(radius, density) at mid-thickness",
            xaxis_title="Packing Density", yaxis_title="Radius (nm)",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        )
        st.plotly_chart(fig_vf, use_container_width=True)

    with tab3:
        fig3d = go.Figure(go.Scatter3d(
            x=result.radius_trajectory,
            y=result.density_trajectory,
            z=result.thickness_trajectory,
            mode="lines+markers",
            line=dict(color=result.jsc_trajectory,
                      colorscale=[[0, "#ff6b35"], [1, "#00ff88"]],
                      width=5),
            marker=dict(size=4, color=result.jsc_trajectory,
                        colorscale=[[0, "#ff6b35"], [1, "#00ff88"]],
                        colorbar=dict(title="Jsc")),
        ))
        fig3d.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            scene=dict(
                xaxis=dict(title="Radius (nm)", backgroundcolor="#020608"),
                yaxis=dict(title="Density", backgroundcolor="#020608"),
                zaxis=dict(title="Thickness (nm)", backgroundcolor="#020608"),
            ),
            title="HJB Design Trajectory in 3D State Space",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            height=600,
        )
        st.plotly_chart(fig3d, use_container_width=True)

    with tab4:
        # Show spectral response for initial vs final design
        wl = np.linspace(300, 1200, 91)
        optics = FastOpticsModel()
        A_init = optics.absorptance_spectrum(
            init_radius, init_density, init_thickness, wl)
        A_final = optics.absorptance_spectrum(
            opt["radius_nm"], opt["packing_density"],
            opt["thickness_nm"], wl)

        fig_spec = go.Figure()
        fig_spec.add_trace(go.Scatter(
            x=wl, y=A_init * 100, mode="lines",
            name="Initial", line=dict(color="#ff6b35", width=2, dash="dot"),
        ))
        fig_spec.add_trace(go.Scatter(
            x=wl, y=A_final * 100, mode="lines",
            name="Optimal (HJB)", line=dict(color="#00ff88", width=3),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.1)",
        ))
        fig_spec.update_layout(
            template="plotly_dark", paper_bgcolor="#020608",
            plot_bgcolor="#020608", height=450,
            title="Spectral Absorptance: Initial vs HJB-Optimized",
            xaxis_title="Wavelength (nm)", yaxis_title="Absorptance (%)",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            legend=dict(x=0.7, y=0.95),
        )
        st.plotly_chart(fig_spec, use_container_width=True)


# ─── SDL Campaign ────────────────────────────────────────────
elif mode == "🧪 SDL Campaign":
    if run_sdl:
        with st.spinner("🧬 Running SDL Campaign..."):
            campaign = SDLCampaign("Dashboard_SDL")
            sdl_result = campaign.run_campaign(n_experiments=n_experiments)
            st.session_state.sdl_result = sdl_result
        st.toast("✅ SDL Campaign Complete!", icon="🧬")

    sdl_result = st.session_state.sdl_result
    if sdl_result is None:
        st.markdown("""
        <div style="text-align: center; padding: 4rem;">
            <p style="font-size: 4rem; margin: 0;">🧬</p>
            <h2 style="color: #00ff88;">Self-Driving Lab Campaign</h2>
            <p style="color: #94a3b8;">
                Configure experiment count and click <strong>▶ Run</strong>
                to launch a closed-loop optimization campaign.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Metrics
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("🧪 Experiments", f"{sdl_result.experiments_run}")
    sm2.metric("🏆 Best PCE", f"{sdl_result.best_pce:.2f}%")
    sm3.metric("⏱️ Time", f"{sdl_result.total_time_s:.1f}s")
    sm4.metric("📊 Decisions", f"{len(sdl_result.active_learning_decisions)}")

    stab1, stab2, stab3 = st.tabs([
        "📈 PCE Convergence", "🧠 Active Learning", "🏛️ Architecture"
    ])

    with stab1:
        pces = [p["pce"] for p in sdl_result.pareto_front]
        preds = [p["predicted_pce"] for p in sdl_result.pareto_front]
        exps = [p["experiment"] for p in sdl_result.pareto_front]

        # Sort by experiment order
        order = np.argsort(exps)
        exps_sorted = [exps[i] for i in order]
        pces_sorted = [pces[i] for i in order]
        preds_sorted = [preds[i] for i in order]

        fig_pce = go.Figure()
        fig_pce.add_trace(go.Scatter(
            x=exps_sorted, y=pces_sorted, mode="lines+markers",
            name="Measured PCE", line=dict(color="#00ff88", width=3),
            marker=dict(size=10),
        ))
        fig_pce.add_trace(go.Scatter(
            x=exps_sorted, y=preds_sorted, mode="lines+markers",
            name="Predicted PCE", line=dict(color="#8a2be2", width=2, dash="dot"),
            marker=dict(size=6),
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
            colors = {
                "continue": "#00d1ff", "pause": "#ffd700",
                "pivot": "#ff6b35", "accelerate": "#00ff88",
                "terminate": "#ff4444",
            }
            fig_al = go.Figure()
            for action, color in colors.items():
                mask = df_al["action"] == action
                if mask.any():
                    subset = df_al[mask]
                    fig_al.add_trace(go.Scatter(
                        x=subset.index, y=subset["measured_pce"],
                        mode="markers", name=action.upper(),
                        marker=dict(color=color, size=12, symbol="diamond"),
                    ))

            fig_al.update_layout(
                template="plotly_dark", paper_bgcolor="#020608",
                plot_bgcolor="#020608", height=400,
                title="Active Learning Decisions",
                xaxis_title="Experiment", yaxis_title="PCE (%)",
                font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            )
            st.plotly_chart(fig_al, use_container_width=True)

            st.markdown("#### Decision Log")
            st.dataframe(
                df_al[["experiment_id", "action", "measured_pce",
                        "predicted_pce", "anomaly_score"]],
                use_container_width=True, hide_index=True,
            )

    with stab3:
        st.markdown("""
### 🏛️ Self-Driving Lab Architecture

```mermaid
graph TB
    subgraph AI["🧠 AI Layer"]
        HJB["HJB Optimizer"]
        BO["Bayesian Optimizer"]
        AL["Active Learning"]
    end

    subgraph ORCH["⚙️ Orchestration"]
        SILA["SiLA 2 Protocol"]
        PLR["PyLabRobot"]
        FAPI["FastAPI Endpoints"]
    end

    subgraph PIPE["📊 Data Pipeline"]
        KAFKA["Kafka / Redpanda"]
        INFLUX["InfluxDB"]
        VEC["Vector Embeddings"]
    end

    subgraph EDGE["🔌 Edge Layer"]
        SPIN["Spin Coater"]
        HOT["Hot Plate"]
        UVVIS["UV-Vis"]
        XRD["XRD"]
        SOLAR["Solar Sim"]
        LH["Liquid Handler"]
        GB["Glovebox"]
    end

    AI -->|Design| ORCH
    ORCH -->|Commands| EDGE
    EDGE -->|Raw Data| PIPE
    PIPE -->|Features| AI
    AL -->|Pivot/Accelerate| ORCH
```

**Key Principles:**
- **FAIR Data**: All measurements tagged with experiment ID, sample ID, device ID
- **Low Latency**: Edge → AI inference < 100ms via Kafka streaming
- **Scalable**: Horizontal scaling of workers and devices
- **Protocol-agnostic**: OPC-UA, MQTT, SiLA 2, REST, Serial, Modbus
        """)


# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Self-Driving Lab &bull;
    Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
