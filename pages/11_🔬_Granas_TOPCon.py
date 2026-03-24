"""PRIMEnergeia — TOPCon Silicon Bottom Cell | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🔬 Granas TOPCon — Silicon Bottom Cell Engine")
st.caption("n-type Cz | Implied Voc > 720mV | Enhanced NIR Response")

# ─── Electrical Model ───
j0_bulk, j0_topcon, j0_front = 2.0, 1.5, 3.0
j0_total = j0_bulk + j0_topcon + j0_front
jsc_standalone = 42.0
voc = 0.02585 * np.log(jsc_standalone * 1e-3 / (j0_total * 1e-15) + 1) * 1000
pce_standalone = (voc/�000) * jsc_standalone * 0.83 / 10
jsc_tandem = 42.0 * 0.38
tandem_pce = (voc/1000) * jsc_tandem * 0.82 / 10

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⚡ Implied Voc", f"{voc:.0f} mV", "+40 vs PERC")
k2.metric("🔌 J₀ Total", f"{j0_total:.1f} fA/cm²")
k3.metric("☀️ PCE (standalone)", f"{pce_standalone:.1f}%")
k4.metric("🔗 Tandem Contribution", f"{tandem_pce:.1f}%")
k5.metric("💰 Cost/Wafer", "$1.80")

st.divider()
c1, c2 = st.columns(2)
with c1:
    # EQE spectrum
    wl = np.linspace(300, 1250, 200)
    eqe = np.zeros_like(wl)
    mask_ramp = (wl >= 786) & (wl <= 850)
    eqe[mask_ramp] = 0.95 * (wl[mask_ramp] - 786) / (850 - 786)
    mask_plat = (wl > 850) & (wl <= 1050)
    eqe[mask_plat] = 0.95
    mask_drop = (wl > 1050) & (wl <= 1200)
    eqe[mask_drop] = 0.95 * np.exp(-((wl[mask_drop] - 1050) / 60)**2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wl, y=eqe*100, mode='lines', name='TOPCon EQE',
        line=dict(color='#FF6347', width=3), fill='tozeroy',
        fillcolor='rgba(255,99,71,0.15)'))
    fig.add_vline(x=786, line_dash="dot", line_color="orange",
                  annotation_text="Perovskite cutoff")
    fig.add_vline(x=1127, line_dash="dot", line_color="gray",
                  annotation_text="Si bandgap")
    fig.update_layout(title="NIR External Quantum Efficiency",
        xaxis_title="λ (nm)", yaxis_title="EQE (%)", height=320,
        margin=dict(t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # J0 breakdown
    fig2 = go.Figure(go.Bar(
        x=['J₀ Bulk\n(n-Cz)', 'J₀ TOPCon\n(rear)', 'J₀ Front\n(SiNₓ)'],
        y=[j0_bulk, j0_topcon, j0_front],
        marker_color=['#FF6347', '#FF8C00', '#FFD700'],
    -�ext=[f'{j0_bulk} fA', f'{j0_topcon} fA', f'{j0_front} fA'],
        textposition='outside'))
    fig2.update_layout(title="Saturation Current Density Breakdown",
        yaxis_title="J₀ (fA/cm²)", height=320,
        margin=dict(t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("📋 Process Specification")
p1, p2, p3 = st.columns(3)
with p1:
    st.markdown("""
**Cell Structure:**
- n-Si (Cz, 180μm, 3.0 Ω·cm)
- SiO₂ (1.5nm tunnel oxide, 630°C)
- n⁺ poly-Si (200nm, LPCVD 580°C)
- Al₂O₃ (10nm) + SiNₓ (75nm)
    """)
with p2:
    st.markdown("""
**Process Flow:**
1. TBA clean (SC1 + HF + SC2)
2. Thermal oxidation (634��C, O₂)
3. LPCVD poly-Si (SiH₄, 580°C)
4. P implant (5×10¹⁵ cm⁻²)
5. Anneal (850°C, N₂, 20min)
    """)
with p3:
    st.markdown(f"""
**Tandem Integration:**
- 🔗 Current-matched: {jsc_tandem:.0f} mA/cm²
- 📐 NIR range: 786-1200nm
- 🎯 EQE peak: 95%
- ⚡ Voc: {voc:.0f} mV
- 🏭 Compatible with Granas deposition
    """)
