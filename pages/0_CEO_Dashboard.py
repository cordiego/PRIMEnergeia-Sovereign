"""PRIMEnergeia - CEO Executive Dashboard | Sovereign Command Center"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(layout="wide") if "page_config_set" not in st.session_state else None

st.markdown("""
<style>
.ceo-title {font-size: 32px; font-weight: 800; background: linear-gradient(90deg, #FFD700, #00c878); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0}
.ceo-sub {font-size: 14px; color: #888; margin-top: -10px}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="ceo-title">PRIMEnergeia S.A.S. - CEO Command Center</p>', unsafe_allow_html=True)
st.markdown(f'<p class="ceo-sub">Sovereign Overview | {datetime.now().strftime("%B %d, %Y %H:%M")} CST</p>', unsafe_allow_html=True)

st.divider()

# Division Portfolio
st.subheader("Division Portfolio")

d1, d2, d3, d4, d5, d6 = st.columns(6)
d1.metric("Granas Solar", "25.6% PCE", "Perovskite-Si Tandem")
d2.metric("Eureka Trading", "VIX-Regime", "Volatility Targeting")
d3.metric("SIBO API", "SaaS Live", "GP Optimizer")
d4.metric("PRIMEngines", "3 Engines", "NH3 / H2 / PEM")
d5.metric("Battery", "100 MWh", "LFP + Solid-State")
d6.metric("Wind", "15 MW", "H2-Ready Turbines")

st.divider()

# Financial Projections
st.subheader("Granas Scale - Financial Projections")

# Revenue projections
tiers = {
    "100 MW": {"capex": 28, "annual_rev": 8.67, "lcoe": 17.42, "payback": 3.3, "lifetime_rev": 236, "employees": 120},
    "1 GW": {"capex": 220, "annual_rev": 73.6, "lcoe": 13.53, "payback": 3.1, "lifetime_rev": 2006, "employees": 800},
    "10 GW": {"capex": 1800, "annual_rev": 672, "lcoe": 10.87, "payback": 2.8, "lifetime_rev": 18306, "employees": 5000},
}

tier_select = st.radio("Select Scale", ["100 MW", "1 GW", "10 GW"], horizontal=True, index=1)
t = tiers[tier_select]

f1, f2, f3, f4, f5, f6 = st.columns(6)
f1.metric("CapEx", f"\${t['capex']}M")
f2.metric("Annual Revenue", f"\${t['annual_rev']:.0f}M")
f3.metric("LCOE", f"\${t['lcoe']:.2f}/MWh")
f4.metric("Payback", f"{t['payback']} yr")
f5.metric("30yr Revenue", f"\${t['lifetime_rev']:,.0f}M")
f6.metric("Employees", f"{t['employees']:,}")

# 30-year cumulative revenue chart
years = np.arange(1, 31)
degradation = (1 - 0.005) ** years
cum_rev = np.cumsum(t["annual_rev"] * degradation)

# Multi-revenue streams (Energy + Carbon + H2 + NH3 + Albedo)
energy_rev = cum_rev
carbon_rev = cum_rev * 0.15
h2_rev = cum_rev * 0.25
nh3_rev = cum_rev * 0.12
albedo_rev = cum_rev * 0.08
total_rev = energy_rev + carbon_rev + h2_rev + nh3_rev + albedo_rev

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=energy_rev, name="Energy (PPA)", fill="tozeroy",
    fillcolor="rgba(255,215,0,0.3)", line=dict(color="#FFD700")))
fig.add_trace(go.Scatter(x=years, y=energy_rev + carbon_rev, name="+ Carbon Credits", fill="tonexty",
    fillcolor="rgba(0,200,120,0.2)", line=dict(color="#00c878")))
fig.add_trace(go.Scatter(x=years, y=energy_rev + carbon_rev + h2_rev, name="+ Green H2", fill="tonexty",
    fillcolor="rgba(0,191,255,0.2)", line=dict(color="#00BFFF")))
fig.add_trace(go.Scatter(x=years, y=energy_rev + carbon_rev + h2_rev + nh3_rev, name="+ Green NH3", fill="tonexty",
    fillcolor="rgba(255,99,71,0.15)", line=dict(color="#FF6347")))
fig.add_trace(go.Scatter(x=years, y=total_rev, name="+ Albedo Cooling", fill="tonexty",
    fillcolor="rgba(148,103,189,0.15)", line=dict(color="#9467bd", width=3)))

fig.update_layout(
    template="plotly_dark", height=400,
    title=f"{tier_select} - 30-Year Cumulative Multi-Stream Revenue",
    xaxis_title="Year", yaxis_title="Cumulative Revenue (\$$M)",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=-0.15),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# Technology Architecture
st.subheader("Technology Architecture")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Granas Solar Stack")
    st.markdown("""
    | Layer | Technology |
    |-------|-----------|
    | Absorber | FAPbI3 Perovskite |
    | Rear Cell | TOPCon Si HJT |
    | Encapsulation | ETFE + Mn2+ |
    | Substrate | CFRP Composite |
    | Thermal | GHB Granule Bed |
    | Optics | Nano-TiO2 AR |
    | Albedo | Green Reflector |
    | PCE | **25.6%** |
    """)

with col2:
    st.markdown("#### PRIMEngines Fleet")
    st.markdown("""
    | Engine | Fuel | Power |
    |--------|------|-------|
    | A-ICE-G1 | NH3 | 450 HP |
    | PEM-PB-50 | H2 | 50 kW |
    | HY-P100 | H2 | 100 kW |
    
    **Applications:** Trucks, Marine, Rail, Aviation, F1, Drones, Military
    """)

with col3:
    st.markdown("#### Infrastructure")
    st.markdown("""
    | System | Status |
    |--------|--------|
    | SIBO API | Live |
    | Streamlit Dashboard | Live |
    | Eureka Trading | Active |
    | PRIMEcycle | Development |
    | Battery Storage | Development |
    | PRIM Wind | Development |
    """)

st.divider()

# GitHub Repository Portfolio
st.subheader("GitHub Repository Portfolio")

repos = [
    ("PRIMEnergeia-Sovereign", "18-page Streamlit Command Center", "Active"),
    ("Eureka-Sovereign", "VIX-Regime Trading Engine + GitHub Actions", "Active"),
    ("Granas-Sovereign", "SIBO Bayesian Optimizer (GP/Matern)", "Active"),
    ("Granas-CFRP", "Carbon Fiber Reinforced Polymer Substrate", "Active"),
    ("Granas-GHB", "Granular Heat Bed Thermal Management", "Active"),
    ("Granas-Albedo", "Green-Wavelength Reflective Cooling", "Active"),
    ("Granas-ETFE", "ETFE Encapsulation + Mn2+ Passivation", "Active"),
    ("Granas-TOPCon", "TOPCon Silicon Heterojunction", "Active"),
    ("Granas-Blueprint", "System Architecture & Integration", "Active"),
    ("Granas-Metrics", "Performance KPIs & Validation", "Active"),
    ("Granas-Scale", "100MW/1GW/10GW Industrial Calculator", "Active"),
    ("PRIMEngines-AICE", "Ammonia Internal Combustion Engine", "Active"),
    ("PRIMEngines-PEM", "PEM Fuel Cell Power Bank", "Active"),
    ("PRIMEngines-HYP", "Hydrogen Gas Turbine 100kW", "Active"),
    ("PRIMEnergeia-Battery", "Grid-Scale Energy Storage", "Active"),
    ("PRIMEcycle", "Perovskite Recycling Platform", "Active"),
    ("PRIM-Wind", "Hydrogen-Ready Wind Energy", "Active"),
]

# Display as table
st.markdown("| # | Repository | Description | Status |")
st.markdown("|---|-----------|-------------|--------|")
for i, (name, desc, status) in enumerate(repos, 1):
    st.markdown(f"| {i} | **{name}** | {desc} | {status} |")

st.divider()

# Competitive Moat
st.subheader("Competitive Moat")

moat_categories = ["Material Science", "Manufacturing IP", "Software/AI",
                   "Vertical Integration", "Revenue Diversity", "Sustainability"]
moat_scores = [95, 85, 90, 88, 92, 97]

fig2 = go.Figure()
fig2.add_trace(go.Scatterpolar(
    r=moat_scores + [moat_scores[0]],
    theta=moat_categories + [moat_categories[0]],
    fill="toself",
    fillcolor="rgba(0,200,120,0.2)",
    line=dict(color="#00c878", width=3),
    name="PRIMEnergeia",
))
fig2.add_trace(go.Scatterpolar(
    r=[70, 60, 50, 45, 40, 55, 70],
    theta=moat_categories + [moat_categories[0]],
    fill="toself",
    fillcolor="rgba(255,99,71,0.1)",
    line=dict(color="#FF6347", width=2, dash="dash"),
    name="Industry Average",
))
fig2.update_layout(
    template="plotly_dark", height=450,
    polar=dict(radialaxis=dict(range=[0, 100], showticklabels=True)),
    paper_bgcolor="rgba(0,0,0,0)",
    showlegend=True,
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #555; padding: 20px 0;">
<strong>PRIMEnergeia S.A.S.</strong> - Sovereign Energy Infrastructure<br>
Solar - Engines - Storage - Wind - Trading - AI Optimization<br>
<em>diego@primenergeia.com</em> | primenergeia.com
</div>
""", unsafe_allow_html=True)
