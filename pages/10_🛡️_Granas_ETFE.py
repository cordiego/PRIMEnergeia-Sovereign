"""PRIMEnergeia — ETFE Encapsulation | CEO-Grade Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.header("🛡️ Granas ETFE — Front Encapsulation Engine")
st.caption("96% Transmittance | Self-Cleaning Lotus Effect | Thermoformed on CFRP Skeleton")

# --- KPIs ---
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("☀️ Transmittance", "96.0%", "+5.5% vs glass")
k2.metric("⚖️ Weight", "0.17 kg/m²", "2.1% of glass")
k3.metric("🧪 Self-Cleaning", "✅ Lotus effect")
k4.metric("🌫️ Haze", "12%", "controlled scattering")
k5.metric("🏗️ UV Lifetime", "30 years")

st.divider()
c1, c2 = st.columns(2)
with c1:
    # Transmittance spectrum
    wl = np.linspace(250, 1300, 200)
    T_base = 0.96
    uv = np.where(wl < 300, np.exp(-((300 - wl) / 20)**2), 1.0)
    ir = np.where(wl > 1100, np.clip(1.0 - 0.05 * (wl - 1100) / 200, 0.8, 1.0), 1.0)
    T = T_base * uv * ir * 100
    T_glass = np.ones_like(wl) * 91
    T_glass[wl < 320] = 91 * np.exp(-((320 - wl[wl < 320]) / 30)**2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wl, y=T, mode='lines', name='ETFE',
        line=dict(color='#00BFFF', width=3), fill='tozeroy',
        fillcolor='rgba(0,191,255,0.1)'))
    fig.add_trace(go.Scatter(x=wl, y=T_glass, mode='lines', name='Glass',
        line=dict(color='gray', width=2, dash='dash')))
    fig.update_layout(title="Optical Transmittance T(λ)",
        xaxis_title="λ (nm)", yaxis_title="T (%)", height=320,
        yaxis_range=[60, 100], margin=dict(t=40, b=40),
        legend=dict(x=0.7, y=0.3),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # Durability over time
    years_arr = np.arange(0, 31)
    t_degrade = 96.0 * (1 - 0.001 * years_arr)
    t_glass_d = 91.0 * (1 - 0.003 * years_arr)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=years_arr, y=t_degrade, mode='lines+markers',
        name='ETFE', line=dict(color='#00BFFF', width=3),
        marker=dict(size=4)))
    fig2.add_trace(go.Scatter(x=years_arr, y=t_glass_d, mode='lines+markers',
        name='Glass', line=dict(color='gray', width=2, dash='dash'),
        marker=dict(size=3)))
    fig2.update_layout(title="Long-term Transmittance Durability",
        xaxis_title="Years", yaxis_title="T (%)", height=320,
        yaxis_range=[80, 100], margin=dict(t=40, b=40),
        legend=dict(x=0.7, y=0.3),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig2, use_container_width=True)

# --- Process ---
st.subheader("🏗️ Thermoforming Process")
p1, p2, p3 = st.columns(3)
with p1:
    st.markdown("""
**LPCVD-based ETFE Deposition:**
- 🌡️ Form temp: **270°C**
- ⚖️ Pressure: **2.0 bar**
- ✨ Cooling rate: 5°C/min
- 🔗 Seal: heat-seal to CFRP
- ⌛ Cycle: ~72 min
""")
with p2:
    st.markdown("""
**Performance:**
- 📈 AR gain vs glass: **5.5%**
- 🌫️ Path enhancement: **1.06×** (haze)
- 🧪 Adhesion: **15 N/cm** peel
- 🔥 Fire rating: **B1**
- 💰 Cost: **$20/m²**
""")
with p3:
    jsc_gain = 22.0 * (96/91) * 1.06
    st.metric("Jsc with ETFE", f"{jsc_gain:.1f} mA/cm²", f"+{jsc_gain-22:.1f} vs glass")
    st.metric("Hail Resistance", "25 mm")
    st.metric("Cleaning Savings", "$2/m²/yr")
