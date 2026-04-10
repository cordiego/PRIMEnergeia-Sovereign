"""
PRIMEnergeia — Granas Dashboard
================================
Interactive Streamlit dashboard for perovskite Bayesian Optimization.
Live optimization controls, convergence tracking, recipe inspection,
and export functionality.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import time

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
except ImportError:
    st.error("Plotly required. Install with: pip install plotly")
    st.stop()

# ─────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ Granas — Perovskite Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Theme CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    .stApp {
        background: linear-gradient(145deg, #0a0e17 0%, #111827 50%, #0a0e17 100%);
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(90deg, rgba(0,255,213,0.08) 0%, rgba(251,192,45,0.05) 100%);
        border: 1px solid rgba(0,255,213,0.2);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        background: linear-gradient(90deg, #00ffd5, #fbc02d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1rem;
        margin: 0.3rem 0 0 0;
    }
    .metric-card {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid rgba(0,255,213,0.15);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #00ffd5;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .recipe-box {
        background: rgba(0,255,213,0.05);
        border: 1px solid rgba(0,255,213,0.2);
        border-radius: 10px;
        padding: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: #00ffd5 !important;
        border-bottom-color: #00ffd5 !important;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1729 0%, #0a0e17 100%);
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# State Management
# ─────────────────────────────────────────────────────────────
if "optimizer" not in st.session_state:
    st.session_state.optimizer = None
if "running" not in st.session_state:
    st.session_state.running = False
if "trials_df" not in st.session_state:
    st.session_state.trials_df = None

# ─── Grid Handshake ─────────────────────────────────────────
try:
    from lib.granas_handshake import (
        require_grid_handshake,
        get_simulation_defaults,
        show_handshake_sidebar,
    )
    _sim_defaults = get_simulation_defaults()
    show_handshake_sidebar()
except Exception:
    _sim_defaults = {
        "n_calls": 50, "n_initial": 8,
        "label": "DORMANT (Handshake N/A)",
    }


def run_optimization(n_calls, n_initial, acq_func, multi_obj, seed):
    """Run the optimizer and cache results."""
    # Import here to avoid circular imports at module level
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from optimization.granas_bayesian import GranasOptimizer

    opt = GranasOptimizer(
        n_calls=n_calls,
        n_initial=n_initial,
        acq_func=acq_func,
        multi_objective=multi_obj,
        random_state=seed if seed > 0 else None,
    )
    opt.run()
    return opt


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="main-header">
    <h1>⚡ Granas — Perovskite Bayesian Optimizer</h1>
    <p>Physics-informed optimization for perovskite solar cell ink recipes &bull;
    PRIMEnergeia S.A.S. &bull;
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
                 color: {'#00ff88' if _sim_defaults.get('n_calls', 50) >= 200 else '#ff8c00' if _sim_defaults.get('n_calls', 50) >= 80 else '#8b5cf6'};">
        {_sim_defaults.get('label', 'UNKNOWN')}
    </span></p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Sidebar — Controls
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔬 Optimization Controls")
    st.markdown("---")

    _def_n = _sim_defaults.get("n_calls", 50)
    _def_init = _sim_defaults.get("n_initial", 8)
    n_calls = st.slider("Total Experiments", 10, 200, min(_def_n, 200), step=5)
    n_initial = st.slider("Initial Random Points", 3, 30, min(_def_init, 30))
    acq_func = st.selectbox(
        "Acquisition Function",
        ["EI", "PI", "LCB"],
        help="EI = Expected Improvement, PI = Probability of Improvement, LCB = Lower Confidence Bound"
    )
    multi_obj = st.checkbox("Multi-Objective (PCE + Stability)", value=False)
    seed = st.number_input("Random Seed (0 = none)", min_value=0, max_value=99999, value=42)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        run_btn = st.button("▶ Run", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("🗑 Clear", use_container_width=True)

    if clear_btn:
        st.session_state.optimizer = None
        st.session_state.trials_df = None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📐 Search Space")
    st.markdown("""
    | Parameter | Range |
    |-----------|-------|
    | Molar Conc | 0.8 – 1.5 M |
    | Solvent Ratio | 0.0 – 1.0 |
    | Spin Speed | 1000 – 6000 RPM |
    | Additive | 0.0 – 5.0 % |
    | Anneal Temp | 80 – 200 °C |
    | Anneal Time | 5 – 60 min |
    """)

# ─────────────────────────────────────────────────────────────
# Run Optimization
# ─────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("🧪 Running Bayesian Optimization..."):
        st.session_state.optimizer = run_optimization(
            n_calls, n_initial, acq_func, multi_obj, seed
        )
    st.toast("✅ Optimization Complete!", icon="⚡")

# ─────────────────────────────────────────────────────────────
# Main Content
# ─────────────────────────────────────────────────────────────
opt = st.session_state.optimizer

if opt is None:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <p style="font-size: 4rem; margin: 0;">🧪</p>
        <h2 style="color: #00ffd5; margin: 0.5rem 0;">Ready to Optimize</h2>
        <p style="color: #94a3b8; max-width: 500px; margin: 0.5rem auto;">
            Configure parameters in the sidebar and click <strong>▶ Run</strong>
            to find the optimal perovskite ink recipe using Bayesian Optimization.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Build DataFrame
best = opt.get_best()
df = pd.DataFrame([{
    "trial_id": t.trial_id,
    "molar_conc": t.recipe.molar_conc,
    "solvent_ratio": t.recipe.solvent_ratio,
    "spin_speed": t.recipe.spin_speed,
    "additive_pct": t.recipe.additive_pct,
    "anneal_temp": t.recipe.anneal_temp,
    "anneal_time": t.recipe.anneal_time,
    "pce": t.pce,
    "stability_score": t.stability_score,
    "grain_size_nm": t.grain_size_nm,
    "defect_density": t.defect_density,
} for t in opt.trials])

# ─── Top Metrics ────────────────────────────────────────────
st.markdown("### 📊 Optimization Results")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("🏆 Best PCE", f"{best.pce:.2f}%")
with c2:
    st.metric("🔬 Grain Size", f"{best.grain_size_nm:.0f} nm")
with c3:
    st.metric("🛡️ Stability", f"{best.stability_score:.3f}")
with c4:
    st.metric("📉 Defects", f"{best.defect_density:.4f}")
with c5:
    st.metric("🧪 Trials", f"{len(opt.trials)}")

# ─── Tabs ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Convergence", "🗺️ Landscapes", "📊 Parallel Coords",
    "🏆 Best Recipe", "📋 Experiment Log"
])

# ─── Tab 1: Convergence ────────────────────────────────────
with tab1:
    best_so_far = df["pce"].cummax()
    fig_conv = go.Figure()
    fig_conv.add_trace(go.Scatter(
        x=df["trial_id"], y=df["pce"],
        mode="markers",
        marker=dict(size=9, color=df["pce"],
                    colorscale=[[0, "#3b82f6"], [1, "#00ffd5"]],
                    opacity=0.65),
        name="All Trials",
        hovertemplate="Trial %{x}<br>PCE: %{y:.2f}%<extra></extra>",
    ))
    fig_conv.add_trace(go.Scatter(
        x=df["trial_id"], y=best_so_far,
        mode="lines",
        line=dict(color="#00ffd5", width=3),
        name="Best So Far",
    ))
    fig_conv.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e17",
        plot_bgcolor="#0a0e17",
        title="Convergence — Best PCE vs. Trial Number",
        xaxis_title="Trial #",
        yaxis_title="PCE (%)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        height=450,
    )
    st.plotly_chart(fig_conv, use_container_width=True)

# ─── Tab 2: Landscapes ─────────────────────────────────────
with tab2:
    col_a, col_b = st.columns(2)
    param_list = ["molar_conc", "solvent_ratio", "spin_speed",
                  "additive_pct", "anneal_temp", "anneal_time"]
    with col_a:
        px_sel = st.selectbox("X Axis", param_list, index=0, key="px")
    with col_b:
        py_sel = st.selectbox("Y Axis", param_list, index=1, key="py")

    fig_land = go.Figure(go.Scatter(
        x=df[px_sel], y=df[py_sel],
        mode="markers",
        marker=dict(
            size=14, color=df["pce"],
            colorscale=[[0, "#0a0e17"], [0.5, "#3b82f6"],
                        [0.8, "#00ffd5"], [1, "#fbc02d"]],
            colorbar=dict(title="PCE (%)"),
            opacity=0.85,
            line=dict(width=1, color="#0a0e17"),
        ),
        hovertemplate=f"{px_sel}: %{{x}}<br>{py_sel}: %{{y}}<br>PCE: %{{marker.color:.2f}}%<extra></extra>",
    ))
    fig_land.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e17",
        plot_bgcolor="#0a0e17",
        title=f"Parameter Landscape: {px_sel} vs {py_sel}",
        xaxis_title=px_sel,
        yaxis_title=py_sel,
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        height=500,
    )
    st.plotly_chart(fig_land, use_container_width=True)

# ─── Tab 3: Parallel Coordinates ───────────────────────────
with tab3:
    dims = [
        dict(label="Molar Conc", values=df["molar_conc"], range=[0.8, 1.5]),
        dict(label="Solvent Ratio", values=df["solvent_ratio"], range=[0, 1]),
        dict(label="Spin Speed", values=df["spin_speed"], range=[1000, 6000]),
        dict(label="Additive %", values=df["additive_pct"], range=[0, 5]),
        dict(label="Anneal Temp", values=df["anneal_temp"], range=[80, 200]),
        dict(label="Anneal Time", values=df["anneal_time"], range=[5, 60]),
        dict(label="PCE (%)", values=df["pce"]),
        dict(label="Stability", values=df["stability_score"], range=[0, 1]),
    ]
    fig_pc = go.Figure(go.Parcoords(
        line=dict(
            color=df["pce"],
            colorscale=[[0, "#3b82f6"], [0.5, "#00ffd5"],
                        [0.8, "#fbc02d"], [1, "#ff3b5c"]],
            showscale=True,
            cmin=df["pce"].min(), cmax=df["pce"].max(),
        ),
        dimensions=dims,
    ))
    fig_pc.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e17",
        plot_bgcolor="#0a0e17",
        title="All Trials — Parallel Coordinates",
        font=dict(family="Inter, sans-serif", color="#e2e8f0", size=11),
        height=500,
    )
    st.plotly_chart(fig_pc, use_container_width=True)

# ─── Tab 4: Best Recipe ────────────────────────────────────
with tab4:
    st.markdown('<div class="recipe-box">', unsafe_allow_html=True)
    st.markdown("### 🏆 Optimal Ink Recipe")
    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown(f"""
        | Parameter | Value |
        |-----------|-------|
        | **Molar Concentration** | `{best.recipe.molar_conc:.3f} M` |
        | **Solvent Ratio (DMSO:DMF)** | `{best.recipe.solvent_ratio:.3f}` |
        | **Spin Speed** | `{best.recipe.spin_speed} RPM` |
        | **Additive** | `{best.recipe.additive_pct:.2f}%` |
        | **Annealing Temperature** | `{best.recipe.anneal_temp:.1f} °C` |
        | **Annealing Time** | `{best.recipe.anneal_time:.1f} min` |
        """)
    with rc2:
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | **Power Conversion Efficiency** | `{best.pce:.2f}%` |
        | **Grain Size** | `{best.grain_size_nm:.1f} nm` |
        | **Defect Density** | `{best.defect_density:.4f}` |
        | **Stability Score** | `{best.stability_score:.3f}` |
        | **Trial #** | `{best.trial_id}` |
        """)
    st.markdown('</div>', unsafe_allow_html=True)

    # Export buttons
    st.markdown("---")
    exp1, exp2 = st.columns(2)
    with exp1:
        from dataclasses import asdict
        best_json = json.dumps({
            "optimal_recipe": asdict(best.recipe),
            "pce_pct": round(best.pce, 3),
            "stability": round(best.stability_score, 3),
            "grain_nm": round(best.grain_size_nm, 1),
            "defects": round(best.defect_density, 4),
        }, indent=2)
        st.download_button(
            "📥 Download Best Recipe (JSON)",
            best_json, "best_recipe.json", "application/json",
            use_container_width=True,
        )
    with exp2:
        st.download_button(
            "📥 Download Experiment Log (CSV)",
            df.to_csv(index=False), "granas_experiment_log.csv", "text/csv",
            use_container_width=True,
        )

# ─── Tab 5: Experiment Log ─────────────────────────────────
with tab5:
    st.markdown("### 📋 Full Experiment Log")

    # Highlight best row
    def highlight_best(row):
        if row["trial_id"] == best.trial_id:
            return ["background-color: rgba(0,255,213,0.1)"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_best, axis=1).format({
        "pce": "{:.2f}",
        "stability_score": "{:.3f}",
        "grain_size_nm": "{:.1f}",
        "defect_density": "{:.4f}",
        "molar_conc": "{:.3f}",
        "solvent_ratio": "{:.3f}",
        "additive_pct": "{:.2f}",
        "anneal_temp": "{:.1f}",
        "anneal_time": "{:.1f}",
    })
    st.dataframe(styled, use_container_width=True, height=500)

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #4b5563; font-size: 0.85rem;">
    <strong>PRIMEnergeia S.A.S.</strong> &bull; Granas Bayesian Optimizer &bull;
    Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <em>Soberanía Energética Global</em> ⚡🇲🇽
</div>
""", unsafe_allow_html=True)
