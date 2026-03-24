"""PRIMEnergeia — PRIMEngines | Hydrogen & Ammonia Engine Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🚀 PRIMEngines — Green Propulsion Systems")
st.caption("Ammonia ICE · PEM Fuel Cell · Hydrogen Turbine | Zero-Carbon Mobility | PRIMEnergeia S.A.S.")

# ─── Engine Portfolio ───
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown("### A-ICE-G1")
    st.caption("Ammonia Internal Combustion Engine")
    st.metric("⚡ Power", "450 HP")
    st.metric("⛽ Fuel", "Green NH₃")
    st.metric("💨 Emissions", "Zero CO₂")
    st.metric("🎯 Application", "Heavy Transport")
    st.metric("🔗 Repo", "PRIMEngines-AICE")

with k2:
    st.markdown("### PEM-PB-50")
    st.caption("Proton Exchange Membrane Fuel Cell")
    st.metric("⚡ Power", "50 kW")
    st.metric("⛽ Fuel", "Green H₂")
    st.metric("📊 Efficiency", "60%")
    st.metric("🎯 Application", "Light Vehicles / UAV")
    st.metric("🔗 Repo", "PRIMEngines-PEM")

with k3:
    st.markdown("### HY-P100")
    st.caption("Hydrogen Gas Turbine")
    st.metric("⚡ Power", "100 kW")
    st.metric("⛽ Fuel", "Green H₂")
    st.metric("📊 Efficiency", "42%")
    st.metric("🎯 Application", "Grid Peaker / Marine")
    st.metric("🔗 Repo", "PRIMEngines-HYP")

st.divider()

# ─── Efficiency Comparison ───
st.subheader("📊 Engine Efficiency vs Load")

load_pct = np.arange(10, 101, 5)
aice_eff = 15 + 25 * (1 - np.exp(-load_pct / 30)) - 0.002 * (load_pct - 70)**2 * (load_pct > 70)
pem_eff = 65 - 0.15 * (load_pct - 40)**2 / 100
hyp_eff = 20 + 22 * (1 - np.exp(-load_pct / 25)) - 0.003 * (load_pct - 80)**2 * (load_pct > 80)
diesel_eff = 18 + 20 * (1 - np.exp(-load_pct / 35)) - 0.002 * (load_pct - 75)**2 * (load_pct > 75)

fig = go.Figure()
fig.add_trace(go.Scatter(x=load_pct, y=aice_eff, name="A-ICE-G1 (NH₃)",
    line=dict(width=3, color="#00c878")))
fig.add_trace(go.Scatter(x=load_pct, y=pem_eff, name="PEM-PB-50 (H₂)",
    line=dict(width=3, color="#00BFFF")))
fig.add_trace(go.Scatter(x=load_pct, y=hyp_eff, name="HY-P100 (Turbine)",
    line=dict(width=3, color="#FFD700")))
fig.add_trace(go.Scatter(x=load_pct, y=diesel_eff, name="Diesel (Reference)",
    line=dict(width=2, color="gray", dash="dash")))
fig.update_layout(
    template="plotly_dark", height=450,
    xaxis_title="Load (%)", yaxis_title="Thermal Efficiency (%)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

# ─── Application Matrix ───
st.subheader("🎯 Application Matrix")
st.markdown("""
| Application | A-ICE-G1 | PEM-PB-50 | HY-P100 |
|-------------|----------|-----------|---------|
| **Heavy Trucks** | ✅ Primary | ❌ | ❌ |
| **Light Vehicles** | ❌ | ✅ Primary | ❌ |
| **Marine** | ✅ Backup | ❌ | ✅ Primary |
| **Aviation** | ❌ | ✅ UAV | ✅ SAF |
| **Rail (TGV)** | ✅ Freight | ❌ | ✅ High-Speed |
| **Grid Peaker** | ❌ | ❌ | ✅ Primary |
| **F1 / Motorsport** | ✅ Primary | ❌ | ❌ |
| **Drones** | ❌ | ✅ Primary | ❌ |
| **Military** | ✅ Tactical | ✅ Silent | ✅ Naval |
""")

st.caption("PRIMEnergeia S.A.S. — PRIMEngines Division | Zero-Carbon Propulsion for Every Application")
