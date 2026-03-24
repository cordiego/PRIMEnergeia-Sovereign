"""PRIMEnergeia — Battery Storage System | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── CEO Styling ───
st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
.block-container {padding-top: 1rem}
</style>""", unsafe_allow_html=True)

st.header("🔋 PRIMEnergeia Battery — Grid-Scale Energy Storage")
st.caption("Perovskite Solar + Storage Integration | LFP · Solid-State · Flow | PRIMEnergeia S.A.S.")

# ─── Executive KPIs ───
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🔬 Chemistry", "LFP / SSB")
k2.metric("📦 System Cap.", "400 MWh")
k3.metric("🔄 Cycle Life", "6,000+")
k4.metric("⏱️ Duration", "4 hr")
k5.metric("⚡ RTE", "92.5%")
k6.metric("📉 Degradation", "2%/yr")

st.divider()

# ─── Tier Selection ───
tier = st.radio("Storage Tier", ["Residential (13.5 kWh)", "Commercial (500 kWh)", "Utility (40 MWh)", "Grid (400 MWh)"], horizontal=True, index=3)

tier_data = {
    "Residential (13.5 kWh)": {"cap": 13.5, "power": 5, "cycles": 6000, "cost_kwh": 350, "rte": 0.94, "warranty": 10, "footprint": 1.2},
    "Commercial (500 kWh)": {"cap": 500, "power": 125, "cycles": 5000, "cost_kwh": 280, "rte": 0.93, "warranty": 15, "footprint": 40},
    "Utility (40 MWh)": {"cap": 40000, "power": 10000, "cycles": 5000, "cost_kwh": 220, "rte": 0.925, "warranty": 20, "footprint": 2000},
    "Grid (400 MWh)": {"cap": 400000, "power": 100000, "cycles": 5000, "cost_kwh": 180, "rte": 0.92, "warranty": 25, "footprint": 15000},
}
td = tier_data[tier]

t1, t2, t3, t4, t5, t6 = st.columns(6)
t1.metric("Capacity", f"{td['cap']:,.0f} kWh")
t2.metric("Power", f"{td['power']:,.0f} kW")
t3.metric("Round-Trip Eff.", f"{td['rte']*100:.1f}%")
t4.metric("Cost/kWh", f"${td['cost_kwh']}")
t5.metric("CapEx", f"${td['cap'] * td['cost_kwh'] / 1e6:,.1f}M")
t6.metric("Warranty", f"{td['warranty']} yr")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📉 Degradation", "☀️ Solar-Storage", "💰 Revenue", "🔬 Chemistry"])

with tab1:
    years = np.arange(0, 26)
    lfp = 100 * (1 - 0.020) ** years
    ssb = 100 * (1 - 0.008) ** years
    flow = 100 * (1 - 0.003) ** years
    nmc = 100 * (1 - 0.030) ** years

    fig = go.Figure()
    for name, data, color in [("NMC (Legacy)", nmc, "#FF6347"), ("LFP", lfp, "#00c878"),
                               ("Solid-State", ssb, "#FFD700"), ("Vanadium Flow", flow, "#00BFFF")]:
        fig.add_trace(go.Scatter(x=years, y=data, name=name, mode="lines", line=dict(width=3, color=color)))
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80% EOL")
    fig.add_hline(y=70, line_dash="dot", line_color="orange", annotation_text="70% Warranty Floor")
    fig.update_layout(template="plotly_dark", height=450, title="Capacity Retention by Chemistry",
        xaxis_title="Years", yaxis_title="Capacity (%)", yaxis=dict(range=[50, 102]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig, use_container_width=True)

    # EOL year table
    st.markdown("**Years to 80% EOL:**")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("NMC", "7.4 yr", delta="-Bad", delta_color="inverse")
    e2.metric("LFP", "11.1 yr")
    e3.metric("Solid-State", "27.7 yr", delta="+Best")
    e4.metric("Vanadium Flow", "74.2 yr", delta="+Exceptional")

with tab2:
    hours = np.arange(0, 24)
    solar = np.maximum(0, np.sin((hours - 6) * np.pi / 12) * td['power'] / 1000)
    solar[hours < 6] = 0; solar[hours > 18] = 0
    demand = td['power'] / 1000 * (0.4 + 0.3 * np.sin((hours - 3) * np.pi / 12))

    soc = np.zeros(24)
    soc[0] = 20
    charge = np.zeros(24)
    discharge = np.zeros(24)
    max_charge_rate = td['power'] / 1000 * 0.25

    for h in range(24):
        surplus = solar[h] - demand[h]
        if surplus > 0 and soc[h] < 95:
            charge[h] = min(surplus, max_charge_rate, (95 - soc[h]) / 100 * td['cap'] / 1000)
            soc[h] = min(95, soc[h] + charge[h] / (td['cap'] / 1000) * 100)
        elif surplus < 0 and soc[h] > 10:
            discharge[h] = min(-surplus, max_charge_rate, (soc[h] - 10) / 100 * td['cap'] / 1000)
            soc[h] = max(10, soc[h] - discharge[h] / (td['cap'] / 1000) * 100)
        if h < 23:
            soc[h + 1] = soc[h]

    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=("Power Flow (MW)", "State of Charge (%)"))
    fig2.add_trace(go.Scatter(x=hours, y=solar, name="Solar", fill="tozeroy",
        fillcolor="rgba(255,215,0,0.3)", line=dict(color="#FFD700", width=2)), row=1, col=1)
    fig2.add_trace(go.Scatter(x=hours, y=demand, name="Demand",
        line=dict(color="#FF6347", width=2, dash="dash")), row=1, col=1)
    fig2.add_trace(go.Bar(x=hours, y=charge, name="Charging", marker_color="rgba(0,200,120,0.7)"), row=1, col=1)
    fig2.add_trace(go.Bar(x=hours, y=-discharge, name="Discharging", marker_color="rgba(0,191,255,0.7)"), row=1, col=1)
    fig2.add_trace(go.Scatter(x=hours, y=soc, name="SOC", fill="tozeroy",
        fillcolor="rgba(0,200,120,0.15)", line=dict(color="#00c878", width=3)), row=2, col=1)
    fig2.update_layout(template="plotly_dark", height=550, barmode="relative",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    years_r = np.arange(1, 26)
    # Revenue from arbitrage + capacity payments + ancillary services
    arbitrage = td['cap'] * 0.15 * 365 / 1e6 * (1 - 0.02) ** years_r  # $/kWh spread * days
    capacity = td['power'] * 50 * 12 / 1e6 * np.ones_like(years_r, dtype=float)  # $/kW-month
    ancillary = td['power'] * 8 * 365 / 1e6 * np.ones_like(years_r, dtype=float)  # freq reg

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=years_r, y=np.cumsum(arbitrage), name="Energy Arbitrage",
        fill="tozeroy", fillcolor="rgba(255,215,0,0.2)", line=dict(color="#FFD700")))
    fig3.add_trace(go.Scatter(x=years_r, y=np.cumsum(arbitrage + capacity), name="+ Capacity Payments",
        fill="tonexty", fillcolor="rgba(0,200,120,0.2)", line=dict(color="#00c878")))
    fig3.add_trace(go.Scatter(x=years_r, y=np.cumsum(arbitrage + capacity + ancillary), name="+ Ancillary Services",
        fill="tonexty", fillcolor="rgba(0,191,255,0.15)", line=dict(color="#00BFFF", width=3)))
    capex_line = td['cap'] * td['cost_kwh'] / 1e6
    fig3.add_hline(y=capex_line, line_dash="dash", line_color="red",
        annotation_text=f"CapEx: ${capex_line:,.1f}M")
    fig3.update_layout(template="plotly_dark", height=450, title="Cumulative Revenue Stack (25yr)",
        xaxis_title="Year", yaxis_title="Cumulative Revenue ($M)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.markdown("""
    | Parameter | LFP | Solid-State | Vanadium Flow | NMC |
    |-----------|-----|-------------|---------------|-----|
    | **Energy Density** | 160 Wh/kg | 400 Wh/kg | 25 Wh/kg | 250 Wh/kg |
    | **Cycle Life** | 6,000 | 10,000+ | 20,000+ | 2,000 |
    | **Safety** | ✅ Excellent | ✅ Excellent | ✅ Excellent | ⚠️ Moderate |
    | **Cost (2026)** | $110/kWh | $200/kWh | $350/kWh | $130/kWh |
    | **Operating Temp** | -20 to 60°C | -30 to 80°C | 10 to 40°C | -20 to 55°C |
    | **Self-Discharge** | 2%/month | <1%/month | 0%/month | 3%/month |
    | **Scalability** | 🟢 GW-scale | 🟡 MW-scale | 🟢 GW-scale | 🟢 GW-scale |
    | **Granas Fit** | ✅ Primary | ✅ Future | 🟡 Auxiliary | ❌ Legacy |
    """)

st.caption("PRIMEnergeia S.A.S. — Battery Division | Grid-Scale Energy Storage for Perovskite Solar Integration")
