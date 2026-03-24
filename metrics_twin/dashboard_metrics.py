"""
Granas Metrics — Full Architecture Dashboard
==============================================
Complete Granas Twin: Composition + Optics + SDL + Thermal + CFRP + SIBO + Albedo + GHB + ETFE + TOPCon + Blueprint

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
    AlbedoMetrics, GHBMetrics, ETFEMetrics, TOPConMetrics, BlueprintMetrics,
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
        font-size: 2.2rem; font-weight: 700; margin: 0;
    }
    .metrics-header p { color: #c8d6e5; font-size: 1.05rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0f1a 0%, #020608 100%); }
    div[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    div[data-testid="stSidebar"] .stMarkdown h3,
    div[data-testid="stSidebar"] .stMarkdown h4 { color: #00ff64 !important; font-size: 1.1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 10px; padding: 18px 22px;
    }
    div[data-testid="stMetricValue"] {
        color: #00ff64; font-family: 'JetBrains Mono', monospace;
        font-size: 40px; font-weight: 700;
        text-shadow: 0 0 12px rgba(0,255,100,0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #c8d6e5; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 14px; letter-spacing: 1px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #c8d6e5; font-weight: 600; font-size: 15px; }
    .stTabs [aria-selected="true"] { color: #00ff64 !important; border-bottom-color: #00ff64 !important; }
    /* Markdown text readability */
    .stMarkdown, .stMarkdown p, .stMarkdown li { color: #e2e8f0 !important; font-size: 15px; line-height: 1.7; }
    .stMarkdown h2, .stMarkdown h3 { color: #00ff64 !important; font-size: 1.4rem; font-weight: 700; margin-top: 1.2rem; }
    .stMarkdown strong { color: #ffffff !important; }
    .stMarkdown code { color: #00d1ff !important; background: rgba(0,209,255,0.08); padding: 2px 6px; border-radius: 4px; }
    /* Table readability */
    .stMarkdown table { border-collapse: collapse; width: 100%; }
    .stMarkdown th { color: #00ff64 !important; background: rgba(0,255,100,0.08); font-size: 14px; padding: 10px 14px; text-align: left; }
    .stMarkdown td { color: #e2e8f0 !important; font-size: 14px; padding: 8px 14px; border-bottom: 1px solid #1e2d4a; }
    .stMarkdown tr:hover td { background: rgba(0,255,100,0.04); }
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

# ─── Default slider values (can be overridden by auto-optimize) ────
_defaults = {
    "opt_radius": 300, "opt_density": 0.50,
    "opt_rpm": 4000, "opt_temp": 120, "opt_conc": 1.2,
    "opt_additive": 3.0, "opt_sol_ratio": 0.7,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _run_auto_optimize():
    """Grid search over 7D recipe space to maximize Figure of Merit."""
    comp = GranasComposition()
    best_fom = -1
    best_params = {}

    radii = list(range(140, 520, 60))
    densities = [0.30, 0.40, 0.50, 0.55, 0.60, 0.65, 0.72]
    rpms = list(range(2000, 6500, 500))
    temps = list(range(80, 155, 10))
    concs = [0.8, 1.0, 1.2, 1.4, 1.6]
    additives = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    sol_ratios = [0.5, 0.6, 0.7, 0.8]

    # Phase 1: coarse sweep over RPM × Temp × Radius (most impactful)
    for r in radii:
        for rpm in rpms:
            for t in temps:
                sdl = SDLMetrics.from_recipe(rpm, t, 1.2, 3.0, 0.7)
                optics = OpticsMetrics.from_params(r, 0.5, 500, comp)
                h = HolisticGranas(optics=optics, sdl=sdl, sibo=[]).compute()
                if h.figure_of_merit > best_fom:
                    best_fom = h.figure_of_merit
                    best_params = {"radius": r, "density": 0.5, "rpm": rpm,
                                   "temp": t, "conc": 1.2, "additive": 3.0, "sol_ratio": 0.7}

    # Phase 2: fine sweep around best point for density, conc, additive, solvent
    bp = best_params
    for d in densities:
        for c in concs:
            for a in additives:
                for s in sol_ratios:
                    sdl = SDLMetrics.from_recipe(bp["rpm"], bp["temp"], c, a, s)
                    optics = OpticsMetrics.from_params(bp["radius"], d, 500, comp)
                    h = HolisticGranas(optics=optics, sdl=sdl, sibo=[]).compute()
                    if h.figure_of_merit > best_fom:
                        best_fom = h.figure_of_merit
                        best_params = {"radius": bp["radius"], "density": d,
                                       "rpm": bp["rpm"], "temp": bp["temp"],
                                       "conc": c, "additive": a, "sol_ratio": s}

    return best_params, best_fom


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧪 Granas Recipe")
    st.markdown("---")

    # Auto-Optimize button
    optimize_btn = st.button("⚡ Auto-Optimize", use_container_width=True,
                              help="Grid search 7D recipe space to maximize Figure of Merit")
    if optimize_btn:
        with st.spinner("⚡ Sweeping 7D recipe space..."):
            best_params, best_fom = _run_auto_optimize()
            # Snap to slider steps
            st.session_state.opt_radius = int(round(best_params["radius"] / 20) * 20)
            st.session_state.opt_density = round(best_params["density"] / 0.05) * 0.05
            st.session_state.opt_rpm = int(round(best_params["rpm"] / 250) * 250)
            st.session_state.opt_temp = int(round(best_params["temp"] / 5) * 5)
            st.session_state.opt_conc = round(best_params["conc"] / 0.1) * 0.1
            st.session_state.opt_additive = round(best_params["additive"] / 0.5) * 0.5
            st.session_state.opt_sol_ratio = round(best_params["sol_ratio"] / 0.1) * 0.1
            st.session_state.auto_optimized = True
            st.session_state._auto_compute = True
            st.session_state.best_fom = best_fom
        st.rerun()

    if st.session_state.get("auto_optimized"):
        st.success(f"⚡ Optimized! FoM: {st.session_state.best_fom:.1f}/100")
        st.session_state.auto_optimized = False

    st.markdown("---")
    st.markdown("#### 🔬 Optics")
    radius = st.slider("Granule Radius (nm)", 80, 600,
                        st.session_state.opt_radius, step=20, key="sl_radius")
    density = st.slider("Packing Density", 0.1, 0.72,
                         st.session_state.opt_density, step=0.05, key="sl_density")
    st.markdown("#### 🧬 Fabrication")
    rpm = st.slider("Spin RPM", 1000, 8000,
                     st.session_state.opt_rpm, step=250, key="sl_rpm")
    temp = st.slider("Anneal Temp (°C)", 50, 200,
                      st.session_state.opt_temp, step=5, key="sl_temp")
    conc = st.slider("Concentration (M)", 0.5, 2.0,
                      st.session_state.opt_conc, step=0.1, key="sl_conc")
    additive = st.slider("Additive (%)", 0.0, 5.0,
                          st.session_state.opt_additive, step=0.5, key="sl_additive")
    sol_ratio = st.slider("Solvent DMF:DMSO", 0.0, 1.0,
                           st.session_state.opt_sol_ratio, step=0.1, key="sl_sol_ratio")
    st.markdown("#### 🧪 SIBO")
    sibo_iters = st.slider("Bayesian Iterations", 5, 50, 25)
    st.markdown("---")
    run_btn = st.button("▶ Compute", type="primary", use_container_width=True)

# ─── Compute ─────────────────────────────────────────────────
_auto = st.session_state.pop("_auto_compute", False)
if run_btn or _auto:
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "🎯 Holistic", "🔬 Optics", "🧬 SDL",
    "🌡️ Thermal", "🏗️ CFRP", "🧪 SIBO",
    "🌿 Albedo", "⚗️ GHB", "🛡️ ETFE", "🔬 TOPCon", "📐 Blueprint"
])

# ─── Tab 1: Holistic Radar ───────────────────────────────────
with tab1:
    categories = ["PCE", "Jsc", "Stability", "Thermal", "Grain", "Film"]
    values = [
        min(h.sdl.pce_pct / 38.0 * 100, 100),
        min(h.optics.jsc_mA_cm2 / 44.0 * 100, 100),
        min(h.sdl.t80_hours / 262800 * 100, 100),  # 30-year target
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

# ─── Tab 7: Albedo ───────────────────────────────────────────
with tab7:
    st.markdown("### 🌿 Albedo — Green Reflectance Thermal Management")
    alb = h.albedo
    a1, a2, a3 = st.columns(3)
    a1.metric("Green Reflectance", f"{alb.green_reflectance_pct:.0f}%")
    a2.metric("Junction Temp", f"{alb.junction_temp_C:.1f} °C")
    a3.metric("Control Temp", f"{alb.control_temp_C:.0f} °C")

    a4, a5, a6 = st.columns(3)
    a4.metric("Voc Gain", f"+{alb.voc_gain_mV:.0f} mV")
    a5.metric("T80 (Granas)", f"{alb.t80_granas_yr:.1f} yr")
    a6.metric("T80 (Control)", f"{alb.t80_control_yr:.1f} yr")

    a7, a8, _ = st.columns(3)
    a7.metric("Urban HVAC Savings", f"{alb.urban_hvac_savings_pct:.1f}%")
    a8.metric("Surface Cooling", f"-{alb.surface_cooling_C:.0f} °C")

    # Arrhenius degradation comparison
    temps_deg = np.linspace(30, 80, 51)
    thermal_m = ThermalModel()
    k_degs = [thermal_m.degradation_rate(t) for t in temps_deg]
    t80s_deg = [thermal_m.t80_hours(t) / 8760 for t in temps_deg]

    fig_alb = go.Figure()
    fig_alb.add_trace(go.Scatter(x=temps_deg, y=t80s_deg, name="T80 Lifetime",
                                  line=dict(color="#00ff64", width=3)))
    fig_alb.add_vline(x=alb.junction_temp_C, line_dash="dash", line_color="#00ff64",
                       annotation_text="Granas Tj")
    fig_alb.add_vline(x=68, line_dash="dash", line_color="#ff4444",
                       annotation_text="Control Tj")
    fig_alb.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="T80 Lifetime vs Junction Temperature (Arrhenius)",
        xaxis_title="Junction Temp (°C)", yaxis_title="T80 (years)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_alb, use_container_width=True)

# ─── Tab 8: GHB ─────────────────────────────────────────────
with tab8:
    st.markdown("### ⚗️ GHB — Green Haber-Bosch Electrochemical NRR")
    ghb = h.ghb
    g1, g2, g3 = st.columns(3)
    g1.metric("Faradaic Efficiency", f"{ghb.faradaic_efficiency_pct:.1f}%")
    g2.metric("NH₃ Yield", f"{ghb.nh3_yield_umol_h_cm2:.1f} μmol/h·cm²")
    g3.metric("Solar→NH₃", f"{ghb.solar_to_nh3_pct:.1f}%")

    g4, g5, g6 = st.columns(3)
    g4.metric("Cell Voltage", f"{ghb.cell_voltage_V:.1f} V")
    g5.metric("Current Density", f"{ghb.current_density_mA_cm2:.1f} mA/cm²")
    g6.metric("Temperature", f"{ghb.temperature_C:.0f} °C")

    g7, g8, _ = st.columns(3)
    g7.metric("Catalyst", ghb.catalyst)
    g8.metric("Electrolyte", ghb.electrolyte)

    st.markdown("""
    **Reaction:** N₂ + 6H₂O + 6e⁻ → 2NH₃ + 3O₂

    The Granas GHB module electrochemically reduces atmospheric nitrogen
    to ammonia using solar-generated electricity from the perovskite/TOPCon tandem.
    This enables decentralized green fertilizer production at the module level.
    """)

# ─── Tab 9: ETFE ─────────────────────────────────────────────
with tab9:
    st.markdown("### 🛡️ ETFE — Front Encapsulation Architecture")
    etfe = h.etfe
    e1, e2, e3 = st.columns(3)
    e1.metric("Transmittance", f"{etfe.transmittance_pct:.0f}%")
    e2.metric("AR Gain vs Glass", f"+{etfe.ar_gain_pct:.1f}%")
    e3.metric("Haze Factor", f"{etfe.haze_factor:.2f}×")

    e4, e5, e6 = st.columns(3)
    e4.metric("Weight", f"{etfe.weight_kg_m2:.2f} kg/m²")
    e5.metric("vs Glass", f"{etfe.weight_ratio*100:.1f}% weight")
    e6.metric("UV Degradation", f"{etfe.uv_degradation_pct_yr:.1f}%/yr")

    e7, e8, e9 = st.columns(3)
    e7.metric("Thermoform Temp", f"{etfe.thermoform_temp_C:.0f} °C")
    e8.metric("Pressure", f"{etfe.thermoform_pressure_bar:.1f} bar")
    e9.metric("Adhesion", f"{etfe.adhesion_N_cm:.0f} N/cm")

    # Transmittance degradation over 30 years
    years = np.arange(0, 31)
    trans_yr = [etfe.transmittance_at_year(y) for y in years]

    fig_etfe = go.Figure(go.Scatter(x=years, y=trans_yr, name="Transmittance",
                                      line=dict(color="#00d1ff", width=3)))
    fig_etfe.add_hline(y=90, line_dash="dash", line_color="#ff4444",
                         annotation_text="Min spec (90%)")
    fig_etfe.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="ETFE Transmittance Degradation (30-Year Projection)",
        xaxis_title="Year", yaxis_title="Transmittance (%)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
        yaxis=dict(range=[85, 100]),
    )
    st.plotly_chart(fig_etfe, use_container_width=True)

# ─── Tab 10: TOPCon ──────────────────────────────────────────
with tab10:
    st.markdown("### 🔬 TOPCon — Silicon Bottom Cell")
    tc = h.topcon
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Implied Voc", f">{tc.implied_voc_mV:.0f} mV")
    tc2.metric("J₀ (total)", f"{tc.j0_fA_cm2:.1f} fA/cm²")
    tc3.metric("PCE (standalone)", f"~{tc.pce_standalone_pct:.1f}%")

    tc4, tc5, tc6 = st.columns(3)
    tc4.metric("Tandem Jsc", f"~{tc.tandem_jsc_mA_cm2:.1f} mA/cm²")
    tc5.metric("NIR EQE Peak", f"{tc.nir_eqe_peak_pct:.0f}%")
    tc6.metric("Wafer", f"{tc.wafer_thickness_um:.0f} μm")

    tc7, tc8, _ = st.columns(3)
    tc7.metric("Tunnel Oxide", f"{tc.tunnel_oxide_nm:.1f} nm SiO₂")
    tc8.metric("Poly-Si", f"{tc.poly_si_nm:.0f} nm n⁺")

    st.markdown("### Architecture Stack")
    st.code("""
    SiNₓ ARC (75nm)
         ↓
    n-Si Absorber (Cz, 180μm)
         ↓
    SiO₂ Tunnel Oxide (1.5nm)
         ↓
    n⁺ Poly-Si Contact (200nm)
         ↓
    Al₂O₃ + SiNₓ Passivation
    """, language=None)

    # NIR EQE curve
    wl_nir = np.linspace(700, 1200, 51)
    eqe_nir = tc.nir_eqe_peak_pct * np.exp(-((wl_nir - 950) / 180)**2)
    eqe_nir = np.clip(eqe_nir, 0, 100)

    fig_tc = go.Figure(go.Scatter(x=wl_nir, y=eqe_nir, name="EQE",
                                    line=dict(color="#8a2be2", width=3),
                                    fill="tozeroy", fillcolor="rgba(138,43,226,0.1)"))
    fig_tc.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="TOPCon NIR External Quantum Efficiency",
        xaxis_title="λ (nm)", yaxis_title="EQE (%)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_tc, use_container_width=True)

# ─── Tab 11: Blueprint ───────────────────────────────────────
with tab11:
    st.markdown("### 📐 Blueprint — Master Geometric Engine")
    bp = h.blueprint
    bp1, bp2, bp3 = st.columns(3)
    bp1.metric("Module Dimensions", f"{bp.width_units:.0f} × {bp.height_units:.1f}")
    bp2.metric("Module Area", f"{bp.module_area_m2:.3f} m²")
    bp3.metric("Total Edges", f"{bp.total_edges}")

    bp4, bp5, bp6 = st.columns(3)
    bp4.metric("Photon Recycling", f"{bp.photon_recycling_pct:.0f}%")
    bp5.metric("Rigidity Gain", f"+{bp.rigidity_gain_pct:.0f}%")
    bp6.metric("Max Deflection", f"{bp.max_deflection_mm:.1f} mm")

    bp7, bp8, bp9 = st.columns(3)
    bp7.metric("COMSOL Jsc", f"{bp.comsol_jsc_mA_cm2:.1f} mA/cm²")
    bp8.metric("Min Absorber Passes", f"{bp.min_absorber_passes}")
    bp9.metric("Test Pressure", f"{bp.test_pressure_Pa:.0f} Pa")

    st.markdown("### Edge Catalog")
    st.markdown("""
    | Type | Length (units) | Count | Role |
    |------|---------------|-------|------|
    | **Peripheral** | 5.5 | 6 | Heavy load-bearing, anchoring triangles |
    | **Internal** | 3.5 | 8 | Stress distribution rhombi |
    | **Central** | 3.0 | 12 | Precision vertex network, crack arrest |
    """)

# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Full Architecture Twin &bull;
    Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ &bull; Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
