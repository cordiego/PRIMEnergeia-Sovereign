"""PRIMEnergeia — Granas Scale | CEO-Grade Industrial Scaling Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import math

st.header("🏭 Granas Scale — Industrial Manufacturing Roadmap")
st.caption("100 MW → 1 GW → 10 GW | Perovskite Module Scaling | CapEx · LCOE · Revenue · BOM")

# ─── Module Specs ───
MODULE_AREA = 1.7        # m²
MODULE_PCE = 25.6        # %
IRRADIANCE = 1000        # W/m²
MODULE_WP = MODULE_AREA * IRRADIANCE * (MODULE_PCE / 100)  # 435.2 Wp
LIFETIME = 30            # years
ANNUAL_DEG = 0.005       # 0.5%/yr

BOM = {
    "Perovskite ink (FAPbI₃)":      12.50,
    "ETFE front sheet":              8.50,
    "CFRP substrate":               15.00,
    "Mn²⁺ passivation":              3.20,
    "TOPCon heterojunction":        18.00,
    "EVA encapsulant":               4.80,
    "Junction box + connectors":     3.50,
    "Copper busbar":                 2.80,
    "AR coating (nano-TiO₂)":       4.20,
    "GHB granule bed":               6.50,
    "Albedo reflector":              2.50,
    "QC & packaging":                3.50,
}
BOM_TOTAL = sum(BOM.values())

TIERS = {
    "100 MW": dict(mw=100,  lines=2,  tp=60,  capex_wp=0.28, opex_wp=0.008, mod_wp=0.18, bos_wp=0.12, cf=0.22, ppa=45, months=18, emp=120,  color="#00c878"),
    "1 GW":  dict(mw=1000, lines=12, tp=100, capex_wp=0.22, opex_wp=0.006, mod_wp=0.14, bos_wp=0.10, cf=0.23, ppa=38, months=30, emp=800,  color="#FFD700"),
    "10 GW": dict(mw=10000, lines=80, tp=150, capex_wp=0.18, opex_wp=0.005, mod_wp=0.11, bos_wp=0.08, cf=0.24, ppa=32, months=48, emp=5000, color="#FF6347"),
}

# ─── Top KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⚡ Module Power", f"{MODULE_WP:.0f} Wp")
k2.metric("🔬 PCE", f"{MODULE_PCE}%")
k3.metric("📐 Area", f"{MODULE_AREA} m²")
k4.metric("🛡️ Lifetime", f"{LIFETIME} yr")
k5.metric("💵 BOM/Module", f"${BOM_TOTAL:.0f}")

st.divider()

# ─── Tier Selector ───
tier_name = st.selectbox("Select Scale Tier", list(TIERS.keys()), index=1)
t = TIERS[tier_name]
nameplate_w = t["mw"] * 1e6

# ─── Calculations ───
total_modules = math.ceil(nameplate_w / MODULE_WP)
years_to_fill = t["mw"] / (t["lines"] * t["tp"])
modules_per_day = total_modules / (years_to_fill * 365)
land_m2 = (total_modules * MODULE_AREA) / 0.4
land_ha = land_m2 / 10000
land_km2 = land_m2 / 1e6

capex = t["capex_wp"] * nameplate_w / 1e6
opex = t["opex_wp"] * nameplate_w / 1e6
mod_cost = t["mod_wp"] * nameplate_w / 1e6
bos_cost = t["bos_wp"] * nameplate_w / 1e6
bom_total = BOM_TOTAL * total_modules / 1e6

annual_gwh = t["mw"] * t["cf"] * 8760 / 1000
lifetime_gwh = sum(annual_gwh * (1 - ANNUAL_DEG)**yr for yr in range(LIFETIME))

annual_rev = annual_gwh * 1000 * t["ppa"] / 1e6
lifetime_rev = sum(annual_gwh * 1000 * t["ppa"] * (1 - ANNUAL_DEG)**yr / 1e6 for yr in range(LIFETIME))

total_cost = capex + opex * LIFETIME
lcoe = total_cost * 1e6 / (lifetime_gwh * 1e3)
payback = capex / (annual_rev - opex) if (annual_rev - opex) > 0 else float('inf')
avg_pce = MODULE_PCE * (lifetime_gwh / (annual_gwh * LIFETIME))

# ─── Tier Metrics ───
st.subheader(f"🏭 {tier_name} — {t['mw']:,} MW Nameplate")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🔢 Total Modules", f"{total_modules:,}")
m2.metric("📦 Modules/Day", f"{modules_per_day:,.0f}")
m3.metric("🏗️ Mfg Lines", f"{t['lines']}")
m4.metric("👷 Employees", f"{t['emp']:,}")

m5, m6, m7, m8 = st.columns(4)
m5.metric("💰 CapEx", f"${capex:,.0f}M")
m6.metric("📉 LCOE", f"${lcoe:.2f}/MWh")
m7.metric("💵 Annual Revenue", f"${annual_rev:,.0f}M")
m8.metric("⏱️ Payback", f"{payback:.1f} yr")

m9, m10, m11, m12 = st.columns(4)
m9.metric("⚡ Annual Energy", f"{annual_gwh:,.0f} GWh")
m10.metric("🌍 Land", f"{land_km2:.1f} km²")
m11.metric("🏦 Lifetime Revenue", f"${lifetime_rev:,.0f}M")
m12.metric("🔬 Avg PCE (30yr)", f"{avg_pce:.1f}%")

st.divider()

# ─── Comparison Chart ───
st.subheader("📊 Tier Comparison")
tab1, tab2, tab3 = st.tabs(["💰 Financial", "⚡ Energy", "🏭 Manufacturing"])

with tab1:
    tiers_data = []
    for name, cfg in TIERS.items():
        nw = cfg["mw"] * 1e6
        cx = cfg["capex_wp"] * nw / 1e6
        ox = cfg["opex_wp"] * nw / 1e6
        agwh = cfg["mw"] * cfg["cf"] * 8760 / 1000
        lgwh = sum(agwh * (1 - ANNUAL_DEG)**yr for yr in range(LIFETIME))
        tc = cx + ox * LIFETIME
        l = tc * 1e6 / (lgwh * 1e3)
        ar = agwh * 1000 * cfg["ppa"] / 1e6
        lr = sum(agwh * 1000 * cfg["ppa"] * (1 - ANNUAL_DEG)**yr / 1e6 for yr in range(LIFETIME))
        pb = cx / (ar - ox) if (ar - ox) > 0 else 0
        tiers_data.append(dict(name=name, capex=cx, lcoe=l, annual_rev=ar, lifetime_rev=lr, payback=pb, color=cfg["color"]))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="CapEx ($M)", x=[d["name"] for d in tiers_data],
        y=[d["capex"] for d in tiers_data],
        marker_color=[d["color"] for d in tiers_data],
        text=[f"${d['capex']:,.0f}M" for d in tiers_data], textposition="outside"
    ))
    fig.update_layout(
        title="Capital Expenditure by Scale", template="plotly_dark",
        yaxis_title="CapEx ($M)", height=400,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=[d["name"] for d in tiers_data],
            y=[d["lcoe"] for d in tiers_data],
            marker_color=[d["color"] for d in tiers_data],
            text=[f"${d['lcoe']:.2f}" for d in tiers_data], textposition="outside"
        ))
        fig2.update_layout(title="LCOE ($/MWh)", template="plotly_dark", height=350,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
    with c2:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=[d["name"] for d in tiers_data],
            y=[d["payback"] for d in tiers_data],
            marker_color=[d["color"] for d in tiers_data],
            text=[f"{d['payback']:.1f} yr" for d in tiers_data], textposition="outside"
        ))
        fig3.update_layout(title="Payback Period (years)", template="plotly_dark", height=350,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

with tab2:
    fig4 = go.Figure()
    for name, cfg in TIERS.items():
        agwh = cfg["mw"] * cfg["cf"] * 8760 / 1000
        years = list(range(1, LIFETIME + 1))
        cumulative = [sum(agwh * (1 - ANNUAL_DEG)**yr for yr in range(y)) for y in years]
        fig4.add_trace(go.Scatter(
            x=years, y=cumulative, name=name, mode="lines",
            line=dict(width=3, color=cfg["color"]),
        ))
    fig4.update_layout(
        title="Cumulative Energy Production (GWh) — 30-Year Lifetime",
        xaxis_title="Year", yaxis_title="Cumulative GWh",
        template="plotly_dark", height=450,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig4, use_container_width=True)

with tab3:
    fig5 = go.Figure()
    names = list(TIERS.keys())
    modules = [math.ceil(TIERS[n]["mw"] * 1e6 / MODULE_WP) for n in names]
    colors = [TIERS[n]["color"] for n in names]
    fig5.add_trace(go.Bar(
        x=names, y=modules, marker_color=colors,
        text=[f"{m:,}" for m in modules], textposition="outside"
    ))
    fig5.update_layout(
        title="Total Modules Required", template="plotly_dark", height=400,
        yaxis_title="Modules", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ─── BOM Breakdown ───
st.subheader("📋 Bill of Materials (per module)")
c1, c2 = st.columns([2, 1])
with c1:
    labels = list(BOM.keys())
    values = list(BOM.values())
    fig6 = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        hole=0.45, textinfo="label+percent",
        marker=dict(colors=[
            "#FF6347", "#FFD700", "#00c878", "#00BFFF", "#FF69B4",
            "#9370DB", "#20B2AA", "#F0E68C", "#DDA0DD", "#87CEEB",
            "#98FB98", "#FFA07A"
        ]),
    )])
    fig6.update_layout(
        title=f"BOM Breakdown — ${BOM_TOTAL:.0f}/module",
        template="plotly_dark", height=450,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig6, use_container_width=True)

with c2:
    st.markdown("**Component Costs**")
    for comp, cost in sorted(BOM.items(), key=lambda x: -x[1]):
        pct = cost / BOM_TOTAL * 100
        st.markdown(f"- **{comp}**: ${cost:.2f} ({pct:.0f}%)")
    st.markdown(f"---\n**Total: ${BOM_TOTAL:.2f}**")

st.divider()

# ─── Revenue Waterfall ───
st.subheader("💰 Lifetime Revenue Projection")
fig7 = go.Figure()
for name, cfg in TIERS.items():
    agwh = cfg["mw"] * cfg["cf"] * 8760 / 1000
    years = list(range(1, LIFETIME + 1))
    cumrev = [sum(agwh * 1000 * cfg["ppa"] * (1 - ANNUAL_DEG)**yr / 1e6 for yr in range(y)) for y in years]
    fig7.add_trace(go.Scatter(
        x=years, y=cumrev, name=name, mode="lines+markers",
        line=dict(width=3, color=cfg["color"]),
        marker=dict(size=4),
    ))
fig7.update_layout(
    xaxis_title="Year", yaxis_title="Cumulative Revenue ($M)",
    template="plotly_dark", height=450,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig7, use_container_width=True)

# ─── Architecture ───
st.divider()
st.subheader("🧬 Granas Architecture Stack")
stack = {
    "SIBO": "Bayesian optimization · PCE maximization",
    "Optics": "Photon harvesting · AR coating",
    "SDL": "Self-driving laboratory integration",
    "CFRP": "Composite frame · structural analysis",
    "ETFE": "Encapsulation · 30-year durability",
    "TOPCon": "Si heterojunction · rear contact",
    "GHB": "Granule Heat Bed · thermal management",
    "Albedo": "Bifacial albedo gain modeling",
    "Metrics": "FoM scoring · benchmarking",
    "Blueprint": "Full fabrication specification",
    "Scale": "Industrial scaling · 100MW → 10GW",
}
cols = st.columns(4)
for i, (eng, desc) in enumerate(stack.items()):
    cols[i % 4].markdown(f"**{eng}**  \n{desc}")

st.caption("PRIMEnergeia S.A.S. — Granas Scale Industrial Manufacturing Roadmap")
