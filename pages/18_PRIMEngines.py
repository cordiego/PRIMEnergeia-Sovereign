"""PRIMEnergeia — PRIMEngines | CEO-Grade Green Propulsion Dashboard"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
# --- End Banner ---
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from lib.engines.power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS
except Exception:
    try:
        from power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS
    except Exception:
        InverterModel = None

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🚀 PRIMEngines — Zero-Carbon Propulsion")
st.caption("Ammonia ICE · PEM Fuel Cell · Hydrogen Turbine | Multi-Sector Mobility | PRIMEnergeia S.A.S.")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🔧 Engines", "3 Models")
k2.metric("⛽ Fuels", "NH₃ / H₂")
k3.metric("💨 CO₂", "ZERO")
k4.metric("🎯 Sectors", "9+")
k5.metric("📊 TRL", "4–6")
k6.metric("🌍 Markets", "Global")

st.divider()

engine = st.radio("Select Engine", ["A-ICE-G1 — Ammonia ICE", "PEM-PB-50 — Fuel Cell", "HY-P100 — H₂ Turbine"], horizontal=True)

if engine == "A-ICE-G1 — Ammonia ICE":
    st.markdown("### 🔥 A-ICE-G1 — Ammonia Internal Combustion Engine")
    e1, e2, e3, e4, e5, e6 = st.columns(6)
    e1.metric("Power", "450 HP / 335 kW")
    e2.metric("Torque", "1,800 Nm")
    e3.metric("Fuel", "Green NH₃")
    e4.metric("Efficiency", "42%")
    e5.metric("Weight", "680 kg")
    e6.metric("TRL", "5")
    desc = "Purpose-built for heavy transport: long-haul trucks, marine vessels, rail freight, and F1 motorsport. Direct ammonia combustion with catalytic NOx reduction system."

elif engine == "PEM-PB-50 — Fuel Cell":
    st.markdown("### ⚡ PEM-PB-50 — Proton Exchange Membrane Fuel Cell")
    e1, e2, e3, e4, e5, e6 = st.columns(6)
    e1.metric("Power", "50 kW")
    e2.metric("Stack Eff.", "60%")
    e3.metric("Fuel", "Green H₂")
    e4.metric("Start Time", "< 5 sec")
    e5.metric("Weight", "45 kg")
    e6.metric("TRL", "6")
    desc = "Compact fuel cell for light vehicles, UAVs, drones, and portable power. Silent operation with only water as exhaust. Ideal for stealth military and urban delivery."

else:
    st.markdown("### 🔋 HY-P100 — Hydrogen Gas Turbine")
    e1, e2, e3, e4, e5, e6 = st.columns(6)
    e1.metric("Power", "100 kW")
    e2.metric("Heat Rate", "9,500 BTU/kWh")
    e3.metric("Fuel", "Green H₂")
    e4.metric("Efficiency", "42%")
    e5.metric("Weight", "350 kg")
    e6.metric("TRL", "4")
    desc = "Micro gas turbine for grid peaking, marine propulsion, and SAF-compatible aviation. High power density with rapid ramp rates for load-following applications."

st.info(desc)
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Efficiency", "💰 TCO", "🎯 Applications", "🗺️ Roadmap", "⚡ Power Electronics"])

with tab1:
    load = np.arange(10, 101, 2)
    aice = np.clip(15 + 30 * (1 - np.exp(-load / 25)) - 0.003 * np.maximum(0, load - 75)**2, 10, 45)
    pem = np.clip(65 - 0.08 * (load - 35)**2 / 100 - 0.1 * np.maximum(0, load - 80), 35, 62)
    hyp = np.clip(18 + 26 * (1 - np.exp(-load / 20)) - 0.004 * np.maximum(0, load - 80)**2, 12, 44)
    diesel = np.clip(12 + 28 * (1 - np.exp(-load / 30)) - 0.003 * np.maximum(0, load - 70)**2, 10, 40)
    bev = np.clip(92 - 0.15 * load, 75, 92)

    fig = go.Figure()
    for name, data, color, dash in [
        ("A-ICE-G1 (NH₃)", aice, "#00c878", "solid"),
        ("PEM-PB-50 (H₂)", pem, "#00BFFF", "solid"),
        ("HY-P100 (Turbine)", hyp, "#FFD700", "solid"),
        ("Diesel (Reference)", diesel, "#888", "dash"),
        ("BEV (Reference)", bev, "#9467bd", "dash"),
    ]:
        fig.add_trace(go.Scatter(x=load, y=data, name=name, line=dict(width=3, color=color, dash=dash)))
    fig.update_layout(template="plotly_dark", height=450, title="System Efficiency vs Load",
        xaxis_title="Load (%)", yaxis_title="System Efficiency (%)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14),
        legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    years = np.arange(1, 16)
    # TCO per km (cents)
    diesel_tco = np.cumsum(np.full(15, 18.5))  # fuel + maintenance
    nh3_tco = np.cumsum(np.full(15, 14.2))
    h2_fc_tco = np.cumsum(np.full(15, 16.8))
    h2_turb_tco = np.cumsum(np.full(15, 15.5))
    bev_tco = np.cumsum(np.full(15, 8.5))

    # Add initial cost premium
    diesel_tco += 0
    nh3_tco += 15  # $15K premium
    h2_fc_tco += 25
    h2_turb_tco += 20
    bev_tco += 35  # battery cost

    fig2 = go.Figure()
    for name, data, color in [("Diesel", diesel_tco, "#888"), ("A-ICE NH₃", nh3_tco, "#00c878"),
                               ("PEM H₂", h2_fc_tco, "#00BFFF"), ("H₂ Turbine", h2_turb_tco, "#FFD700"),
                               ("BEV", bev_tco, "#9467bd")]:
        fig2.add_trace(go.Scatter(x=years, y=data, name=name, line=dict(width=3, color=color)))
    fig2.update_layout(template="plotly_dark", height=450, title="Total Cost of Ownership — Heavy Transport ($K)",
        xaxis_title="Year", yaxis_title="Cumulative TCO ($K)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.markdown("""
| Application | A-ICE-G1 (NH₃) | PEM-PB-50 (H₂) | HY-P100 (Turbine) | Priority |
|-------------|:-:|:-:|:-:|:---:|
| **Long-Haul Trucks** | ✅ Primary | ❌ | ❌ | 🔴 High |
| **Marine / Shipping** | ✅ Dual-Fuel | ❌ | ✅ Primary | 🔴 High |
| **Rail Freight** | ✅ Primary | ❌ | ✅ Backup | 🟡 Medium |
| **High-Speed Rail** | ❌ | ❌ | ✅ Primary | 🟡 Medium |
| **Light Vehicles** | ❌ | ✅ Primary | ❌ | 🟡 Medium |
| **UAV / Drones** | ❌ | ✅ Primary | ❌ | 🔴 High |
| **Commercial Aviation** | ✅ SAF-Blend | ❌ | ✅ Primary | 🔵 Future |
| **Supersonic** | ❌ | ❌ | ✅ Primary | 🔵 Future |
| **F1 / Motorsport** | ✅ Primary | ❌ | ❌ | 🟡 Medium |
| **Grid Peaking** | ❌ | ❌ | ✅ Primary | 🔴 High |
| **Military Tactical** | ✅ Multi-Fuel | ✅ Silent | ✅ Naval | 🔴 High |
| **Mining Equipment** | ✅ Primary | ❌ | ❌ | 🟡 Medium |
""")

with tab4:
    st.markdown("""
### 🗺️ Development Roadmap
| Phase | Timeline | Milestone | Status |
|-------|----------|-----------|--------|
| **Phase 1** | 2025-2026 | A-ICE-G1 prototype + dyno testing | 🟢 Active |
| **Phase 2** | 2026-2027 | PEM-PB-50 stack integration + UAV demo | 🟡 Planning |
| **Phase 3** | 2027-2028 | HY-P100 turbine certification | 🔵 Design |
| **Phase 4** | 2028-2029 | Marine pilot (A-ICE + HY-P100) | 🔵 Design |
| **Phase 5** | 2029-2030 | Series production ramp (all 3 engines) | ⚪ Future |
| **Phase 6** | 2030+ | Aviation certification (HY-P100) | ⚪ Future |
""")

with tab5:
    st.subheader("⚡ DC-AC Power Conversion — Engine Inverter Models")
    st.caption("Physics-based model: η(P) = P / (P + k₀ + k₁P + k₂P²) | PRIMEnergeia Power Electronics Division")

    if InverterModel is not None:
        inv_pem = InverterModel(preset="pem_50kw")
        inv_hyp = InverterModel(preset="h2_turbine_100kw")
        inv_aice = InverterModel(preset="aice_genset_335kw")

        pe1, pe2, pe3 = st.columns(3)
        pe1.metric("PEM-PB-50 Inv η", f"{inv_pem.efficiency(0.5)*100:.1f}%",
            delta="NEW — was missing", delta_color="normal")
        pe2.metric("HY-P100 Inv η", f"{inv_hyp.efficiency(0.5)*100:.1f}%",
            delta=f"{(inv_hyp.efficiency(0.5)-0.98)*100:+.1f}pp vs old")
        pe3.metric("A-ICE-G1 Genset η", f"{inv_aice.efficiency(0.5)*100:.1f}%",
            delta="NEW — genset mode")

        loads = np.arange(5, 105, 5)
        pem_etas = [inv_pem.efficiency(l/100) * 100 for l in loads]
        hyp_etas = [inv_hyp.efficiency(l/100) * 100 for l in loads]
        aice_etas = [inv_aice.efficiency(l/100) * 100 for l in loads]

        fig_pe = go.Figure()
        fig_pe.add_trace(go.Scatter(x=loads, y=pem_etas, name="PEM-PB-50 (50 kW)",
            line=dict(color="#00BFFF", width=3)))
        fig_pe.add_trace(go.Scatter(x=loads, y=hyp_etas, name="HY-P100 (100 kW)",
            line=dict(color="#FFD700", width=3)))
        fig_pe.add_trace(go.Scatter(x=loads, y=aice_etas, name="A-ICE-G1 Genset (335 kW)",
            line=dict(color="#00c878", width=3)))
        fig_pe.add_hline(y=98, line_dash="dash", line_color="#888",
            annotation_text="Old flat constant (98%)")
        fig_pe.update_layout(template="plotly_dark", height=400,
            title="Inverter Efficiency vs Load — All Engines",
            xaxis_title="Load (%)", yaxis_title="Inverter η (%)",
            yaxis=dict(range=[90, 100]),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
        st.plotly_chart(fig_pe, use_container_width=True)

        st.info("**PEM Fuel Cell impact**: The PEM-PB-50 previously reported raw DC stack output as final power. "
                "A 2.5% inverter loss is now correctly modeled, meaning 50 kW DC → 48.75 kW AC delivered to grid.")

        temps = np.arange(20, 65, 1)
        fig_td = go.Figure()
        for name, model, color in [
            ("PEM-PB-50", inv_pem, "#00BFFF"),
            ("HY-P100", inv_hyp, "#FFD700"),
            ("A-ICE-G1", inv_aice, "#00c878"),
        ]:
            deratings = [model.temperature_derating(t) * 100 for t in temps]
            fig_td.add_trace(go.Scatter(x=temps, y=deratings, name=name,
                line=dict(color=color, width=3)))
        fig_td.add_vline(x=45, line_dash="dot", line_color="red", annotation_text="Derating Threshold")
        fig_td.update_layout(template="plotly_dark", height=350,
            title="Temperature Derating — Summer Performance",
            xaxis_title="Ambient °C", yaxis_title="Max Output (%)",
            yaxis=dict(range=[50, 105]),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
        st.plotly_chart(fig_td, use_container_width=True)
    else:
        st.warning("Power electronics module not available.")

st.caption("PRIMEnergeia S.A.S. — PRIMEngines Division | Zero-Carbon Propulsion for Every Application")
