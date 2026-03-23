"""
Granas Metrics — Holistic Performance Dashboard
=================================================
Twin of Granas: unified view of Optics + SDL + SIBO performance.

Tabs: Holistic Overview | Optics | SDL | SIBO | Pareto | Correlation

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import numpy as np
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    st.error("pip install plotly")
    st.stop()

from metrics.granas_metrics import (
    OpticsMetrics, SDLMetrics, SIBOMetrics, HolisticGranas
)

st.set_page_config(
    page_title="Granas Metrics | Holistic Twin",
    page_icon="📊", layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .stApp { background: linear-gradient(145deg, #020608 0%, #0a1020 50%, #020608 100%); }
    .metrics-header {
        background: linear-gradient(90deg, rgba(255,215,0,0.12) 0%, rgba(0,209,255,0.08) 100%);
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
    }
    .metrics-header h1 {
        background: linear-gradient(90deg, #ffd700, #00d1ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.2rem; font-weight: 700; margin: 0;
    }
    .metrics-header p { color: #94a3b8; font-size: 1rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0f1a 0%, #020608 100%); }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 8px; padding: 16px 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #ffd700; font-family: 'JetBrains Mono', monospace;
        font-size: 34px; font-weight: 700;
        text-shadow: 0 0 12px rgba(255,215,0,0.3);
    }
    div[data-testid="stMetricDelta"] { font-size: 13px; }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #ffd700 !important; border-bottom-color: #ffd700 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="metrics-header">
    <h1>📊 Granas Metrics — Holistic Performance Twin</h1>
    <p>Unified view: Optics + SDL Fabrication + Bayesian Optimization &bull;
    Cross-product performance analytics</p>
</div>
""", unsafe_allow_html=True)

# ─── Session State ───────────────────────────────────────────
if "holistic" not in st.session_state:
    st.session_state.holistic = None
if "sweep_data" not in st.session_state:
    st.session_state.sweep_data = None

# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Granas Parameters")
    st.markdown("---")

    st.markdown("#### 🔬 Optics Design")
    radius = st.slider("Granule Radius (nm)", 80, 600, 300, step=20)
    density = st.slider("Packing Density", 0.1, 0.72, 0.50, step=0.05)

    st.markdown("#### 🧬 SDL Fabrication")
    rpm = st.slider("Spin RPM", 1000, 8000, 4000, step=250)
    temp = st.slider("Anneal Temp (°C)", 50, 200, 120, step=5)
    conc = st.slider("Concentration (M)", 0.5, 2.0, 1.2, step=0.1)

    st.markdown("#### 🧪 SIBO Campaign")
    sibo_iters = st.slider("Bayesian Iterations", 5, 50, 25)

    st.markdown("---")
    run_btn = st.button("▶ Compute Holistic Metrics", type="primary",
                        use_container_width=True)
    sweep_btn = st.button("🔄 Run Pareto Sweep", use_container_width=True)

# ─── Compute ─────────────────────────────────────────────────
if run_btn:
    with st.spinner("📊 Computing holistic metrics..."):
        optics = OpticsMetrics.from_params(radius, density, 500)
        sdl = SDLMetrics.from_recipe(rpm, temp, conc)
        sibo = SIBOMetrics.generate_campaign(sibo_iters)
        h = HolisticGranas(optics=optics, sdl=sdl, sibo=sibo).compute()
        st.session_state.holistic = h
    st.toast("✅ Holistic metrics computed!", icon="📊")

if sweep_btn:
    with st.spinner("🔄 Running Pareto sweep (200 points)..."):
        sweep = HolisticGranas.generate_sweep(
            rpm_range=(2000, 6000, 5),
            temp_range=(60, 150, 8),
            radius_range=(100, 500, 5),
        )
        st.session_state.sweep_data = sweep
    st.toast("✅ Pareto sweep complete!", icon="🔄")

h = st.session_state.holistic
if h is None:
    st.markdown("""
    <div style="text-align: center; padding: 4rem;">
        <p style="font-size: 4rem; margin: 0;">📊</p>
        <h2 style="color: #ffd700;">Granas Holistic Performance Twin</h2>
        <p style="color: #94a3b8;">
            Set parameters in the sidebar and click <strong>Compute Holistic Metrics</strong>
            to see unified performance across Optics, SDL, and SIBO.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════
# TOP METRICS
# ═══════════════════════════════════════════════════════════
m1, m2, m3 = st.columns(3)
m1.metric("📊 Figure of Merit", f"{h.figure_of_merit:.1f} / 100")
m2.metric("🏆 Device PCE", f"{h.device_pce:.2f}%")
m3.metric("🔬 Technology Readiness", f"TRL {h.technology_readiness:.0f}")

m4, m5, m6 = st.columns(3)
m4.metric("⚡ Jsc (Optics)", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²")
m5.metric("🧬 PCE (SDL)", f"{h.sdl.pce_pct:.2f}%")
m6.metric("💰 Cost Efficiency", f"{h.cost_efficiency:.1f}")

# ═══════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Holistic", "🔬 Optics", "🧬 SDL",
    "🧪 SIBO", "📈 Pareto"
])

# ─── Tab 1: Holistic Radar ───────────────────────────────────
with tab1:
    categories = ["PCE", "Jsc", "Grain Quality", "Absorption",
                   "Cost Efficiency", "Film Quality"]
    values = [
        h.sdl.pce_pct / 22.0 * 100,
        h.optics.jsc_mA_cm2 / 25.0 * 100,
        h.sdl.grain_nm / 500.0 * 100,
        h.optics.weighted_absorption_pct,
        min(h.cost_efficiency / 40 * 100, 100),
        h.sdl.film_quality * 100,
    ]
    values.append(values[0])
    categories.append(categories[0])

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values, theta=categories,
        fill="toself", line=dict(color="#ffd700", width=3),
        fillcolor="rgba(255,215,0,0.15)", name="Current",
    ))
    # Reference: ideal
    ideal = [100, 100, 100, 100, 100, 100, 100]
    fig_radar.add_trace(go.Scatterpolar(
        r=ideal, theta=categories,
        line=dict(color="#3a4a6b", width=1, dash="dot"),
        name="Ideal",
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="#020608",
            radialaxis=dict(range=[0, 100], showticklabels=True,
                           gridcolor="#1e2d4a", tickfont=dict(color="#6b7fa3")),
            angularaxis=dict(gridcolor="#1e2d4a",
                            tickfont=dict(color="#94a3b8", size=13)),
        ),
        template="plotly_dark", paper_bgcolor="#020608",
        height=550, showlegend=True,
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        title="Holistic Performance Radar",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # Cross-product breakdown
    st.markdown("### Cross-Product Breakdown")
    df_cross = pd.DataFrame([
        {"Metric": "Optics → Jsc", "Value": f"{h.optics.jsc_mA_cm2:.2f} mA/cm²",
         "Score": f"{h.optics.jsc_mA_cm2/25*100:.0f}%"},
        {"Metric": "Optics → Absorption", "Value": f"{h.optics.weighted_absorption_pct:.1f}%",
         "Score": f"{h.optics.weighted_absorption_pct:.0f}%"},
        {"Metric": "Optics → EQE (400-750nm)", "Value": f"{h.optics.eqe_avg_pct:.1f}%",
         "Score": f"{h.optics.eqe_avg_pct:.0f}%"},
        {"Metric": "SDL → PCE", "Value": f"{h.sdl.pce_pct:.2f}%",
         "Score": f"{h.sdl.pce_pct/22*100:.0f}%"},
        {"Metric": "SDL → Grain Size", "Value": f"{h.sdl.grain_nm:.0f} nm",
         "Score": f"{h.sdl.grain_nm/500*100:.0f}%"},
        {"Metric": "SDL → Film Quality", "Value": f"{h.sdl.film_quality:.3f}",
         "Score": f"{h.sdl.film_quality*100:.0f}%"},
        {"Metric": "Device PCE", "Value": f"{h.device_pce:.2f}%",
         "Score": f"{h.device_pce/22*100:.0f}%"},
        {"Metric": "Figure of Merit", "Value": f"{h.figure_of_merit:.1f}/100",
         "Score": f"{h.figure_of_merit:.0f}%"},
    ])
    st.dataframe(df_cross, use_container_width=True, hide_index=True)

# ─── Tab 2: Optics Detail ─────────────────────────────────────
with tab2:
    st.markdown("### 🔬 Optics Performance")
    o1, o2, o3 = st.columns(3)
    o1.metric("Jsc", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²")
    o2.metric("Absorption", f"{h.optics.weighted_absorption_pct:.1f}%")
    o3.metric("EQE (400-750)", f"{h.optics.eqe_avg_pct:.1f}%")

    o4, o5, o6 = st.columns(3)
    o4.metric("Radius", f"{h.optics.radius_nm:.0f} nm")
    o5.metric("Packing Density", f"{h.optics.packing_density:.2f}")
    o6.metric("Size Parameter", f"{h.optics.size_parameter:.2f}")

    # Wavelength sweep (vary radius)
    wl = np.linspace(300, 1200, 91)
    fig_wl = go.Figure()
    for r in [100, 200, 300, 400, 500]:
        om = OpticsMetrics.from_params(r, h.optics.packing_density, h.optics.thickness_nm)
        # Recompute absorptance spectrum
        x = 2 * np.pi * r / wl
        q_ext = np.clip(2.0 - (4.0/x)*np.sin(x) + (4.0/x**2)*(1-np.cos(x)), 0, 4)
        path = 1.0 + h.optics.packing_density * q_ext
        n_imag = 0.5 * np.exp(-((wl-400)/200)**2)
        alpha = 4 * np.pi * n_imag / wl * 1e7
        A = np.clip(1 - np.exp(-alpha * h.optics.thickness_nm * 1e-7 * path), 0, 1)
        fig_wl.add_trace(go.Scatter(x=wl, y=A*100, name=f"r={r}nm",
                                     line=dict(width=2)))
    fig_wl.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="Absorptance vs Radius", xaxis_title="λ (nm)", yaxis_title="%",
        font=dict(family="Inter", color="#e2e8f0"), height=450,
    )
    st.plotly_chart(fig_wl, use_container_width=True)

# ─── Tab 3: SDL Detail ─────────────────────────────────────────
with tab3:
    st.markdown("### 🧬 SDL Fabrication Performance")
    s1, s2, s3 = st.columns(3)
    s1.metric("PCE", f"{h.sdl.pce_pct:.2f}%")
    s2.metric("Grain Size", f"{h.sdl.grain_nm:.0f} nm")
    s3.metric("Film Thickness", f"{h.sdl.thickness_nm:.0f} nm")

    s4, s5, s6 = st.columns(3)
    s4.metric("Spin RPM", f"{h.sdl.spin_rpm:.0f}")
    s5.metric("Anneal Temp", f"{h.sdl.anneal_temp_C:.0f} °C")
    s6.metric("Concentration", f"{h.sdl.concentration_M:.2f} M")

    # PCE vs Temperature sweep
    temps_sweep = np.linspace(50, 200, 31)
    pces_sweep = [SDLMetrics.from_recipe(h.sdl.spin_rpm, t, h.sdl.concentration_M).pce_pct
                  for t in temps_sweep]
    grains_sweep = [SDLMetrics.from_recipe(h.sdl.spin_rpm, t, h.sdl.concentration_M).grain_nm
                    for t in temps_sweep]

    fig_sdl = make_subplots(specs=[[{"secondary_y": True}]])
    fig_sdl.add_trace(go.Scatter(x=temps_sweep, y=pces_sweep, name="PCE",
                                  line=dict(color="#00ffcc", width=3)), secondary_y=False)
    fig_sdl.add_trace(go.Scatter(x=temps_sweep, y=grains_sweep, name="Grain (nm)",
                                  line=dict(color="#ffd700", width=2, dash="dot")),
                       secondary_y=True)
    fig_sdl.add_vline(x=h.sdl.anneal_temp_C, line_dash="dash",
                       line_color="#8a2be2", annotation_text="Current")
    fig_sdl.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="PCE & Grain Size vs Anneal Temperature",
        xaxis_title="Temperature (°C)", height=450,
        font=dict(family="Inter", color="#e2e8f0"),
    )
    fig_sdl.update_yaxes(title_text="PCE (%)", secondary_y=False)
    fig_sdl.update_yaxes(title_text="Grain (nm)", secondary_y=True)
    st.plotly_chart(fig_sdl, use_container_width=True)

# ─── Tab 4: SIBO ─────────────────────────────────────────────
with tab4:
    st.markdown("### 🧪 SIBO Bayesian Optimization")
    sibo = h.sibo
    best_sibo = sibo[-1]

    b1, b2, b3 = st.columns(3)
    b1.metric("Best PCE", f"{best_sibo.best_pce:.2f}%")
    b2.metric("GP Uncertainty", f"±{best_sibo.gp_uncertainty:.2f}%")
    b3.metric("Params Explored", f"{best_sibo.params_explored}")

    fig_sibo = make_subplots(rows=1, cols=2,
                              subplot_titles=["PCE Convergence", "Exploration vs Exploit"])
    fig_sibo.add_trace(go.Scatter(
        x=[s.iteration for s in sibo], y=[s.best_pce for s in sibo],
        line=dict(color="#ffd700", width=3), name="Best PCE",
    ), row=1, col=1)
    fig_sibo.add_trace(go.Scatter(
        x=[s.iteration for s in sibo], y=[s.exploration_ratio for s in sibo],
        name="Explore", line=dict(color="#00d1ff", width=2),
    ), row=1, col=2)
    fig_sibo.add_trace(go.Scatter(
        x=[s.iteration for s in sibo], y=[1-s.exploration_ratio for s in sibo],
        name="Exploit", line=dict(color="#ff6b35", width=2),
    ), row=1, col=2)
    fig_sibo.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_sibo, use_container_width=True)

# ─── Tab 5: Pareto ─────────────────────────────────────────────
with tab5:
    st.markdown("### 📈 Pareto Front — PCE vs Jsc")
    sweep = st.session_state.sweep_data
    if sweep is None:
        st.info("Click **Run Pareto Sweep** in the sidebar to generate data.")
    else:
        df = pd.DataFrame(sweep)

        fig_p = go.Figure(go.Scatter(
            x=df["jsc"], y=df["pce"],
            mode="markers",
            marker=dict(
                size=8, color=df["fom"],
                colorscale=[[0, "#020608"], [0.3, "#8a2be2"],
                            [0.7, "#ffd700"], [1, "#00ffcc"]],
                colorbar=dict(title="FoM"),
                line=dict(width=0.5, color="#1e2d4a"),
            ),
            hovertemplate="Jsc: %{x:.2f}<br>PCE: %{y:.1f}%<br>"
                          "RPM: %{customdata[0]:.0f}<br>"
                          "Temp: %{customdata[1]:.0f}°C<br>"
                          "Radius: %{customdata[2]:.0f}nm<extra></extra>",
            customdata=df[["rpm", "temp", "radius"]].values,
        ))
        # Current point
        fig_p.add_trace(go.Scatter(
            x=[h.optics.jsc_mA_cm2], y=[h.sdl.pce_pct],
            mode="markers", marker=dict(size=18, color="#ff0000",
                                         symbol="star", line=dict(width=2, color="#fff")),
            name="Current Design",
        ))
        fig_p.update_layout(
            template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
            title="Design Space: PCE vs Jsc (color = Figure of Merit)",
            xaxis_title="Jsc (mA/cm²)", yaxis_title="PCE (%)",
            font=dict(family="Inter", color="#e2e8f0"),
            height=550, showlegend=True,
        )
        st.plotly_chart(fig_p, use_container_width=True)

        # Top 10
        top10 = df.nlargest(10, "fom")
        st.markdown("### 🏆 Top 10 Designs by Figure of Merit")
        st.dataframe(
            top10[["rpm", "temp", "radius", "pce", "jsc", "grain_nm", "fom", "trl"]].round(2),
            use_container_width=True, hide_index=True,
        )

# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Metrics Twin &bull;
    Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
