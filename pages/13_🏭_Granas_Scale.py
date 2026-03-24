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

# ─── MULTI-REVENUE STREAM ENGINE ───
st.subheader("💎 Revenue Streams — Beyond Energy")
st.caption("Carbon credits · Green hydrogen · Green ammonia · Albedo cooling · Energy sales")

# Revenue stream parameters
GRID_EMISSION_FACTOR = 0.45     # tCO2/MWh (Mexico grid average)
CARBON_PRICE = 50.0             # $/tCO2 (voluntary market avg)
CARBON_PRICE_GROWTH = 0.05      # 5%/yr price escalation

ELECTROLYZER_EFF = 0.70         # 70% efficiency (PEM)
H2_KWH_PER_KG = 55.0           # kWh electricity per kg H2
H2_PRICE = 4.50                 # $/kg green H2
H2_SOLAR_FRACTION = 0.15        # 15% of energy diverted to H2

NH3_KG_PER_KG_H2 = 5.67        # kg NH3 per kg H2 (Haber-Bosch)
NH3_PRICE = 800                 # $/tonne green ammonia
NH3_CONVERSION = 0.30           # 30% of H2 goes to NH3

ALBEDO_RF_OFFSET = 0.002        # W/m² radiative forcing offset per m² of albedo panel
ALBEDO_CREDIT = 15.0            # $/tCO2e equivalent for cooling credit
ALBEDO_TCO2E_PER_M2_YR = 0.01  # tCO2e offset per m² per year

# ─── Calculate all revenue streams ───
# 1. Energy revenue (already calculated above)
energy_annual = annual_rev

# 2. Carbon credits
annual_avoided_co2 = annual_gwh * 1000 * GRID_EMISSION_FACTOR  # tonnes CO2
carbon_annual = annual_avoided_co2 * CARBON_PRICE / 1e6  # $M

# 3. Green hydrogen
h2_energy_gwh = annual_gwh * H2_SOLAR_FRACTION
h2_kg_annual = h2_energy_gwh * 1e6 / H2_KWH_PER_KG  # kg H2
h2_annual = h2_kg_annual * H2_PRICE / 1e6  # $M

# 4. Green ammonia (from H2)
nh3_kg_annual = h2_kg_annual * NH3_CONVERSION * NH3_KG_PER_KG_H2
nh3_annual = nh3_kg_annual * NH3_PRICE / 1e9  # $M (price is per tonne)

# 5. Albedo cooling credits
albedo_area = total_modules * MODULE_AREA  # m² of reflective surface
albedo_co2e = albedo_area * ALBEDO_TCO2E_PER_M2_YR  # tCO2e
albedo_annual = albedo_co2e * ALBEDO_CREDIT / 1e6  # $M

# Total
total_annual = energy_annual + carbon_annual + h2_annual + nh3_annual + albedo_annual

# ─── Revenue Stream KPIs ───
r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("⚡ Energy", f"${energy_annual:,.1f}M/yr", delta=f"{energy_annual/total_annual*100:.0f}%")
r2.metric("🌱 Carbon", f"${carbon_annual:,.1f}M/yr", delta=f"{annual_avoided_co2:,.0f} tCO2")
r3.metric("💧 Hydrogen", f"${h2_annual:,.1f}M/yr", delta=f"{h2_kg_annual/1e6:,.1f}M kg")
r4.metric("🧪 Ammonia", f"${nh3_annual:,.1f}M/yr", delta=f"{nh3_kg_annual/1e6:,.2f}M kg")
r5.metric("🪞 Albedo", f"${albedo_annual:,.2f}M/yr", delta=f"{albedo_co2e:,.0f} tCO2e")

st.markdown(f"### **Total Annual Revenue: ${total_annual:,.1f}M** — {total_annual/energy_annual:.1f}x energy-only")

# ─── Revenue Breakdown Pie ───
c1, c2 = st.columns([2, 1])
with c1:
    fig_rev = go.Figure(data=[go.Pie(
        labels=["Energy Sales", "Carbon Credits", "Green Hydrogen", "Green Ammonia", "Albedo Cooling"],
        values=[energy_annual, carbon_annual, h2_annual, nh3_annual, albedo_annual],
        hole=0.5, textinfo="label+percent+value",
        texttemplate="%{label}<br>$%{value:.1f}M<br>%{percent}",
        marker=dict(colors=["#FFD700", "#00c878", "#00BFFF", "#9370DB", "#FF69B4"]),
    )])
    fig_rev.update_layout(
        title=f"Annual Revenue Mix — {tier_name}",
        template="plotly_dark", height=450,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_rev, use_container_width=True)

with c2:
    st.markdown("**Revenue Streams**")
    streams = [
        ("⚡ Energy", energy_annual, t["ppa"], "$/MWh PPA"),
        ("🌱 Carbon", carbon_annual, CARBON_PRICE, "$/tCO2"),
        ("💧 Hydrogen", h2_annual, H2_PRICE, "$/kg H2"),
        ("🧪 Ammonia", nh3_annual, NH3_PRICE, "$/tonne"),
        ("🪞 Albedo", albedo_annual, ALBEDO_CREDIT, "$/tCO2e"),
    ]
    for emoji_name, val, price, unit in streams:
        pct = val / total_annual * 100
        st.markdown(f"- **{emoji_name}**: ${val:,.1f}M ({pct:.0f}%) @ {price} {unit}")
    st.markdown(f"---\n**Total: ${total_annual:,.1f}M/yr**")

st.divider()

# ─── 30-Year Multi-Stream Cumulative Revenue ───
st.subheader("📈 30-Year Cumulative Revenue — All Streams")

fig_multi = go.Figure()
years = list(range(1, LIFETIME + 1))

for name, cfg in TIERS.items():
    agwh = cfg["mw"] * cfg["cf"] * 8760 / 1000
    t_mods = math.ceil(cfg["mw"] * 1e6 / MODULE_WP)

    cum_total = []
    running = 0
    for yr in range(LIFETIME):
        deg = (1 - ANNUAL_DEG) ** yr
        cp = CARBON_PRICE * (1 + CARBON_PRICE_GROWTH) ** yr  # escalating carbon price

        e_rev = agwh * 1000 * cfg["ppa"] * deg / 1e6
        c_rev = agwh * 1000 * GRID_EMISSION_FACTOR * cp * deg / 1e6
        h_gwh = agwh * H2_SOLAR_FRACTION * deg
        h_kg = h_gwh * 1e6 / H2_KWH_PER_KG
        h_rev = h_kg * H2_PRICE / 1e6
        n_kg = h_kg * NH3_CONVERSION * NH3_KG_PER_KG_H2
        n_rev = n_kg * NH3_PRICE / 1e9
        a_rev = t_mods * MODULE_AREA * ALBEDO_TCO2E_PER_M2_YR * ALBEDO_CREDIT / 1e6

        running += e_rev + c_rev + h_rev + n_rev + a_rev
        cum_total.append(running)

    fig_multi.add_trace(go.Scatter(
        x=years, y=cum_total, name=name, mode="lines",
        line=dict(width=3, color=cfg["color"]),
    ))

fig_multi.update_layout(
    xaxis_title="Year", yaxis_title="Cumulative Revenue ($M)",
    template="plotly_dark", height=450,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    title="Total Revenue — Energy + Carbon + H2 + NH3 + Albedo",
)
st.plotly_chart(fig_multi, use_container_width=True)

# ─── Stacked area by stream ───
st.subheader("🔋 Revenue Stack — Stream Breakdown Over Time")
fig_stack = go.Figure()

agwh_sel = t["mw"] * t["cf"] * 8760 / 1000
t_mods_sel = total_modules

streams_data = {"Energy": [], "Carbon": [], "Hydrogen": [], "Ammonia": [], "Albedo": []}
for yr in range(LIFETIME):
    deg = (1 - ANNUAL_DEG) ** yr
    cp = CARBON_PRICE * (1 + CARBON_PRICE_GROWTH) ** yr
    streams_data["Energy"].append(agwh_sel * 1000 * t["ppa"] * deg / 1e6)
    streams_data["Carbon"].append(agwh_sel * 1000 * GRID_EMISSION_FACTOR * cp * deg / 1e6)
    h_gwh = agwh_sel * H2_SOLAR_FRACTION * deg
    h_kg = h_gwh * 1e6 / H2_KWH_PER_KG
    streams_data["Hydrogen"].append(h_kg * H2_PRICE / 1e6)
    n_kg = h_kg * NH3_CONVERSION * NH3_KG_PER_KG_H2
    streams_data["Ammonia"].append(n_kg * NH3_PRICE / 1e9)
    streams_data["Albedo"].append(t_mods_sel * MODULE_AREA * ALBEDO_TCO2E_PER_M2_YR * ALBEDO_CREDIT / 1e6)

colors_stack = {"Energy": "#FFD700", "Carbon": "#00c878", "Hydrogen": "#00BFFF", "Ammonia": "#9370DB", "Albedo": "#FF69B4"}
for stream, vals in streams_data.items():
    fig_stack.add_trace(go.Scatter(
        x=years, y=vals, name=stream, stackgroup="one",
        line=dict(width=0.5, color=colors_stack[stream]),
    ))

fig_stack.update_layout(
    title=f"Annual Revenue by Stream — {tier_name}",
    xaxis_title="Year", yaxis_title="Revenue ($M/yr)",
    template="plotly_dark", height=450,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_stack, use_container_width=True)

st.divider()

# ─── Comparative Table ───
st.subheader("📊 Multi-Stream Comparison — All Tiers")
comp_data = []
for name, cfg in TIERS.items():
    agwh = cfg["mw"] * cfg["cf"] * 8760 / 1000
    t_mods = math.ceil(cfg["mw"] * 1e6 / MODULE_WP)

    e = agwh * 1000 * cfg["ppa"] / 1e6
    c = agwh * 1000 * GRID_EMISSION_FACTOR * CARBON_PRICE / 1e6
    h_gwh = agwh * H2_SOLAR_FRACTION
    h_kg = h_gwh * 1e6 / H2_KWH_PER_KG
    h = h_kg * H2_PRICE / 1e6
    n_kg = h_kg * NH3_CONVERSION * NH3_KG_PER_KG_H2
    n = n_kg * NH3_PRICE / 1e9
    a = t_mods * MODULE_AREA * ALBEDO_TCO2E_PER_M2_YR * ALBEDO_CREDIT / 1e6
    tot = e + c + h + n + a

    comp_data.append({
        "Tier": name,
        "Energy ($M)": f"${e:,.1f}",
        "Carbon ($M)": f"${c:,.1f}",
        "H2 ($M)": f"${h:,.1f}",
        "NH3 ($M)": f"${n:,.1f}",
        "Albedo ($M)": f"${a:,.2f}",
        "Total ($M)": f"${tot:,.1f}",
        "Multiplier": f"{tot/e:.1f}x",
    })

st.table(comp_data)

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

# ─── Architecture ───
st.subheader("🧬 Granas Architecture Stack")
stack = {
    "SIBO": "Bayesian optimization - PCE maximization",
    "Optics": "Photon harvesting - AR coating",
    "SDL": "Self-driving laboratory integration",
    "CFRP": "Composite frame - structural analysis",
    "ETFE": "Encapsulation - 30-year durability",
    "TOPCon": "Si heterojunction - rear contact",
    "GHB": "Granule Heat Bed - thermal management",
    "Albedo": "Bifacial albedo gain modeling",
    "Metrics": "FoM scoring - benchmarking",
    "Blueprint": "Full fabrication specification",
    "Scale": "Industrial scaling - 100MW to 10GW",
}
cols = st.columns(4)
for i, (eng, desc) in enumerate(stack.items()):
    cols[i % 4].markdown(f"**{eng}**  \n{desc}")

st.caption("PRIMEnergeia S.A.S. - Granas Scale Industrial Manufacturing Roadmap")

