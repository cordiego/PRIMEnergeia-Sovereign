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
    AlbedoMetrics, GHBMetrics, H2Metrics, ETFEMetrics, TOPConMetrics, BlueprintMetrics,
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
            # Push optimized values into the actual widget keys so sliders
            # pick them up on rerun (Streamlit ignores `value=` once a key exists)
            st.session_state.sl_radius = st.session_state.opt_radius
            st.session_state.sl_density = st.session_state.opt_density
            st.session_state.sl_rpm = st.session_state.opt_rpm
            st.session_state.sl_temp = st.session_state.opt_temp
            st.session_state.sl_conc = st.session_state.opt_conc
            st.session_state.sl_additive = st.session_state.opt_additive
            st.session_state.sl_sol_ratio = st.session_state.opt_sol_ratio
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
m1.metric("🏆 Device PCE", f"{h.device_pce:.2f}%", help="Power Conversion Efficiency of the full tandem device. Computed as SDL PCE × optics enhancement (Mie scattering + CFRP photon recycling). This is the headline efficiency for the Granas perovskite/TOPCon stack under AM1.5G.")
m2.metric("📊 Figure of Merit", f"{h.figure_of_merit:.1f} / 100", help="Composite score (0-100) weighting PCE (25%), Jsc (20%), grain quality (15%), T80 stability (20%), and thermal management (20%). Captures how balanced the Granas architecture performs across all critical axes.")
m3.metric("🔬 TRL", f"TRL {h.technology_readiness:.0f}", help="Technology Readiness Level (NASA scale 1-9). Estimated from tandem PCE thresholds: TRL 7 at >33%, TRL 6 at >28%, TRL 5 at >22%. Indicates proximity to production-scale Granas deployment.")

m4, m5, m6 = st.columns(3)
m4.metric("⚡ Jsc", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²", help="Short-circuit current density. Integrated from AM1.5G spectrum × absorptance × Mie path-enhancement × CFRP photon recycling. Granas targets 43.9 mA/cm² via green-reflective granule optics.")
m5.metric("🔋 Voc", f"{h.sdl.voc_mV:.0f} mV", help="Open-circuit voltage of the tandem stack. Base ~1100 mV + thermal Voc gain from green-reflectance cooling (dVoc/dT = -1.8 mV/°C). Granas' lower Tj directly boosts voltage vs dark absorbers.")
m6.metric("🧬 PCE (SDL)", f"{h.sdl.pce_pct:.2f}%", help="PCE from the Self-Driving Lab fabrication engine. Combines perovskite top-cell (~23% max) + TOPCon bottom-cell (~15%) as a 2-terminal tandem, modulated by film quality, Mn2+ passivation, and green sacrifice factor.")

m7, m8, m9 = st.columns(3)
m7.metric("🌡️ Junction Temp", f"{h.sdl.junction_temp_C:.1f} °C", help="Cell junction temperature under 1-sun. Granas' 35% green reflectance at 535 nm rejects peak solar heat: Tj ~ 42 °C vs 68 °C for standard dark absorbers. Lower Tj improves Voc, reduces degradation.")
m8.metric("⏱️ T80 Lifetime", f"{h.t80_years:.1f} yr", help="Time for PCE to drop to 80% of initial. From Arrhenius kinetics: T80 = -ln(0.8)/k_deg. Granas' low Tj + ETFE UV barrier + Mn2+ passivation targets 30+ year encapsulated lifetime.")
m9.metric("🏗️ Weight", f"{h.cfrp.weight_kg_m2} kg/m²", help="Module areal weight using CFRP skeleton instead of glass. 2.5 kg/m² vs 12 kg/m² for glass — Granas modules are ~5x lighter, critical for rooftop deployment and reduced BOS costs.")

# ═══════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
    "🎯 Holistic", "🔬 Optics", "🧬 SDL",
    "🌡️ Thermal", "🏗️ CFRP", "🧪 SIBO",
    "🌿 Albedo", "💧 H2", "⚗️ GHB", "🛡️ ETFE", "🔬 TOPCon", "📐 Blueprint"
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
    cc1.metric("Tolerance t", f"{h.composition.tolerance_factor:.3f}", help="Goldschmidt tolerance factor t = (rA + rX)/(sqrt(2)*(rB + rX)). Values 0.9-1.0 indicate stable perovskite phase. Granas' Cs/FA A-site and Ni/Mn B-site doping keep t in the cubic stability window.")
    cc2.metric("Bandgap", f"{h.composition.bandgap_eV:.3f} eV", help="Optical bandgap of the perovskite absorber. Base MAPbI3 (1.55 eV) modified by Ni2+ lattice compression (+24 meV) and Mn2+ passivation (-4 meV). Tuned for optimal tandem current-matching with TOPCon silicon.")
    cc3.metric("Lattice Strain", f"{h.composition.lattice_strain:.4f}", help="Williamson-Hall lattice strain from Ni2+ and Mn2+ dopant incorporation. Ni2+ (69 pm vs Pb2+ 119 pm) introduces compressive strain. Moderate strain improves grain boundary passivation without cracking.")
    cc4.metric("Green Peak", f"{h.composition.green_reflection_peak_nm:.0f} nm", help="Wavelength of peak green reflectance from quarter-wave interference in the perovskite film. Fixed at 535 nm — the AM1.5G solar irradiance peak — maximizing thermal rejection while the reflected green light provides the signature Granas aesthetic.")

# ─── Tab 2: Optics ───────────────────────────────────────────
with tab2:
    st.markdown("### 🔬 Optics + CFRP Recycling")
    o1, o2, o3 = st.columns(3)
    o1.metric("Jsc", f"{h.optics.jsc_mA_cm2:.2f} mA/cm²", help="Short-circuit current from Mie-enhanced optics. Computed by integrating AM1.5G photon flux × absorptance over 300-1200 nm with CFRP recycling boost. The Granas granule radius and packing density directly control Mie path-enhancement.")
    o2.metric("EQE (400-750)", f"{h.optics.eqe_avg_pct:.1f}%", help="Average External Quantum Efficiency in the visible range. Measures the fraction of incident photons converted to current. The green reflectance dip at 535 nm intentionally sacrifices ~5% EQE for thermal management benefits.")
    o3.metric("Green Refl.", f"{h.optics.green_reflection_pct:.1f}%", help="Average reflectance in the 500-570 nm green band. This is the core Granas albedo mechanism — selectively reflecting green photons (peak of solar spectrum) to reduce junction temperature by ~26 °C, boosting Voc and lifetime.")

    o4, o5, o6 = st.columns(3)
    o4.metric("CFRP Recycling", f"{h.optics.cfrp_recycling_pct:.0f}%", help="Percentage of boundary-incident photons redirected back to the absorber by chamfered CFRP ridges. The carbon fiber skeleton acts as an intra-module light concentrator, boosting effective Jsc by ~13% (COMSOL-validated).")
    o5.metric("Absorption", f"{h.optics.weighted_absorption_pct:.1f}%", help="Spectrally-weighted absorptance averaged over 300-1200 nm. Accounts for green reflection dip, Mie scattering path-enhancement, and CFRP photon recycling. Higher values mean less optical loss in the Granas stack.")
    o6.metric("Size Param", f"{h.optics.size_parameter:.2f}", help="Mie size parameter x = 2*pi*r/lambda at 500 nm. Controls the scattering regime: x~1 gives strongest Mie resonance. Granas granule radius is tuned so x falls in the optimal scattering range for path-length enhancement.")

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
    s1.metric("PCE", f"{h.sdl.pce_pct:.2f}%", help="Tandem power conversion efficiency from the SDL fabrication model. Perovskite top-cell + TOPCon bottom-cell, modulated by grain size, film thickness, Mn2+ defect passivation, and the green sacrifice factor (~5% Jsc traded for thermal cooling).")
    s2.metric("Grain Size", f"{h.sdl.grain_nm:.0f} nm", help="Average crystallite grain diameter. Computed via sigmoid growth model with Mn2+ passivation bonus. Larger grains (>400 nm) reduce grain-boundary recombination. Controlled by anneal temperature and spin RPM in the Granas SDL recipe.")
    s3.metric("Thickness", f"{h.sdl.thickness_nm:.0f} nm", help="Perovskite film thickness. Scales as 1200*concentration/sqrt(RPM/1000). Optimal ~500-600 nm balances full light absorption against charge-carrier extraction length. Too thick increases recombination; too thin loses photons.")

    s4, s5, s6 = st.columns(3)
    s4.metric("Spin RPM", f"{h.sdl.spin_rpm:.0f}", help="Spin-coating rotational speed. Controls film thickness and uniformity. Higher RPM gives thinner, more uniform films but smaller grains. The Granas SDL optimizes RPM jointly with anneal temp for maximum tandem PCE.")
    s5.metric("Anneal Temp", f"{h.sdl.anneal_temp_C:.0f} °C", help="Post-deposition annealing temperature. Drives perovskite crystallization and grain growth. Optimal ~100-130 °C; above 150 °C causes thermal decomposition. Critical SDL parameter for Granas film quality.")
    s6.metric("Concentration", f"{h.sdl.concentration_M:.2f} M", help="Precursor solution molar concentration. Higher concentration yields thicker films. Optimal ~1.0-1.4 M for the Granas Cs/FA/Pb/Ni/Mn composition. Interacts with spin RPM to determine final film thickness.")

    s7, s8, s9 = st.columns(3)
    s7.metric("Additive", f"{h.sdl.additive_pct:.1f}%", help="Percentage of additive in the precursor solution (optimal 2.5-3.5%). Additives control nucleation density and grain morphology. Within Granas, this tunes the Mn2+ passivation pathway and final film crystallinity.")
    s8.metric("Solvent Ratio", f"{h.sdl.solvent_ratio:.1f}", help="DMF:DMSO solvent ratio (0-1). DMSO forms intermediate adducts that slow crystallization for larger grains. Optimal ~0.6-0.8 for the Granas composition. Controls the Lewis-base coordination during spin-coating.")
    s9.metric("Film Quality", f"{h.sdl.film_quality:.3f}", help="Composite quality score (0-1) combining grain size, thickness uniformity, anneal integrity, and Mn2+ passivation factor. Directly multiplies PCE calculation. A Film Quality >0.8 indicates a production-grade Granas absorber.")

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
    t1.metric("Junction Temp", f"{h.sdl.junction_temp_C:.1f} °C", help="Granas junction temperature under 1-sun. Thermal model: Tj = T_amb + 43°C (full absorption) - green cooling - PCE cooling. The 35% green reflectance at 535 nm is the primary cooling mechanism, targeting Tj = 42 °C.")
    t2.metric("Voc Gain", f"+{h.thermal.voc_gain_mV(h.sdl.junction_temp_C):.0f} mV", help="Voltage gain from reduced junction temperature vs a 68 °C control. dVoc/dT = -1.8 mV/°C for perovskite. A 26 °C reduction yields ~+45 mV — directly boosting Granas tandem efficiency and energy yield.")
    t3.metric("k_deg", f"{h.sdl.degradation_rate:.2e} h⁻¹", help="Arrhenius degradation rate constant. k = A*exp(-Ea/kBT) with Ea = 0.75 eV. Lower Tj exponentially slows degradation. Granas k_deg ~ 8.5e-7 h-1 at 42 °C (encapsulated) vs ~2.4e-4 h-1 at 68 °C (unencapsulated control).")

    t4, t5, t6 = st.columns(3)
    t4.metric("T80 Lifetime", f"{h.t80_years:.1f} years", help="Time to 80% retained PCE from Arrhenius kinetics: T80 = -ln(0.8)/k_deg. Granas' full encapsulation stack (ETFE + Mn2+ + CFRP moisture barrier + low Tj) targets T80 > 30 years for production modules.")
    t5.metric("Green Reflectance", f"{h.optics.green_reflection_pct:.1f}%", help="Average reflectance in the 500-570 nm green band (peak ~35% at 535 nm). This is the Granas albedo engine — the single design choice that simultaneously reduces Tj, boosts Voc, extends lifetime, and creates the green module aesthetic.")
    t6.metric("Control Tj", "68 °C", help="Reference junction temperature for a standard dark-absorber perovskite module without green reflectance. Used as the baseline for computing Granas' thermal advantage: delta_T = 68 - 42 = 26 °C.")

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
    c1.metric("Weight", f"{h.cfrp.weight_kg_m2} kg/m²", help="Areal weight of the CFRP structural skeleton. At 2.5 kg/m² vs 12 kg/m² for tempered glass, the carbon fiber frame is the structural backbone of Granas — enabling lightweight rooftop-deployable modules.")
    c2.metric("vs Glass", f"{h.weight_reduction:.0f}% lighter", help="Weight reduction percentage compared to standard glass-framed modules. Granas CFRP achieves ~79% weight savings, reducing structural load requirements, shipping costs, and enabling installations on weight-limited rooftops.")
    c3.metric("Module Area", f"{h.cfrp.area_m2:.3f} m²", help="Total module area from the 21x34 geometric blueprint (1 unit = 10 cm -> 2.1 m x 3.4 m = 7.14 m2). This is the production-scale Granas module footprint defined by the CFRP skeleton geometry.")

    c4, c5, c6 = st.columns(3)
    c4.metric("Max Deflection", f"{h.cfrp.max_deflection_mm():.1f} mm", help="Maximum center deflection under 5400 Pa transverse load (IEC 61215 test). COMSOL-simulated at 1.8 mm — 42% better than glass frames. The interlocking triangle/rhombus CFRP geometry distributes stress efficiently.")
    c5.metric("Rigidity Gain", f"+{h.cfrp.rigidity_gain_pct:.0f}%", help="Rigidity improvement vs standard perimeter-framed modules. The 21x34 internal CFRP network with peripheral triangles (5.5u), internal rhombi (3.5u), and central vertices (3.0u) creates a distributed load-bearing skeleton.")
    c6.metric("Photon Recycling", f"{h.cfrp.photon_recycling_pct:.0f}%", help="Fraction of boundary-incident photons redirected to the absorber layer. Chamfered CFRP ridges act as intra-module concentrators, recovering ~89% of edge-escaping light. This is a dual structural-optical function unique to Granas.")

    st.markdown("### Blueprint: 21 × 34 Geometric Matrix (2.1 × 3.4 m)")
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
    b1.metric("Best PCE", f"{best_sibo.best_pce:.2f}%", help="Highest PCE found so far in the SIBO Bayesian optimization campaign. The optimizer uses a Gaussian Process surrogate model to efficiently explore the 7D Granas recipe space (RPM, temp, conc, additive, solvent, radius, density).")
    b2.metric("GP Uncertainty", f"±{best_sibo.gp_uncertainty:.2f}%", help="Gaussian Process posterior uncertainty at the current optimum. Decreases as more experiments are sampled. Low uncertainty (<0.5%) indicates the SIBO engine has converged on the optimal Granas fabrication recipe.")
    b3.metric("Params Explored", f"{best_sibo.params_explored}", help="Total number of parameter combinations evaluated by the SIBO Bayesian optimizer. Each iteration samples 8 new points in the recipe space. Higher counts improve confidence that the global PCE optimum has been found.")

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
    a1.metric("Green Reflectance", f"{alb.green_reflectance_pct:.0f}%", help="Spectral-selective reflectance at 535 nm green. This is the Granas albedo engine core — reflecting the highest-irradiance portion of sunlight to cool the cell while harvesting the rest. Measured as R(535nm) from thin-film interference.")
    a2.metric("Junction Temp", f"{alb.junction_temp_C:.1f} °C", help="Junction temperature with green reflectance active. The albedo engine reduces Tj from 68 °C (standard dark cell) to ~42 °C by rejecting green photons. This 26 °C drop cascades into Voc, degradation, and lifetime improvements.")
    a3.metric("Control Temp", f"{alb.control_temp_C:.0f} °C", help="Junction temperature of a control cell without green reflectance. At 68 °C, the control degrades ~280× faster than Granas. This baseline demonstrates the thermal advantage of the albedo engineering approach.")

    a4, a5, a6 = st.columns(3)
    a4.metric("Voc Gain", f"+{alb.voc_gain_mV:.0f} mV", help="Open-circuit voltage gained from lower junction temperature. At dVoc/dT = -1.8 mV/°C and delta_T = 26 °C, Granas gains ~45 mV. This partially compensates the Jsc lost from green reflection, keeping net PCE positive.")
    a5.metric("T80 (Granas)", f"{alb.t80_granas_yr:.1f} yr", help="T80 lifetime projection for the full Granas encapsulated module (ETFE + Mn2+ + green cooling). Arrhenius model at Tj = 42 °C with encapsulation-calibrated k_deg. Target: 30+ years for commercial deployment.")
    a6.metric("T80 (Control)", f"{alb.t80_control_yr:.1f} yr", help="T80 lifetime for the unencapsulated control cell at Tj = 68 °C. Dramatically shorter due to exponential Arrhenius dependence on temperature. Demonstrates why Granas albedo cooling is essential for module-level stability.")

    a7, a8, _ = st.columns(3)
    a7.metric("Urban HVAC Savings", f"{alb.urban_hvac_savings_pct:.1f}%", help="Estimated HVAC energy savings from Granas rooftop installations reflecting green light back to the atmosphere instead of absorbing it as heat. The urban heat island mitigation effect — a co-benefit of the albedo design.")
    a8.metric("Surface Cooling", f"-{alb.surface_cooling_C:.0f} °C", help="Roof surface temperature reduction from green-reflective Granas modules vs dark conventional panels. Reduces building cooling load and contributes to urban heat island mitigation in dense deployments.")

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

# ─── Tab 8: H2 (NEW) ─────────────────────────────────────────
with tab8:
    st.markdown("### 💧 H2 — PEM Electrolysis Green Hydrogen")
    h2m = h.h2
    h2_1, h2_2, h2_3 = st.columns(3)
    h2_1.metric("⚗️ Electrolyzer Eff.", f"{h2m.electrolyzer_efficiency_pct:.0f}%", help="PEM electrolyzer stack efficiency (HHV basis). Ratio of hydrogen energy content to electrical input. At 70%, the Granas H2 engine converts excess solar electricity into storable green hydrogen fuel.")
    h2_2.metric("⚡ Energy/kg H₂", f"{h2m.h2_energy_kwh_per_kg:.0f} kWh", help="System-level electrical energy required to produce 1 kg of hydrogen. Includes stack losses and balance-of-plant. Granas targets ~55 kWh/kg (HHV/eff). Lower is better — driven by stack efficiency improvements.")
    h2_3.metric("💧 H₂O / kg H₂", f"{h2m.water_consumption_kg_per_kg_h2:.0f} kg", help="Water consumption per kg of hydrogen produced (stoichiometric: 9 kg H2O/kg H2). The PEM electrolyzer splits ultrapure water: 2H2O -> 2H2 + O2. Granas H2 uses solar-generated electricity, so the only input is water.")

    h2_4, h2_5, h2_6 = st.columns(3)
    h2_4.metric("🔋 Cell Voltage", f"{h2m.stack_voltage_V:.3f} V", help="Individual PEM cell operating voltage. Thermodynamic minimum is 1.229 V (reversible). Overpotentials from kinetics, ohmic, and mass transport raise it to ~2.0 V. Lower cell voltage means higher efficiency in the Granas H2 engine.")
    h2_5.metric("⚡ Cell Efficiency", f"{h2m.cell_efficiency_pct:.1f}%", help="Single-cell electrochemical efficiency = E_thermo/E_cell = 1.481V/V_cell (HHV basis). Measures how close the PEM cell operates to the thermodynamic ideal. The Granas H2 engine targets >70% cell efficiency.")
    h2_6.metric("🏭 System Efficiency", f"{h2m.system_efficiency_pct:.1f}%", help="Overall system efficiency including balance-of-plant (pumps, cooling, power electronics). Typically 5-8% lower than cell efficiency. This is the real-world conversion rate for the Granas solar-to-hydrogen pathway.")

    h2_7, h2_8, h2_9 = st.columns(3)
    h2_7.metric("💰 LCOH", f"${h2m.lcoh_usd_kg:.2f}/kg", help="Levelized Cost of Hydrogen. Includes annualized CAPEX (CRF), OPEX (3%/yr), and electricity cost over system lifetime. Granas targets LCOH < $4.50/kg (green H2 market) by using free solar electricity from the tandem modules.")
    h2_8.metric("🏢 H₂ Annual", f"{h2m.h2_annual_tonnes:.0f} tonnes", help="Annual hydrogen production in tonnes. Computed from solar capacity x solar fraction (15%) x capacity factor x system efficiency. Scales with Granas PCE — higher tandem efficiency means more electricity for electrolysis.")
    h2_9.metric("💵 Revenue", f"${h2m.revenue_annual_M_usd:.1f}M/yr", help="Annual revenue from green hydrogen sales at $4.50/kg market price. This is the downstream revenue stream from Granas' excess solar electricity, creating a second monetization pathway beyond grid electricity sales.")

    h2_10, h2_11, h2_12 = st.columns(3)
    h2_10.metric("☀️ Solar Fraction", f"{h2m.solar_fraction_pct:.0f}%", help="Fraction of total Granas solar output diverted to hydrogen production (default 15%). The remaining 85% goes to grid electricity. This split optimizes the dual-revenue model of the PRIMEnergeia platform.")
    h2_11.metric("📉 Degradation", f"{h2m.stack_degradation_uV_per_h:.0f} μV/h", help="PEM stack voltage degradation rate in microvolts per hour. At 4 uV/h, the stack reaches end-of-life (~200 mV increase) after ~80,000 hours. Determines stack replacement schedule in the Granas H2 engine.")
    h2_12.metric("⏱️ Stack Lifetime", f"{h2m.stack_lifetime_kh:.0f} kh", help="PEM electrolyzer stack lifetime in thousands of hours before replacement. At 80 kh (~9 years continuous), the stack degrades ~200 mV. Replacement cost is factored into the LCOH calculation for the Granas H2 engine.")

    # LCOH Sensitivity to Electricity Price
    elec_prices = np.arange(10, 110, 5)
    lcohs = []
    for ep in elec_prices:
        crf = (0.08 * 1.08**10) / (1.08**10 - 1)
        annual_capex = 810 * 1000 * crf
        annual_opex = 810 * 1000 * 0.03
        annual_kwh = 1000 * 0.50 * 8760
        annual_elec = annual_kwh * ep / 1000
        kwh_kg = 39.4 / 0.65
        h2_kg = annual_kwh / kwh_kg
        lcohs.append((annual_capex + annual_opex + annual_elec) / h2_kg)

    fig_lcoh = go.Figure(go.Scatter(
        x=elec_prices, y=lcohs, name="LCOH",
        line=dict(color="#00d1ff", width=3),
        fill="tozeroy", fillcolor="rgba(0,209,255,0.08)",
    ))
    fig_lcoh.add_hline(y=4.50, line_dash="dash", line_color="#00ff64",
                        annotation_text="Green H₂ Market ($4.50/kg)")
    fig_lcoh.add_hline(y=1.50, line_dash="dash", line_color="#ff4444",
                        annotation_text="Grey H₂ SMR ($1.50/kg)")
    fig_lcoh.update_layout(
        template="plotly_dark", paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="LCOH Sensitivity to Electricity Price",
        xaxis_title="Electricity Price ($/MWh)", yaxis_title="LCOH ($/kg H₂)",
        height=450, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_lcoh, use_container_width=True)

    st.markdown("""
    **Reaction:** 2H₂O → 2H₂ + O₂  (E° = 1.229 V)

    Granas panels generate excess solar electricity. **15%** is diverted to a PEM
    electrolyzer (Nafion membrane, IrO₂ anode, Pt/C cathode), producing zero-carbon
    green hydrogen. This H₂ feeds downstream:
    - **PEM fuel cells** (PEM-PB-50) for clean power
    - **H₂ turbines** (HY-P100) for fast dispatchable generation
    - **Haber-Bosch** synthesis for green ammonia (NH₃)
    """)

# ─── Tab 9: GHB ─────────────────────────────────────────────
with tab9:
    st.markdown("### ⚗️ GHB — Green Haber-Bosch Electrochemical NRR")
    ghb = h.ghb
    g1, g2, g3 = st.columns(3)
    g1.metric("Faradaic Efficiency", f"{ghb.faradaic_efficiency_pct:.1f}%", help="Fraction of electrons that produce ammonia vs competing hydrogen evolution. At ~47%, nearly half the current goes to NH3. Scales with Granas solar input quality — better PCE provides more stable electrochemical driving force.")
    g2.metric("NH₃ Yield", f"{ghb.nh3_yield_umol_h_cm2:.1f} μmol/h·cm²", help="Ammonia production rate per electrode area. Measured as micromoles per hour per cm2 of catalyst. Scales with available Granas solar current. This metric determines the economics of decentralized green fertilizer production.")
    g3.metric("Solar→NH₃", f"{ghb.solar_to_nh3_pct:.1f}%", help="Overall solar-to-ammonia conversion efficiency. Chains Granas tandem PCE with electrochemical NRR efficiency. At ~3%, this represents the frontier of solar-driven nitrogen fixation — eliminating need for Haber-Bosch fossil heat.")

    g4, g5, g6 = st.columns(3)
    g4.metric("Cell Voltage", f"{ghb.cell_voltage_V:.1f} V", help="Electrochemical cell operating voltage for NRR. Thermodynamic minimum is ~1.17 V. Overpotentials raise it to ~1.8 V. Powered directly by Granas solar output — zero fossil energy input for the entire ammonia synthesis.")
    g5.metric("Current Density", f"{ghb.current_density_mA_cm2:.1f} mA/cm²", help="Operating current density at the NRR cathode. Derived from Granas Jsc x 0.65 coupling factor. Higher current increases NH3 throughput but can reduce Faradaic efficiency. Capped at 25 mA/cm2 for selectivity.")
    g6.metric("Temperature", f"{ghb.temperature_C:.0f} °C", help="NRR cell operating temperature. Ambient (25 °C) electrochemical process — unlike conventional Haber-Bosch which requires 400-500 °C. This low temperature is key to Granas GHB's energy advantage over industrial ammonia.")

    g7, g8, _ = st.columns(3)
    g7.metric("Catalyst", ghb.catalyst, help="NRR electrocatalyst composition. Fe2O3/CNT (iron oxide on carbon nanotubes) provides nitrogen adsorption sites while suppressing competing hydrogen evolution. Earth-abundant materials keep costs low for the Granas ammonia pathway.")
    g8.metric("Electrolyte", ghb.electrolyte, help="Aqueous electrolyte for the NRR cell. 0.1M Li2SO4 provides ionic conductivity while the Li+ cation mediates nitrogen reduction at the cathode surface. Non-corrosive and inexpensive, fitting the Granas decentralized production model.")

    st.markdown("""
    **Reaction:** N₂ + 6H₂O + 6e⁻ → 2NH₃ + 3O₂

    The Granas GHB module electrochemically reduces atmospheric nitrogen
    to ammonia using solar-generated electricity from the perovskite/TOPCon tandem.
    This enables decentralized green fertilizer production at the module level.
    """)

# ─── Tab 10: ETFE ────────────────────────────────────────────
with tab10:
    st.markdown("### 🛡️ ETFE — Front Encapsulation Architecture")
    etfe = h.etfe
    e1, e2, e3 = st.columns(3)
    e1.metric("Transmittance", f"{etfe.transmittance_pct:.0f}%", help="Optical transmittance of the ETFE frontsheet across the solar spectrum. At 96%, ETFE passes more light than tempered glass (~92%). This directly boosts Granas Jsc by reducing front-surface optical losses.")
    e2.metric("AR Gain vs Glass", f"+{etfe.ar_gain_pct:.1f}%", help="Anti-reflection current gain compared to glass encapsulation. ETFE's lower refractive index (n=1.40 vs glass n=1.52) reduces Fresnel reflection. Combined with surface texturing, this adds ~5.5% more photocurrent to the Granas stack.")
    e3.metric("Haze Factor", f"{etfe.haze_factor:.2f}×", help="Light-scattering enhancement factor from ETFE surface texture. Haze >1.0 means forward-scattered light gets longer path length in the absorber. At 1.06x, ETFE adds a subtle diffuse component that improves low-angle performance.")

    e4, e5, e6 = st.columns(3)
    e4.metric("Weight", f"{etfe.weight_kg_m2:.2f} kg/m²", help="ETFE frontsheet areal weight. At 0.17 kg/m2 vs 8.0 kg/m2 for tempered glass, ETFE is ~47x lighter. Combined with the CFRP skeleton, this makes Granas modules exceptionally lightweight for transport and rooftop installation.")
    e5.metric("vs Glass", f"{etfe.weight_ratio*100:.1f}% weight", help="ETFE weight as a percentage of glass encapsulation weight. At 2.1% of glass mass, the ETFE frontsheet is nearly negligible in the module weight budget — the CFRP skeleton dominates at 2.5 kg/m2.")
    e6.metric("UV Degradation", f"{etfe.uv_degradation_pct_yr:.1f}%/yr", help="Annual transmittance loss from UV exposure. ETFE's fluoropolymer chemistry resists UV photolysis far better than EVA. At 0.1%/yr, transmittance stays above 90% for 60+ years — protecting the perovskite underneath from UV damage.")

    e7, e8, e9 = st.columns(3)
    e7.metric("Thermoform Temp", f"{etfe.thermoform_temp_C:.0f} °C", help="Temperature for thermoforming ETFE onto the Granas module. At 270 °C, ETFE softens enough to conform to the CFRP skeleton geometry while maintaining its fluoropolymer crystal structure for long-term UV resistance.")
    e8.metric("Pressure", f"{etfe.thermoform_pressure_bar:.1f} bar", help="Thermoforming pressure for ETFE lamination. At 2.0 bar, the film conforms tightly to the module surface, eliminating air gaps that would scatter light. Critical for achieving the 96% transmittance specification in production.")
    e9.metric("Adhesion", f"{etfe.adhesion_N_cm:.0f} N/cm", help="Peel adhesion strength between ETFE and the underlying layers. At 15 N/cm, the bond survives thermal cycling (-40 to +85 °C) and mechanical loading per IEC 61215. Ensures long-term encapsulation integrity for the Granas perovskite.")

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

# ─── Tab 11: TOPCon ──────────────────────────────────────────
with tab11:
    st.markdown("### 🔬 TOPCon — Silicon Bottom Cell")
    tc = h.topcon
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Implied Voc", f">{tc.implied_voc_mV:.0f} mV", help="Implied open-circuit voltage from quasi-steady-state photoconductance. Measures the recombination quality of the TOPCon silicon bottom cell. >720 mV indicates excellent surface passivation from the SiO2/poly-Si contact.")
    tc2.metric("J₀ (total)", f"{tc.j0_fA_cm2:.1f} fA/cm²", help="Total saturation current density combining bulk and surface recombination. At 6.5 fA/cm2, the TOPCon cell approaches the theoretical silicon limit. Lower J0 means higher Voc — critical for tandem voltage addition with the perovskite top cell.")
    tc3.metric("PCE (standalone)", f"~{tc.pce_standalone_pct:.1f}%", help="Standalone efficiency of the TOPCon bottom cell if used alone (not in tandem). At ~25.4%, this is near the single-junction silicon record. In the Granas tandem, it operates as the NIR-harvesting bottom cell.")

    tc4, tc5, tc6 = st.columns(3)
    tc4.metric("Tandem Jsc", f"~{tc.tandem_jsc_mA_cm2:.1f} mA/cm²", help="Current density of the TOPCon cell when filtered by the perovskite top cell. In 2-terminal tandem, the lower Jsc cell limits total current. Granas aims for current-matching at ~20 mA/cm2 between the perovskite and TOPCon sub-cells.")
    tc5.metric("NIR EQE Peak", f"{tc.nir_eqe_peak_pct:.0f}%", help="Peak external quantum efficiency in the near-infrared (800-1100 nm). The TOPCon bottom cell harvests photons transmitted through the perovskite. At 95% NIR EQE, nearly all sub-bandgap light is captured for tandem current.")
    tc6.metric("Wafer", f"{tc.wafer_thickness_um:.0f} μm", help="n-type Czochralski silicon wafer thickness. At 180 um, it balances mechanical strength against material cost. The TOPCon passivated contacts allow thinner wafers while maintaining voltage — a cost advantage in the Granas tandem.")

    tc7, tc8, _ = st.columns(3)
    tc7.metric("Tunnel Oxide", f"{tc.tunnel_oxide_nm:.1f} nm SiO₂", help="Ultra-thin SiO2 tunnel oxide between absorber and poly-Si contact. At 1.5 nm, it provides chemical passivation while allowing quantum tunneling for current extraction. This is the key innovation enabling TOPCon's high Voc in the Granas stack.")
    tc8.metric("Poly-Si", f"{tc.poly_si_nm:.0f} nm n⁺", help="Phosphorus-doped polysilicon carrier-selective contact. At 200 nm, it creates a high-low junction for electron extraction while the tunnel oxide passivates interface defects. Forms the rear contact of the Granas tandem bottom cell.")

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

# ─── Tab 12: Blueprint ───────────────────────────────────────
with tab12:
    st.markdown("### 📐 Blueprint — Master Geometric Engine")
    bp = h.blueprint
    bp1, bp2, bp3 = st.columns(3)
    bp1.metric("Module Dimensions", f"{bp.width_units:.0f} × {bp.height_units:.1f}", help="Blueprint dimensions in geometric units (1 unit = 10 cm). 21 x 34 units = 2.1 m x 3.4 m physical module. This is the master geometric engine that defines the CFRP skeleton, edge catalog, and optical recycling geometry for Granas.")
    bp2.metric("Module Area", f"{bp.module_area_m2:.3f} m²", help="Total module area from the blueprint geometry: 2.1 m x 3.4 m = 7.14 m2. This production-scale footprint is optimized for shipping container compatibility, rooftop installation, and standard racking systems.")
    bp3.metric("Total Edges", f"{bp.total_edges}", help="Total number of structural edges in the CFRP geometric skeleton. Sum of peripheral (6), internal (8), and central (12) edges. Each edge type has a specific structural and optical role in the Granas module architecture.")

    bp4, bp5, bp6 = st.columns(3)
    bp4.metric("Photon Recycling", f"{bp.photon_recycling_pct:.0f}%", help="Fraction of edge-escaping photons redirected to the absorber by chamfered CFRP ridges. At 89% (COMSOL-validated), this dual-purpose structural-optical feature is unique to the Granas blueprint geometry.")
    bp5.metric("Rigidity Gain", f"+{bp.rigidity_gain_pct:.0f}%", help="Structural rigidity improvement vs conventional perimeter-only framing. The distributed triangle/rhombus CFRP network transfers load across the entire module area, enabling the lightweight 2.5 kg/m2 design to withstand IEC mechanical loads.")
    bp6.metric("Max Deflection", f"{bp.max_deflection_mm:.1f} mm", help="Max center deflection under IEC 61215 transverse load test (5400 Pa). At 1.8 mm, the CFRP skeleton outperforms glass frames by 42%. This low deflection protects the brittle perovskite absorber from mechanical cracking.")

    bp7, bp8, bp9 = st.columns(3)
    bp7.metric("COMSOL Jsc", f"{bp.comsol_jsc_mA_cm2:.1f} mA/cm²", help="Short-circuit current density from COMSOL ray-tracing simulation of the full blueprint geometry. The 43.9 mA/cm2 target includes Mie scattering, CFRP photon recycling, and ETFE anti-reflection — the complete Granas optical stack.")
    bp8.metric("Min Absorber Passes", f"{bp.min_absorber_passes}", help="Minimum number of times a photon traverses the absorber layer before escaping. The CFRP recycling geometry ensures at least 3 passes, dramatically increasing absorption probability for weakly-absorbed near-bandgap photons.")
    bp9.metric("Test Pressure", f"{bp.test_pressure_Pa:.0f} Pa", help="Reference transverse load pressure for structural validation per IEC 61215. At 5400 Pa (equivalent to ~2 kPa snow + wind), the blueprint geometry is validated for all-climate rooftop deployment of the Granas module.")

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
