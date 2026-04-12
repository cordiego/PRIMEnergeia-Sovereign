"""PRIMEnergeia — Engine Research Lab | Live Physics Testing Dashboard"""
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
import sys, os

# Resolve bundled engine modules
_LIB_ENGINES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib", "engines")
sys.path.insert(0, _LIB_ENGINES)

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🔬 Engine Research Lab — Physics Deep-Dive")
st.caption("Live Simulation · Test Validation · Performance Maps | All 6 Engine Models | PRIMEnergeia S.A.S.")

engine = st.selectbox("Select Engine", [
    "A-ICE-G1 — Ammonia ICE (335 kW)",
    "PEM-PB-50 — PEM Fuel Cell (50 kW)",
    "HY-P100 — H₂ Gas Turbine (100 kW)",
    "BESS-400 — Grid Battery (400 MWh)",
    "PRIMEcycle — Module Recycling",
    "PRIM-Wind — Wind Farm + H₂ (1 GW)"
])

st.divider()

# ═══════════════════════════════════════════════════════════════
#  A-ICE — AMMONIA COMBUSTION
# ═══════════════════════════════════════════════════════════════
if "A-ICE" in engine:
    from aice_engine import AICESimulator

    sim = AICESimulator()
    st.markdown("### 🔥 A-ICE-G1 — Ammonia Internal Combustion Engine")

    tab1, tab2, tab3 = st.tabs(["📊 Performance Map", "🧪 Operating Point", "🧬 NOx Model"])

    with tab1:
        rpm_range = list(range(800, 2201, 200))
        load_range = list(range(10, 101, 10))
        results = sim.full_map(rpm_range=rpm_range, load_range=load_range)

        power = np.zeros((len(load_range), len(rpm_range)))
        bte = np.zeros_like(power)
        for r in results:
            i = load_range.index(r["load_pct"])
            j = rpm_range.index(r["rpm"])
            power[i, j] = r["power_kw"]
            bte[i, j] = r["bte_pct"]

        fig = make_subplots(rows=1, cols=2, subplot_titles=["Power (kW)", "BTE (%)"])
        fig.add_trace(go.Heatmap(z=power, x=rpm_range, y=load_range,
                                  colorscale="Hot", colorbar=dict(x=0.45, title="kW")), row=1, col=1)
        fig.add_trace(go.Heatmap(z=bte, x=rpm_range, y=load_range,
                                  colorscale="Viridis", colorbar=dict(title="%")), row=1, col=2)
        fig.update_layout(template="plotly_dark", height=450,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="RPM")
        fig.update_yaxes(title_text="Load (%)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        rpm = c1.slider("RPM", 600, 2100, 1400, 100)
        load = c2.slider("Load (%)", 10, 100, 75, 5)
        op = sim.operating_point(rpm, load)

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Power", f"{op['power_kw']:.1f} kW")
        m2.metric("Torque", f"{op['torque_nm']:.0f} Nm")
        m3.metric("BTE", f"{op['bte_pct']:.1f}%")
        m4.metric("BSFC", f"{op['bsfc_g_kwh']:.0f} g/kWh")
        m5.metric("NH₃ Flow", f"{op['nh3_flow_kg_h']:.1f} kg/h")
        m6.metric("CO₂", f"{op['co2_gpkwh']:.0f} g/kWh")

        st.info(f"Exhaust Temp: {op['exhaust']['temp_c']:.0f}°C | "
                f"NOx Tailpipe: {op['nox_tailpipe_gpkwh']:.3f} g/kWh (SCR 95%)")

    with tab3:
        temps = np.arange(1500, 2200, 10)
        from aice_engine import NOxModel
        nox = NOxModel()
        nox_vals = [nox.thermal_nox_ppm(t) for t in temps]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=temps, y=nox_vals, name="Zeldovich NOx",
                                   line=dict(color="#ff4444", width=3)))
        fig2.add_vline(x=1800, line=dict(color="#FFD700", dash="dash"),
                       annotation_text="Crossover: passivation > creation")
        fig2.update_layout(template="plotly_dark", height=400,
                           title="Thermal NOx (Zeldovich) vs Flame Temperature",
                           xaxis_title="Flame Temperature (K)", yaxis_title="NOx (ppm)",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  PEM FUEL CELL
# ═══════════════════════════════════════════════════════════════
elif "PEM" in engine:
    from pem_stack import PEMSystem

    pem = PEMSystem()
    st.markdown("### ⚡ PEM-PB-50 — Polarization Curve & Efficiency")

    tab1, tab2 = st.tabs(["📈 Polarization Curve", "🔋 Operating Points"])

    with tab1:
        pol = pem.echem.polarization_curve(steps=100)
        j_vals = [p["current_density_A_cm2"] for p in pol]
        v_vals = [p["cell_voltage_V"] for p in pol]
        power_vals = [p["stack_power_kW"] for p in pol]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=j_vals, y=v_vals, name="Cell Voltage (V)",
                                  line=dict(color="#00d1ff", width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=j_vals, y=power_vals, name="Stack Power (kW)",
                                  line=dict(color="#00c878", width=2, dash="dot")), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=450, title="PEM-PB-50 Polarization Curve",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="Current Density (A/cm²)")
        fig.update_yaxes(title_text="Cell Voltage (V)", secondary_y=False)
        fig.update_yaxes(title_text="Stack Power (kW)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        loads = list(range(10, 101, 10))
        ops = [pem.operating_point(l) for l in loads]

        fig2 = make_subplots(rows=1, cols=2, subplot_titles=["System Efficiency (%)", "H₂ Consumption (kg/h)"])
        fig2.add_trace(go.Bar(x=loads, y=[o["system_efficiency_pct"] for o in ops],
                               marker_color="#00d1ff"), row=1, col=1)
        fig2.add_trace(go.Bar(x=loads, y=[o["h2_consumption_kg_h"] for o in ops],
                               marker_color="#FFD700"), row=1, col=2)
        fig2.update_layout(template="plotly_dark", height=400, showlegend=False,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig2.update_xaxes(title_text="Load (%)")
        st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  HYDROGEN TURBINE
# ═══════════════════════════════════════════════════════════════
elif "HY-P100" in engine:
    from h2_turbine import BraytonCycle, HYP100Spec

    cycle = BraytonCycle(HYP100Spec())
    st.markdown("### 🔋 HY-P100 — Brayton Cycle Performance")

    tab1, tab2 = st.tabs(["📊 Part-Load Performance", "🌡️ Ambient Correction"])

    with tab1:
        loads = list(range(10, 101, 5))
        results = [cycle.cycle_efficiency(load_pct=l) for l in loads]
        valid = [r for r in results if "error" not in r]
        valid_loads = [r["load_pct"] for r in valid]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=valid_loads, y=[r["electrical_power_kw"] for r in valid],
                                  name="Electrical Power (kW)", line=dict(color="#FFD700", width=3)),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=valid_loads, y=[r["electrical_efficiency_pct"] for r in valid],
                                  name="η_elec (%)", line=dict(color="#00c878", width=2, dash="dot")),
                      secondary_y=True)
        fig.update_layout(template="plotly_dark", height=450, title="HY-P100 Part-Load Map",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="Load (%)")
        fig.update_yaxes(title_text="Power (kW)", secondary_y=False)
        fig.update_yaxes(title_text="Efficiency (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        temps_c = list(range(-20, 51, 5))
        amb_results = [cycle.cycle_efficiency(t_ambient_k=t+273.15, load_pct=100) for t in temps_c]
        valid_amb = [(t, r) for t, r in zip(temps_c, amb_results) if "error" not in r]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=[v[0] for v in valid_amb],
                                   y=[v[1]["electrical_power_kw"] for v in valid_amb],
                                   name="Power at Full Load",
                                   line=dict(color="#00d1ff", width=3), fill="tozeroy",
                                   fillcolor="rgba(0,209,255,0.1)"))
        fig2.update_layout(template="plotly_dark", height=400, title="Rated Power vs Ambient Temperature",
                           xaxis_title="Ambient (°C)", yaxis_title="Power (kW)",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  BATTERY BESS
# ═══════════════════════════════════════════════════════════════
elif "BESS" in engine:
    from battery_system import CHEMISTRIES, BESSSpec, DegradationModel, RevenueModel

    chem = st.selectbox("Battery Chemistry", list(CHEMISTRIES.keys()))
    cell = CHEMISTRIES[chem]
    spec = BESSSpec(chemistry=chem)
    deg = DegradationModel(cell)

    st.markdown(f"### 🔋 BESS-400 — {cell.name} | Degradation & Revenue")

    tab1, tab2 = st.tabs(["📉 Degradation", "💰 Lifetime Economics"])

    with tab1:
        years = list(range(1, 26))
        deg_data = [deg.total_degradation(y) for y in years]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=[d["soh_pct"] for d in deg_data],
                                  name="SOH", line=dict(color="#00c878", width=3),
                                  fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"))
        fig.add_hline(y=80, line=dict(color="red", dash="dash"), annotation_text="EOL (80% SOH)")
        fig.update_layout(template="plotly_dark", height=400, title=f"{cell.name} — State of Health",
                          xaxis_title="Year", yaxis_title="SOH (%)",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        rev = RevenueModel(spec, cell, deg)
        econ = rev.lifetime_economics(25)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CapEx", f"${econ['capex_M']:.0f}M")
        m2.metric("25yr Net Revenue", f"${econ['lifetime_net_revenue_M']:.0f}M")
        m3.metric("ROI", f"{econ['roi_pct']:.0f}%")
        m4.metric("Payback", f"{econ['payback_years']} years")

        yearly = econ["yearly_detail"]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=[y["year"] for y in yearly],
                               y=[y["net_revenue_M"] for y in yearly],
                               name="Net Revenue", marker_color="#00d1ff"))
        fig2.add_trace(go.Scatter(x=[y["year"] for y in yearly],
                                   y=[y["cumulative_net_M"] for y in yearly],
                                   name="Cumulative", line=dict(color="#FFD700", width=3)))
        fig2.add_hline(y=econ["capex_M"], line=dict(color="red", dash="dash"),
                       annotation_text=f"CapEx: ${econ['capex_M']:.0f}M")
        fig2.update_layout(template="plotly_dark", height=400, title="Annual Revenue & Payback",
                           xaxis_title="Year", yaxis_title="$M",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  PRIMECYCLE RECYCLING
# ═══════════════════════════════════════════════════════════════
elif "PRIMEcycle" in engine:
    from primecycle import PRIMEcycleSimulator

    sim = PRIMEcycleSimulator()
    result = sim.process_module()
    s = result["summary"]

    st.markdown("### ♻️ PRIMEcycle — Material Recovery & Economics")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Yield", f"{s['overall_yield_pct']:.1f}%")
    m2.metric("Value/Module", f"${s['total_value_usd']:.2f}")
    m3.metric("CO₂ Avoided", f"{s['co2_avoided_kg']:.1f} kg")
    m4.metric("Pb Captured", f"{s['pb_captured_g']:.1f} g")
    m5.metric("Energy", f"{s['total_energy_kwh']:.1f} kWh")

    tab1, tab2 = st.tabs(["📊 Material Recovery", "🏭 Plant Scaling"])

    with tab1:
        mats = sorted(result["materials"], key=lambda m: m["value_usd"], reverse=True)[:10]
        fig = go.Figure(go.Bar(
            x=[m["value_usd"] for m in mats], y=[m["material"] for m in mats],
            orientation="h", marker_color=["#ff4444" if m["hazardous"] else "#00c878" for m in mats]))
        fig.update_layout(template="plotly_dark", height=400, title="Top 10 Materials by Recovery Value",
                          xaxis_title="Value ($/module)",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        scales = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
        econs = [sim.plant_economics(s) for s in scales]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Scatter(x=scales, y=[e["annual_profit_M"] for e in econs],
                                   name="Annual Profit ($M)", line=dict(color="#00c878", width=3)),
                       secondary_y=False)
        fig2.add_trace(go.Scatter(x=scales, y=[e["payback_years"] for e in econs],
                                   name="Payback (years)", line=dict(color="#FFD700", width=2, dash="dot")),
                       secondary_y=True)
        fig2.update_layout(template="plotly_dark", height=400, title="Plant Economics vs Scale",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig2.update_xaxes(title_text="Modules/Year", type="log")
        fig2.update_yaxes(title_text="Profit ($M/yr)", secondary_y=False)
        fig2.update_yaxes(title_text="Payback (years)", secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  WIND FARM
# ═══════════════════════════════════════════════════════════════
elif "PRIM-Wind" in engine:
    from wind_farm import WindFarmSimulator, TurbineSpec, WindResource

    c1, c2, c3 = st.columns(3)
    mean_wind = c1.slider("Mean Wind Speed (m/s)", 6.0, 14.0, 9.5, 0.5)
    n_turbines = c2.slider("Number of Turbines", 10, 150, 67, 1)
    weibull_k = c3.slider("Weibull k", 1.5, 3.0, 2.1, 0.1)

    sim = WindFarmSimulator(num_turbines=n_turbines,
                             wind_resource=WindResource(mean_wind, weibull_k))
    aep = sim.annual_energy_production()

    st.markdown("### 🌊 PRIM Wind — Offshore Wind + Green H₂")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Farm Capacity", f"{aep['farm_capacity_mw']:.0f} MW")
    m2.metric("Net AEP", f"{aep['net_aep_gwh']:.0f} GWh")
    m3.metric("Capacity Factor", f"{aep['capacity_factor_pct']:.1f}%")
    m4.metric("Wake Loss", f"{aep['wake_loss_pct']:.1f}%")
    m5.metric("H₂ Annual", f"{aep['h2_annual_tonnes']:.0f} t")
    m6.metric("EFLH", f"{aep['equivalent_full_load_hours']:.0f} h")

    tab1, tab2 = st.tabs(["📈 Power Curve", "💰 LCOE"])

    with tab1:
        curve = sim.power_model.full_curve()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=[c["wind_speed_ms"] for c in curve],
                                  y=[c["power_kw"]/1000 for c in curve],
                                  name="Power (MW)", line=dict(color="#00d1ff", width=3)),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=[c["wind_speed_ms"] for c in curve],
                                  y=[c["cp"] for c in curve],
                                  name="Cp", line=dict(color="#FFD700", width=2, dash="dot")),
                      secondary_y=True)
        fig.add_hline(y=0.593, line=dict(color="red", dash="dash"),
                      annotation_text="Betz Limit", secondary_y=True)
        fig.update_layout(template="plotly_dark", height=450, title="PRIM-WT-15 Power Curve",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="Wind Speed (m/s)")
        fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
        fig.update_yaxes(title_text="Cp", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fin = sim.financial_model()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CapEx", f"${fin['capex_M']:.0f}M")
        m2.metric("LCOE", f"${fin['lcoe_usd_mwh']:.1f}/MWh")
        m3.metric("25yr Revenue", f"${fin['total_revenue_25yr_M']:.0f}M")
        m4.metric("Payback", f"{fin['payback_years']:.1f} yr")

st.divider()
st.caption("PRIMEnergeia S.A.S. — Engine Research Lab | Advanced Simulation & Testing")
