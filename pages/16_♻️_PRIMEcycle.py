"""PRIMEnergeia — PRIMEcycle | Perovskite Recycling Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("♻️ PRIMEcycle — Circular Economy Platform")
st.caption("Perovskite Module Recycling | Material Recovery | End-of-Life Management | PRIMEnergeia S.A.S.")

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🔄 Recovery Rate", "97.3%")
k2.metric("💰 Pb Recovered", "99.8%")
k3.metric("🌱 CO₂ Avoided", "85%")
k4.metric("⚡ Energy Saved", "78%")
k5.metric("📦 Modules/Day", "500")

st.divider()

# ─── Material Recovery ───
st.subheader("🧪 Material Recovery by Component")

materials = {
    "Glass/ETFE": {"mass_pct": 68, "recovery": 99.5, "value_per_kg": 0.8},
    "Silver (Ag)": {"mass_pct": 0.04, "recovery": 98.0, "value_per_kg": 850},
    "Lead (Pb)": {"mass_pct": 0.05, "recovery": 99.8, "value_per_kg": 2.1},
    "Copper (Cu)": {"mass_pct": 3.2, "recovery": 99.0, "value_per_kg": 8.5},
    "Silicon (Si)": {"mass_pct": 12, "recovery": 95.0, "value_per_kg": 12},
    "FAI / MAI": {"mass_pct": 0.8, "recovery": 92.0, "value_per_kg": 180},
    "PbI₂": {"mass_pct": 1.2, "recovery": 97.5, "value_per_kg": 45},
    "CFRP": {"mass_pct": 8, "recovery": 88.0, "value_per_kg": 15},
    "EVA": {"mass_pct": 5, "recovery": 85.0, "value_per_kg": 1.2},
    "Other": {"mass_pct": 1.71, "recovery": 70.0, "value_per_kg": 0.5},
}

names = list(materials.keys())
recoveries = [m["recovery"] for m in materials.values()]
values = [m["mass_pct"] * m["recovery"] / 100 * m["value_per_kg"] for m in materials.values()]

col1, col2 = st.columns(2)
with col1:
    fig = go.Figure(go.Bar(
        y=names, x=recoveries, orientation="h",
        marker=dict(color=recoveries, colorscale="Viridis", showscale=True,
                   colorbar=dict(title="%")),
        text=[f"{r:.1f}%" for r in recoveries], textposition="auto",
    ))
    fig.update_layout(template="plotly_dark", height=450, title="Recovery Rate (%)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[60, 100]))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig2 = go.Figure(go.Bar(
        y=names, x=values, orientation="h",
        marker=dict(color=values, colorscale="YlOrRd", showscale=True,
                   colorbar=dict(title="$/module")),
        text=[f"${v:.2f}" for v in values], textposition="auto",
    ))
    fig2.update_layout(template="plotly_dark", height=450, title="Recovery Value ($/module)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ─── Circular Economy Flow ───
st.subheader("🔄 Circular Economy Lifecycle")

stages = ["Manufacturing", "Deployment", "Operation (30yr)", "Collection", "Disassembly",
          "Chemical Recovery", "Purification", "Remanufacturing"]
efficiency = [100, 99.5, 92.8, 98, 96, 97.3, 99, 95]

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=stages, y=efficiency, mode="lines+markers",
    marker=dict(size=14, color=efficiency, colorscale="RdYlGn", showscale=True,
               colorbar=dict(title="Yield %")),
    line=dict(width=3, color="#00c878"),
))
fig3.update_layout(
    template="plotly_dark", height=400,
    yaxis_title="Process Yield (%)", yaxis=dict(range=[88, 101]),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig3, use_container_width=True)

# ─── Environmental Impact ───
st.subheader("🌍 Environmental Impact vs Landfill")
c1, c2, c3, c4 = st.columns(4)
c1.metric("CO₂ Avoided", "3.2 kg/module", "vs landfill")
c2.metric("Pb Captured", "99.8%", "zero leaching")
c3.metric("Water Saved", "45 L/module")
c4.metric("Energy ROI", "12:1")

st.caption("PRIMEnergeia S.A.S. — PRIMEcycle Division | Zero-Waste Perovskite Solar Recycling")
