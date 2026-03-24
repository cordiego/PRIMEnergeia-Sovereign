"""PRIMEnergeia — PRIMEngines | CEO-Grade Green Propulsion Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

tab1, tab2, tab3, tab4 = st.tabs(["📊 Efficiency", "💰 TCO", "🎯 Applications", "🗺️ Roadmap"])

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

st.caption("PRIMEnergeia S.A.S. — PRIMEngines Division | Zero-Carbon Propulsion for Every Application")
