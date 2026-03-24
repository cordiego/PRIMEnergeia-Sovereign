"""PRIMEnergeia — TOPCon Silicon Bottom Cell | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🔬 Granas TOPCon — Silicon Bottom Cell Engine")
st.caption("n-type Cz | 1.5nm Tunnel Oxide | Implied Voc > 720mV | Enhanced NIR Response")

# Physics Model
j0_bulk, j0_topcon, j0_front = 2.0, 1.5, 3.0
j0_total = j0_bulk + j0_topcon + j0_front
jsc_standalone = 42.0
voc = 0.02585 * np.log(jsc_standalone * 1e-3 / (j0_total * 1e-15) + 1) * 1000
pce_standalone = (voc/1000) * jsc_standalone * 0.83 / 10
jsc_tandem = 42.0 * 0.38
tandem_pce = (voc/1000) * jsc_tandem * 0.82 / 10

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Implied Voc", f"{voc:.0f} mV", "+40 vs PERC")
k2.metric("J0 Total", f"{j0_total:.1f} fA/cm2")
k3.metric("PCE (standalone)", f"{pce_standalone:.1f}%")
k4.metric("Tandem Contribution", f"{tandem_pce:.1f}%")
k5.metric("Cost/Wafer", "$1.80")

st.divider()
c1, c2 = st.columns(2)
with c1:
    wl = np.linspace(300, 1250, 200)
    eqe = np.zeros_like(wl)
    mask_ramp = (wl >= 786) & (wl <= 850)
    eqe[mask_ramp] = 0.95 * (wl[mask_ramp] - 786) / (850 - 786)
    mask_plat = (wl > 850) & (wl <= 1050)
    eqe[mask_plat] = 0.95
    mask_drop = (wl > 1050) & (wl <= 1200)
    eqe[mask_drop] = 0.95 * np.exp(-((wl[mask_drop] - 1050) / 60)**2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wl, y=eqe*100, mode='lines', name='TOPCon EQE', line=dict(color='#FF6347', width=3), fill='tozeroy', fillcolor='rgba(255,99,71,0.15)'))
    fig.update_layout(title="NIR External Quantum Efficiency", xaxis_title="λ (nm)", yaxis_title="EQE (%)", height=320)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig2 = go.Figure(go.Bar(x=['J0 Bulk', 'J0 TOPCon', 'J0 Front'], y=[j0_bulk, j0_topcon, j0_front], marker_color=['#FF6347', '#FF8C00', '#FFD700']))
    fig2.update_layout(title="J0 Breakdown", yaxis_title="J0 (fA/cm2)", height=320)
    st.plotly_chart(fig2, use_container_width=True)
