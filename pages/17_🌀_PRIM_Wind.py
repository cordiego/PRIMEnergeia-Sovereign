"""PRIMEnergeia — PRIM Wind | Hydrogen-Ready Wind Energy Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🌀 PRIM Wind — Hydrogen-Ready Wind Energy")
st.caption("Offshore & Onshore Wind Turbines | Green H₂ Integration | PRIMEnergeia S.A.S.")

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💨 Turbine Class", "IEC I/II")
k2.metric("⚡ Rated Power", "15 MW")
k3.metric("📏 Rotor Dia.", "236 m")
k4.metric("📊 Capacity Factor", "48%")
k5.metric("🔋 H₂ Ready", "YES")

st.divider()

# ─── Wind Farm Scaling ───
st.subheader("🏗️ Wind Farm Scaling Tiers")

tiers = {
    "Onshore 50MW": {"turbines": 10, "power_mw": 50, "cf": 0.35, "capex_per_mw": 1.3,
                     "lcoe": 35, "h2_kg_day": 2400, "area_km2": 25},
    "Onshore 500MW": {"turbines": 100, "power_mw": 500, "cf": 0.36, "capex_per_mw": 1.15,
                      "lcoe": 30, "h2_kg_day": 25000, "area_km2": 200},
    "Offshore 1GW": {"turbines": 67, "power_mw": 1000, "cf": 0.48, "capex_per_mw": 2.8,
                     "lcoe": 55, "h2_kg_day": 65000, "area_km2": 300},
    "Floating 2GW": {"turbines": 133, "power_mw": 2000, "cf": 0.52, "capex_per_mw": 3.2,
                     "lcoe": 62, "h2_kg_day": 140000, "area_km2": 600},
}

cols = st.columns(4)
for i, (name, t) in enumerate(tiers.items()):
    with cols[i]:
        st.markdown(f"**{name}**")
        st.metric("Turbines", f"{t['turbines']}")
        st.metric("Capacity Factor", f"{t['cf']*100:.0f}%")
        annual_gwh = t['power_mw'] * t['cf'] * 8.76
        st.metric("Annual Output", f"{annual_gwh:,.0f} GWh")
        st.metric("LCOE", f"${t['lcoe']}/MWh")
        st.metric("H₂ Production", f"{t['h2_kg_day']:,} kg/day")

st.divider()

# ─── Wind Rose / Power Curve ───
st.subheader("📈 Turbine Power Curve (15 MW)")

wind_speeds = np.arange(0, 30, 0.5)
cut_in = 3
rated_speed = 12
cut_out = 25
rated_power = 15

power = np.zeros_like(wind_speeds)
for i, ws in enumerate(wind_speeds):
    if ws < cut_in:
        power[i] = 0
    elif ws < rated_speed:
        power[i] = rated_power * ((ws - cut_in) / (rated_speed - cut_in)) ** 3
    elif ws <= cut_out:
        power[i] = rated_power
    else:
        power[i] = 0

fig = go.Figure()
fig.add_trace(go.Scatter(x=wind_speeds, y=power, mode="lines",
    fill="tozeroy", fillcolor="rgba(0,191,255,0.2)",
    line=dict(width=3, color="#00BFFF"), name="Power Output"))
fig.add_vline(x=cut_in, line_dash="dash", line_color="gray", annotation_text="Cut-in (3 m/s)")
fig.add_vline(x=rated_speed, line_dash="dash", line_color="#00c878", annotation_text="Rated (12 m/s)")
fig.add_vline(x=cut_out, line_dash="dash", line_color="red", annotation_text="Cut-out (25 m/s)")
fig.update_layout(
    template="plotly_dark", height=400,
    xaxis_title="Wind Speed (m/s)", yaxis_title="Power Output (MW)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

# ─── Wind + Solar + H2 Synergy ───
st.subheader("⚡ Wind-Solar-H₂ Hybrid Output (24hr)")

hours = np.arange(0, 24)
solar = np.maximum(0, np.sin((hours - 6) * np.pi / 12) * 80)
solar[hours < 6] = 0
solar[hours > 18] = 0
np.random.seed(42)
wind = 40 + 20 * np.sin(hours * np.pi / 8) + np.random.normal(0, 8, 24)
wind = np.clip(wind, 5, 90)
total = solar + wind
h2_production = total * 0.018  # kg H2 per MWh

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=hours, y=solar, name="Solar", fill="tozeroy",
    fillcolor="rgba(255,215,0,0.3)", line=dict(color="#FFD700")))
fig2.add_trace(go.Scatter(x=hours, y=wind, name="Wind", fill="tozeroy",
    fillcolor="rgba(0,191,255,0.2)", line=dict(color="#00BFFF")))
fig2.add_trace(go.Scatter(x=hours, y=total, name="Combined",
    line=dict(color="#00c878", width=3)))
fig2.update_layout(
    template="plotly_dark", height=400,
    xaxis_title="Hour", yaxis_title="Power (MW)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig2, use_container_width=True)

st.caption("PRIMEnergeia S.A.S. — PRIM Wind Division | Hydrogen-Ready Wind Energy Systems")
