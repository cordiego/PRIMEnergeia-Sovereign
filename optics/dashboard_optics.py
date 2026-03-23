"""
PRIMEnergeia — Granas Optics Dashboard
=======================================
Interactive Streamlit dashboard for optical simulation of
bio-mimetic granular photonic panels.

Mie Scattering | Transfer Matrix Method | AM1.5G Solar | E-field Maps

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import numpy as np
import pandas as pd
import os
import sys

# Add all possible paths where optics module might live
_this_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_this_dir)
for _p in [_project_root, _this_dir, os.getcwd(), os.path.dirname(os.getcwd())]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    st.error("Plotly required. Install with: pip install plotly")
    st.stop()

st.set_page_config(
    page_title="Granas Optics | Light-Trapping Simulator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Theme CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .stApp {
        background: linear-gradient(145deg, #050810 0%, #0a1628 50%, #050810 100%);
        font-family: 'Inter', sans-serif;
    }
    .optics-header {
        background: linear-gradient(90deg, rgba(138,43,226,0.12) 0%, rgba(0,209,255,0.08) 100%);
        border: 1px solid rgba(138,43,226,0.3);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
    }
    .optics-header h1 {
        background: linear-gradient(90deg, #8a2be2, #00d1ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem; font-weight: 700; margin: 0;
    }
    .optics-header p { color: #94a3b8; font-size: 1rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0f1a 0%, #050810 100%);
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 8px; padding: 16px 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #8a2be2; font-family: 'JetBrains Mono', monospace;
        font-size: 26px; font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #6b7fa3; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 500; }
    .stTabs [aria-selected="true"] {
        color: #8a2be2 !important; border-bottom-color: #8a2be2 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Import optics engine
# ─────────────────────────────────────────────────────────────
ENGINE_AVAILABLE = False
try:
    from optics.granas_optics import (
        MieScatterer, GranularMatrix, TransferMatrixSolver,
        SolarSpectrum, GranasEngine, MATERIAL_LIBRARY, MaterialData
    )
    ENGINE_AVAILABLE = True
except ImportError:
    pass

if not ENGINE_AVAILABLE:
    try:
        from granas_optics import (
            MieScatterer, GranularMatrix, TransferMatrixSolver,
            SolarSpectrum, GranasEngine, MATERIAL_LIBRARY, MaterialData
        )
        ENGINE_AVAILABLE = True
    except ImportError:
        pass

if not ENGINE_AVAILABLE:
    import importlib.util
    for _candidate in [
        os.path.join(_project_root, "optics", "granas_optics.py"),
        os.path.join(_this_dir, "granas_optics.py"),
        os.path.join(os.getcwd(), "optics", "granas_optics.py"),
    ]:
        if os.path.exists(_candidate):
            _spec = importlib.util.spec_from_file_location("granas_optics", _candidate)
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            MieScatterer = _mod.MieScatterer
            GranularMatrix = _mod.GranularMatrix
            TransferMatrixSolver = _mod.TransferMatrixSolver
            SolarSpectrum = _mod.SolarSpectrum
            GranasEngine = _mod.GranasEngine
            MATERIAL_LIBRARY = _mod.MATERIAL_LIBRARY
            MaterialData = _mod.MaterialData
            ENGINE_AVAILABLE = True
            break


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="optics-header">
    <h1>🔬 Granas Optics — Light-Trapping Simulator</h1>
    <p>Bio-mimetic granular photonic panel simulation &bull;
    Mie Scattering &bull; TMM &bull; AM1.5G &bull; Yablonovitch Limit</p>
</div>
""", unsafe_allow_html=True)


if not ENGINE_AVAILABLE:
    st.warning("⚠️ Optics engine not found. Copy `optics/` folder from Granas-Optics repo.")
    st.code("cp -r ~/Granas-Optics/optics/ ~/PRIMEnergeia-Sovereign/optics/")
    st.stop()


# ─────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────
if "optics_result" not in st.session_state:
    st.session_state.optics_result = None
if "optics_engine" not in st.session_state:
    st.session_state.optics_engine = None
if "optics_params" not in st.session_state:
    st.session_state.optics_params = {}


# ─────────────────────────────────────────────────────────────
# Sidebar — Controls
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔬 Simulation Controls")
    st.markdown("---")

    materials = list(MATERIAL_LIBRARY.keys())
    material = st.selectbox("Granule Material", materials, index=0)

    granule_radius = st.slider("Granule Radius (nm)", 50, 800, 250, step=25)

    domain_x = st.slider("Domain X (nm)", 500, 5000, 2000, step=250)
    domain_y = st.slider("Domain Y (nm)", 500, 5000, 2000, step=250)
    domain_z = st.slider("Domain Z (nm)", 200, 3000, 1000, step=100)

    min_spacing = st.slider("Min Spacing (nm)", 100, 800, 300, step=50)

    n_wavelengths = st.slider("Wavelength Points", 20, 200, 91, step=10)

    seed = st.number_input("Random Seed", min_value=0, max_value=99999, value=42)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        run_btn = st.button("▶ Simulate", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("🗑 Clear", use_container_width=True)

    if clear_btn:
        st.session_state.optics_result = None
        st.session_state.optics_engine = None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📐 Physics")
    st.markdown("""
    | Concept | |
    |---------|--|
    | **Mie Theory** | Q_ext, Q_sca, Q_abs |
    | **TMM** | R + T + A = 1 |
    | **AM1.5G** | 300-1200 nm |
    | **Yablonovitch** | 4n² limit |
    """)


# ─────────────────────────────────────────────────────────────
# Run Simulation
# ─────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("🔬 Running optical simulation..."):
        engine = GranasEngine(f"Dashboard_{material}")
        engine.domain_nm = (float(domain_x), float(domain_y), float(domain_z))
        engine.granule_radius_nm = float(granule_radius)
        engine.min_spacing_nm = float(min_spacing)
        engine.granule_material = material

        wl = np.linspace(300, 1200, n_wavelengths)
        engine.build_granular_matrix(
            density=0.7,
            radius_mean=float(granule_radius),
            radius_std=50.0,
            material=material,
            seed=seed,
        )
        result = engine.run_analysis(wl)
        st.session_state.optics_result = result
        st.session_state.optics_engine = engine
        st.session_state.optics_params = {
            "material": material,
            "granule_radius": granule_radius,
            "domain": (domain_x, domain_y, domain_z),
            "min_spacing": min_spacing,
        }
    st.toast("✅ Simulation Complete!", icon="🔬")


# ─────────────────────────────────────────────────────────────
# Main Content
# ─────────────────────────────────────────────────────────────
result = st.session_state.optics_result
engine = st.session_state.optics_engine
params = st.session_state.optics_params

if result is None:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <p style="font-size: 4rem; margin: 0;">🔬</p>
        <h2 style="color: #8a2be2; margin: 0.5rem 0;">Ready to Simulate</h2>
        <p style="color: #94a3b8; max-width: 600px; margin: 0.5rem auto;">
            Configure granule parameters in the sidebar and click <strong>▶ Simulate</strong>
            to run a full Mie + TMM optical simulation of the granular photonic panel.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─── Top Metrics ────────────────────────────────────────────
st.markdown("### 📊 Simulation Results")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🔆 Absorption", f"{result.weighted_absorption:.1f}%")
m2.metric("⚡ Jsc", f"{result.jsc_mA_cm2:.2f} mA/cm²")
m3.metric("🔄 Path Enh.", f"{result.path_length_enhancement:.1f}×")
m4.metric("🎯 4n² Limit", f"{result.yablonovitch_limit:.1f}×")
m5.metric("💡 LTE", f"{result.light_trapping_efficiency:.3f}")
m6.metric("🔵 Granules", f"{len(result.granule_positions)}")

st.markdown("")


# ─── Tabs ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Spectral Response", "⚡ E-field Map", "🎯 Mie Spectrum",
    "🔬 EQE / Jsc", "🔵 Granule Packing", "📊 Optimization Sweep"
])


# ─── Tab 1: Spectral Response (A, R, T) ─────────────────────
with tab1:
    fig_spec = go.Figure()
    wl = result.wavelengths_nm

    fig_spec.add_trace(go.Scatter(
        x=wl, y=result.absorptance * 100,
        mode="lines", name="Absorptance",
        line=dict(color="#8a2be2", width=3),
        fill="tozeroy", fillcolor="rgba(138,43,226,0.15)",
    ))
    fig_spec.add_trace(go.Scatter(
        x=wl, y=result.reflectance * 100,
        mode="lines", name="Reflectance",
        line=dict(color="#00d1ff", width=2),
    ))
    fig_spec.add_trace(go.Scatter(
        x=wl, y=result.transmittance * 100,
        mode="lines", name="Transmittance",
        line=dict(color="#ff6b35", width=2),
    ))

    fig_spec.update_layout(
        template="plotly_dark",
        paper_bgcolor="#050810", plot_bgcolor="#050810",
        title="Spectral Response — A / R / T",
        xaxis_title="Wavelength (nm)", yaxis_title="Fraction (%)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        height=500, legend=dict(x=0.75, y=0.95),
        yaxis=dict(range=[0, 105]),
    )
    st.plotly_chart(fig_spec, use_container_width=True)

    total = result.absorptance + result.reflectance + result.transmittance
    col_a, col_b = st.columns(2)
    col_a.metric("R + T + A (avg)", f"{total.mean():.4f}")
    col_b.metric("Conservation", "✅ PASS" if np.all(total < 1.05) else "⚠️ CHECK")


# ─── Tab 2: E-field Map ─────────────────────────────────────
with tab2:
    if result.efield_map is not None and result.efield_map.size > 0:
        fig_ef = go.Figure(go.Heatmap(
            z=result.efield_map,
            colorscale=[
                [0, "#050810"], [0.2, "#1a0a3e"], [0.4, "#8a2be2"],
                [0.6, "#ff6b35"], [0.8, "#ffd700"], [1.0, "#ffffff"],
            ],
            colorbar=dict(title="|E|²"),
        ))
        fig_ef.update_layout(
            template="plotly_dark",
            paper_bgcolor="#050810", plot_bgcolor="#050810",
            title="Near-Field |E|² Distribution (Cross-Section)",
            xaxis_title="X (grid units)", yaxis_title="Y (grid units)",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            height=550,
        )
        st.plotly_chart(fig_ef, use_container_width=True)

        emax = result.efield_map.max()
        eavg = result.efield_map.mean()
        c1, c2, c3 = st.columns(3)
        c1.metric("|E|² max", f"{emax:.3f}")
        c2.metric("|E|² mean", f"{eavg:.3f}")
        c3.metric("Enhancement", f"{emax/eavg:.1f}×" if eavg > 0 else "N/A")
    else:
        st.info("E-field map not available for this configuration.")


# ─── Tab 3: Mie Spectrum ────────────────────────────────────
with tab3:
    mat_data = MATERIAL_LIBRARY[params.get("material", "MAPbI3")]
    _radius = params.get("granule_radius", 250)
    wl_mie = np.linspace(300, 1200, 100)
    q_ext_arr, q_sca_arr, q_abs_arr, g_arr = [], [], [], []

    for w in wl_mie:
        # Interpolate n_complex at this wavelength
        n_real_interp = np.interp(w, mat_data.wavelengths_nm, mat_data.n_real)
        n_imag_interp = np.interp(w, mat_data.wavelengths_nm, mat_data.n_imag)
        n_complex = complex(n_real_interp, n_imag_interp)

        eff = MieScatterer.efficiencies(_radius, w, n_complex)
        q_ext_arr.append(eff["Q_ext"])
        q_sca_arr.append(eff["Q_sca"])
        q_abs_arr.append(eff["Q_abs"])
        g_arr.append(eff["g"])

    fig_mie = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            subplot_titles=["Mie Efficiencies", "Asymmetry Parameter g"],
                            vertical_spacing=0.12)

    fig_mie.add_trace(go.Scatter(x=wl_mie, y=q_ext_arr, name="Q_ext",
                                  line=dict(color="#8a2be2", width=3)), row=1, col=1)
    fig_mie.add_trace(go.Scatter(x=wl_mie, y=q_sca_arr, name="Q_sca",
                                  line=dict(color="#00d1ff", width=2)), row=1, col=1)
    fig_mie.add_trace(go.Scatter(x=wl_mie, y=q_abs_arr, name="Q_abs",
                                  line=dict(color="#ff6b35", width=2)), row=1, col=1)
    fig_mie.add_trace(go.Scatter(x=wl_mie, y=g_arr, name="g",
                                  line=dict(color="#00ff88", width=2),
                                  showlegend=False), row=2, col=1)

    fig_mie.update_layout(
        template="plotly_dark",
        paper_bgcolor="#050810", plot_bgcolor="#050810",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        height=600, legend=dict(x=0.75, y=0.95),
    )
    fig_mie.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)
    fig_mie.update_yaxes(title_text="Efficiency Q", row=1, col=1)
    fig_mie.update_yaxes(title_text="g", row=2, col=1)
    st.plotly_chart(fig_mie, use_container_width=True)

    x_500 = 2 * np.pi * _radius / 500
    st.metric("Size Parameter x (at 500nm)", f"{x_500:.2f}",
              help="x = 2πr/λ. Rayleigh: x<<1, Mie: x~1, Geometric: x>>1")


# ─── Tab 4: EQE / Jsc ───────────────────────────────────────
with tab4:
    eqe = np.clip(result.absorptance, 0, 1)

    fig_eqe = go.Figure()
    fig_eqe.add_trace(go.Scatter(
        x=wl, y=eqe * 100,
        mode="lines", name="EQE (ideal IQE=1)",
        line=dict(color="#00ff88", width=3),
        fill="tozeroy", fillcolor="rgba(0,255,136,0.1)",
    ))

    irr = SolarSpectrum.am15g_irradiance(wl)
    irr_norm = irr / irr.max() * 100
    fig_eqe.add_trace(go.Scatter(
        x=wl, y=irr_norm,
        mode="lines", name="AM1.5G (normalized)",
        line=dict(color="#ffd700", width=1.5, dash="dot"),
    ))

    fig_eqe.update_layout(
        template="plotly_dark",
        paper_bgcolor="#050810", plot_bgcolor="#050810",
        title="External Quantum Efficiency & AM1.5G Solar Spectrum",
        xaxis_title="Wavelength (nm)", yaxis_title="%",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        height=500, legend=dict(x=0.6, y=0.95),
    )
    st.plotly_chart(fig_eqe, use_container_width=True)

    jc1, jc2, jc3 = st.columns(3)
    jc1.metric("Jsc", f"{result.jsc_mA_cm2:.2f} mA/cm²")
    theoretical_max = 69.0
    jc2.metric("Jsc (theoretical max)", f"{theoretical_max:.0f} mA/cm²")
    jc3.metric("Jsc / Max", f"{result.jsc_mA_cm2/theoretical_max*100:.1f}%")


# ─── Tab 5: Granule Packing ─────────────────────────────────
with tab5:
    granules = result.granule_positions
    if granules:
        xs = [g.x for g in granules]
        ys = [g.y for g in granules]
        zs = [g.z for g in granules]
        rs = [g.radius_nm for g in granules]

        fig_pack = go.Figure(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="markers",
            marker=dict(
                size=[r/30 for r in rs], color=rs,
                colorscale=[[0, "#3b82f6"], [0.5, "#8a2be2"], [1, "#ff6b35"]],
                colorbar=dict(title="Radius (nm)"),
                opacity=0.8, line=dict(width=1, color="#050810"),
            ),
            hovertemplate="x: %{x:.0f} nm<br>y: %{y:.0f} nm<br>z: %{z:.0f} nm<extra></extra>",
        ))

        dom = params.get("domain", (2000, 2000, 1000))
        fig_pack.update_layout(
            template="plotly_dark",
            paper_bgcolor="#050810",
            scene=dict(
                xaxis=dict(title="X (nm)", backgroundcolor="#050810"),
                yaxis=dict(title="Y (nm)", backgroundcolor="#050810"),
                zaxis=dict(title="Z (nm)", backgroundcolor="#050810"),
            ),
            title=f"Poisson Disc 3D Packing — {len(granules)} Granules",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            height=600,
        )
        st.plotly_chart(fig_pack, use_container_width=True)

        density = GranularMatrix.packing_density(granules, dom)
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Granules", f"{len(granules)}")
        pc2.metric("Packing Density", f"{density:.3f}")
        pc3.metric("FCC Limit", "0.740")
    else:
        st.info("No granules packed.")


# ─── Tab 6: Optimization Sweep ──────────────────────────────
with tab6:
    st.markdown("### Radius × Density Optimization")
    st.markdown("Sweep granule radius and spacing to find optimal Jsc.")

    sweep_col1, sweep_col2 = st.columns(2)
    with sweep_col1:
        r_min = st.number_input("Radius min (nm)", value=100, step=50)
        r_max = st.number_input("Radius max (nm)", value=500, step=50)
        r_steps = st.slider("Radius steps", 3, 10, 5)
    with sweep_col2:
        s_min = st.number_input("Spacing min (nm)", value=200, step=50)
        s_max = st.number_input("Spacing max (nm)", value=600, step=50)
        s_steps = st.slider("Spacing steps", 3, 10, 4)

    sweep_btn = st.button("🔄 Run Sweep", type="primary")

    if sweep_btn:
        radii = np.linspace(r_min, r_max, r_steps)
        spacings = np.linspace(s_min, s_max, s_steps)
        jsc_map = np.zeros((len(radii), len(spacings)))
        abs_map = np.zeros((len(radii), len(spacings)))

        progress = st.progress(0)
        total_sims = len(radii) * len(spacings)
        count = 0

        _mat = params.get("material", "MAPbI3")
        _dom = params.get("domain", (2000, 2000, 1000))
        wl_sweep = np.linspace(300, 1200, 46)

        for i, r in enumerate(radii):
            for j, s in enumerate(spacings):
                eng = GranasEngine(f"sweep_r{r:.0f}_s{s:.0f}")
                eng.domain_nm = (float(_dom[0]), float(_dom[1]), float(_dom[2]))
                eng.granule_radius_nm = float(r)
                eng.min_spacing_nm = float(s)
                eng.granule_material = _mat
                eng.build_granular_matrix(
                    density=0.7, radius_mean=float(r),
                    radius_std=50.0, material=_mat, seed=42,
                )
                res = eng.run_analysis(wl_sweep)
                jsc_map[i, j] = res.jsc_mA_cm2
                abs_map[i, j] = res.weighted_absorption
                count += 1
                progress.progress(count / total_sims)

        progress.empty()

        fig_sweep = go.Figure(go.Heatmap(
            z=jsc_map,
            x=[f"{s:.0f}" for s in spacings],
            y=[f"{r:.0f}" for r in radii],
            colorscale=[[0, "#050810"], [0.3, "#1a0a3e"],
                        [0.6, "#8a2be2"], [0.8, "#ff6b35"], [1, "#ffd700"]],
            colorbar=dict(title="Jsc (mA/cm²)"),
            hovertemplate="Spacing: %{x} nm<br>Radius: %{y} nm<br>Jsc: %{z:.2f} mA/cm²<extra></extra>",
        ))
        fig_sweep.update_layout(
            template="plotly_dark",
            paper_bgcolor="#050810", plot_bgcolor="#050810",
            title="Jsc Optimization — Radius × Spacing",
            xaxis_title="Min Spacing (nm)", yaxis_title="Granule Radius (nm)",
            font=dict(family="Inter, sans-serif", color="#e2e8f0"),
            height=500,
        )
        st.plotly_chart(fig_sweep, use_container_width=True)

        best_idx = np.unravel_index(np.argmax(jsc_map), jsc_map.shape)
        best_r = radii[best_idx[0]]
        best_s = spacings[best_idx[1]]
        best_jsc = jsc_map[best_idx]
        best_abs = abs_map[best_idx]

        st.success(f"🏆 Optimal: r = {best_r:.0f} nm, spacing = {best_s:.0f} nm → "
                   f"Jsc = {best_jsc:.2f} mA/cm², Absorption = {best_abs:.1f}%")


# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Optics Engine &bull;
    Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
