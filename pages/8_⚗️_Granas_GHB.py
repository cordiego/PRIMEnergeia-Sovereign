"""PRIMEnergeia — Green Haber-Bosch NRR | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.header("️ Granas GHB — Green Haber-Bosch Engine")
st.caption("Mo-N₄ Single-Site NRR | PG-MoSA-BC Back Contact | Decentralized NH₃")

F = 96485

with st.expander("️ Electrochemical Parameters", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        potential = st.slider("Potential (V vs RHE)", -0.8, -0.1, -0.4, 0.05)
        pressure = st.slider("N₂ Pressure (bar)", 1, 100, 50, 5)
    with c2:
        mo_loading = st.slider("Mo Loading (wt%)", 0.5, 5.0, 2.5, 0.5)
        temperature = st.slider("Temperature (°C)", 10, 60, 25, 5)

# ─── NRR Calculations ───
delta_g_h = 0.45; n2_binding = -0.65
her_suppress = 1.0 - np.exp(-delta_g_h / 0.2)
n2_quality = float(np.clip((-n2_binding - 0.3) / 0.5, 0, 1))
pot_score = np.exp(-((potential + 0.4) / 0.3)**2)
p_score = min(1.0, np.log(pressure + 1) / np.log(51))
fe = float(np.clip(65 * her_suppress * n2_quality * pot_score * p_score, 0.1, 80))
j = 5.0
yield_mol = (j * 1e-3 * fe/100) / (3 * F) * 3600
nh3_yield = float(yield_mol * 17e6)
energy_eff = 0.06 / abs(potential) * fe

# ─── KPI Row ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⚡ Faradaic Eff.", f"{fe:.1f}%", f"{'73× Pt/C' if fe > 5 else ''}")
k2.metric("🧪 NH₃ Yield", f"{nh3_yield:.1f} μg/h·cm²")
k3.metric("🔋 Energy Eff.", f"{energy_eff:.1f}%")
k4.metric("🛡️ HER Suppress", f"{her_suppress*100:.0f}%")
k5.metric("🌍 CO₂ Emission", "0 t/t NH₃", "-1.6 vs HB")

st.divider()

# ─── Charts ───
c1, c2 = st.columns(2)
with c1:
    # FE vs Potential sweep
    pots = np.linspace(-0.8, -0.1, 50)
    fes = [float(np.clip(65 * her_suppress * n2_quality * np.exp(-((p+0.4)/0.3)**2) * p_score, 0.1, 80)) for p in pots]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pots, y=fes, mode='lines',
        line=dict(color='#7B68EE', width=3), fill='tozeroy',
        fillcolor='rgba(123,104,238,0.1)', name='Mo-N₄'))
    fig.add_trace(go.Scatter(x=pots, y=[0.8]*50, mode='lines',
        line=dict(color='red', width=1, dash='dash'), name='Pt/C baseline'))
    fig.add_vline(x=potential, line_dash="dot", line_color="gold")
    fig.update_layout(title="Faradaic Efficiency vs Potential",
        xaxis_title="V vs RHE", yaxis_title="FE (%)", height=320,
        margin=dict(t=40, b=40), legend=dict(x=0.02, y=0.98),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # Gauge for Faradaic Efficiency
    fig2 = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=fe, delta={'reference': 0.8, 'relative': False, 'suffix': ' vs Pt'},
        title={'text': "Faradaic Efficiency (%)", 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, 80], 'tickwidth': 1},
            'bar': {'color': "#7B68EE"},
            'steps': [
                {'range': [0, 10], 'color': 'rgba(255,0,0,0.1)'},
                {'range': [10, 40], 'color': 'rgba(255,200,0,0.1)'},
                {'range': [40, 80], 'color': 'rgba(0,200,0,0.1)'}],
            'threshold': {'line': {'color': "red", 'width': 3}, 'thickness': 0.8, 'value': 0.8}}))
    fig2.update_layout(height=320, margin=dict(t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)

# ─── Comparison ───
st.subheader("📊 Granas NRR vs Industrial Haber-Bosch")
t1, t2 = st.columns(2)
with t1:
    fig3 = go.Figure(go.Bar(
        x=['Temperature\n(°C)', 'Pressure\n(bar)', 'CO₂\n(t/t NH₃)', 'Energy\n(relative)'],
        y=[25, 50, 0, 30], name='Granas NRR',
        marker_color='rgba(123,104,238,0.7)'))
    fig3.add_trace(go.Bar(
        x=['Temperature\n(°C)', 'Pressure\n(bar)', 'CO₂\n(t/t NH₃)', 'Energy\n(relative)'],
        y=[450, 200, 1.6, 100], name='Industrial HB',
        marker_color='rgba(200,80,80,0.7)'))
    fig3.update_layout(barmode='group', title="Process Comparison", height=300,
        margin=dict(t=40, b=40), legend=dict(x=0.6, y=0.98),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig3, use_container_width=True)
with t2:
    st.markdown("""
**Mo-N₄ Catalyst Mechanism:**
1. N₂ chemisorption on Mo site (E_bind = -0.65 eV)
2. Proton-coupled electron transfer (PCET)
3. N₂H* → N₂H₂* → ... → 2NH₃
4. HER suppressed by ΔG_H = +0.45 eV

**Advantages:**
- 🌡️ Ambient temperature (25°C vs 450°C)
- ⚡ Solar-powered (excess Granas electricity)
- 🏡 Decentralized (farm/village scale)
- 🌍 Zero carbon emissions
    """)
