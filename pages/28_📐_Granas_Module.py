"""
Granas Module Dashboard — Production-Scale Power Scaling
=========================================================
Streamlit page for the 2.1m × 3.4m Granas module within
the PRIMEnergeia Sovereign Command Center.

Features:
  - Module specification KPIs
  - Power scaling: Home → Continent
  - Border-only blueprint visualization
  - Interactive: adjust PCE, CF, irradiance

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import numpy as np
import sys, os

# Ensure project root is on path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import plotly.graph_objects as go
except ImportError:
    st.error("pip install plotly")
    st.stop()

from granas_module.module_spec import GranasProductionModule
from granas_module.power_scaling import PowerScaling, SCALE_LEVELS
from granas_module.blueprint import create_blueprint

# ─── Grid Handshake ─────────────────────────────────────────
try:
    from lib.granas_handshake import verify_power_input, show_handshake_sidebar
    _hs = verify_power_input()
    _hs_available = True
except Exception:
    _hs_available = False

# ─── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .stApp { background: linear-gradient(145deg, #020608 0%, #0a1020 50%, #020608 100%); }
    .module-header {
        background: linear-gradient(90deg, rgba(0,255,100,0.10) 0%, rgba(0,209,255,0.08) 100%);
        border: 1px solid rgba(0,255,100,0.3);
        border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
    }
    .module-header h1 {
        background: linear-gradient(90deg, #00ff64, #00d1ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.2rem; font-weight: 700; margin: 0;
    }
    .module-header p { color: #c8d6e5; font-size: 1.05rem; margin: 0.3rem 0 0 0; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0f1a 0%, #020608 100%); }
    div[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    div[data-testid="stSidebar"] .stMarkdown h3,
    div[data-testid="stSidebar"] .stMarkdown h4 { color: #00ff64 !important; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
        border: 1px solid #1e2d4a; border-radius: 10px; padding: 18px 22px;
    }
    div[data-testid="stMetricValue"] {
        color: #00ff64; font-family: 'JetBrains Mono', monospace;
        font-size: 36px; font-weight: 700;
        text-shadow: 0 0 12px rgba(0,255,100,0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #c8d6e5; font-family: 'Inter', sans-serif; font-weight: 600;
        font-size: 13px; letter-spacing: 1px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"] { color: #c8d6e5; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #00ff64 !important; border-bottom-color: #00ff64 !important; }
    .stMarkdown, .stMarkdown p, .stMarkdown li { color: #e2e8f0 !important; }
    .stMarkdown h2, .stMarkdown h3 { color: #00ff64 !important; }
    .stMarkdown strong { color: #ffffff !important; }
    .stMarkdown code { color: #00d1ff !important; background: rgba(0,209,255,0.08); padding: 2px 6px; border-radius: 4px; }
    .stMarkdown table { border-collapse: collapse; width: 100%; }
    .stMarkdown th { color: #00ff64 !important; background: rgba(0,255,100,0.08); font-size: 14px; padding: 10px 14px; }
    .stMarkdown td { color: #e2e8f0 !important; font-size: 14px; padding: 8px 14px; border-bottom: 1px solid #1e2d4a; }
    .scale-card {
        background: linear-gradient(135deg, #0d1520, #111b2a);
        border: 1px solid #1e2d4a; border-radius: 12px;
        padding: 20px; margin: 8px 0;
    }
    .scale-card h4 { color: #00ff64; margin: 0 0 8px 0; font-size: 1.2rem; }
    .scale-card .number { color: #00d1ff; font-family: 'JetBrains Mono'; font-size: 1.8rem; font-weight: 700; }
    .scale-card .label { color: #94a3b8; font-size: 0.85rem; }

    .status-live {
        display: inline-block;
        background: rgba(0, 255, 136, 0.12);
        color: #00ff88;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 4px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="module-header">
    <h1>📐 Granas Module — 2.1m × 3.4m Production Scale</h1>
    <p>Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ / TOPCon Tandem &bull;
    100 Sub-cells &bull; CFRP Skeleton &bull; Green Reflectance Cooling
    &nbsp;&nbsp;<span class="status-live">● LIVE</span></p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Module Parameters")
    st.markdown("---")

    pce_adjust = st.slider("Tandem PCE (%)", 20.0, 42.0, 33.6, 0.1,
                            help="Total tandem PCE (perovskite + TOPCon)")
    capacity_factor = st.slider("Capacity Factor", 0.10, 0.35, 0.22, 0.01,
                                 help="Solar capacity factor (Mexico avg: 0.22)")
    irradiance = st.slider("Irradiance (W/m²)", 500, 1200, 1000, 50,
                            help="Operating irradiance (STC: 1000 W/m²)")

    st.markdown("---")
    st.markdown("#### 📐 Module Geometry")
    st.markdown(f"""
    | Parameter | Value |
    |-----------|-------|
    | Width | **2.1 m** |
    | Height | **3.4 m** |
    | Total Area | **7.14 m²** |
    | Active Area | **6.24 m²** |
    | Sub-cells | **100** (10×10) |
    | Config | **50S × 2P** |
    """)

    # Grid stabilizer sidebar
    if _hs_available:
        st.markdown("---")
        show_handshake_sidebar()

# ─── Compute Module ──────────────────────────────────────────
module = GranasProductionModule(
    capacity_factor=capacity_factor,
    irradiance_W_m2=float(irradiance),
)
# Override PCE if user adjusts
if abs(pce_adjust - module.tandem_pce_pct) > 0.1:
    module.tandem_pce_pct = pce_adjust
    module.perovskite_pce_pct = pce_adjust * 0.62  # ~62% from perovskite
    module.topcon_pce_pct = pce_adjust * 0.38       # ~38% from TOPCon
    module.peak_power_W = (pce_adjust / 100.0) * irradiance * module.active_area_m2
    # Recalculate Jsc from PCE
    cell_voc_V = module.cell_voc_mV / 1000.0
    g_mw = irradiance / 10.0
    module.cell_jsc_mA_cm2 = (pce_adjust / 100.0) * g_mw / (cell_voc_V * module.module_ff)
    module.cell_isc_A = module.cell_jsc_mA_cm2 * module.subcell_active_cm2 / 1000.0
    module.module_isc_A = module.n_parallel * module.cell_isc_A
    module.annual_energy_kWh = module.peak_power_W * capacity_factor * 8760 / 1000.0

scaling = PowerScaling(module)

# ═══════════════════════════════════════════════════════════
# TOP METRICS — 3 rows
# ═══════════════════════════════════════════════════════════
m1, m2, m3, m4 = st.columns(4)
m1.metric("⚡ Peak Power", f"{module.peak_power_W:,.0f} W")
m2.metric("🔋 Module Voc", f"{module.module_voc_V:.2f} V")
m3.metric("⚡ Module Isc", f"{module.module_isc_A:.1f} A")
m4.metric("📊 Tandem PCE", f"{module.tandem_pce_pct:.1f}%")

m5, m6, m7, m8 = st.columns(4)
m5.metric("🔬 Cell Voc", f"{module.cell_voc_mV:.0f} mV")
m6.metric("⚡ Cell Jsc", f"{module.cell_jsc_mA_cm2:.1f} mA/cm²")
m7.metric("📐 Active Area", f"{module.active_area_m2:.2f} m²")
m8.metric("🔋 Annual Energy", f"{module.annual_energy_kWh:,.0f} kWh")

m9, m10, m11, m12 = st.columns(4)
m9.metric("🌡️ Junction Temp", f"{module.junction_temp_C:.1f} °C")
m10.metric("⏱️ T80 Lifetime", f"{module.t80_years:.1f} yr")
m11.metric("🏗️ Weight", f"{module.weight_kg:.1f} kg")
m12.metric("🏠 Modules/Home", f"{int(np.ceil(10000/module.annual_energy_kWh))}")

# ═══════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "🌎 Power Scaling", "📐 Blueprint", "⚡ Module Spec", "📊 Analysis",
])

# ─── Tab 1: Power Scaling ────────────────────────────────────
with tab1:
    st.markdown("### 🌎 Granas Modules: Home → Continent")
    st.markdown(f"Each **2.1m × 3.4m** module produces "
                f"**{module.peak_power_W:,.0f} W** peak / "
                f"**{module.annual_energy_kWh:,.0f} kWh/year** "
                f"(CF={capacity_factor})")

    results = scaling.compute_all()

    for r in results:
        n = r.modules_needed
        if n < 1000:
            n_str = f"{n:,}"
        elif n < 1_000_000:
            n_str = f"{n/1000:,.1f}K"
        elif n < 1_000_000_000:
            n_str = f"{n/1_000_000:,.1f}M"
        else:
            n_str = f"{n/1_000_000_000:,.2f}B"

        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.markdown(f"""
            <div class="scale-card">
                <h4>{r.scale.emoji} {r.scale.name}</h4>
                <div class="number">{n_str}</div>
                <div class="label">modules needed</div>
            </div>
            """, unsafe_allow_html=True)

            if r.total_power_MW < 1:
                power_str = f"{r.total_power_MW*1000:.1f} kW"
            elif r.total_power_GW >= 1:
                power_str = f"{r.total_power_GW:,.1f} GW"
            else:
                power_str = f"{r.total_power_MW:,.1f} MW"

            c2.markdown(f"""
            <div class="scale-card">
                <h4>⚡ Installed Power</h4>
                <div class="number">{power_str}</div>
                <div class="label">peak capacity</div>
            </div>
            """, unsafe_allow_html=True)

            if r.total_area_km2 >= 1:
                area_str = f"{r.total_area_km2:,.1f} km²"
            elif r.total_area_m2 >= 10000:
                area_str = f"{r.total_area_ha:,.1f} ha"
            else:
                area_str = f"{r.total_area_m2:,.0f} m²"

            c3.markdown(f"""
            <div class="scale-card">
                <h4>📐 Total Area</h4>
                <div class="number">{area_str}</div>
                <div class="label">module footprint</div>
            </div>
            """, unsafe_allow_html=True)

            if r.scale.annual_kWh >= 1e9:
                cons_str = f"{r.scale.annual_kWh/1e9:,.0f} TWh/yr"
            elif r.scale.annual_kWh >= 1e6:
                cons_str = f"{r.scale.annual_kWh/1e6:,.0f} GWh/yr"
            else:
                cons_str = f"{r.scale.annual_kWh:,.0f} kWh/yr"

            c4.markdown(f"""
            <div class="scale-card">
                <h4>🔌 Consumption</h4>
                <div class="number">{cons_str}</div>
                <div class="label">{r.scale.reference}</div>
            </div>
            """, unsafe_allow_html=True)

    # Summary bar chart
    st.markdown("### 📊 Modules Needed (Log Scale)")
    fig_bar = go.Figure(go.Bar(
        x=[r.scale.name for r in results],
        y=[r.modules_needed for r in results],
        text=[f"{r.modules_needed:,.0f}" if r.modules_needed < 1e6
              else f"{r.modules_needed/1e6:.1f}M" for r in results],
        textposition="outside",
        marker=dict(
            color=["#00ff64", "#00d1ff", "#fbc02d", "#ff6b35", "#ff3b5c", "#a855f7"],
            line=dict(width=0),
        ),
        textfont=dict(color="#e2e8f0", size=12, family="JetBrains Mono"),
    ))
    fig_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020608", plot_bgcolor="#020608",
        yaxis_type="log",
        yaxis_title="Modules (log scale)",
        height=400,
        font=dict(family="Inter", color="#e2e8f0"),
        margin=dict(t=20),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ─── Tab 2: Blueprint ────────────────────────────────────────
with tab2:
    st.markdown("### 📐 Module Blueprint — Border Only")
    st.markdown("**2.1m × 3.4m** production module with CFRP skeleton tessellation. "
                "Green borders = module perimeter. Cyan = CFRP structural elements.")

    bp_col1, bp_col2 = st.columns([3, 1])
    with bp_col2:
        show_grid = st.checkbox("Sub-cell grid", True)
        show_cfrp = st.checkbox("CFRP skeleton", True)
        show_annot = st.checkbox("Annotations", True)

    with bp_col1:
        fig_bp = create_blueprint(
            show_annotations=show_annot,
            show_cfrp_skeleton=show_cfrp,
            show_subcell_grid=show_grid,
        )
        st.plotly_chart(fig_bp, use_container_width=True)

    st.markdown("### Edge Catalog")
    st.markdown("""
    | Type | Length | Count | Role |
    |------|--------|-------|------|
    | **Peripheral** | 5.5 units | 6 | Heavy load-bearing, anchoring triangles |
    | **Internal Rhombi** | 3.5 units | 8 | Stress distribution |
    | **Central Network** | 3.0 units | 12 | Precision crack-arrest vertices |
    """)

# ─── Tab 3: Module Spec ──────────────────────────────────────
with tab3:
    st.markdown("### ⚡ Full Module Specification")

    st.markdown("#### Geometry")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Width", f"{module.width_m} m")
    g2.metric("Height", f"{module.height_m} m")
    g3.metric("Total Area", f"{module.total_area_m2:.2f} m²")
    g4.metric("Active Area", f"{module.active_area_m2:.2f} m²")

    st.markdown("#### Cell Architecture")
    st.markdown(f"""
    | Parameter | Value |
    |-----------|-------|
    | Sub-cells | **{module.n_subcells}** (10 × 10 grid) |
    | Cell Size | **21 × 34 cm** (714 cm² total, 624 cm² active) |
    | Configuration | **{module.n_series}S × {module.n_parallel}P** |
    | Cell Voc | **{module.cell_voc_mV:.1f} mV** (1,100 base + {module.thermal.voc_gain_mV:.1f} green gain) |
    | Cell Jsc | **{module.cell_jsc_mA_cm2:.1f} mA/cm²** |
    | Cell Isc | **{module.cell_isc_A:.2f} A** |
    | Fill Factor | **{module.module_ff}** |
    """)

    st.markdown("#### Module Electrical")
    st.markdown(f"""
    | Parameter | Value | How |
    |-----------|-------|-----|
    | Module Voc | **{module.module_voc_V:.2f} V** | {module.n_series} × {module.cell_voc_mV:.1f} mV |
    | Module Isc | **{module.module_isc_A:.2f} A** | {module.n_parallel} × {module.cell_isc_A:.2f} A |
    | Peak Power | **{module.peak_power_W:,.1f} W** | PCE × G × A |
    | Annual Energy | **{module.annual_energy_kWh:,.1f} kWh** | P × CF × 8760h |
    """)

    st.markdown("#### Tandem Architecture")
    st.code(f"""
    ┌──────────────────────────────────┐
    │  ETFE Front Sheet (96% T)       │
    │  ─────────────────────────────── │
    │  Perovskite Top Cell            │
    │  Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃  │
    │  PCE: {module.perovskite_pce_pct:.1f}%                      │
    │  ─────────────────────────────── │
    │  TOPCon Silicon Bottom Cell     │
    │  n-type Cz, 180μm              │
    │  PCE: {module.topcon_pce_pct:.1f}%                      │
    │  ─────────────────────────────── │
    │  CFRP Skeleton (87.4% active)   │
    │  2.5 kg/m² (5× lighter)        │
    └──────────────────────────────────┘
    """, language=None)

# ─── Tab 4: Analysis ─────────────────────────────────────────
with tab4:
    st.markdown("### 📊 Sensitivity Analysis")

    # PCE vs Power
    pce_range = np.linspace(15, 42, 55)
    powers = [(p/100) * irradiance * module.active_area_m2 for p in pce_range]
    annuals = [pw * capacity_factor * 8760 / 1000 for pw in powers]
    homes = [10000 / a for a in annuals]

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x=pce_range, y=powers, name="Peak Power (W)",
        line=dict(color="#00ff64", width=3),
    ))
    fig_sens.add_vline(x=module.tandem_pce_pct, line_dash="dash",
                        line_color="#00d1ff",
                        annotation_text=f"Current: {module.tandem_pce_pct:.1f}%")
    fig_sens.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="Peak Power vs Tandem PCE",
        xaxis_title="Tandem PCE (%)", yaxis_title="Peak Power (W)",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_sens, use_container_width=True)

    # Modules per home vs CF
    cf_range = np.linspace(0.10, 0.35, 26)
    modules_home = [
        int(np.ceil(10000 / (module.peak_power_W * cf * 8760 / 1000)))
        for cf in cf_range
    ]

    fig_cf = go.Figure(go.Scatter(
        x=cf_range, y=modules_home, name="Modules per Home",
        line=dict(color="#00d1ff", width=3),
        fill="tozeroy", fillcolor="rgba(0,209,255,0.08)",
    ))
    fig_cf.add_vline(x=capacity_factor, line_dash="dash",
                      line_color="#00ff64",
                      annotation_text=f"CF={capacity_factor}")
    fig_cf.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020608", plot_bgcolor="#020608",
        title="Modules per Home vs Capacity Factor",
        xaxis_title="Capacity Factor", yaxis_title="Modules Needed",
        height=400, font=dict(family="Inter", color="#e2e8f0"),
    )
    st.plotly_chart(fig_cf, use_container_width=True)

# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;">
    PRIMEnergeia S.A.S. &bull; Granas Module 2.1m × 3.4m &bull;
    Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ / TOPCon Tandem &bull; Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
