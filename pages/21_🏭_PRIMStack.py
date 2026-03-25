"""PRIMEnergeia — PRIMStack Plant Integrator Dashboard"""
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
import sys, os

# Resolve bundled modules
_LIB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib", "primstack")
sys.path.insert(0, _LIB)

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🏭 PRIMStack — Unified Plant Integrator")
st.caption("Multi-Timescale HJB Dispatch | Solar + Wind + Engines + Storage + Recycling | PRIMEnergeia S.A.S.")

st.markdown("""
**Closed-loop regenerative energy plant** — all subsystems dispatched as one:

Solar ☀️ + Wind 🌊 → Electrolyzer → H₂ → Engines / NH₃ → Grid + Waste Heat → Annealing ♻️
""")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  PLANT CONFIGURATION
# ═══════════════════════════════════════════════════════════════
from primstack import PRIMStackPlant, PlantConfig

config = PlantConfig()
grid_demand = 500

with st.expander("⚙️ Plant Configuration", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    solar_mw = c1.number_input("Solar (MW)", 10, 200, 50, 10)
    wind_mw = c2.number_input("Wind (MW)", 10, 500, 100, 10)
    elec_mw = c3.number_input("Electrolyzer (MW)", 5, 100, 25, 5)
    bess_mwh = c4.number_input("BESS (MWh)", 50, 1000, 400, 50)

    c5, c6, c7, c8 = st.columns(4)
    n_aice = c5.number_input("A-ICE units", 1, 10, 3)
    n_pem = c6.number_input("PEM units", 1, 20, 5)
    n_hyp = c7.number_input("HYP units", 1, 10, 2)
    grid_demand = c8.number_input("Grid Demand (kW)", 100, 5000, 500, 100)

    config = PlantConfig(
        solar_capacity_mw=solar_mw, wind_capacity_mw=wind_mw,
        electrolyzer_capacity_mw=elec_mw, bess_capacity_mwh=bess_mwh,
        n_aice=n_aice, n_pem=n_pem, n_hyp=n_hyp,
    )

plant = PRIMStackPlant(config)
summary = plant.plant_summary()

# ═══════════════════════════════════════════════════════════════
#  PLANT OVERVIEW
# ═══════════════════════════════════════════════════════════════
st.markdown("### 📊 Plant Overview")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Solar", f"{summary['solar_mw']:.0f} MW")
m2.metric("Wind", f"{summary['wind_mw']:.0f} MW")
m3.metric("Engine Fleet", f"{summary['engine_fleet_kw']:.0f} kW")
m4.metric("BESS", f"{summary['bess_mwh']:.0f} MWh")
m5.metric("H₂ Storage", f"{summary['h2_storage_kg']:,.0f} kg")
m6.metric("NH₃ Storage", f"{summary['nh3_storage_kg']:,.0f} kg")

st.info(f"**Fuel:** {summary['fuel_type']} | "
        f"**Engines:** {summary['engine_fleet_breakdown']['aice']} + "
        f"{summary['engine_fleet_breakdown']['pem']} + {summary['engine_fleet_breakdown']['hyp']}")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  SIMULATION
# ═══════════════════════════════════════════════════════════════
mode = st.radio("Simulation Mode", ["⚡ 24-Hour Dispatch", "🧠 HJB Optimal Control"], horizontal=True)

if "24-Hour" in mode:
    if st.button("🚀 Run 24h Plant Simulation", type="primary"):
        with st.spinner("Simulating 24 hours of plant operation..."):
            state, hourly = plant.simulate_day(grid_demand_kw=grid_demand)

        # KPIs
        st.markdown("### 📈 24-Hour Results")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("H₂ Final", f"{state.h2_stored_kg:,.0f} kg")
        m2.metric("NH₃ Final", f"{state.nh3_stored_kg:,.0f} kg")
        m3.metric("Battery SOC", f"{state.battery_soc:.0%}")
        m4.metric("Revenue", f"${state.cumulative_revenue_usd:,.0f}")
        m5.metric("H₂ Produced", f"{state.cumulative_h2_produced_kg:,.0f} kg")
        m6.metric("Waste Heat", f"{state.waste_heat_available_kw:.0f} kW")

        hours = list(range(24))

        tab1, tab2, tab3, tab4 = st.tabs(["☀️ Generation", "⛽ Storage", "💰 Grid", "🔥 Thermal"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hours, y=[h["solar_mw"] for h in hourly],
                                     name="Solar", fill="tozeroy",
                                     line=dict(color="#FFD700", width=2),
                                     fillcolor="rgba(255,215,0,0.2)"))
            fig.add_trace(go.Scatter(x=hours, y=[h["wind_mw"] for h in hourly],
                                     name="Wind", fill="tozeroy",
                                     line=dict(color="#00d1ff", width=2),
                                     fillcolor="rgba(0,209,255,0.2)"))
            fig.add_trace(go.Scatter(x=hours, y=[h["total_gen_mw"] for h in hourly],
                                     name="Total", line=dict(color="#00c878", width=3)))
            fig.add_hline(y=grid_demand/1000, line=dict(color="red", dash="dash"),
                          annotation_text=f"Demand: {grid_demand/1000:.1f} MW")
            fig.update_layout(template="plotly_dark", height=450, title="Generation Profile",
                              xaxis_title="Hour", yaxis_title="Power (MW)",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Scatter(x=hours, y=[h["h2_stored_kg"] for h in hourly],
                                      name="H₂ (kg)", line=dict(color="#FFD700", width=3),
                                      fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"),
                           secondary_y=False)
            fig2.add_trace(go.Scatter(x=hours, y=[h["nh3_stored_kg"] for h in hourly],
                                      name="NH₃ (kg)", line=dict(color="#00c878", width=2, dash="dot")),
                           secondary_y=False)
            fig2.add_trace(go.Scatter(x=hours, y=[h["battery_soc"] * 100 for h in hourly],
                                      name="Battery SOC (%)", line=dict(color="#00d1ff", width=2)),
                           secondary_y=True)
            fig2.update_layout(template="plotly_dark", height=450, title="Storage Levels",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig2.update_xaxes(title_text="Hour")
            fig2.update_yaxes(title_text="Fuel Stored (kg)", secondary_y=False)
            fig2.update_yaxes(title_text="SOC (%)", secondary_y=True)
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(go.Bar(x=hours, y=[h["grid_export_mw"] for h in hourly],
                                   name="Export (MW)", marker_color="#00c878"),
                           secondary_y=False)
            fig3.add_trace(go.Bar(x=hours, y=[-h["grid_import_mw"] for h in hourly],
                                   name="Import (MW)", marker_color="#ff6b6b"),
                           secondary_y=False)
            fig3.add_trace(go.Scatter(x=hours, y=[h["h2_produced_kg"] for h in hourly],
                                      name="H₂ Produced (kg/h)",
                                      line=dict(color="#FFD700", width=2)),
                           secondary_y=True)
            fig3.update_layout(template="plotly_dark", height=450, title="Grid Exchange & H₂ Production",
                               barmode="relative",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig3.update_xaxes(title_text="Hour")
            fig3.update_yaxes(title_text="Power (MW)", secondary_y=False)
            fig3.update_yaxes(title_text="H₂ (kg/h)", secondary_y=True)
            st.plotly_chart(fig3, use_container_width=True)

        with tab4:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=hours, y=[h["waste_heat_kw"] for h in hourly],
                                      name="Waste Heat Available",
                                      line=dict(color="#ff6b6b", width=3),
                                      fill="tozeroy", fillcolor="rgba(255,107,107,0.2)"))
            fig4.add_hline(y=config.anneal_heat_requirement_kw,
                           line=dict(color="#FFD700", dash="dash"),
                           annotation_text=f"Anneal Demand: {config.anneal_heat_requirement_kw} kW")
            fig4.update_layout(template="plotly_dark", height=400,
                               title="Waste Heat → Perovskite Annealing",
                               xaxis_title="Hour", yaxis_title="Thermal Power (kW)",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  HJB OPTIMAL CONTROL
# ═══════════════════════════════════════════════════════════════
else:
    st.markdown("### 🧠 Stack HJB — Multi-Timescale Optimal Dispatch")
    st.markdown("""
    **V(H₂, NH₃, SOC, t) = min_{u} [-revenue·dt + buffer_penalties·dt + V(x', t+dt)]**
    
    Controls: electrolyzer %, engine dispatch, battery mode, grid export
    """)

    c1, c2 = st.columns(2)
    sim_hours = c1.slider("Simulation Hours", 24, 336, 168, 24)
    h2_init = c2.slider("Initial H₂ Level (%)", 10, 90, 50, 5)

    if st.button("🚀 Run HJB Optimization", type="primary"):
        with st.spinner("Solving plant-level HJB value function..."):
            sys.path.insert(0, os.path.join(_LIB, "optimization"))
            from stack_hjb import StackHJBController, StackHJBState

            ctrl = StackHJBController(n_h2=8, n_nh3=8, n_soc=6,
                                       n_elec=5, n_engine=5)
            result = ctrl.simulate(
                initial=StackHJBState(h2_init/100, 0.50, 0.50, 0.5, 0.5),
                hours=sim_hours)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Annual Revenue", f"${result.annual_revenue_usd:,.0f}")
        m2.metric("H₂ Sufficiency", f"{result.h2_self_sufficiency_pct:.0f}%")
        m3.metric("Renewable Fraction", f"{result.renewable_fraction_pct:.0f}%")
        m4.metric("Final H₂", f"{result.optimal_strategy['final_h2_level']:.0%}")

        tab1, tab2, tab3 = st.tabs(["📈 Dispatch", "⛽ Buffers", "📊 Value Function"])

        t = result.time_grid[:-1]

        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                subplot_titles=["Electrolyzer %", "Engine Load %", "Grid Export %"])
            fig.add_trace(go.Scatter(x=t, y=result.electrolyzer_trajectory,
                                     name="Electrolyzer", line=dict(color="#FFD700", width=2),
                                     fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=t, y=result.engine_trajectory,
                                     name="Engines", line=dict(color="#ff6b6b", width=2),
                                     fill="tozeroy", fillcolor="rgba(255,107,107,0.1)"), row=2, col=1)
            fig.add_trace(go.Scatter(x=t, y=result.grid_export_trajectory,
                                     name="Grid Export", line=dict(color="#00c878", width=2),
                                     fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=600, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(title_text="Hours", row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=result.time_grid, y=result.h2_trajectory * 100,
                                      name="H₂ Level (%)", line=dict(color="#FFD700", width=3)))
            fig2.add_trace(go.Scatter(x=result.time_grid, y=result.nh3_trajectory * 100,
                                      name="NH₃ Level (%)", line=dict(color="#00c878", width=2, dash="dot")))
            fig2.add_trace(go.Scatter(x=result.time_grid, y=result.soc_trajectory * 100,
                                      name="Battery SOC (%)", line=dict(color="#00d1ff", width=2, dash="dash")))
            fig2.add_hline(y=30, line=dict(color="red", dash="dash"),
                           annotation_text="Critical Low (30%)")
            fig2.update_layout(template="plotly_dark", height=450,
                               title="Buffer Levels — HJB Optimal Management",
                               xaxis_title="Hours", yaxis_title="Level (%)",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            fig3 = go.Figure()
            fig3.add_trace(go.Heatmap(
                z=result.value_function,
                x=ctrl.soc_grid * 100,
                y=ctrl.h2_grid * 100,
                colorscale="Viridis",
                colorbar=dict(title="V(x)")
            ))
            fig3.update_layout(template="plotly_dark", height=450,
                               title="Value Function V(H₂, SOC) at mid NH₃",
                               xaxis_title="Battery SOC (%)",
                               yaxis_title="H₂ Level (%)",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption("PRIMEnergeia S.A.S. — PRIMStack Unified Plant Integrator | V(H₂,NH₃,SOC) = min_u[-R·dt + penalties + V(x')]")
