"""PRIMEnergeia - PRIMEcycle | CEO-Grade Circular Economy Dashboard"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
try:
    from lib.granas_handshake import show_handshake_sidebar
    show_handshake_sidebar()
except Exception: pass
# --- End Banner ---
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("PRIMEcycle - Circular Economy Platform")
st.caption("Perovskite Module Recycling | Material Recovery | Zero-Waste EOL | PRIMEnergeia S.A.S.")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Recovery", "97.3%")
k2.metric("Pb Capture", "99.8%")
k3.metric("CO2 Avoided", "85%")
k4.metric("Energy Saved", "78%")
k5.metric("Throughput", "500/day")
k6.metric("Value/Mod", "\$$18.50")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Recovery", "Lifecycle", "Economics", "Impact"])

with tab1:
    materials = [
        ("Glass / ETFE", 68.0, 99.5, 0.80, "#4FC3F7"),
        ("Silicon (Si)", 12.0, 95.0, 12.0, "#FFD700"),
        ("CFRP Substrate", 8.0, 88.0, 15.0, "#FF6347"),
        ("EVA Encapsulant", 5.0, 85.0, 1.2, "#9467bd"),
        ("Copper (Cu)", 3.2, 99.0, 8.5, "#FF8C00"),
        ("PbI2 (Perovskite)", 1.2, 97.5, 45.0, "#00c878"),
        ("FAI / MAI", 0.8, 92.0, 180.0, "#00BFFF"),
        ("Lead (Pb)", 0.05, 99.8, 2.1, "#E74C3C"),
        ("Silver (Ag)", 0.04, 98.0, 850.0, "#C0C0C0"),
    ]

    names = [m[0] for m in materials]
    mass_pct = [m[1] for m in materials]
    recovery = [m[2] for m in materials]
    colors = [m[4] for m in materials]
    value_per_mod = [m[1] * m[2] / 100 * m[3] / 100 for m in materials]

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Bar(y=names, x=recovery, orientation="h",
            marker=dict(color=colors), text=[f"{r:.1f}%" for r in recovery], textposition="auto"))
        fig.update_layout(template="plotly_dark", height=450, title="Recovery Rate by Material (%)",
            xaxis=dict(range=[80, 100]), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=14))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(y=names, x=value_per_mod, orientation="h",
            marker=dict(color=colors), text=[f"\${v:.2f}" for v in value_per_mod], textposition="auto"))
        fig2.update_layout(template="plotly_dark", height=450, title="Recovery Value (\$/module)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"**Total material value recovered per module: \${sum(value_per_mod):.2f}**")

with tab2:
    stages = ["Raw Material Extraction", "Module Manufacturing", "Field Deployment",
              "30-Year Operation", "Collection & Transport", "Mechanical Disassembly",
              "Chemical Recovery", "Purification & Refining", "Remanufacturing & Reuse"]
    yields = [100, 99.5, 99.8, 92.8, 98.0, 96.5, 97.3, 99.0, 95.0]
    cumulative = [100]
    for i in range(1, len(yields)):
        cumulative.append(cumulative[-1] * yields[i] / 100)

    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Bar(x=stages, y=yields, name="Stage Yield",
        marker=dict(color=yields, colorscale="RdYlGn", cmin=88, cmax=100),
        text=[f"{y:.1f}%" for y in yields], textposition="auto"), secondary_y=False)
    fig3.add_trace(go.Scatter(x=stages, y=cumulative, name="Cumulative",
        mode="lines+markers", marker=dict(size=10, color="#FFD700"),
        line=dict(width=3, color="#FFD700")), secondary_y=True)
    fig3.update_layout(template="plotly_dark", height=500, title="Circular Lifecycle Yield Chain",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=13))
    fig3.update_yaxes(title_text="Stage Yield (%)", range=[85, 101], secondary_y=False)
    fig3.update_yaxes(title_text="Cumulative (%)", range=[75, 101], secondary_y=True)
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    scale = st.radio("Processing Scale", ["Pilot (1K/yr)", "Regional (100K/yr)", "Industrial (1M/yr)"], horizontal=True, index=2)
    scale_data = {
        "Pilot (1K/yr)": {"modules": 1000, "capex": 0.5, "opex_per_mod": 12, "rev_per_mod": 18.5},
        "Regional (100K/yr)": {"modules": 100000, "capex": 15, "opex_per_mod": 6, "rev_per_mod": 18.5},
        "Industrial (1M/yr)": {"modules": 1000000, "capex": 80, "opex_per_mod": 3.5, "rev_per_mod": 18.5},
    }
    sd = scale_data[scale]

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("CapEx", f"\${sd['capex']}M")
    s2.metric("OpEx/Module", f"\${sd['opex_per_mod']:.1f}")
    s3.metric("Margin/Module", f"\${sd['rev_per_mod'] - sd['opex_per_mod']:.1f}")
    annual_profit = sd['modules'] * (sd['rev_per_mod'] - sd['opex_per_mod']) / 1e6
    s4.metric("Annual Profit", f"\${annual_profit:,.1f}M")

    years = np.arange(1, 21)
    cum_profit = np.cumsum(np.full_like(years, annual_profit, dtype=float))
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=years, y=cum_profit, name="Cumulative Profit",
        fill="tozeroy", fillcolor="rgba(0,200,120,0.2)", line=dict(color="#00c878", width=3)))
    fig4.add_hline(y=sd['capex'], line_dash="dash", line_color="red", annotation_text=f"CapEx: \${sd['capex']}M")
    fig4.update_layout(template="plotly_dark", height=400, title="Recycling Plant Payback",
        xaxis_title="Year", yaxis_title="Cumulative Profit (\$$M)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig4, use_container_width=True)

with tab4:
    st.markdown("### Environmental Scorecard vs. Landfill")
    i1, i2, i3, i4, i5, i6 = st.columns(6)
    i1.metric("CO2 Avoided", "3.2 kg/mod")
    i2.metric("Pb Diversion", "99.8%", "zero leaching")
    i3.metric("Water Saved", "45 L/mod")
    i4.metric("Energy ROI", "12:1")
    i5.metric("Waste Diverted", "97.3%")
    i6.metric("Toxics Neutralized", "100%")

    categories = ["Carbon Footprint", "Water Usage", "Energy Use", "Toxic Waste", "Material Loss", "Land Impact"]
    landfill = [100, 100, 0, 100, 100, 100]
    primecycle = [15, 55, 22, 0.2, 2.7, 5]

    fig5 = go.Figure()
    fig5.add_trace(go.Scatterpolar(r=landfill + [landfill[0]], theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(255,99,71,0.2)", line=dict(color="#FF6347", width=2), name="Landfill"))
    fig5.add_trace(go.Scatterpolar(r=primecycle + [primecycle[0]], theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(0,200,120,0.2)", line=dict(color="#00c878", width=3), name="PRIMEcycle"))
    fig5.update_layout(template="plotly_dark", height=450, polar=dict(radialaxis=dict(range=[0, 110])),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(size=14))
    st.plotly_chart(fig5, use_container_width=True)

st.caption("PRIMEnergeia S.A.S. - PRIMEcycle Division | Zero-Waste Perovskite Solar Recycling")
