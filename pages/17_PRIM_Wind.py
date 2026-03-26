"""PRIMEnergeia - PRIM Wind | CEO-Grade Hydrogen-Ready Wind Dashboard"""
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
    from lib.engines.power_electronics import InverterModel, InverterSpec
except Exception:
    try:
        from power_electronics import InverterModel, InverterSpec
    except Exception:
        InverterModel = None

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("PRIM Wind - Hydrogen-Ready Wind Energy")
st.caption("Offshore & Onshore Wind | Green H2 Integration | 15 MW Direct-Drive Turbines | PRIMEnergeia S.A.S.")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Class", "IEC I/II")
k2.metric("Rated", "15 MW")
k3.metric("Rotor", "236 m")
k4.metric("CF", "48%")
k5.metric("Conv. η", "98.0%")
k6.metric("Hub Height", "150 m")

st.divider()

tier = st.radio("Farm Configuration", ["Onshore 50 MW", "Onshore 500 MW", "Offshore 1 GW", "Floating 2 GW"], horizontal=True, index=2)
tier_data = {
    "Onshore 50 MW": {"turbines": 10, "mw": 50, "cf": 0.35, "capex_mw": 1.3, "lcoe": 35, "h2": 2400, "area": 25, "jobs": 45},
    "Onshore 500 MW": {"turbines": 100, "mw": 500, "cf": 0.36, "capex_mw": 1.15, "lcoe": 30, "h2": 25000, "area": 200, "jobs": 280},
    "Offshore 1 GW": {"turbines": 67, "mw": 1000, "cf": 0.48, "capex_mw": 2.8, "lcoe": 55, "h2": 65000, "area": 300, "jobs": 650},
    "Floating 2 GW": {"turbines": 133, "mw": 2000, "cf": 0.52, "capex_mw": 3.2, "lcoe": 62, "h2": 140000, "area": 600, "jobs": 1200},
}
td = tier_data[tier]

t1, t2, t3, t4, t5, t6 = st.columns(6)
t1.metric("Turbines", f"{td['turbines']}")
t2.metric("Annual GWh", f"{td['mw'] * td['cf'] * 8.76:,.0f}")
t3.metric("CapEx", f"\${td['mw'] * td['capex_mw']:,.0f}M")
t4.metric("LCOE", f"\${td['lcoe']}/MWh")
t5.metric("H2 Output", f"{td['h2']:,} kg/day")
t6.metric("Direct Jobs", f"{td['jobs']}")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Power Curve", "Hybrid", "Revenue", "Wind Map", "⚡ Power Electronics"])

with tab1:
    ws = np.arange(0, 30, 0.5)
    power = np.zeros_like(ws)
    for i, w in enumerate(ws):
        if w < 3: power[i] = 0
        elif w < 12: power[i] = 15 * ((w - 3) / 9) ** 3
        elif w <= 25: power[i] = 15
        else: power[i] = 0

    ct = np.zeros_like(ws)
    for i, w in enumerate(ws):
        if w < 3: ct[i] = 0
        elif w < 12: ct[i] = 0.85 * (1 - 0.3 * ((w - 7) / 7) ** 2)
        elif w <= 25: ct[i] = 0.85 * (12 / max(w, 12)) ** 2
        else: ct[i] = 0

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=ws, y=power, name="Power (MW)", fill="tozeroy",
        fillcolor="rgba(0,191,255,0.2)", line=dict(color="#00BFFF", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=ws, y=ct, name="Thrust Coeff (Ct)", mode="lines",
        line=dict(color="#FFD700", width=2, dash="dash")), secondary_y=True)
    fig.add_vline(x=3, line_dash="dot", line_color="gray", annotation_text="Cut-in")
    fig.add_vline(x=12, line_dash="dot", line_color="#00c878", annotation_text="Rated")
    fig.add_vline(x=25, line_dash="dot", line_color="red", annotation_text="Cut-out")
    fig.update_layout(template="plotly_dark", height=450, title="15 MW Direct-Drive Turbine Curves",
        xaxis_title="Wind Speed (m/s)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="Ct", range=[0, 1], secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    hours = np.arange(0, 24)
    np.random.seed(42)
    solar = np.maximum(0, np.sin((hours - 6) * np.pi / 12) * td['mw'] * 0.3)
    solar[hours < 6] = 0; solar[hours > 18] = 0
    wind = td['mw'] * td['cf'] * (0.8 + 0.4 * np.sin(hours * np.pi / 10) + np.random.normal(0, 0.1, 24))
    wind = np.clip(wind, td['mw'] * 0.1, td['mw'] * 0.95)
    total = solar + wind
    h2_rate = total * 18

    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=(f"Combined Output - {tier}", "Green H2 Production Rate"))
    fig2.add_trace(go.Scatter(x=hours, y=solar, name="Solar (MW)", fill="tozeroy",
        fillcolor="rgba(255,215,0,0.3)", line=dict(color="#FFD700")), row=1, col=1)
    fig2.add_trace(go.Scatter(x=hours, y=solar + wind, name="+ Wind (MW)", fill="tonexty",
        fillcolor="rgba(0,191,255,0.2)", line=dict(color="#00BFFF")), row=1, col=1)
    fig2.add_trace(go.Bar(x=hours, y=h2_rate, name="H2 (kg/hr)",
        marker_color="rgba(0,200,120,0.6)"), row=2, col=1)
    fig2.update_layout(template="plotly_dark", height=550,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    years = np.arange(1, 26)
    ppa = 55
    annual_gwh = td['mw'] * td['cf'] * 8.76
    energy_rev = annual_gwh * ppa / 1000
    h2_rev = td['h2'] * 365 * 4 / 1e6
    rec_rev = annual_gwh * 5 / 1000

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=years, y=np.cumsum(np.full_like(years, energy_rev, dtype=float)),
        name="Energy PPA", fill="tozeroy", fillcolor="rgba(0,191,255,0.2)", line=dict(color="#00BFFF")))
    fig3.add_trace(go.Scatter(x=years, y=np.cumsum(np.full_like(years, energy_rev + h2_rev, dtype=float)),
        name="+ H2 Sales", fill="tonexty", fillcolor="rgba(0,200,120,0.15)", line=dict(color="#00c878")))
    fig3.add_trace(go.Scatter(x=years, y=np.cumsum(np.full_like(years, energy_rev + h2_rev + rec_rev, dtype=float)),
        name="+ RECs", fill="tonexty", fillcolor="rgba(255,215,0,0.1)", line=dict(color="#FFD700", width=3)))
    capex = td['mw'] * td['capex_mw']
    fig3.add_hline(y=capex, line_dash="dash", line_color="red", annotation_text=f"CapEx: \${capex:,.0f}M")
    fig3.update_layout(template="plotly_dark", height=450, title="25-Year Revenue Stack",
        xaxis_title="Year", yaxis_title="Cumulative Revenue (\$$M)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.markdown("""
    ### Target Regions for PRIM Wind
    | Region | Type | Avg Wind (m/s) | CF | Status |
    |--------|------|---------------|-----|--------|
    | **Oaxaca, Mexico** | Onshore | 10.2 | 42% | Prospecting |
    | **Tamaulipas, Mexico** | Onshore | 8.5 | 36% | Prospecting |
    | **Baja California** | Offshore | 9.8 | 45% | Planning |
    | **Gulf of Mexico** | Floating | 11.5 | 52% | R&D |
    | **North Sea (EU)** | Offshore | 10.8 | 48% | Partner Ready |
    | **Patagonia (ARG)** | Onshore | 12.0 | 55% | Prospecting |
    | **Australia (WA)** | Offshore | 10.0 | 46% | Prospecting |
    """)

with tab5:
    st.subheader("⚡ Full-Converter Power Electronics")
    st.caption("Direct-drive PMG → Full converter (AC-DC-AC) → Grid | PRIMEnergeia Power Electronics Division")

    if InverterModel is not None:
        conv = InverterModel(InverterSpec(
            name="WIND-CONV", rated_power_kw=15000,
            peak_efficiency=0.98, standby_power_w=450,
            tare_loss_pct=0.0020, switching_loss_pct=0.0040,
            apparent_power_kva=16500,
        ))

        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("Peak Conv. η", f"{conv.efficiency(0.5)*100:.1f}%")
        pc2.metric("10% Load η", f"{conv.efficiency(0.1)*100:.1f}%")
        pc3.metric("VAR Capacity", f"{conv.reactive_power_capability(7500)['q_max_kvar']:.0f} kVAR")
        pc4.metric("Derating", "45°C threshold")

        # Converter efficiency vs wind speed
        ws = np.arange(3, 26, 0.5)
        conv_etas = []
        old_etas = []
        for w in ws:
            if w < 3 or w > 25:
                conv_etas.append(0)
                old_etas.append(0)
            elif w < 12:
                p_frac = ((w - 3) / 9) ** 3
                conv_etas.append(conv.efficiency(p_frac) * 100)
                old_etas.append(98.0)
            else:
                conv_etas.append(conv.efficiency(1.0) * 100)
                old_etas.append(98.0)

        fig_pe = go.Figure()
        fig_pe.add_trace(go.Scatter(x=ws, y=conv_etas, name="New: Load-Dependent η",
            line=dict(color="#00BFFF", width=3)))
        fig_pe.add_trace(go.Scatter(x=ws, y=old_etas, name="Old: Flat 98%",
            line=dict(color="#888", width=2, dash="dash")))
        fig_pe.add_vline(x=12, line_dash="dot", line_color="#00c878", annotation_text="Rated (12 m/s)")
        fig_pe.update_layout(template="plotly_dark", height=400,
            title="Converter Efficiency vs Wind Speed",
            xaxis_title="Wind Speed (m/s)", yaxis_title="Converter η (%)",
            yaxis=dict(range=[88, 100]),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
        st.plotly_chart(fig_pe, use_container_width=True)

        st.info("**Low-wind impact**: Below rated wind speed, the converter operates at partial load "
                "where fixed losses (fans, control boards) represent a larger fraction of output. "
                "At 5 m/s (~15% load), converter η drops to ~96% vs the old flat 98%.")

        # Temperature derating
        temps = np.arange(20, 65, 1)
        deratings = [conv.temperature_derating(t) * 100 for t in temps]
        max_outputs = [conv.temperature_derating(t) * 15 for t in temps]

        fig_td = make_subplots(specs=[[{"secondary_y": True}]])
        fig_td.add_trace(go.Scatter(x=temps, y=max_outputs, name="Max Output (MW)",
            fill="tozeroy", fillcolor="rgba(0,191,255,0.15)",
            line=dict(color="#00BFFF", width=3)), secondary_y=False)
        fig_td.add_trace(go.Scatter(x=temps, y=deratings, name="Derating (%)",
            line=dict(color="#FF6347", width=2, dash="dash")), secondary_y=True)
        fig_td.add_vline(x=45, line_dash="dot", line_color="red", annotation_text="Threshold")
        fig_td.update_layout(template="plotly_dark", height=350,
            title="Temperature Derating — Nacelle Inverter",
            xaxis_title="Ambient °C",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
        fig_td.update_yaxes(title_text="Max Output (MW)", secondary_y=False)
        fig_td.update_yaxes(title_text="Derating (%)", range=[50, 105], secondary_y=True)
        st.plotly_chart(fig_td, use_container_width=True)
    else:
        st.warning("Power electronics module not available.")

st.caption("PRIMEnergeia S.A.S. - PRIM Wind Division | Hydrogen-Ready Wind Energy Systems")
