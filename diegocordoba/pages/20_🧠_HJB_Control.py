"""PRIMEnergeia — HJB Optimal Engine Dispatch Controller"""
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
import sys, os

# Resolve bundled engine modules
_LIB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib", "engines")
sys.path.insert(0, _LIB)

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🧠 HJB Optimal Engine Control")
st.caption("Hamilton-Jacobi-Bellman Dynamic Programming | Optimal RPM × Load Dispatch | PRIMEnergeia S.A.S.")

st.markdown("""
Solves the HJB equation over the engine operating space to find the **minimum-fuel schedule** 
that meets a power demand profile:

> **V(E,t) = min_{rpm,load} [fuel_rate · dt + V(E', t+dt)]**

- **State:** cumulative energy delivered (kWh)  
- **Control:** (RPM, load%) at each timestep  
- **Objective:** minimize total fuel while tracking power demand  
- **CO₂:** Zero across all engines (NH₃ / H₂ fuel)
""")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════
c1, c2, c3 = st.columns(3)
engine_type = c1.selectbox("Engine", [
    "A-ICE-G1 — 335 kW (NH₃ Combustion)",
    "PEM-PB-50 — 50 kW (H₂ Fuel Cell)",
    "HY-P100 — 100 kW (H₂ Gas Turbine)"
])

mission = c2.selectbox("Mission Profile", [
    "Long-Haul Truck",
    "Marine Vessel",
    "Grid Peaking",
    "UAV / Drone"
])

duration = c3.slider("Mission Duration (hours)", 1.0, 12.0, 6.0, 0.5)

# Map selection to engine codes
engine_map = {"A-ICE": "AICE", "PEM": "PEM", "HY-P100": "HYP"}
rated_map = {"AICE": 335.0, "PEM": 50.0, "HYP": 100.0}
fuel_map = {"AICE": "NH₃", "PEM": "H₂", "HYP": "H₂"}
etype = [v for k, v in engine_map.items() if k in engine_type][0]
fuel_label = fuel_map[etype]

# Engine capability summary
st.divider()
col1, col2, col3, col4, col5, col6 = st.columns(6)
if etype == "AICE":
    col1.metric("Rated Power", "335 kW")
    col2.metric("Peak BTE", "44%")
    col3.metric("Fuel", "Green NH₃")
    col4.metric("RPM Range", "800–2100")
    col5.metric("Sweet Spot", "1400 RPM / 70%")
    col6.metric("CO₂", "ZERO")
elif etype == "PEM":
    col1.metric("Rated Power", "50 kW")
    col2.metric("Peak Eff.", "60%")
    col3.metric("Fuel", "Green H₂")
    col4.metric("Cells", "370")
    col5.metric("Sweet Spot", "30–40% Load")
    col6.metric("CO₂", "ZERO")
else:
    col1.metric("Rated Power", "100 kW")
    col2.metric("Peak Eff.", "42%")
    col3.metric("Fuel", "Green H₂")
    col4.metric("PR", "7.5:1")
    col5.metric("Sweet Spot", "80% Load")
    col6.metric("CO₂", "ZERO")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  RUN OPTIMIZATION
# ═══════════════════════════════════════════════════════════════
if st.button("🚀 Optimize Engine Dispatch", type="primary"):
    with st.spinner(f"Running HJB dispatch optimization for {fuel_label} engine..."):
        from engine_hjb import EngineHJBDispatch, generate_mission_profile

        demand = generate_mission_profile(mission, duration, dt_h=0.1, rated_kw=rated_map[etype])
        optimizer = EngineHJBDispatch(engine_type=etype)
        result = optimizer.optimize_dispatch(demand, dt_h=0.1)

    # ═══ KPIs ═══
    st.markdown("### 📊 Optimization Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Fuel", f"{result.total_fuel_kg:.1f} kg {fuel_label}")
    m2.metric("Avg Efficiency", f"{result.avg_efficiency_pct:.1f}%")
    m3.metric("Baseline Fuel", f"{result.baseline_fuel_kg:.1f} kg",
              help="Naive dispatch at constant operating point")
    m4.metric("Fuel Savings", f"{result.fuel_savings_pct:.1f}%",
              f"-{max(0, result.baseline_fuel_kg - result.total_fuel_kg):.1f} kg")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Dispatch Schedule", "⚡ Power Tracking", "⛽ Fuel & Efficiency", "📋 Mission Summary"
    ])

    t = result.time_grid

    # ═══ TAB 1: Dispatch Schedule ═══
    with tab1:
        if etype == "AICE":
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=["Optimal Load (%)", "Optimal RPM"])
            fig.add_trace(go.Scatter(x=t, y=result.load_trajectory, name="Load %",
                                     line=dict(color="#00c878", width=2),
                                     fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=t, y=result.rpm_trajectory, name="RPM",
                                     line=dict(color="#FFD700", width=2),
                                     fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"), row=2, col=1)
            fig.update_yaxes(title_text="Load (%)", row=1, col=1)
            fig.update_yaxes(title_text="RPM", row=2, col=1)
        else:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=["Optimal Load (%)", "System Efficiency (%)"])
            fig.add_trace(go.Scatter(x=t, y=result.load_trajectory, name="Load %",
                                     line=dict(color="#00c878", width=2),
                                     fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=t, y=result.efficiency_trajectory, name="Efficiency",
                                     line=dict(color="#00d1ff", width=2),
                                     fill="tozeroy", fillcolor="rgba(0,209,255,0.1)"), row=2, col=1)
            fig.update_yaxes(title_text="Load (%)", row=1, col=1)
            fig.update_yaxes(title_text="Efficiency (%)", row=2, col=1)

        fig.update_layout(template="plotly_dark", height=550, showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="Time (hours)", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

    # ═══ TAB 2: Power Tracking ═══
    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=t, y=result.demand_profile, name="Power Demand",
                                  line=dict(color="#ff6b6b", width=2, dash="dot")))
        fig2.add_trace(go.Scatter(x=t, y=result.power_trajectory, name="Power Delivered",
                                  line=dict(color="#00d1ff", width=2),
                                  fill="tonexty", fillcolor="rgba(0,209,255,0.15)"))
        fig2.update_layout(template="plotly_dark", height=450,
                           title=f"{mission} — Power Demand vs Engine Output",
                           xaxis_title="Time (hours)", yaxis_title="Power (kW)",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ═══ TAB 3: Fuel & Efficiency ═══
    with tab3:
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(go.Scatter(x=t, y=result.fuel_trajectory,
                                  name=f"Cumulative {fuel_label} (kg)",
                                  line=dict(color="#FFD700", width=3),
                                  fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"), secondary_y=False)
        fig3.add_trace(go.Scatter(x=t, y=result.efficiency_trajectory,
                                  name="Instantaneous Efficiency (%)",
                                  line=dict(color="#00c878", width=2, dash="dot")), secondary_y=True)
        fig3.update_layout(template="plotly_dark", height=450,
                           title=f"Fuel Consumption & Engine Efficiency — {fuel_label}",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig3.update_xaxes(title_text="Time (hours)")
        fig3.update_yaxes(title_text=f"{fuel_label} Consumed (kg)", secondary_y=False)
        fig3.update_yaxes(title_text="Efficiency (%)", secondary_y=True)
        st.plotly_chart(fig3, use_container_width=True)

    # ═══ TAB 4: Mission Summary ═══
    with tab4:
        energy_delivered = np.sum(result.power_trajectory * 0.1)  # kWh
        avg_power = np.mean(result.power_trajectory)
        peak_power = np.max(result.power_trajectory)
        specific_consumption = result.total_fuel_kg / max(0.1, energy_delivered) * 1000  # g/kWh

        st.markdown(f"""
### Mission: {mission} | Engine: {engine_type.split('—')[0].strip()}

| Parameter | Value |
|-----------|-------|
| **Duration** | {duration:.1f} hours |
| **Energy Delivered** | {energy_delivered:.0f} kWh |
| **Average Power** | {avg_power:.0f} kW |
| **Peak Power** | {peak_power:.0f} kW |
| **Total {fuel_label} Consumed** | {result.total_fuel_kg:.1f} kg |
| **Specific Consumption** | {specific_consumption:.0f} g/kWh |
| **Average Efficiency** | {result.avg_efficiency_pct:.1f}% |
| **Baseline Fuel (naive)** | {result.baseline_fuel_kg:.1f} kg |
| **HJB Savings** | {result.fuel_savings_pct:.1f}% ({max(0, result.baseline_fuel_kg - result.total_fuel_kg):.1f} kg) |
| **CO₂ Emissions** | 0 g/kWh |
        """)

st.divider()
st.caption("PRIMEnergeia S.A.S. — HJB Optimal Engine Control | V(E,t) = min_{rpm,load}[fuel·dt + V(E',t+dt)]")
