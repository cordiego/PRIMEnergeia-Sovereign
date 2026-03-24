"""PRIMEnergeia — HJB Optimal Control | Annealing + SDL Fabrication"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🧠 HJB Optimal Control — Perovskite Manufacturing")
st.caption("Hamilton-Jacobi-Bellman Dynamic Programming | Annealing Schedule + SDL Fabrication Recipe | PRIMEnergeia S.A.S.")

controller = st.radio("Select Controller", [
    "🔬 Annealing Schedule (Grain Growth + Defect Passivation)",
    "🧬 SDL Fabrication Recipe (Spin + Anneal + Concentration)"
], horizontal=False)

st.divider()

# ═══════════════════════════════════════════════════════════════
#  ANNEALING HJB
# ═══════════════════════════════════════════════════════════════
if "Annealing" in controller:
    st.markdown("### 🔬 HJB Annealing — Crystallization Dynamics Controller")
    st.markdown("""
    Solves the HJB equation over the perovskite crystallization state space:
    
    > **∂V/∂t + min_u [L(x,u) + (∂V/∂x)·f(x,u)] = 0**
    
    - **State:** (grain_size_nm, defect_density, film_temp_°C)
    - **Control:** temperature ramp rate (°C/s)
    - **Dynamics:** Arrhenius grain growth + defect evolution + thermal lag
    """)

    c1, c2, c3 = st.columns(3)
    total_time = c1.slider("Anneal Duration (s)", 300, 2400, 1200, 60)
    dt = c2.slider("Time Step (s)", 1.0, 5.0, 2.0, 0.5)
    n_grid = c3.slider("Grid Resolution", 8, 30, 15, 1)

    c4, c5, c6 = st.columns(3)
    init_grain = c4.number_input("Initial Grain (nm)", 30, 200, 50)
    init_defect = c5.number_input("Initial Defect Density", 0.5, 2.5, 1.5, 0.1)
    init_temp = c6.number_input("Initial Temp (°C)", 20, 100, 25)

    if st.button("🚀 Solve HJB & Simulate Trajectory", key="hjb_anneal"):
        with st.spinner("Solving HJB value function (value iteration)..."):
            # Add granas_hjb.py to path
            hjb_path = os.path.expanduser("~/Granas-Sovereign/optimization")
            sys.path.insert(0, hjb_path)
            from granas_hjb import GranasHJBController, AnnealingState

            ctrl = GranasHJBController(
                total_time_s=total_time, dt=dt,
                n_grain=n_grid, n_defect=n_grid, n_temp=max(8, n_grid//2),
                n_control=9,
            )
            result = ctrl.simulate_trajectory(
                AnnealingState(init_grain, init_defect, init_temp)
            )

        # KPIs
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Terminal Grain", f"{result.terminal_grain_nm:.0f} nm",
                  f"+{result.terminal_grain_nm - init_grain:.0f} nm")
        m2.metric("Terminal Defects", f"{result.terminal_defects:.4f}",
                  f"{result.terminal_defects - init_defect:.4f}")
        m3.metric("PCE Boost", f"+{result.pce_boost_pct:.2f}%")
        m4.metric("Total Cost", f"{result.total_cost:.3f}")

        tab1, tab2, tab3, tab4 = st.tabs(["📈 Trajectories", "🌡️ Temperature Schedule",
                                           "🗺️ Value Function", "📋 Schedule Table"])

        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                subplot_titles=["Grain Size (nm)", "Defect Density", "Control (°C/s)"])
            t = result.time_grid / 60  # minutes
            fig.add_trace(go.Scatter(x=t, y=result.grain_trajectory, name="Grain",
                                     line=dict(color="#00c878", width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=t, y=result.defect_trajectory, name="Defects",
                                     line=dict(color="#ff6b6b", width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=t[:-1], y=result.control_trajectory, name="Ramp Rate",
                                     line=dict(color="#FFD700", width=2)), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=650, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(title_text="Time (min)", row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=t, y=result.temp_trajectory, name="Film Temp",
                                      line=dict(color="#00d1ff", width=3),
                                      fill="tozeroy", fillcolor="rgba(0,209,255,0.1)"))
            fig2.add_hline(y=200, line=dict(color="red", dash="dash"), annotation_text="Decomposition Onset")
            fig2.update_layout(template="plotly_dark", height=400, title="Optimal Temperature Profile",
                               xaxis_title="Time (min)", yaxis_title="Temperature (°C)",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            fig3 = go.Figure(data=go.Heatmap(
                z=result.value_function.T, x=ctrl.grain_grid, y=ctrl.defect_grid,
                colorscale="Viridis", colorbar=dict(title="V(x)")))
            fig3.update_layout(template="plotly_dark", height=450,
                               title="Value Function V(grain, defect) at Mean Temperature",
                               xaxis_title="Grain Size (nm)", yaxis_title="Defect Density",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

        with tab4:
            st.markdown("**Optimal Annealing Schedule (time → temperature)**")
            for t_s, T in result.optimal_schedule:
                st.text(f"  t = {t_s:7.1f}s ({t_s/60:5.1f} min) → {T:.1f} °C")

# ═══════════════════════════════════════════════════════════════
#  SDL FABRICATION HJB
# ═══════════════════════════════════════════════════════════════
else:
    st.markdown("### 🧬 SDL-HJB — Self-Driving Lab Fabrication Optimizer")
    st.markdown("""
    Optimizes perovskite fabrication recipe parameters via HJB dynamic programming:
    
    > **V(x,k) = min_u [L(x,u) + V(x', k+1)]**
    
    - **State:** (spin_rpm, anneal_temp_°C, concentration_M)
    - **Control:** (Δrpm, Δtemp, Δconc) adjustments per iteration
    - **Target:** Maximize Power Conversion Efficiency (PCE)
    """)

    c1, c2, c3 = st.columns(3)
    n_iter = c1.slider("Optimization Iterations", 5, 40, 20)
    n_sdl_grid = c2.slider("State Grid Resolution", 6, 20, 12, 1)
    n_ctrl = c3.slider("Control Grid Size", 3, 7, 5)

    c4, c5, c6 = st.columns(3)
    init_rpm = c4.number_input("Initial Spin RPM", 1000, 8000, 3000, 500)
    init_anneal = c5.number_input("Initial Anneal Temp (°C)", 50, 180, 80, 5)
    init_conc = c6.number_input("Initial Concentration (M)", 0.5, 2.0, 0.8, 0.1)

    if st.button("🚀 Optimize Fabrication Recipe", key="hjb_sdl"):
        with st.spinner("Solving SDL-HJB value function..."):
            sdl_path = os.path.expanduser("~/Granas-SDL/sdl")
            sys.path.insert(0, sdl_path)
            from hjb_sdl import SDLHJBController, FabricationState

            ctrl = SDLHJBController(
                n_iterations=n_iter, n_rpm=n_sdl_grid, n_temp=n_sdl_grid,
                n_conc=max(6, n_sdl_grid//2), n_control=n_ctrl,
            )
            result = ctrl.optimize(FabricationState(init_rpm, init_anneal, init_conc))

        # KPIs
        recipe = result.optimal_recipe
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Optimal PCE", f"{recipe['pce_pct']:.1f}%",
                  f"+{result.pce_improvement_pct:.1f}%")
        m2.metric("Spin RPM", f"{recipe['spin_rpm']:.0f}")
        m3.metric("Anneal Temp", f"{recipe['anneal_temp_C']:.0f}°C")
        m4.metric("Concentration", f"{recipe['concentration_M']:.2f} M")
        m5.metric("Grain Size", f"{recipe['grain_nm']:.0f} nm")

        tab1, tab2, tab3 = st.tabs(["📈 Convergence", "🗺️ Value Function", "📋 Optimal Recipe"])

        with tab1:
            fig = make_subplots(rows=2, cols=2, subplot_titles=[
                "PCE (%)", "Spin Speed (RPM)", "Anneal Temperature (°C)", "Concentration (M)"
            ])
            iters = result.iteration_grid
            fig.add_trace(go.Scatter(x=iters, y=result.pce_trajectory, name="PCE",
                                     line=dict(color="#00c878", width=3)), row=1, col=1)
            fig.add_trace(go.Scatter(x=iters, y=result.rpm_trajectory, name="RPM",
                                     line=dict(color="#00d1ff", width=2)), row=1, col=2)
            fig.add_trace(go.Scatter(x=iters, y=result.temp_trajectory, name="Temp",
                                     line=dict(color="#FFD700", width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=iters, y=result.conc_trajectory, name="Conc",
                                     line=dict(color="#ff6b6b", width=2)), row=2, col=2)
            fig.update_layout(template="plotly_dark", height=550, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure(data=go.Heatmap(
                z=result.value_function.T, x=ctrl.rpm_grid, y=ctrl.temp_grid,
                colorscale="Viridis", colorbar=dict(title="V(x)")))
            fig2.update_layout(template="plotly_dark", height=450,
                               title="Value Function V(rpm, temp) at Mid-Concentration",
                               xaxis_title="Spin RPM", yaxis_title="Anneal Temp (°C)",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            st.markdown("### 🏆 Optimal Fabrication Recipe")
            for k, v in recipe.items():
                st.text(f"  {k}: {v:.2f}")

st.divider()
st.caption("PRIMEnergeia S.A.S. — HJB Optimal Control Division | ∂V/∂t + min_u[L + ∇V·f] = 0")
