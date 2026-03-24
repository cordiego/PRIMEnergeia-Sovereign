"""PRIMEnergeia — PRIME-Kernel Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os

# Resolve PRIME-Kernel (bundled in lib/)
_LIB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
sys.path.insert(0, _LIB)

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("🧠 PRIME-Kernel — Shared IP Core")
st.caption("Physics Constants · HJB Solver · Telemetry | PRIMEnergeia S.A.S.")

st.markdown("""
**Central nervous system of PRIMEnergeia** — shared constants, HJB optimal control solver,
and telemetry modules used across all 5 Strategic Business Units.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS EXPLORER
# ═══════════════════════════════════════════════════════════════
try:
    from prime_kernel.constants import PhysicsConstants, MarketConstants, EngineConstants
    from prime_kernel.hjb_solver import HJBSolver, GridFrequencyDynamics, PerovskiteAnnealingDynamics
    from prime_kernel import SBU_REGISTRY, __version__
    KERNEL_LOADED = True
except ImportError:
    KERNEL_LOADED = False

if not KERNEL_LOADED:
    st.error("⚠️ PRIME-Kernel not found. Install with: `cd ~/PRIME-Kernel && pip install -e .`")
    st.stop()

st.markdown("### 📊 Kernel Status")
m1, m2, m3, m4 = st.columns(4)
m1.metric("VERSION", __version__)
m2.metric("SBUs", len(SBU_REGISTRY))
m3.metric("TOTAL REPOS", sum(len(sbu["repos"]) for sbu in SBU_REGISTRY.values()))
m4.metric("TOTAL TAM", f"${sum(sbu['tam_usd'] for sbu in SBU_REGISTRY.values()) / 1e6:.0f}M")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🏗️ SBU Registry", "⚛️ Constants", "🧠 HJB Solver", "📈 Markets"])

# ─── TAB 1: SBU Registry ───
with tab1:
    st.markdown("### Strategic Business Units")
    for sbu_name, sbu in SBU_REGISTRY.items():
        with st.expander(f"**{sbu_name}** — {sbu['model']} | {sbu['status']}", expanded=False):
            st.markdown(f"**TAM:** ${sbu['tam_usd'] / 1e6:.0f}M USD")
            st.markdown(f"**Repos:** {', '.join(f'`{r}`' for r in sbu['repos'])}")

# ─── TAB 2: Constants ───
with tab2:
    st.markdown("### ⚛️ Physics Constants")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Hydrogen**")
        st.code(f"H₂ LHV: {PhysicsConstants.H2_LHV_KWH_KG} kWh/kg\n"
                f"H₂ HHV: {PhysicsConstants.H2_HHV_KWH_KG} kWh/kg\n"
                f"H₂O per H₂: {PhysicsConstants.H2O_PER_H2} kg/kg")

    with c2:
        st.markdown("**Ammonia**")
        st.code(f"NH₃ LHV: {PhysicsConstants.NH3_LHV_MJ_KG} MJ/kg\n"
                f"NH₃ Stoich: {PhysicsConstants.NH3_STOICH_H2} kg/kg H₂\n"
                f"NH₃ Molar: {PhysicsConstants.NH3_MOLAR_MASS * 1000:.3f} g/mol")

    with c3:
        st.markdown("**Fundamentals**")
        st.code(f"kB: {PhysicsConstants.BOLTZMANN_EV:.6e} eV/K\n"
                f"Faraday: {PhysicsConstants.FARADAY:.2f} C/mol\n"
                f"SQ Limit: {PhysicsConstants.SHOCKLEY_QUEISSER_LIMIT:.1%}")

    st.markdown("### 🔧 Carnot Efficiency Calculator")
    c1, c2 = st.columns(2)
    t_hot = c1.slider("T_hot (K)", 400, 2000, 800, 50)
    t_cold = c2.slider("T_cold (K)", 200, 500, 300, 10)
    eta = PhysicsConstants.carnot_efficiency(t_hot, t_cold)
    st.metric("η_Carnot", f"{eta:.2%}", f"T_hot={t_hot}K, T_cold={t_cold}K")

    st.markdown("### ⚡ Engine Fleet")
    for eid, eng in EngineConstants.ENGINES.items():
        st.markdown(f"**{eid}** — {eng['name']}")
        st.code(f"Fuel: {eng['fuel']} | Power: {eng['rated_kw']} kW | η: {eng['efficiency']:.0%} | "
                f"Emissions: {eng['emissions']}")

# ─── TAB 3: HJB Solver ───
with tab3:
    st.markdown("### 🧠 HJB Optimal Control Solver")
    st.latex(r"\frac{\partial V}{\partial t} + \min_u \left\{ L(x,u) + \nabla V \cdot f(x,u) \right\} = 0")

    domain = st.radio("Dynamics Domain", ["🔌 Grid Frequency", "🧪 Perovskite Annealing"], horizontal=True)

    if "Grid" in domain:
        st.markdown("**Grid Frequency Stabilization** — State: [Δf (Hz), P_inj (MW)]")
        c1, c2, c3 = st.columns(3)
        sim_time = c1.number_input("Horizon (s)", 5, 120, 30, 5)
        dt = c2.number_input("dt (s)", 0.1, 2.0, 0.5, 0.1)
        grid_pts = c3.number_input("Grid Points", 3, 15, 6, 1)

        if st.button("🚀 Solve Grid HJB", type="primary"):
            with st.spinner("Solving value function..."):
                dynamics = GridFrequencyDynamics(nominal_freq=60.0)
                solver = HJBSolver(dynamics, total_time=sim_time, dt=dt,
                                   grid_points=[grid_pts, grid_pts], n_controls=7, max_sweeps=4)
                result = solver.solve().simulate(np.array([0.5, 30.0]))

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Cost", f"{result.total_cost:.2f}")
            m2.metric("Sweeps", result.n_sweeps)
            m3.metric("Converged", "✅" if result.converged else "⏳")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                subplot_titles=["Frequency Deviation (Hz)", "Optimal Injection (MW)"])
            fig.add_trace(go.Scatter(x=result.time_grid, y=result.state_trajectory[:, 0],
                                     name="Δf", line=dict(color="#00d1ff", width=3),
                                     fill="tozeroy", fillcolor="rgba(0,209,255,0.1)"), row=1, col=1)
            fig.add_hline(y=0, line=dict(color="white", dash="dash"), row=1, col=1)
            fig.add_trace(go.Scatter(x=result.time_grid, y=result.state_trajectory[:, 1],
                                     name="P_inj", line=dict(color="#00c878", width=3),
                                     fill="tozeroy", fillcolor="rgba(0,200,120,0.1)"), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=500, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(title_text="Time (s)", row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.markdown("**Perovskite Annealing** — State: [grain_nm, defect_density, temp_°C]")
        c1, c2, c3 = st.columns(3)
        sim_time = c1.number_input("Duration (s)", 60, 1200, 300, 60)
        dt = c2.number_input("dt (s)", 1.0, 10.0, 3.0, 1.0)
        grid_pts = c3.number_input("Grid Points", 3, 12, 5, 1)

        if st.button("🚀 Solve Annealing HJB", type="primary"):
            with st.spinner("Solving value function..."):
                dynamics = PerovskiteAnnealingDynamics()
                solver = HJBSolver(dynamics, total_time=sim_time, dt=dt,
                                   grid_points=[grid_pts, grid_pts, grid_pts],
                                   n_controls=7, max_sweeps=4)
                result = solver.solve().simulate(np.array([50.0, 1.5, 25.0]))

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Final Grain", f"{result.state_trajectory[-1, 0]:.0f} nm")
            m2.metric("Final Defects", f"{result.state_trajectory[-1, 1]:.3f}")
            m3.metric("Total Cost", f"{result.total_cost:.2f}")
            m4.metric("Converged", "✅" if result.converged else "⏳")

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                subplot_titles=["Grain Size (nm)", "Defect Density", "Temperature (°C)"])
            fig.add_trace(go.Scatter(x=result.time_grid, y=result.state_trajectory[:, 0],
                                     name="Grain", line=dict(color="#FFD700", width=3),
                                     fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=result.time_grid, y=result.state_trajectory[:, 1],
                                     name="Defects", line=dict(color="#ff6b6b", width=3)), row=2, col=1)
            fig.add_trace(go.Scatter(x=result.time_grid, y=result.state_trajectory[:, 2],
                                     name="Temp", line=dict(color="#00d1ff", width=3),
                                     fill="tozeroy", fillcolor="rgba(0,209,255,0.1)"), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=600, showlegend=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(title_text="Time (s)", row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)

# ─── TAB 4: Markets ───
with tab4:
    st.markdown("### 🌐 Multi-Market Coverage")

    for mid, market in MarketConstants.MARKETS.items():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{market['region']}", mid)
        c2.metric("Nodes", market["nodes"])
        c3.metric("Frequency", f"{market['frequency_hz']:.0f} Hz")
        c4.metric("Pricing", market["pricing"])

    st.divider()
    st.markdown("### 💰 Revenue Projections")
    projections = MarketConstants.projected_annual_revenue()
    total_rev = 0
    for mid, proj in projections.items():
        st.markdown(f"**{mid}** — {proj['nodes']} nodes × $180K/month × 25% royalty")
        st.code(f"Annual Rescue:  ${proj['annual_rescue_usd'] / 1e6:.1f}M {proj['currency']}\n"
                f"PRIME Revenue:  ${proj['prime_revenue_usd'] / 1e6:.1f}M {proj['currency']}")
        total_rev += proj["prime_revenue_usd"]
    st.metric("TOTAL PRIME REVENUE", f"${total_rev / 1e6:.1f}M USD/yr")

st.divider()
st.caption("PRIMEnergeia S.A.S. — PRIME-Kernel v" + __version__ + " | Shared IP Core")
