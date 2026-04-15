"""PRIMEnergeia — Granas Fuel Hub | Solar → H₂ → NH₃ → Engine Pipeline Dashboard"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
try:
    from lib.granas_handshake import show_handshake_sidebar
    show_handshake_sidebar()
except Exception: pass
# --- End Banner ---

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── Import pipeline engine ──────────────────────────────────
_lib_engines = _os.path.join(_root, "lib", "engines")
if _lib_engines not in _sys.path:
    _sys.path.insert(0, _lib_engines)

from solar_fuel_pipeline import (
    GranasChargingHub,
    GranasStructureFeed,
    SolarElectrolyzer,
    HaberBoschReactor,
    ChargingMetrics,
    ENGINE_SPECS,
    LHV_H2,
    LHV_NH3,
    HOURS_PER_YEAR,
)

# ═══════════════════════════════════════════════════════════════
# Page Config & Styling
# ═══════════════════════════════════════════════════════════════
st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 24px !important}
[data-testid="stMetricLabel"] {font-size: 12px !important; font-weight: 600}
.block-container {padding-top: 1rem}
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {font-size: 14px}
</style>""", unsafe_allow_html=True)

st.header("⚡ Granas Fuel Hub — Solar → H₂ → NH₃ → Engines")
st.caption(
    "Granas 2.1×3.4m Module Array · PEM Electrolysis · Green Haber-Bosch · "
    "A-ICE-G1 / PEM-PB-50 / HY-P100 | PRIMEnergeia S.A.S."
)

# ═══════════════════════════════════════════════════════════════
# Sidebar Controls
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Charging Hub Configuration")

    n_modules = st.slider(
        "Granas Modules", 1, 10_000, 100, 1,
        help="Number of 2.1 × 3.4 m Granas perovskite/TOPCon tandem panels"
    )
    mode = st.selectbox(
        "Operating Mode",
        ["H₂ Only", "H₂ + NH₃", "Full Fleet"],
        index=1,
        help="H₂ Only: all H₂ to storage. H₂ + NH₃: split to Haber-Bosch. Full Fleet: balanced for all engines."
    )

    st.markdown("---")
    st.markdown("**Electrolyzer Stack**")
    n_cells = st.slider("PEM Cells", 20, 200, 80, 10,
                         help="Number of cells in PEM electrolysis stack")
    stack_temp = st.slider("Stack Temp (°C)", 50, 90, 80, 5)
    h2_pressure = st.slider("H₂ Pressure (bar)", 5, 50, 30, 5)
    solar_frac = st.slider("Solar → Electrolysis (%)", 20, 100, 80, 5,
                            help="Fraction of solar power directed to electrolysis (rest exported to grid)")

    st.markdown("---")
    st.markdown("**Solar Conditions**")
    irradiance = st.slider("Irradiance (W/m²)", 200, 1200, 1000, 50)
    cap_factor = st.slider("Capacity Factor", 0.10, 0.35, 0.22, 0.01,
                            help="Annual solar capacity factor. Mexico avg: 0.22")

# ═══════════════════════════════════════════════════════════════
# Build and Run Pipeline
# ═══════════════════════════════════════════════════════════════
module = GranasStructureFeed(
    irradiance_W_m2=irradiance,
    capacity_factor=cap_factor,
)

electrolyzer = SolarElectrolyzer(
    n_cells=n_cells,
    temperature_C=stack_temp,
    pressure_bar=h2_pressure,
)

hub = GranasChargingHub(
    n_modules=n_modules,
    module=module,
    electrolyzer=electrolyzer,
    mode=mode,
    solar_to_h2_fraction=solar_frac / 100.0,
)

# Run at full irradiance
irr_factor = irradiance / 1000.0
result = hub.run_pipeline(irradiance_factor=irr_factor)
metrics = ChargingMetrics.extract(result)

# ═══════════════════════════════════════════════════════════════
# Header KPI Row
# ═══════════════════════════════════════════════════════════════
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("☀️ Solar Capacity", f"{result['solar_peak_kW']:.1f} kW",
          help="Total peak DC output from all Granas modules at current irradiance")
k2.metric("💧 H₂ Rate", f"{result['h2_output_kg_h']:.2f} kg/h",
          help="Net hydrogen production rate available for engines/storage")
k3.metric("⚗️ NH₃ Rate", f"{result['nh3_output_kg_h']:.2f} kg/h",
          help="Ammonia production rate from Green Haber-Bosch reactor")
k4.metric("🎯 Solar→Fuel η", f"{result['overall_solar_to_fuel_pct']:.1f}%",
          help="Overall efficiency: solar irradiance → chemical energy in fuel")
k5.metric("🌍 CO₂", "ZERO",
          help="All fuel produced from solar + water + air. Zero fossil carbon.")
k6.metric("🚀 Engines Ready", f"{len(ENGINE_SPECS)}",
          help="A-ICE-G1 (NH₃), PEM-PB-50 (H₂), HY-P100 (H₂)")

st.divider()

# ═══════════════════════════════════════════════════════════════
# Granas Structure Panel
# ═══════════════════════════════════════════════════════════════
with st.expander("🔋 Granas Module Structure → Fuel Pipeline", expanded=True):
    gs = result["granas_structure"]

    struct_cols = st.columns([1, 1, 1])
    with struct_cols[0]:
        st.markdown("#### 📐 Module Blueprint")
        st.metric("Dimensions", gs["module_dimensions"],
                  help="Physical module footprint: 2.1m width × 3.4m height")
        st.metric("Active Area", f"{gs['active_area_m2']} m²",
                  help="87.4% of total area — CFRP skeleton takes 12.6%")
        st.metric("Sub-cells", f"{gs['n_subcells']} ({gs['tessellation']})",
                  help="100 tandem sub-cells in a 10×10 grid of 21×34 cm cells")
        st.metric("Configuration", gs["config"],
                  help="50 series × 2 parallel: Voc stacks in series, Isc doubles in parallel")
        st.metric("Weight", f"{gs['weight_kg']} kg",
                  help="CFRP structure: 5× lighter than glass-encapsulated panels")

    with struct_cols[1]:
        st.markdown("#### ⚡ Electrical Output")
        st.metric("Module Voc", f"{gs['module_voc_V']} V",
                  help="50 cells × 1.132 V/cell = open-circuit voltage")
        st.metric("Module Isc", f"{gs['module_isc_A']} A",
                  help="2 parallel strings: short-circuit current")
        st.metric("Peak Power", f"{gs['peak_power_W']} W",
                  help="Module output at STC (1000 W/m², 25°C)")
        st.metric("Tandem PCE", f"{gs['tandem_pce_pct']}%",
                  delta=f"Perovskite {gs['perovskite_pce_pct']}% + TOPCon {gs['topcon_pce_pct']}%",
                  help="Combined two-junction power conversion efficiency")
        st.metric("Junction Temp", f"{gs['junction_temp_C']}°C",
                  help="35% green reflectance cooling: Tj = 42°C vs 68°C control")

    with struct_cols[2]:
        st.markdown("#### 🏭 Charging Hub Field")
        st.metric("Total Modules", f"{n_modules:,}",
                  help="Granas 2.1×3.4m modules in the charging hub array")
        st.metric("Field Area", f"{result['field_area_ha']:.2f} ha",
                  help=f"{result['field_area_m2']:,.0f} m² total installation footprint")
        st.metric("Total Solar", f"{result['solar_peak_kW']:.1f} kW",
                  help="Combined peak DC capacity of all modules")
        st.metric("Annual Energy", f"{result['solar_annual_MWh']:.1f} MWh",
                  help=f"CF={cap_factor}, {cap_factor*HOURS_PER_YEAR:.0f} equivalent sun-hours/yr")
        st.metric("Grid Export", f"{result['grid_export_kW']:.1f} kW",
                  help="Solar power not used for electrolysis, exported to grid")

    # Module → Pipeline flow diagram (text-based)
    st.markdown("---")
    st.markdown(f"""
```
   ☀️ {irradiance} W/m²
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  🔋 GRANAS MODULE ARRAY  ({n_modules:,} × 2.1m × 3.4m)          │
│  {gs['tandem_pce_pct']}% PCE │ {gs['config']} │ {gs['peak_power_W']}W/module     │
│  Total: {result['solar_peak_kW']:.1f} kW DC                                  │
└────────────────────────┬────────────────────────────────┘
                         │ DC Bus ({result['solar_peak_kW']:.1f} kW)
        ┌────────────────┴────────────────┐
        │ {solar_frac}% to electrolysis              │ {100-solar_frac}% grid export
        ▼                                 ▼
┌──────────────────┐              ┌──────────────┐
│ 💧 PEM Stack     │              │ ⚡ Grid      │
│ {n_cells} cells, {stack_temp}°C │              │ {result['grid_export_kW']:.1f} kW     │
│ → {result['h2_output_kg_h']:.3f} kg H₂/h │              └──────────────┘
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│ H₂     │ │ ⚗️ Haber-Bosch│
│ Storage│ │ → {result['nh3_output_kg_h']:.3f} kg │
│ Tank   │ │   NH₃/h      │
└───┬────┘ └──────┬───────┘
    │             │
    ▼             ▼
┌────────────────────────────────────────────┐
│ 🚀 ENGINE FUEL DISPATCH                   │
│  PEM-PB-50 (H₂) │ HY-P100 (H₂) │ A-ICE (NH₃) │
└────────────────────────────────────────────┘
```
""")

st.divider()

# ═══════════════════════════════════════════════════════════════
# Tabs
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔋 Solar → Fuel Pipeline",
    "⚡ Charging Metrics",
    "🚀 Engine Fuel Readiness",
    "📊 Efficiency Waterfall",
    "📈 Scaling Analysis",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: Sankey Pipeline
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🔋 Energy Flow — Solar to Fuel")

    # Build Sankey diagram
    solar_kw = result["solar_peak_kW"]
    elec_kw = result["electrolyzer_input_kW"]
    grid_kw = result["grid_export_kW"]
    conv_loss = result["conversion_loss_kW"]
    h2_energy = result["h2_energy_kWh_h"]
    nh3_energy = result["nh3_energy_kWh_h"]
    elec_loss = elec_kw - h2_energy - nh3_energy if elec_kw > 0 else 0
    elec_loss = max(0, elec_loss)

    # Sankey nodes
    labels = [
        f"☀️ Solar\n{solar_kw:.1f} kW",              # 0
        f"⚡ DC Bus\n{solar_kw:.1f} kW",              # 1
        f"💧 Electrolyzer\n{elec_kw:.1f} kW",         # 2
        f"🔌 Grid Export\n{grid_kw:.1f} kW",          # 3
        f"🔥 Conv. Loss\n{conv_loss:.1f} kW",         # 4
        f"H₂ Fuel\n{h2_energy:.1f} kWh/h",            # 5
        f"NH₃ Fuel\n{nh3_energy:.1f} kWh/h",          # 6
        f"⚡ Elec. Loss\n{elec_loss:.1f} kW",         # 7
    ]

    # Sankey links: source → target → value
    source = [0, 1, 1, 1, 2, 2, 2]
    target = [1, 2, 3, 4, 5, 6, 7]
    value = [
        max(0.01, solar_kw),
        max(0.01, elec_kw),
        max(0.01, grid_kw),
        max(0.01, conv_loss),
        max(0.01, h2_energy),
        max(0.01, nh3_energy),
        max(0.01, elec_loss),
    ]
    colors = [
        "rgba(255,215,0,0.5)",     # Solar → DC
        "rgba(0,209,255,0.5)",     # DC → Electrolyzer
        "rgba(0,200,120,0.4)",     # DC → Grid
        "rgba(255,99,71,0.3)",     # DC → Loss
        "rgba(0,191,255,0.6)",     # Elec → H₂
        "rgba(123,104,238,0.5)",   # Elec → NH₃
        "rgba(200,80,80,0.3)",     # Elec → Loss
    ]

    fig_sankey = go.Figure(go.Sankey(
        node=dict(
            pad=20, thickness=25,
            label=labels,
            color=[
                "#FFD700",   # Solar
                "#00d1ff",   # DC Bus
                "#00BFFF",   # Electrolyzer
                "#00c878",   # Grid
                "#FF6347",   # Conv Loss
                "#00d1ff",   # H₂
                "#7B68EE",   # NH₃
                "#FF4444",   # Elec Loss
            ],
        ),
        link=dict(
            source=source, target=target, value=value,
            color=colors,
        ),
    ))
    fig_sankey.update_layout(
        title="Solar → Fuel Energy Flow (kW / kWh/h)",
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color="white"),
        margin=dict(t=50, b=30),
    )
    st.plotly_chart(fig_sankey, use_container_width=True)

    # 24-hour charging profile
    st.subheader("🕐 24-Hour Charging Profile")
    profile = hub.hourly_profile()
    hours = [p["hour"] for p in profile]
    solar_profile = [p["solar_kW"] for p in profile]
    elec_profile = [p["electrolyzer_kW"] for p in profile]
    h2_profile = [p["h2_kg_h"] for p in profile]
    nh3_profile = [p["nh3_kg_h"] for p in profile]

    fig_profile = make_subplots(specs=[[{"secondary_y": True}]])
    fig_profile.add_trace(go.Scatter(
        x=hours, y=solar_profile, name="Solar (kW)",
        fill="tozeroy", fillcolor="rgba(255,215,0,0.2)",
        line=dict(color="#FFD700", width=3),
    ), secondary_y=False)
    fig_profile.add_trace(go.Scatter(
        x=hours, y=elec_profile, name="Electrolyzer (kW)",
        line=dict(color="#00d1ff", width=2, dash="dot"),
    ), secondary_y=False)
    fig_profile.add_trace(go.Scatter(
        x=hours, y=h2_profile, name="H₂ (kg/h)",
        line=dict(color="#00BFFF", width=3),
    ), secondary_y=True)
    if mode != "H₂ Only":
        fig_profile.add_trace(go.Scatter(
            x=hours, y=nh3_profile, name="NH₃ (kg/h)",
            line=dict(color="#7B68EE", width=2),
        ), secondary_y=True)

    fig_profile.update_layout(
        template="plotly_dark", height=420,
        title="Daily Solar → Fuel Production Profile",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", y=-0.15),
    )
    fig_profile.update_xaxes(title_text="Hour of Day", dtick=2)
    fig_profile.update_yaxes(title_text="Power (kW)", secondary_y=False,
                              gridcolor="rgba(128,128,128,0.2)")
    fig_profile.update_yaxes(title_text="Fuel Rate (kg/h)", secondary_y=True)
    st.plotly_chart(fig_profile, use_container_width=True)

    # Daily totals
    total_h2_day = sum(h2_profile)
    total_nh3_day = sum(nh3_profile)
    total_solar_kwh = sum(solar_profile)
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("☀️ Solar Energy/Day", f"{total_solar_kwh:.0f} kWh")
    d2.metric("💧 H₂ / Day", f"{total_h2_day:.1f} kg")
    d3.metric("⚗️ NH₃ / Day", f"{total_nh3_day:.1f} kg")
    d4.metric("💡 Equiv. Homes", f"{total_solar_kwh * 365 / 10000:.0f}",
              help="Based on 10,000 kWh/yr per household")


# ═══════════════════════════════════════════════════════════════
# TAB 2: All Charging Metrics
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("⚡ Complete Charging Hub Metrics")
    st.caption("All metrics from the Granas solar-to-fuel pipeline exposed below")

    # ── Capacity Metrics ──────────────────────────────────────
    st.markdown("#### 📏 Capacity")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Solar Capacity", f"{metrics['solar_capacity_kW']:.1f} kW",
              help="Total peak DC output from Granas module array")
    c2.metric("Solar (MW)", f"{metrics['solar_capacity_MW']:.3f} MW",
              help="Same capacity in megawatts")
    c3.metric("Granas Modules", f"{metrics['n_granas_modules']:,}",
              help="Number of 2.1×3.4m tandem panels in array")
    c4.metric("Field Area", f"{metrics['field_area_ha']:.2f} ha",
              help=f"{metrics['field_area_m2']:,.0f} m² total installation footprint")
    c5.metric("Annual Solar", f"{metrics['annual_solar_MWh']:.1f} MWh",
              help="Estimated annual energy production at given capacity factor")

    # ── Electrolyzer Metrics ──────────────────────────────────
    st.markdown("#### 💧 Electrolyzer")
    e1, e2, e3, e4, e5 = st.columns(5)
    e1.metric("Input Power", f"{metrics['electrolyzer_input_kW']:.1f} kW",
              help="Electrical power delivered to PEM stack after conversion losses")
    e2.metric("Current Density", f"{metrics['current_density_A_cm2']:.2f} A/cm²",
              help="Operating current density on the polarization curve")
    e3.metric("Cell Voltage", f"{metrics['cell_voltage_V']:.3f} V",
              help="Single cell operating voltage (reversible + overpotentials)")
    e4.metric("Stack Cells", f"{metrics['electrolyzer_cells']}",
              help=f"PEM cells at {metrics['stack_temp_C']}°C, {metrics['h2_pressure_bar']} bar")
    e5.metric("kWh/kg H₂", f"{metrics['kwh_per_kg_h2']:.1f}",
              help="Specific energy consumption for hydrogen production")

    # ── Production Rate Metrics ───────────────────────────────
    st.markdown("#### 🏭 Production Rates")
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("H₂ Rate", f"{metrics['h2_rate_kg_h']:.3f} kg/h",
              help="Net hydrogen available for engines/storage after HB split")
    p2.metric("H₂/Day", f"{metrics['h2_rate_kg_day']:.1f} kg/day",
              help="24-hour hydrogen production (peak conditions)")
    p3.metric("NH₃ Rate", f"{metrics['nh3_rate_kg_h']:.3f} kg/h",
              help="Ammonia from Green Haber-Bosch reactor")
    p4.metric("H₂O Consumed", f"{metrics['h2o_consumption_kg_h']:.1f} kg/h",
              help="Deionized water feedstock: 9 kg H₂O per kg H₂")
    p5.metric("O₂ Co-product", f"{metrics['o2_coproduct_kg_h']:.2f} kg/h",
              help="Oxygen byproduct from water splitting (medical/industrial grade)")

    # ── Energy Metrics ────────────────────────────────────────
    st.markdown("#### ⚡ Energy Content")
    n1, n2, n3, n4, n5 = st.columns(5)
    n1.metric("H₂ Energy", f"{metrics['h2_energy_content_kWh_h']:.1f} kWh/h",
              help="Chemical energy content of H₂ output (LHV = 33.3 kWh/kg)")
    n2.metric("NH₃ Energy", f"{metrics['nh3_energy_content_kWh_h']:.1f} kWh/h",
              help="Chemical energy content of NH₃ output (LHV = 5.17 kWh/kg)")
    n3.metric("Total Fuel", f"{metrics['total_fuel_energy_kWh_h']:.1f} kWh/h",
              help="Combined chemical energy in all produced fuel")
    n4.metric("Grid Export", f"{metrics['grid_export_kW']:.1f} kW",
              help="Surplus solar power exported to electrical grid")
    n5.metric("Conv. Loss", f"{metrics['conversion_loss_kW']:.1f} kW",
              help="Power lost in DC-AC-DC conversion chain")

    # ── Efficiency Chain ──────────────────────────────────────
    st.markdown("#### 🎯 Efficiency Chain")
    ef1, ef2, ef3, ef4, ef5 = st.columns(5)
    ef1.metric("Solar→Wire", f"{metrics['solar_to_wire_eff_pct']:.1f}%",
               help="DC bus efficiency: inverter × rectifier × DC-DC = 93.8%")
    ef2.metric("Cell η", f"{metrics['cell_efficiency_pct']:.1f}%",
               help="Electrochemical cell voltage efficiency (thermoneutral / operating)")
    ef3.metric("System η", f"{metrics['system_efficiency_pct']:.1f}%",
               help="Cell efficiency × balance-of-plant (92%)")
    ef4.metric("H-B η", f"{metrics['hb_conversion_eff_pct']:.1f}%",
               help="Haber-Bosch H₂→NH₃ energy conversion efficiency")
    ef5.metric("Solar→Fuel", f"{metrics['overall_solar_to_fuel_pct']:.1f}%",
               help="End-to-end: sunlight → chemical fuel energy")

    # ── Storage Metrics ───────────────────────────────────────
    st.markdown("#### 🛢️ Storage")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("H₂ Tank", f"{metrics['h2_tank_capacity_kg']:.0f} kg",
              help="Hydrogen storage capacity at 350 bar")
    s2.metric("H₂ Fill Time", f"{metrics['h2_fill_time_h']:.1f} h",
              help="Time to fill H₂ tank from empty at current production rate")
    s3.metric("NH₃ Tank", f"{metrics['nh3_tank_capacity_kg']:,.0f} kg",
              help="Ammonia storage at 10 bar (liquid)")
    s4.metric("NH₃ Fill Time", f"{metrics['nh3_fill_time_h']:.1f} h",
              help="Time to fill NH₃ tank at current production rate")
    s5.metric("CO₂ Avoided", f"{metrics['co2_avoided_vs_smr_kg_h']:.1f} kg/h",
              help="CO₂ saved vs steam methane reforming (9.3 kg CO₂/kg H₂)")

    # ── Gauges ────────────────────────────────────────────────
    st.markdown("#### 📊 Operating Gauges")
    g1, g2, g3 = st.columns(3)

    with g1:
        fig_g1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=metrics["current_density_A_cm2"],
            title={"text": "Current Density (A/cm²)", "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, 4.0], "tickwidth": 1},
                "bar": {"color": "#00d1ff"},
                "steps": [
                    {"range": [0, 1.5], "color": "rgba(0,200,120,0.15)"},
                    {"range": [1.5, 3.0], "color": "rgba(255,215,0,0.15)"},
                    {"range": [3.0, 4.0], "color": "rgba(255,99,71,0.15)"},
                ],
                "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.8, "value": 3.5},
            },
        ))
        fig_g1.update_layout(height=250, margin=dict(t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g1, use_container_width=True)

    with g2:
        h2_fill_pct = min(100, (result["h2_output_kg_h"] * 24 / max(metrics["h2_tank_capacity_kg"], 1)) * 100)
        fig_g2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=h2_fill_pct,
            title={"text": "H₂ Tank (% fill/day)", "font": {"size": 13}},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00BFFF"},
                "steps": [
                    {"range": [0, 50], "color": "rgba(255,99,71,0.1)"},
                    {"range": [50, 80], "color": "rgba(255,215,0,0.1)"},
                    {"range": [80, 100], "color": "rgba(0,200,120,0.1)"},
                ],
            },
        ))
        fig_g2.update_layout(height=250, margin=dict(t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g2, use_container_width=True)

    with g3:
        nh3_fill_pct = min(100, (result["nh3_output_kg_h"] * 24 / max(metrics["nh3_tank_capacity_kg"], 1)) * 100)
        fig_g3 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=nh3_fill_pct,
            title={"text": "NH₃ Tank (% fill/day)", "font": {"size": 13}},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#7B68EE"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(255,99,71,0.1)"},
                    {"range": [30, 70], "color": "rgba(255,215,0,0.1)"},
                    {"range": [70, 100], "color": "rgba(0,200,120,0.1)"},
                ],
            },
        ))
        fig_g3.update_layout(height=250, margin=dict(t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g3, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3: Engine Fuel Readiness
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🚀 Engine Fuel Readiness — How Fast Each Engine Gets Fueled")
    st.caption("Based on current Granas charging hub production rates")

    # Engine cards
    for name, eng in result["engines"].items():
        spec = ENGINE_SPECS[name]
        fuel_color = "#7B68EE" if eng["fuel_type"] == "NH₃" else "#00BFFF"
        fuel_emoji = "⚗️" if eng["fuel_type"] == "NH₃" else "💧"

        with st.container():
            st.markdown(f"### {fuel_emoji} {eng['engine']} — {eng['model']}")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Fuel Type", eng["fuel_type"],
                      help=f"{'Ammonia for combustion' if eng['fuel_type'] == 'NH₃' else 'Hydrogen for fuel cell/turbine'}")
            m2.metric("Rated Power", f"{eng['rated_power_kW']:.0f} kW",
                      help=f"Engine rated output at full load")
            m3.metric("Fuel @ Rated", f"{eng['fuel_rate_rated_kg_h']:.2f} kg/h",
                      help=f"Fuel consumption at rated power ({spec.thermal_efficiency*100:.0f}% η)")
            m4.metric("Fuel Available", f"{eng['fuel_available_kg_h']:.3f} kg/h",
                      help="Current production rate from charging hub")
            m5.metric("Tank Fill", f"{eng['fill_time_h']:.1f} h",
                      help=f"Time to fill {eng['tank_capacity_kg']:.0f} kg tank from empty")
            m6.metric("Runtime/Day", f"{eng['runtime_from_1day_charge_h']:.1f} h",
                      help="Hours of rated-power operation from 1 full day of charging")

            # Fuel supply vs demand bar
            supply = eng["fuel_available_kg_h"]
            demand = eng["fuel_rate_rated_kg_h"]
            coverage = min(100, (supply / max(demand, 1e-10)) * 100)

            st.progress(min(1.0, coverage / 100), text=f"Fuel Coverage: {coverage:.1f}% of rated demand")
            st.markdown(f"*Sectors: {eng['sectors']} | TRL: {eng['trl']}*")
            st.markdown("---")

    # Comparison bar chart
    engines = list(result["engines"].keys())
    runtimes = [result["engines"][e]["runtime_from_1day_charge_h"] for e in engines]
    fill_times = [result["engines"][e]["fill_time_h"] for e in engines]
    fuel_types = [result["engines"][e]["fuel_type"] for e in engines]

    fig_eng = make_subplots(rows=1, cols=2,
                             subplot_titles=["Runtime from 1 Day Charging (h)", "Tank Fill Time (h)"])

    colors = ["#7B68EE" if f == "NH₃" else "#00BFFF" for f in fuel_types]
    fig_eng.add_trace(go.Bar(x=engines, y=runtimes, marker_color=colors,
                              text=[f"{r:.1f}h" for r in runtimes], textposition="auto",
                              name="Runtime"), row=1, col=1)
    fig_eng.add_trace(go.Bar(x=engines, y=fill_times, marker_color=colors,
                              text=[f"{f:.1f}h" for f in fill_times], textposition="auto",
                              name="Fill Time"), row=1, col=2)
    fig_eng.update_layout(template="plotly_dark", height=380, showlegend=False,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font=dict(size=13))
    st.plotly_chart(fig_eng, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 4: Efficiency Waterfall
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📊 Efficiency Waterfall — Loss Breakdown")

    # Calculate stage-by-stage losses
    stages = ["Solar Input", "PV Conversion", "DC Bus", "Electrolyzer", "Compression", "H₂ Fuel"]
    pv_eff = module.tandem_pce_pct / 100
    wire_eff = hub.wire_efficiency()
    elec_eff = result["electrolysis"]["system_efficiency_pct"] / 100 if result["electrolysis"]["system_efficiency_pct"] > 0 else 0.70
    comp_eff = hub.compression_efficiency

    # Waterfall values (start at irradiance, multiply through)
    irr = irradiance  # W/m² input
    after_pv = irr * pv_eff
    after_dc = after_pv * wire_eff
    after_elec = after_dc * elec_eff
    after_comp = after_elec * comp_eff

    # Losses at each stage
    measures = ["absolute", "relative", "relative", "relative", "relative", "total"]
    values = [
        irr,                           # Solar Input (base)
        -(irr - after_pv),             # PV loss
        -(after_pv - after_dc),        # DC bus loss
        -(after_dc - after_elec),      # Electrolyzer loss
        -(after_elec - after_comp),    # Compression loss
        0,                             # Total (auto)
    ]

    fig_wf = go.Figure(go.Waterfall(
        x=stages, y=values,
        measure=measures,
        text=[f"{abs(v):.1f} W/m²" for v in values],
        textposition="outside",
        connector=dict(line=dict(color="#444")),
        increasing=dict(marker=dict(color="#FFD700")),
        decreasing=dict(marker=dict(color="#FF6347")),
        totals=dict(marker=dict(color="#00c878")),
    ))
    fig_wf.update_layout(
        template="plotly_dark", height=480,
        title="Energy Conversion Losses (per m² of module)",
        yaxis_title="Effective Power (W/m²)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Comparison table
    st.markdown("#### 🔄 Granas Green Fuel vs Conventional")
    st.markdown(f"""
| Metric | Granas Solar→Fuel | Steam Methane Reform | Haber-Bosch (Industrial) |
|--------|:-:|:-:|:-:|
| **Source** | Solar + Water + Air | Natural Gas | Natural Gas + N₂ |
| **CO₂/kg H₂** | **0 kg** | 9.3 kg | — |
| **CO₂/kg NH₃** | **0 kg** | — | 1.6 kg |
| **Energy (kWh/kg H₂)** | {metrics['kwh_per_kg_h2']:.1f} | 58 | — |
| **Temperature** | {stack_temp}°C | 850°C | 450°C |
| **Pressure** | {h2_pressure} bar | 25 bar | 200 bar |
| **Scaling** | Modular ({n_modules} modules) | Centralized | Centralized |
| **Feedstock** | H₂O + sunlight | CH₄ | H₂ + N₂ |
| **Renewable** | ✅ 100% | ❌ Fossil | ❌ Fossil |
""")

    # Efficiency bars
    eff_labels = ["Solar→Wire", "PEM Cell", "PEM System", "H-B Conv.", "Overall"]
    eff_values = [
        metrics["solar_to_wire_eff_pct"],
        metrics["cell_efficiency_pct"],
        metrics["system_efficiency_pct"],
        metrics["hb_conversion_eff_pct"],
        metrics["overall_solar_to_fuel_pct"],
    ]
    eff_colors = ["#FFD700", "#00d1ff", "#00BFFF", "#7B68EE", "#00c878"]

    fig_eff = go.Figure(go.Bar(
        x=eff_labels, y=eff_values,
        marker_color=eff_colors,
        text=[f"{v:.1f}%" for v in eff_values],
        textposition="auto",
    ))
    fig_eff.update_layout(
        template="plotly_dark", height=350,
        title="Stage-by-Stage Efficiency",
        yaxis_title="Efficiency (%)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    st.plotly_chart(fig_eff, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 5: Scaling Analysis
# ═══════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📈 Scaling Analysis — Modules vs Production")

    scaling = hub.scaling_analysis()
    n_arr = [s["n_modules"] for s in scaling]
    h2_arr = [s["h2_kg_day"] for s in scaling]
    nh3_arr = [s["nh3_kg_day"] for s in scaling]
    mw_arr = [s["solar_MW"] for s in scaling]
    area_arr = [s["area_ha"] for s in scaling]

    # Production vs module count
    fig_scale = make_subplots(specs=[[{"secondary_y": True}]])
    fig_scale.add_trace(go.Scatter(
        x=n_arr, y=h2_arr, name="H₂ (kg/day)",
        line=dict(color="#00BFFF", width=3),
        fill="tozeroy", fillcolor="rgba(0,191,255,0.1)",
    ), secondary_y=False)
    if mode != "H₂ Only":
        fig_scale.add_trace(go.Scatter(
            x=n_arr, y=nh3_arr, name="NH₃ (kg/day)",
            line=dict(color="#7B68EE", width=3),
            fill="tozeroy", fillcolor="rgba(123,104,238,0.1)",
        ), secondary_y=False)
    fig_scale.add_trace(go.Scatter(
        x=n_arr, y=mw_arr, name="Solar (MW)",
        line=dict(color="#FFD700", width=2, dash="dot"),
    ), secondary_y=True)
    fig_scale.update_layout(
        template="plotly_dark", height=450,
        title="Fuel Production vs Granas Module Count",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
    )
    fig_scale.update_xaxes(title_text="Number of Granas Modules", type="log")
    fig_scale.update_yaxes(title_text="Fuel Production (kg/day)", secondary_y=False,
                            gridcolor="rgba(128,128,128,0.2)")
    fig_scale.update_yaxes(title_text="Solar Capacity (MW)", secondary_y=True)
    st.plotly_chart(fig_scale, use_container_width=True)

    # Engine runtime vs module count
    aice_rt = [s["aice_runtime_h_day"] for s in scaling]
    pem_rt = [s["pem_runtime_h_day"] for s in scaling]
    hyp_rt = [s["hyp_runtime_h_day"] for s in scaling]

    fig_rt = go.Figure()
    fig_rt.add_trace(go.Scatter(x=n_arr, y=aice_rt, name="A-ICE-G1 (NH₃)",
                                 line=dict(color="#00c878", width=3)))
    fig_rt.add_trace(go.Scatter(x=n_arr, y=pem_rt, name="PEM-PB-50 (H₂)",
                                 line=dict(color="#00BFFF", width=3)))
    fig_rt.add_trace(go.Scatter(x=n_arr, y=hyp_rt, name="HY-P100 (H₂)",
                                 line=dict(color="#FFD700", width=3)))
    fig_rt.add_hline(y=24, line_dash="dash", line_color="rgba(255,255,255,0.4)",
                     annotation_text="24h = Continuous Operation")
    fig_rt.update_layout(
        template="plotly_dark", height=420,
        title="Engine Runtime from 1 Day of Charging vs Module Count",
        xaxis_title="Number of Granas Modules",
        yaxis_title="Runtime (hours/day of charging)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    fig_rt.update_xaxes(type="log")
    st.plotly_chart(fig_rt, use_container_width=True)

    # Break-even table
    st.markdown("#### 🎯 Modules for Continuous Engine Operation")
    st.caption("Number of Granas modules needed to fuel each engine 24/7")

    # Find break-even (where runtime > 24h)
    for eng_name in ["A-ICE-G1", "PEM-PB-50", "HY-P100"]:
        rt_key = {"A-ICE-G1": "aice_runtime_h_day", "PEM-PB-50": "pem_runtime_h_day", "HY-P100": "hyp_runtime_h_day"}[eng_name]
        for s in scaling:
            if s[rt_key] >= 24:
                st.success(f"**{eng_name}**: {s['n_modules']:,} modules ({s['solar_MW']:.1f} MW, {s['area_ha']:.2f} ha) → 24/7 operation")
                break
        else:
            st.warning(f"**{eng_name}**: >10,000 modules needed for 24/7 operation")

    # Area comparison
    st.markdown("---")
    st.markdown("#### 📐 Scale Reference")
    st.markdown(f"""
| Scale | Modules | Solar (MW) | Area (ha) | H₂ (kg/day) | NH₃ (kg/day) |
|-------|---------|-----------|-----------|-------------|-------------|
""" + "\n".join([
        f"| {'🏠' if s['n_modules']<=5 else '🏘️' if s['n_modules']<=50 else '🏙️' if s['n_modules']<=500 else '🏭'} "
        f"{s['n_modules']:,} | {s['solar_MW']:.2f} | {s['area_ha']:.3f} | {s['h2_kg_day']:.1f} | {s['nh3_kg_day']:.1f} |"
        for s in scaling
    ]))


# ═══════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════
st.divider()
st.caption(
    "PRIMEnergeia S.A.S. — Granas Fuel Hub Division | "
    "Solar → H₂ → NH₃ → Zero-Carbon Propulsion for Every Application"
)
