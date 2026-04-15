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
# Use importlib to load directly (avoids __init__.py package conflict)
import importlib.util as _ilu
_pipeline_path = _os.path.join(_root, "lib", "engines", "solar_fuel_pipeline.py")
_spec = _ilu.spec_from_file_location("solar_fuel_pipeline", _pipeline_path)
_sfp = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_sfp)

GranasChargingHub = _sfp.GranasChargingHub
GranasStructureFeed = _sfp.GranasStructureFeed
SolarElectrolyzer = _sfp.SolarElectrolyzer
HaberBoschReactor = _sfp.HaberBoschReactor
ChargingMetrics = _sfp.ChargingMetrics
ENGINE_SPECS = _sfp.ENGINE_SPECS
LHV_H2 = _sfp.LHV_H2
LHV_NH3 = _sfp.LHV_NH3
HOURS_PER_YEAR = _sfp.HOURS_PER_YEAR
VEHICLE_FLEET = _sfp.VEHICLE_FLEET
PEM_TRANSPORT_FLEET = _sfp.PEM_TRANSPORT_FLEET

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
tab1, tab_dn, tab_vf, tab_pem, tab2, tab3, tab4, tab5 = st.tabs([
    "🔋 Solar → Fuel Pipeline",
    "🌗 Day/Night Cycle",
    "🚀 Vehicle Fleet",
    "🔌 PEM Transport",
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
# TAB DAY/NIGHT: Solar Charging → Tank Buffer → Nighttime Mobility
# ═══════════════════════════════════════════════════════════════
with tab_dn:
    st.subheader("🌗 Day/Night Ecosystem — Solar Charges, Engines Move")
    st.caption(
        "☀️ DAY (06–18h): Granas panels produce fuel, tanks fill  ·  "
        "🌙 NIGHT (18–06h): Engines consume stored fuel for mobility"
    )

    # Controls for day/night cycle
    dn_c1, dn_c2, dn_c3, dn_c4 = st.columns(4)
    with dn_c1:
        dn_load = st.slider("Night Engine Load (%)", 25, 100, 75, 5,
                             key="dn_load",
                             help="Engine load during nighttime operation")
    with dn_c2:
        n_aice = st.number_input("A-ICE-G1 (NH₃)", 0, 10, 1, key="n_aice",
                                  help="Number of ammonia engines active at night")
    with dn_c3:
        n_pem = st.number_input("PEM-PB-50 (H₂)", 0, 10, 1, key="n_pem",
                                 help="Number of fuel cells active at night")
    with dn_c4:
        n_hyp = st.number_input("HY-P100 (H₂)", 0, 10, 1, key="n_hyp",
                                 help="Number of H₂ turbines active at night")

    # Run cycle simulation
    cycle = hub.day_night_cycle(
        engine_load_pct=dn_load,
        engines_active={"A-ICE-G1": n_aice, "PEM-PB-50": n_pem, "HY-P100": n_hyp},
    )

    # ── KPI summary from cycle ────────────────────────────────
    final = cycle[-1]
    peak_h2_soc = max(c["h2_tank_soc_pct"] for c in cycle)
    peak_nh3_soc = max(c["nh3_tank_soc_pct"] for c in cycle)
    total_km = sum(final["cumulative_km"].values())
    total_kWh_delivered = sum(final["cumulative_kWh"].values())

    dk1, dk2, dk3, dk4, dk5, dk6 = st.columns(6)
    dk1.metric("☀️ Day Hours", "12 h", help="Solar charging window: 06:00–18:00")
    dk2.metric("🌙 Night Hours", "12 h", help="Engine mobility window: 18:00–06:00")
    dk3.metric("⛽ Peak H₂ SOC", f"{peak_h2_soc:.1f}%", help="Maximum H₂ tank level reached during day")
    dk4.metric("⛽ Peak NH₃ SOC", f"{peak_nh3_soc:.1f}%", help="Maximum NH₃ tank level reached during day")
    dk5.metric("🛣️ Total km", f"{total_km:.0f}", help="Combined distance across all engines (night)")
    dk6.metric("⚡ Energy Delivered", f"{total_kWh_delivered:.0f} kWh",
              help="Total mechanical/electrical energy delivered by engines")

    st.divider()

    # ── Tank SOC + Solar/Engine Power chart ────────────────────
    hours = [c["hour"] for c in cycle]
    h2_soc = [c["h2_tank_soc_pct"] for c in cycle]
    nh3_soc = [c["nh3_tank_soc_pct"] for c in cycle]
    solar_arr = [c["solar_kW"] for c in cycle]

    # Engine power consumed per hour
    eng_power = []
    for c in cycle:
        total_p = sum(e["power_delivered_kW"] for e in c["engines"].values())
        eng_power.append(total_p)

    fig_dn = make_subplots(specs=[[{"secondary_y": True}]])

    # Day/night background shading
    fig_dn.add_vrect(x0=0, x1=6, fillcolor="rgba(30,30,80,0.3)",
                     line_width=0, annotation_text="🌙 Night", annotation_position="top left")
    fig_dn.add_vrect(x0=6, x1=18, fillcolor="rgba(255,215,0,0.08)",
                     line_width=0, annotation_text="☀️ Day", annotation_position="top left")
    fig_dn.add_vrect(x0=18, x1=23, fillcolor="rgba(30,30,80,0.3)",
                     line_width=0, annotation_text="🌙 Night", annotation_position="top left")

    # Tank SOC (primary y)
    fig_dn.add_trace(go.Scatter(
        x=hours, y=h2_soc, name="H₂ Tank SOC (%)",
        line=dict(color="#00BFFF", width=3),
        fill="tozeroy", fillcolor="rgba(0,191,255,0.1)",
    ), secondary_y=False)
    fig_dn.add_trace(go.Scatter(
        x=hours, y=nh3_soc, name="NH₃ Tank SOC (%)",
        line=dict(color="#7B68EE", width=3),
        fill="tozeroy", fillcolor="rgba(123,104,238,0.1)",
    ), secondary_y=False)

    # Solar production + engine consumption (secondary y)
    fig_dn.add_trace(go.Scatter(
        x=hours, y=solar_arr, name="☀️ Solar (kW)",
        line=dict(color="#FFD700", width=2, dash="dot"),
    ), secondary_y=True)
    fig_dn.add_trace(go.Bar(
        x=hours, y=[-p for p in eng_power], name="🚀 Engine Draw (kW)",
        marker_color="rgba(255,99,71,0.6)",
    ), secondary_y=True)

    fig_dn.update_layout(
        template="plotly_dark", height=500,
        title="24-Hour Day/Night Cycle — Tank SOC & Power Flows",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", y=-0.18),
        barmode="relative",
    )
    fig_dn.update_xaxes(title_text="Hour of Day", dtick=2,
                         gridcolor="rgba(128,128,128,0.2)")
    fig_dn.update_yaxes(title_text="Tank SOC (%)", range=[0, 105],
                         secondary_y=False, gridcolor="rgba(128,128,128,0.2)")
    fig_dn.update_yaxes(title_text="Power (kW)", secondary_y=True)
    st.plotly_chart(fig_dn, use_container_width=True)

    # ── Cumulative mobility chart ─────────────────────────────
    st.subheader("🛣️ Nighttime Mobility — Cumulative Distance")

    fig_km = go.Figure()
    for eng_name, color in [("A-ICE-G1", "#00c878"), ("PEM-PB-50", "#00BFFF"), ("HY-P100", "#FFD700")]:
        km_arr = [c["cumulative_km"][eng_name] for c in cycle]
        fig_km.add_trace(go.Scatter(
            x=hours, y=km_arr, name=eng_name,
            line=dict(color=color, width=3),
        ))
    fig_km.add_vrect(x0=6, x1=18, fillcolor="rgba(255,215,0,0.05)", line_width=0)
    fig_km.add_vrect(x0=0, x1=6, fillcolor="rgba(30,30,80,0.15)", line_width=0)
    fig_km.add_vrect(x0=18, x1=23, fillcolor="rgba(30,30,80,0.15)", line_width=0)
    fig_km.update_layout(
        template="plotly_dark", height=380,
        title="Cumulative Distance by Engine (km)",
        xaxis_title="Hour of Day", yaxis_title="Cumulative km",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    fig_km.update_xaxes(dtick=2)
    st.plotly_chart(fig_km, use_container_width=True)

    # ── Per-engine night results ──────────────────────────────
    st.subheader("🚀 Night Operation Summary")
    for eng_name in ["A-ICE-G1", "PEM-PB-50", "HY-P100"]:
        spec = ENGINE_SPECS[eng_name]
        km = final["cumulative_km"][eng_name]
        kwh = final["cumulative_kWh"][eng_name]
        fuel_used = final["cumulative_fuel_kg"][eng_name]

        # Find last status
        last_status = "⏸️ Standby"
        for c in reversed(cycle):
            if not c["is_day"]:
                last_status = c["engines"][eng_name]["status"]
                break

        r1, r2, r3, r4, r5 = st.columns(5)
        fuel_emoji = "⚗️" if spec.fuel_type == "NH₃" else "💧"
        r1.metric(f"{fuel_emoji} {eng_name}", last_status)
        r2.metric("Fuel Used", f"{fuel_used:.2f} kg {spec.fuel_type}")
        r3.metric("Energy", f"{kwh:.0f} kWh")
        r4.metric("Distance", f"{km:.0f} km")
        r5.metric("Efficiency", f"{km / max(fuel_used, 0.01):.1f} km/kg")

    # Ecosystem diagram
    st.markdown("---")
    st.markdown(f"""
### 🔄 The Granas Ecosystem
```
      ☀️ DAYTIME (06:00 – 18:00)                    🌙 NIGHTTIME (18:00 – 06:00)
┌───────────────────────────────────┐      ┌────────────────────────────────────────┐
│                                   │      │                                        │
│  🔋 Granas Modules ({n_modules:,}×)        │      │  🚀 ENGINES consume stored fuel:       │
│      ↓ {result['solar_peak_kW']:.0f} kW solar             │      │                                        │
│  💧 PEM Electrolyzer              │      │  A-ICE-G1: {final['cumulative_fuel_kg']['A-ICE-G1']:.1f} kg NH₃ → {final['cumulative_km']['A-ICE-G1']:.0f} km     │
│      ↓ H₂ + O₂                   │      │  PEM-PB-50: {final['cumulative_fuel_kg']['PEM-PB-50']:.1f} kg H₂ → {final['cumulative_km']['PEM-PB-50']:.0f} km    │
│  ⚗️ Haber-Bosch → NH₃            │      │  HY-P100: {final['cumulative_fuel_kg']['HY-P100']:.1f} kg H₂ → {final['cumulative_km']['HY-P100']:.0f} km      │
│      ↓                            │      │                                        │
│  ⛽ TANKS FILL                    │  →   │  ⛽ TANKS DRAIN                         │
│  H₂: 0% → {peak_h2_soc:.0f}%  (peak)          │      │  H₂: {peak_h2_soc:.0f}% → {final['h2_tank_soc_pct']:.0f}%                        │
│  NH₃: 0% → {peak_nh3_soc:.0f}%  (peak)         │      │  NH₃: {peak_nh3_soc:.0f}% → {final['nh3_tank_soc_pct']:.0f}%                       │
│                                   │      │                                        │
│  Zero emissions, zero noise       │      │  Zero-carbon mobility: {total_km:.0f} km total   │
└───────────────────────────────────┘      └────────────────────────────────────────┘
```
""")

    # ── OPTIMIZER: Find continuous operation config ────────
    st.markdown("---")
    st.subheader("🎯 Optimize for Continuous Operation")
    st.caption(
        "Find the exact number of Granas modules needed so daytime solar "
        "production fills tanks enough to run engines all night, every night."
    )

    op1, op2 = st.columns(2)
    with op1:
        opt_load = st.slider("Night Engine Load (%)", 25, 100, 75, 5,
                              key="opt_load",
                              help="Engine load during nighttime mobility")
        opt_margin = st.slider("Safety Margin (%)", 0, 50, 15, 5,
                                key="opt_margin",
                                help="Extra capacity for cloudy days / weather variance")
    with op2:
        opt_sun = st.slider("Effective Sun Hours", 6, 14, 12, 1,
                             key="opt_sun",
                             help="Hours of usable solar irradiance per day")
        opt_night = st.slider("Night Operation Hours", 4, 14, 12, 1,
                               key="opt_night",
                               help="Hours engines run at night")

    if st.button("🔍 Find Optimal Configuration", type="primary", use_container_width=True):
        with st.spinner("Solving energy balance... (binary search over module count)"):
            opt = hub.optimize_continuous(
                engines_active={"A-ICE-G1": n_aice, "PEM-PB-50": n_pem, "HY-P100": n_hyp},
                engine_load_pct=opt_load,
                sun_hours=opt_sun,
                night_hours=opt_night,
                safety_margin=1.0 + opt_margin / 100,
            )

        st.success(f"**{opt['status']}** — {opt['optimal_modules']:,} Granas modules needed")

        # Results
        o1, o2, o3, o4, o5, o6 = st.columns(6)
        o1.metric("🔋 Modules", f"{opt['optimal_modules']:,}",
                  help="Minimum Granas 2.1×3.4m modules for continuous operation")
        o2.metric("☀️ Solar", f"{opt['solar_capacity_MW']:.1f} MW",
                  help=f"{opt['solar_capacity_kW']:.0f} kW total capacity")
        o3.metric("📐 Field", f"{opt['field_area_ha']:.1f} ha",
                  help="Total installation footprint")
        o4.metric("💧 H₂ Tank", f"{opt['optimal_h2_tank_kg']:.0f} kg",
                  help="Optimal H₂ storage capacity")
        o5.metric("⚗️ NH₃ Tank", f"{opt['optimal_nh3_tank_kg']:.0f} kg",
                  help="Optimal NH₃ storage capacity")
        o6.metric("💰 CAPEX", f"${opt['capex_total_usd']/1e6:.2f}M",
                  help="Estimated total capital expenditure")

        # Fuel balance
        st.markdown("#### ⚖️ Fuel Balance (Day Production vs Night Demand)")
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("**H₂ Balance**")
            st.metric("Produced (day)", f"{opt['h2_produced_day_kg']:.1f} kg")
            st.metric("Consumed (night)", f"{opt['h2_demand_night_kg']:.1f} kg")
            surplus = opt['h2_surplus_kg']
            st.metric("Surplus", f"{surplus:.1f} kg",
                      delta=f"{'✅' if surplus >= 0 else '❌'} {'buffer' if surplus >= 0 else 'deficit'}")
        with b2:
            st.markdown("**NH₃ Balance**")
            st.metric("Produced (day)", f"{opt['nh3_produced_day_kg']:.1f} kg")
            st.metric("Consumed (night)", f"{opt['nh3_demand_night_kg']:.1f} kg")
            surplus_nh3 = opt['nh3_surplus_kg']
            st.metric("Surplus", f"{surplus_nh3:.1f} kg",
                      delta=f"{'✅' if surplus_nh3 >= 0 else '❌'} {'buffer' if surplus_nh3 >= 0 else 'deficit'}")

        # Supply vs demand chart
        fuels = ["H₂", "NH₃"]
        produced = [opt["h2_produced_day_kg"], opt["nh3_produced_day_kg"]]
        consumed = [opt["h2_demand_night_kg"], opt["nh3_demand_night_kg"]]

        fig_bal = go.Figure()
        fig_bal.add_trace(go.Bar(x=fuels, y=produced, name="☀️ Day Production",
                                  marker_color="#FFD700"))
        fig_bal.add_trace(go.Bar(x=fuels, y=consumed, name="🌙 Night Demand",
                                  marker_color="#FF6347"))
        fig_bal.update_layout(
            template="plotly_dark", height=350, barmode="group",
            title="Daily Fuel Balance — Production vs Consumption",
            yaxis_title="kg / day",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=14),
        )
        st.plotly_chart(fig_bal, use_container_width=True)

        # CAPEX breakdown
        st.markdown("#### 💰 CAPEX Breakdown")
        cx1, cx2, cx3, cx4 = st.columns(4)
        cx1.metric("Granas Modules", f"${opt['capex_modules_usd']/1e6:.2f}M",
                   help=f"{opt['optimal_modules']:,} × $450/module")
        cx2.metric("Electrolyzer", f"${opt['capex_electrolyzer_usd']/1e6:.2f}M",
                   help="$810/kW PEM stack")
        cx3.metric("Storage Tanks", f"${opt['capex_tanks_usd']/1e6:.2f}M",
                   help="H₂ @ $500/kg + NH₃ @ $50/kg capacity")
        cx4.metric("**TOTAL**", f"${opt['capex_total_usd']/1e6:.2f}M")


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
# TAB VEHICLE FLEET: How Each Vehicle Uses Granas Fuel
# ═══════════════════════════════════════════════════════════════
with tab_vf:
    st.subheader("🚀 Vehicle Fleet — Granas Fuel for Every Application")
    st.caption(
        "How trucks, ships, aircraft, drones, and F1 cars use solar fuel. "
        "HY-P100 (500 kW H₂ turbine) is the long-range champion."
    )

    # Fleet overview cards
    for vname, vehicle in VEHICLE_FLEET.items():
        p = vehicle.profile_summary()
        with st.container():
            st.markdown(f"### {p['emoji']} {p['vehicle']} — {p['engine_model']}")
            v1, v2, v3, v4, v5, v6 = st.columns(6)
            v1.metric("Engine", f"{p['n_engines']}× {p['engine']}",
                      help=p['engine_model'])
            v2.metric("Power", f"{p['total_power_kW']:.0f} kW",
                      help=f"{p['n_engines']} engines × {ENGINE_SPECS[p['engine']].rated_power_kW:.0f} kW each")
            v3.metric("Fuel Tank", f"{p['total_tank_kg']:.0f} kg {p['fuel_type']}",
                      help=f"Total onboard fuel capacity")
            v4.metric("🛣️ Range", f"{p['range_km']:,.0f} km",
                      help=f"Maximum range at 75% cruise load, {p['cruise_speed_kmh']} km/h")
            v5.metric("⏱️ Endurance", f"{p['endurance_h']:.1f} h",
                      help="Maximum operational time at cruise")
            v6.metric("🔋 Granas Modules", f"{p['granas_modules_daily']:,}",
                      help="Number of 2.1×3.4m Granas modules needed to fuel 1 daily mission")

            # Fuel rate + mission
            v7, v8, v9 = st.columns(3)
            v7.metric("Cruise Fuel Rate", f"{p['fuel_rate_cruise_kg_h']:.2f} kg/h",
                      help="Fuel consumption at 75% cruise load")
            v8.metric("Payload", f"{p['payload_kg']:,.0f} kg",
                      help="Useful cargo/passenger capacity")
            v9.metric("TRL", f"{p['trl']}",
                      help="Technology Readiness Level")

            st.info(f"🎯 **Mission**: {p['mission']}")
            st.markdown("---")

    # Range comparison chart
    st.subheader("🛣️ Range Comparison")
    v_names = list(VEHICLE_FLEET.keys())
    v_ranges = [VEHICLE_FLEET[v].range_km() for v in v_names]
    v_emojis = [VEHICLE_FLEET[v].emoji for v in v_names]
    v_colors = []
    for v in v_names:
        eng = VEHICLE_FLEET[v].engine
        if eng == "HY-P100":
            v_colors.append("#FFD700")    # Gold for HY long-range
        elif eng == "A-ICE-G1":
            v_colors.append("#7B68EE")    # Purple for NH₃
        else:
            v_colors.append("#00BFFF")    # Blue for PEM

    fig_range = go.Figure(go.Bar(
        x=[f"{e} {n}" for e, n in zip(v_emojis, v_names)],
        y=v_ranges,
        marker_color=v_colors,
        text=[f"{r:,.0f} km" for r in v_ranges],
        textposition="auto",
    ))
    fig_range.update_layout(
        template="plotly_dark", height=420,
        title="Maximum Range by Vehicle (km) — HY-P100 = Long Range Champion",
        yaxis_title="Range (km)", yaxis_type="log",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    st.plotly_chart(fig_range, use_container_width=True)

    # Granas modules needed chart
    st.subheader("🔋 Granas Modules per Daily Mission")
    v_modules = [VEHICLE_FLEET[v].modules_for_daily_mission() for v in v_names]

    fig_mod = go.Figure(go.Bar(
        x=[f"{e} {n}" for e, n in zip(v_emojis, v_names)],
        y=v_modules,
        marker_color=v_colors,
        text=[f"{m:,}" for m in v_modules],
        textposition="auto",
    ))
    fig_mod.update_layout(
        template="plotly_dark", height=380,
        title="Granas 2.1×3.4m Modules Needed to Fuel 1 Daily Mission",
        yaxis_title="Number of Modules", yaxis_type="log",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
    )
    st.plotly_chart(fig_mod, use_container_width=True)

    # Fleet summary table
    st.subheader("📊 Fleet Summary")
    st.markdown("""
| Vehicle | Engine | Fuel | Power | Tank | Range | Endurance | Granas Modules | Mission |
|---------|--------|------|-------|------|-------|-----------|:---:|---------|""" + "\n".join([
        f"| {VEHICLE_FLEET[v].emoji} {v} | {VEHICLE_FLEET[v].n_engines}×{VEHICLE_FLEET[v].engine} | "
        f"{ENGINE_SPECS[VEHICLE_FLEET[v].engine].fuel_type} | "
        f"{VEHICLE_FLEET[v].total_power_kW():.0f} kW | "
        f"{VEHICLE_FLEET[v].total_tank_kg():.0f} kg | "
        f"**{VEHICLE_FLEET[v].range_km():,.0f} km** | "
        f"{VEHICLE_FLEET[v].endurance_h():.1f} h | "
        f"{VEHICLE_FLEET[v].modules_for_daily_mission():,} | "
        f"{VEHICLE_FLEET[v].mission} |"
        for v in v_names
    ]))


# ═══════════════════════════════════════════════════════════════
# TAB PEM TRANSPORT: Fuel Cell Integration into Existing Transport
# ═══════════════════════════════════════════════════════════════
with tab_pem:
    st.subheader("🔌 PEM Fuel Cell — Integration into Existing Transport")
    st.caption(
        "PEM-PB-50 stacks (50 kW each) integrated into 8 real-world transport "
        "categories. 5-minute refueling. 60% efficiency. Drop-in H₂ powertrain."
    )

    # Summary KPIs
    pem_count = len(PEM_TRANSPORT_FLEET)
    avg_range = sum(v.range_km for v in PEM_TRANSPORT_FLEET.values()) / pem_count
    avg_refuel = sum(v.refuel_time_min for v in PEM_TRANSPORT_FLEET.values()) / pem_count
    total_co2 = sum(v.co2_avoided_per_fill_kg for v in PEM_TRANSPORT_FLEET.values())

    pk1, pk2, pk3, pk4 = st.columns(4)
    pk1.metric("🔌 Platforms", f"{pem_count}", help="Transport categories integrated")
    pk2.metric("🛣️ Avg Range", f"{avg_range:.0f} km", help="Average range across all platforms")
    pk3.metric("⛽ Avg Refuel", f"{avg_refuel:.0f} min", help="Average refueling time")
    pk4.metric("🌍 CO₂ Avoided", f"{total_co2:.0f} kg/fill", help="Total CO₂ avoided per full fleet refuel")

    st.divider()

    # Vehicle cards
    for vname, vehicle in PEM_TRANSPORT_FLEET.items():
        p = vehicle.profile_summary()
        complexity_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(p["retrofit_complexity"], "⚪")

        with st.container():
            st.markdown(f"### {p['emoji']} {p['name']} — {p['base_platform']}")

            p1, p2, p3, p4, p5, p6 = st.columns(6)
            p1.metric("⚡ Power", f"{p['total_power_kW']:.0f} kW",
                      help=f"{vehicle.n_stacks}× PEM-PB-50 (50 kW each)")
            p2.metric("⛽ H₂ Tank", f"{p['h2_tank_kg']} kg",
                      help=f"{p['tank_pressure_bar']} bar Type IV composite")
            p3.metric("🛣️ Range", f"{p['range_km']:,.0f} km",
                      help=f"{p['km_per_kg_h2']:.1f} km per kg H₂")
            p4.metric("⛽ Refuel", f"{p['refuel_time_min']:.0f} min",
                      help="Time to refuel from empty")
            p5.metric("η Efficiency", f"{p['stack_efficiency_pct']:.0f}%",
                      help="PEM fuel cell stack efficiency")
            p6.metric(f"{complexity_color} Retrofit", p["retrofit_complexity"],
                      help="Integration complexity into existing platform")

            p7, p8, p9 = st.columns(3)
            p7.metric("🌍 CO₂ Avoided", f"{p['co2_avoided_kg']:.0f} kg/fill",
                      help="CO₂ avoided vs diesel equivalent")
            p8.metric("🔋 Granas Modules", f"{p['granas_modules_per_fill']}",
                      help="Modules needed to produce 1 full tank of H₂")
            p9.metric("🚧 Platforms", p["existing_platforms"],
                      help="Compatible existing models")
            st.markdown("---")

    # Range comparison chart
    st.subheader("🛣️ PEM Transport Range Comparison")
    pem_names = list(PEM_TRANSPORT_FLEET.keys())
    pem_ranges = [PEM_TRANSPORT_FLEET[v].range_km for v in pem_names]
    pem_emojis = [PEM_TRANSPORT_FLEET[v].emoji for v in pem_names]
    pem_refuels = [PEM_TRANSPORT_FLEET[v].refuel_time_min for v in pem_names]

    fig_pem = make_subplots(specs=[[{"secondary_y": True}]])
    fig_pem.add_trace(go.Bar(
        x=[f"{e} {n}" for e, n in zip(pem_emojis, pem_names)],
        y=pem_ranges, name="Range (km)",
        marker_color="#00BFFF",
        text=[f"{r:,.0f} km" for r in pem_ranges],
        textposition="auto",
    ), secondary_y=False)
    fig_pem.add_trace(go.Scatter(
        x=[f"{e} {n}" for e, n in zip(pem_emojis, pem_names)],
        y=pem_refuels, name="Refuel (min)",
        line=dict(color="#FFD700", width=3),
        mode="lines+markers+text",
        text=[f"{r:.0f} min" for r in pem_refuels],
        textposition="top center",
    ), secondary_y=True)
    fig_pem.update_layout(
        template="plotly_dark", height=450,
        title="PEM H₂ Transport: Range vs Refuel Time",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13), legend=dict(orientation="h", y=-0.2),
    )
    fig_pem.update_yaxes(title_text="Range (km)", secondary_y=False,
                          gridcolor="rgba(128,128,128,0.2)")
    fig_pem.update_yaxes(title_text="Refuel Time (min)", secondary_y=True)
    st.plotly_chart(fig_pem, use_container_width=True)

    # Efficiency comparison
    st.subheader("🔋 Why PEM Fuel Cell Wins")
    st.markdown("""
| Metric | PEM Fuel Cell (H₂) | Diesel ICE | Battery EV |
|--------|-------------------|-----------|------------|
| **Efficiency** | **55–60%** | 35–42% | 85–90% |
| **Refuel Time** | **3–5 min** | 3–5 min | 30–60 min |
| **Range per fill** | **400–650 km** | 600–900 km | 250–450 km |
| **CO₂ Emissions** | **0 g/km** | 120–250 g/km | 0 g/km (tailpipe) |
| **Cold Weather** | **No degradation** | No effect | −30% range |
| **Weight Penalty** | Low (H₂ is light) | N/A | High (batteries) |
| **Fuel Source** | Granas Solar | Fossil oil | Grid mix |
| **Noise** | **Silent** | 75–85 dB | Silent |

> PEM combines the **refuel speed of diesel** with the **zero emissions of EV** —
> without the battery weight, range anxiety, or grid dependency.
""")


# ═══════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════
st.divider()
st.caption(
    "PRIMEnergeia S.A.S. — Granas Fuel Hub Division | "
    "Solar → H₂ → NH₃ → Zero-Carbon Propulsion for Every Application"
)
