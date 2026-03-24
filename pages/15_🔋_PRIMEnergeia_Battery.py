"""PRIMEnergeia — Battery Storage System Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🔋 PRIMEnergeia Battery — Grid-Scale Energy Storage")
st.caption("Perovskite Solar + Battery Integration | Lithium-Iron-Phosphate (LFP) & Solid-State | PRIMEnergeia S.A.S.")

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⚡ Chemistry", "LFP / SSB")
k2.metric("📦 Capacity", "100 MWh")
k3.metric("🔄 Cycles", "6,000+")
k4.metric("⏱️ Duration", "4 hr")
k5.metric("📊 RTE", "92%")

st.divider()

# ─── Storage Tiers ───
st.subheader("📊 Battery Storage Scaling Tiers")

tiers = {
    "Residential": {"capacity_kwh": 13.5, "power_kw": 5, "cycles": 6000, "cost_per_kwh": 350, "units": 1},
    "Commercial": {"capacity_kwh": 500, "power_kw": 125, "cycles": 5000, "cost_per_kwh": 280, "units": 1},
    "Utility 10MW": {"capacity_kwh": 40000, "power_kw": 10000, "cycles": 5000, "cost_per_kwh": 220, "units": 1},
    "Grid 100MW": {"capacity_kwh": 400000, "power_kw": 100000, "cycles": 5000, "cost_per_kwh": 180, "units": 1},
}

cols = st.columns(4)
for i, (name, t) in enumerate(tiers.items()):
    with cols[i]:
        st.markdown(f"**{name}**")
        st.metric("Capacity", f"{t['capacity_kwh']:,.0f} kWh")
        st.metric("Power", f"{t['power_kw']:,.0f} kW")
        st.metric("Cost/kWh", f"${t['cost_per_kwh']}")
        total = t['capacity_kwh'] * t['cost_per_kwh'] / 1000
        st.metric("Total Cost", f"${total:,.0f}K")

st.divider()

# ─── Degradation Curve ───
st.subheader("📉 Capacity Degradation Over Lifetime")
years = np.arange(0, 21)
lfp_cap = 100 * (1 - 0.02) ** years  # 2%/yr degradation
ssb_cap = 100 * (1 - 0.01) ** years   # 1%/yr degradation (solid-state)

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=lfp_cap, name="LFP", mode="lines",
    line=dict(width=3, color="#00c878"), fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"))
fig.add_trace(go.Scatter(x=years, y=ssb_cap, name="Solid-State", mode="lines",
    line=dict(width=3, color="#FFD700"), fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"))
fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80% EOL Threshold")
fig.update_layout(
    template="plotly_dark", height=400,
    xaxis_title="Years", yaxis_title="Capacity Retention (%)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

# ─── Solar + Storage Synergy ───
st.subheader("☀️🔋 Solar-Storage Revenue Stack")
hours = np.arange(0, 24)
solar = np.maximum(0, np.sin((hours - 6) * np.pi / 12) * 100)
solar[hours < 6] = 0
solar[hours > 18] = 0
demand = 40 + 30 * np.sin((hours - 3) * np.pi / 12)
storage_charge = np.where((solar > demand) & (solar > 0), np.minimum(solar - demand, 25), 0)
storage_discharge = np.where((demand > solar + 5) & (hours > 16), np.minimum(demand - solar, 25), 0)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=hours, y=solar, name="Solar Generation", fill="tozeroy",
    fillcolor="rgba(255,215,0,0.3)", line=dict(color="#FFD700", width=2)))
fig2.add_trace(go.Scatter(x=hours, y=demand, name="Grid Demand",
    line=dict(color="#FF6347", width=2, dash="dash")))
fig2.add_trace(go.Bar(x=hours, y=storage_charge, name="Battery Charging",
    marker_color="rgba(0,200,120,0.6)"))
fig2.add_trace(go.Bar(x=hours, y=-storage_discharge, name="Battery Discharging",
    marker_color="rgba(0,191,255,0.6)"))
fig2.update_layout(
    template="plotly_dark", height=400, barmode="relative",
    xaxis_title="Hour of Day", yaxis_title="Power (MW)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig2, use_container_width=True)

st.caption("PRIMEnergeia S.A.S. — Battery Storage Division | Grid-Scale Energy Storage for Perovskite Solar Integration")
