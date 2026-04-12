"""PRIMEnergeia — ETFE Encapsulation | CEO-Grade Dashboard"""
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

st.header("🛡️ Granas ETFE — Front Encapsulation Engine")
st.caption("96% Transmittance | Self-Cleaning Lotus Effect | Thermoformed on CFRP Skeleton")

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("☀️ Transmittance", "96.0%", "+5.5% vs glass", help="Broadband optical transmittance of the ETFE frontsheet. At 96%, ETFE passes more light than glass (~91%). The fluoropolymer's low refractive index (n=1.40) reduces Fresnel reflection, directly boosting Granas Jsc.")
k2.metric("💨 Weight", "0.17 kg/m²", "2.1% of glass", help="Areal weight of the ETFE encapsulation film. At 0.17 kg/m² vs 8 kg/m² for glass, ETFE is ~47× lighter. Combined with the CFRP skeleton, this makes Granas modules among the lightest tandem panels available.")
k3.metric("🧹 Self-Cleaning", "✅ Lotus effect", help="ETFE's low surface energy creates a lotus-like hydrophobic surface. Water beads and rolls off, carrying dust and debris. This self-cleaning property maintains >95% transmittance in the field without manual washing.")
k4.metric("🔬 Haze", "12%", "controlled scattering", help="Forward light scattering percentage from ETFE surface texture. Controlled haze increases effective optical path length in the absorber, improving absorption of weakly-absorbed near-bandgap photons within the Granas tandem.")
k5.metric("🏗️ UV Lifetime", "30 years", help="Projected UV-stable operational lifetime of the ETFE frontsheet. Fluoropolymer C-F bonds are highly resistant to UV photodegradation. At 0.1%/yr transmittance loss, ETFE stays above 90% T for 60+ years, protecting the perovskite underneath.")

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

# ─── Process ───
st.subheader("🏭 Thermoforming Process")
p1, p2, p3 = st.columns(3)
with p1:
    st.markdown("""
**Process Parameters:**
- 🌡️ Form temp: **270°C**
- 💨 Pressure: **2.0 bar**
- ❄️ Cooling rate: 5°C/min
- 🔗 Seal: heat-seal to CFRP
- ⏱️ Cycle: ~72 min
    """)
with p2:
    st.markdown("""
**Performance:**
- 🔬 AR gain vs glass: **5.5%**
- 🌫️ Path enhancement: **1.06×** (haze)
- 🔩 Adhesion: **15 N/cm** peel
- 🔥 Fire rating: **B1**
- 💰 Cost: **$20/m²**
    """)
with p3:
    jsc_gain = 22.0 * (96/91) * 1.06
    st.metric("Jsc with ETFE", f"{jsc_gain:.1f} mA/cm²", f"+{jsc_gain-22:.1f} vs glass", help="Net short-circuit current with ETFE encapsulation. Combines transmittance gain (96% vs 91% glass), AR coating effect, and haze path-enhancement (1.06×). This is the real-world Jsc boost from choosing ETFE over glass in Granas.")
    st.metric("Hail Resistance", "25 mm", help="Maximum hail stone diameter the ETFE frontsheet can withstand without damage (IEC 61215 compliant). ETFE's flexibility absorbs impact energy that would crack rigid glass, improving field reliability for Granas modules.")
    st.metric("Cleaning Savings", "$2/m²/yr", help="Annual O&M cost savings from ETFE's self-cleaning lotus effect vs manual panel washing. Over a 30-year module lifetime, this saves ~$60/m² in maintenance costs for each Granas module deployed.")
