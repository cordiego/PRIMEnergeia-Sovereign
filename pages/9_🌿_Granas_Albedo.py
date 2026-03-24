"""PRIMEnergeia — Albedo Green Reflectance | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🌿 Granas Albedo — Green Reflectance Engine")
st.caption("535nm Spectral Selection | Junction Cooling | Arrhenius Degradation | Urban Albedo")

KB = 8.617e-5

with st.expander("⚙️ Thermal & Optical Parameters", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        reflectance = st.slider("Peak Green R(535nm)", 0.10, 0.60, 0.35, 0.05)
        ambient = st.slider("Ambient Temp (°C)", 15, 45, 25, 1)
    with c2:
        pce_init = st.slider("Initial PCE (%)", 15.0, 25.0, 19.8, 0.5)
        years = st.slider("Projection (years)", 1, 10, 5, 1)

# ─── Thermal Model ───
dt_full = 43.0
green_cool = dt_full * reflectance * 1.2
pce_cool = dt_full * (pce_init / 100) * 0.15
tj = max(ambient + 5, ambient + dt_full - green_cool - pce_cool)
tj_control = ambient + dt_full - dt_full * (22.1/100) * 0.15
voc_gain = (tj_control - tj) * 1.8

ea = 0.75; k_ref = 1.2e-5
k_g = k_ref * np.exp(-ea / KB * (1/(tj+273.15) - 1/315.15))
k_c = k_ref * np.exp(-ea / KB * (1/(tj_control+273.15) - 1/315.15))
t80_g = -np.log(0.8) / max(k_g, 1e-7) / 8760
t80_c = -np.log(0.8) / max(k_c, 1e-7) / 8760

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🌡️ Tj Granas", f"{tj:.1f}°C", f"-{tj_control-tj:.0f}°C")
k2.metric("🌡️ Tj Control", f"{tj_control:.0f}°C")
k3.metric("⚡ Voc Gain", f"+{voc_gain:.1f} mV")
k4.metric("⏱️ T80 (Granas)", f"{t80_g:.1f} yr", f"+{t80_g-t80_c:.1f} yr")
k5.metric("🏢 HVAC Savings", "17.5%")

st.divider()

# ─── Charts ───
c1, c2 = st.columns(2)
with c1:
    # Reflectance spectrum
    wl = np.linspace(300, 1200, 200)
    sigma = 70 / (2 * np.sqrt(2 * np.log(2)))
    R = reflectance * np.exp(-((wl - 535) / sigma)**2)
    am15 = 1.4 * np.exp(-((wl - 500) / 300)**2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wl, y=am15, mode='lines', name='AM1.5G',
        line=dict(color='orange', width=1), fill='tozeroy',
        fillcolor='rgba(255,200,0,0.1)'))
    fig.add_trace(go.Scatter(x=wl, y=R * max(am15), mode='lines', name='Green R(λ)',
        line=dict(color='#00c878', width=3), fill='tozeroy',
        fillcolor='rgba(0,200,120,0.2)'))
    fig.add_vline(x=535, line_dash="dot", line_color="#00c878",
                  annotation_text="535nm")
    fig.update_layout(title="Spectral Selectivity", xaxis_title="λ (nm)",
        yaxis_title="Irradiance / Reflectance", height=320,
        margin=dict(t=40, b=40), legend=dict(x=0.7, y=0.98),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # Degradation curves
    hours = np.linspace(0, years * 8760, 200)
    pce_g = pce_init * np.exp(-k_g * hours)
    pce_c = 22.1 * np.exp(-k_c * hours)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=hours/8760, y=pce_g, mode='lines',
        name='Granas', line=dict(color='#00c878', width=3)))
    fig2.add_trace(go.Scatter(x=hours/8760, y=pce_c, mode='lines',
        name='Control (MAPbI₃)', line=dict(color='red', width=2, dash='dash')))
    fig2.add_hline(y=pce_init*0.8, line_dash="dot", line_color="gray",
                   annotation_text="T80 threshold")
    fig2.update_layout(title="PCE Degradation Projection",
        xaxis_title="Time (years)", yaxis_title="PCE (%)", height=320,
        margin=dict(t=40, b=40), legend=dict(x=0.6, y=0.98),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig2, use_container_width=True)

# ─── Urban Albedo ───
st.subheader("🏢 Urban Cooling Effect")
u1, u2, u3 = st.columns(3)
with u1:
    rooftop = st.number_input("Rooftop Area (m²)", 50, 5000, 500, 50)
    cooling_kwh = 60 * rooftop * 2000 / 1000
    st.metric("Annual Green Reflected", f"{cooling_kwh:,.0f} kWh")
with u2:
    st.metric("Surface Temp Reduction", "-8°C", "vs black panels")
    st.metric("Film Thickness", f"{535/(4*2.5):.1f} nm", "quarter-wave optimal")
with u3:
    dark_ratio = np.exp(-1.578 / (2*KB*(tj+273.15))) / np.exp(-1.578 / (2*KB*(tj_control+273.15)))
    st.metric("J₀ Ratio (Granas/Ctrl)", f"{dark_ratio**2:.4f}", "lower = better")
    st.metric("k_deg Ratio", f"{k_g/k_c:.3f}", f"{(1-k_g/k_c)*100:.0f}% slower")
