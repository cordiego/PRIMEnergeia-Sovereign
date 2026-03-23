"""
Granas Metrics — Full Architecture Dashboard
==============================================
Complete Granas Twin: Composition + Optics + SDL + Thermal + CFRP + SIBO

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
    OpticsMetrics, SDLMetrics, SIBOMetrics, HolisticGranas,
    GranasComposition, ThermalModel, CFRPModel, load_experiment_log,
)

st.set_page_config(
    page_title="Granas Metrics | Full Architecture",
    page_icon="📊", layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .stApp { background: linear-gradient(145deg, #020608 0%, #0a1020 50%, #020608 100%); }
    .metrics-header {
        background: linear-gradient(90deg, rgba(0,255,100,0.10) 0%, rgba(0,209,255,0.08) 100%);
        border: 1px solid rgba(0,255,100,0.3);
        border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
    }
    .metrics-header h1 {
        background: linear-gradient(90deg, #00ff64, #00d1ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2rem; font-weight: 700; margin: 0;
    }
    .metrics-header p { color: #94a3b8; font-size: 0.95rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0f1a 0%, #020608 100%); }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 8px; padding: 16px 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #00ff64; font-family: 'JetBrains Mono', monospace;
        font-size: 34px; font-weight: 700;
        text-shadow: 0 0 12px rgba(0,255,100,0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #00ff64 !important; border-bottom-color: #00ff64 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="metrics-header">
    <h1>🧪 Granas — Full Architecture Twin</h1>
    <p>Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ &bull;
    Green Reflectance &bull; CFRP Skeleton &bull; TOPCon Tandem</p>
</div>
""", unsafe_allow_html=True)

if "holistic" not in st.session_state:
    st.session_state.holistic = None

# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧪 Granas Recipe")
    st.markdown("---")
    st.markdown("#### 🔬 Optics")
    radius = st.slider("Granule Radius (nm)", 80, 600, 300, step=20)
    density = st.slider("Packing Density", 0.1, 0.72, 0.50, step=0.05)
    st.markdown("#### 🧬 Fabrication")
    rpm = st.slider("Spin RPM", 1000, 8000, 4000, step=250)
    temp = st.slider("Anneal Temp (°C)", 50, 200, 120, step=5)
    conc = st.slider("Concentration (M)", 0.5, 2.0, 1.2, step=0.1)
    additive = st.slider("Additive (%)", 0.0, 5.0, 3.0, step=0.5)
    sol_ratio = st.slider("Solvent DMF:DMSO", 0.0, 1.0, 0.7, step=0.1)
    st.markdown("#### 🧪 SIBO")
    sibo_iters = st.slider("Bayesian Iterations", 5, 50, 25)
    st.markdown("---")
    run_btn = st.button("▶ Compute", type="primary", use_container_width=True)

# ─── Compute ─────────────────────────────────────────────────
if run_btn:
    with st.spinner("🧪 Computing full Granas architecture..."):
        comp = GranasComposition()
        optics = OpticsMetrics.from_params(radius, density, 500, comp)
        sdl = SDLMetrics.from_recipe(rpm, temp, conc, additive, sol_ratio)
        sibo = SIBOMetrics.generate_campaign(sibo_iters)
        h = HolisticGranas(optics=optics, sdl=sdl, sibo=sibo).compute()
        st.session_state.holistic = h
    st.toast("✅ Granas architecture computed!", icon="🧪")

h = st.session_state.holistic
if h is None:
    st.markdown("""
    <div style="text-align: center; padding: 4rem;">
        <p style="font-size: 4rem; margin: 0;">🧪</p>
        <h2 style="color: #00ff64;">Granas Full Architecture Twin</h2>
        <p style="color: #94a3b8;">
            Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ — Green Reflectance — CFRP — TOPCon<br>
            Set parameters and click <strong>Compute</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════
# TOP METRICS — 3 rows of 3
# ═══════════════════════════════════════════════════════════
m1, m2, m3 = st.columns(3)
m1.metric("🏆 Device PCE", f"{h.device_pce:.2f}%")
m2.metric("📊 Figure of Merit", f"{h.figure_of_merit:.1f} / 100")
m3.metric("🔬 TRL", f"TRL {h.technology_readiness:.0f}")

m4, m5, m6 = st.columns(3)
m4.metric("⚡ Jsc", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²")
m5.metric("🔋 Voc", f"{h.sdl.voc_mV:.0f} mV")
m6.metric("🧬 PCE (SDL)", f"{h.sdl.pce_pct:.2f}%")

m7, m8, m9 = st.columns(3)
m7.metric("🌡️ Junction Temp", f"{h.sdl.junction_temp_C:.1f} °C")
m8.metric("⏱️ T80 Lifetime", f"{h.t80_years:.1f} yr")
m9.metric("🏗️ Weight", f"{h.cfrp.weight_kg_m2} kg/m²")

# ═══════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Holistic", "🔬 Optics", "🧬 SDL",
    "🌡️ Thermal", "🏗️ CFRP", "🧪 SIBO"
])

# ─── Tab 1: Holistic Radar ───────────────────────────────────
with tab1:
    categories = ["PCE", "Jsc", "Stability", "Thermal", "Grain", "Film"]
    values = [
        min(h.sdl.pce_pct / 38.0 * 100, 100),
        min(h.optics.jsc_mA_cm2 / 44.0 * 100, 100),
        min(h.sdl.t80_hours / 80000 * 100, 100),
        max(0, (1.0 - (h.sdl.junction_temp_C - 25)/50)) * 100,
        min(h.sdl.grain_nm / 500.0 * 100, 100),
        h.sdl.film_quality * 100,
    ]
    values.append(values[0])
    categories.append(categories[0])

    fig_r = go.Figure()
    fig_r.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill="toself",
        line=dict(color="#00ff64", width=3),
        fillcolor="rgba(0,255,100,0.12)", name="Granas",
    ))
    fig_r.add_trace(go.Scatterpolar(
        r=[100]*7, theta=categories,
        line=dict(color="#3a4a6b", width=1, dash="dot"), name="Ideal",
    ))
    fig_r.update_layout(
        polar=dict(bgcolor="#020608",
                   radialaxis=dict(range=[0, 100], gridcolor="#1e2d4a",
                                  tickfont=dict(color="#6b7fa3")),
                   angularaxis=dict(gridcolor="#1e2d4a",
                                   tickfont=dict(color="#94a3b8", size=13))),
        template="plotly_dark", paper_bgcolor="#020608",
        height=500, showlegend=True,
        font=dict(family="Inter", color="#e2e8f0"),
        title="Holistic Performance Radar",
    )
    st.plotly_chart(fig_r, use_container_width=True)

    # Composition card
    st.markdown("### 🧪 Composition")
    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Tolerance t", f"{h.composition.tolerance_factor:.3f}")
    cc2.metric("Bandgap", f"{h.composition.bandgap_eV:.3f} eV")
    cc3.metric("Lattice Strain", f"{h.composition.lattice_strain:.4f}")
    cc4.metric("Green Peak", f"{h.composition.green_reflection_peak_nm:.0f} nm")

# ─── Tab 2: Optics ───────────────────────────────────────────
with tab2:
    st.markdown("### 🔬 Optics + CFRP Recycling")
    o1, o2, o3 = st.columns(3)
    o1.metric("Jsc", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²")
    o2.metric("EQE (400-750)", f"{h.optics.eqe_avg_pct:.1f}%")
    o3.metric("Green Refl.", f"{h.optics.green_reflection_pct:.1f}%")

    o4, o5, o6 = st.columns(3)
    o4.metric("CFRP Recycling", f"{h.optics.cfrp_recycling_pct:.0f}%")
    o5.metric("Absorption", f"{h.optics.weighted_absorption_pct:.1f}%")
    o6.metric("Size Param", f"{h.optics.size_parameter:.2f}")

    # Spectrum with green dip
    wl = np.linspace(300, 1200, 91)
    green_R = 0.35 * np.exp(-((wl - 535)/30)**2)
    x = 2 * np.pi * radius / wl
    q = np.clip(2.0 - (4.0/x)*np.sin(x) + (4.0/x**2)*(1-np.cos(x)), 0, 4)
    path = 1.0 + density * q * 1.1335
    n_imag = 0.5 * np.exp(-((wl-400)/200)**2)
    alpha = 4 * np.pi * n_imag / wl * 1e7
    A = np.clip((1-green_R) * (1 - np.exp(-alpha * 500e-7 * path)), 0, 1)

    fig_spec = go.Figure()
    fig_spec.add_trace(go.Scatter(x=wl, y=A*100, name="Absorptance",
                                   line=dict(color="#00ff64", width=2)))
    fig_spec.add_trace(go.Scatter(x=wl, y=green_R*100, name="Green Reflection",
                                   line=dict(color="#00ff00", width=2, dash="dot"),
                                   fill="tozeroy", fillcolor="rgba(0,255,0,0.08)"))
    fig_spec.add_vline(x=535, line_dash="dash", line_color="rgba(0,255,0,0.5)")
    fig_spec.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="Absorptance & Green Reflectance", height=450,
        xaxis_title="λ (nm)", yaxis_title="%",
        font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_spec, use_container_width=True)

# ─── Tab 3: SDL ─────────────────────────────────────────────
with tab3:
    st.markdown("### 🧬 SDL Fabrication")
    s1, s2, s3 = st.columns(3)
    s1.metric("PCE", f"{h.sdl.pce_pct:.2f}%")
    s2.metric("Grain Size", f"{h.sdl.grain_nm:.0f} nm")
    s3.metric("Thickness", f"{h.sdl.thickness_nm:.0f} nm")

    s4, s5, s6 = st.columns(3)
    s4.metric("Spin RPM", f"{h.sdl.spin_rpm:.0f}")
    s5.metric("Anneal Temp", f"{h.sdl.anneal_temp_C:.0f} °C")
    s6.metric("Concentration", f"{h.sdl.concentration_M:.2f} M")

    s7, s8, s9 = st.columns(3)
    s7.metric("Additive", f"{h.sdl.additive_pct:.1f}%")
    s8.metric("Solvent Ratio", f"{h.sdl.solvent_ratio:.1f}")
    s9.metric("Film Quality", f"{h.sdl.film_quality:.3f}")

    # PCE vs Temp sweep
    temps_sw = np.linspace(50, 200, 31)
    pces_sw = [SDLMetrics.from_recipe(h.sdl.spin_rpm, t, h.sdl.concentration_M,
               h.sdl.additive_pct, h.sdl.solvent_ratio).pce_pct for t in temps_sw]
    fig_sdl = go.Figure(go.Scatter(x=temps_sw, y=pces_sw, name="PCE",
                                    line=dict(color="#00ffcc", width=3)))
    fig_sdl.add_vline(x=h.sdl.anneal_temp_C, line_dash="dash", line_color="#8a2be2")
    fig_sdl.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="PCE vs Anneal Temperature", xaxis_title="°C", yaxis_title="PCE (%)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_sdl, use_container_width=True)

# ─── Tab 4: Thermal ─────────────────────────────────────────
with tab4:
    st.markdown("### 🌡️ Thermal Management (Green Reflectance)")
    t1, t2, t3 = st.columns(3)
    t1.metric("Junction Temp", f"{h.sdl.junction_temp_C:.1f} °C")
    t2.metric("Voc Gain", f"+{h.thermal.voc_gain_mV(h.sdl.junction_temp_C):.0f} mV")
    t3.metric("k_deg", f"{h.sdl.degradation_rate:.2e} h⁻¹")

    t4, t5, t6 = st.columns(3)
    t4.metric("T80 Lifetime", f"{h.t80_years:.1f} years")
    t5.metric("Green Reflectance", f"{h.optics.green_reflection_pct:.1f}%")
    t6.metric("Control Tj", "68 °C")

    # Tj vs green reflectance
    refls = np.linspace(0, 0.5, 21)
    tjs = [h.thermal.junction_temp(h.sdl.pce_pct, r) for r in refls]
    kdegs = [h.thermal.degradation_rate(tj) for tj in tjs]
    t80s = [h.thermal.t80_hours(tj)/8760 for tj in tjs]

    fig_th = make_subplots(rows=1, cols=2,
                            subplot_titles=["Tj vs Green Reflectance", "T80 vs Green Reflectance"])
    fig_th.add_trace(go.Scatter(x=refls*100, y=tjs, name="Tj (°C)",
                                 line=dict(color="#ff6b35", width=3)), row=1, col=1)
    fig_th.add_shape(type="line", x0=0, x1=50, y0=42, y1=42,
                      line=dict(color="rgba(0,255,100,0.5)", width=1, dash="dot"),
                      xref="x", yref="y", row=1, col=1)
    fig_th.add_trace(go.Scatter(x=refls*100, y=t80s, name="T80 (yr)",
                                 line=dict(color="#00d1ff", width=3)), row=1, col=2)
    fig_th.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    fig_th.update_xaxes(title_text="Green Reflectance (%)")
    st.plotly_chart(fig_th, use_container_width=True)

# ─── Tab 5: CFRP ─────────────────────────────────────────────
with tab5:
    st.markdown("### 🏗️ CFRP Structural Skeleton")
    c1, c2, c3 = st.columns(3)
    c1.metric("Weight", f"{h.cfrp.weight_kg_m2} kg/m²")
    c2.metric("vs Glass", f"{h.weight_reduction:.0f}% lighter")
    c3.metric("Module Area", f"{h.cfrp.area_m2:.3f} m²")

    c4, c5, c6 = st.columns(3)
    c4.metric("Max Deflection", f"{h.cfrp.max_deflection_mm():.1f} mm")
    c5.metric("Rigidity Gain", f"+{h.cfrp.rigidity_gain_pct:.0f}%")
    c6.metric("Photon Recycling", f"{h.cfrp.photon_recycling_pct:.0f}%")

    st.markdown("### Blueprint: 17 × 10.5 Geometric Matrix")
    st.markdown("""
    | Edge | Length (units) | Role |
    |------|---------------|------|
    | **Peripheral triangles** | 5.5 | Heavy load-bearing, anchoring |
    | **Internal rhombi** | 3.5 | Stress distribution, optical routing |
    | **Central network** | 3.0 | Precision vertices, crack arrest |
    """)

# ─── Tab 6: SIBO ─────────────────────────────────────────────
with tab6:
    st.markdown("### 🧪 SIBO Bayesian Convergence")
    sibo = h.sibo
    best_sibo = sibo[-1]
    b1, b2, b3 = st.columns(3)
    b1.metric("Best PCE", f"{best_sibo.best_pce:.2f}%")
    b2.metric("GP Uncertainty", f"±{best_sibo.gp_uncertainty:.2f}%")
    b3.metric("Params Explored", f"{best_sibo.params_explored}")

    fig_s = go.Figure(go.Scatter(
        x=[s.iteration for s in sibo], y=[s.best_pce for s in sibo],
        line=dict(color="#00ff64", width=3), name="Best PCE",
    ))
    fig_s.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="PCE Convergence", xaxis_title="Iteration", yaxis_title="PCE (%)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_s, use_container_width=True)

# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Full Architecture Twin &bull;
    Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ &bull; Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
