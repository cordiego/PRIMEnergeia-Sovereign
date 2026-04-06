"""PRIMEnergeia — SIBO API | Bayesian Optimization Dashboard"""
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
import time

st.header("🧠 SIBO API — Sol-Ink Bayesian Optimizer")
st.caption("Gaussian Process (Matern 5/2) | Expected Improvement | 4D Perovskite Search Space | SaaS-Ready")

# ─── Search Space ───
PARAMS = {
    "molar_conc": {"name": "Molar Concentration (M)", "min": 0.8, "max": 1.5, "step": 0.01, "default": 1.15, "unit": "M"},
    "solvent_ratio": {"name": "DMF:DMSO Ratio", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.5, "unit": ""},
    "additive_loading": {"name": "Additive Loading (vol%)", "min": 0.0, "max": 5.0, "step": 0.1, "default": 2.5, "unit": "%"},
    "spin_speed": {"name": "Spin Speed (RPM)", "min": 1000, "max": 6000, "step": 100, "default": 4000, "unit": "RPM"},
}

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🧬 Kernel", "Matern 5/2")
k2.metric("🎯 Acquisition", "EI")
k3.metric("📐 Dimensions", "4D")
k4.metric("⚡ Latency", "< 2s")
k5.metric("🔒 Auth", "API Key")

st.divider()

# ─── Interactive Optimizer Simulation ───
st.subheader("🔬 Live Optimization Simulation")
st.caption("Simulate a Bayesian optimization run with random lab results")

n_iterations = st.slider("Number of iterations", 5, 50, 20)

if st.button("Run SIBO Simulation", type="primary"):
    # Simulate GP optimization
    np.random.seed(42)
    progress = st.progress(0)
    status = st.empty()

    X_observed = []
    Y_observed = []
    best_pce = 0
    best_recipe = None
    best_history = []
    pce_history = []
    iteration_times = []

    # Ground truth function (simulated perovskite response surface)
    def simulate_pce(conc, ratio, additive, speed):
        """Simulated PCE response surface with known optimum near (1.15, 0.65, 2.0, 4000)"""
        base = 18.0
        conc_eff = -15 * (conc - 1.15)**2
        ratio_eff = -8 * (ratio - 0.65)**2
        additive_eff = -3 * (additive - 2.0)**2
        speed_eff = -0.000002 * (speed - 4000)**2
        interaction = 2.5 * np.exp(-((conc - 1.15)**2 + (ratio - 0.65)**2) / 0.1)
        noise = np.random.normal(0, 0.3)
        return max(0, base + conc_eff + ratio_eff + additive_eff + speed_eff + interaction + noise)

    for i in range(n_iterations):
        t0 = time.time()

        # Simulated ask (random for initial, then exploitation)
        if i < 5:
            conc = np.random.uniform(0.8, 1.5)
            ratio = np.random.uniform(0.0, 1.0)
            additive = np.random.uniform(0.0, 5.0)
            speed = np.random.randint(1000, 6001)
        else:
            # Simulate GP exploitation — move toward best with noise
            conc = np.clip(best_recipe[0] + np.random.normal(0, 0.05), 0.8, 1.5)
            ratio = np.clip(best_recipe[1] + np.random.normal(0, 0.05), 0.0, 1.0)
            additive = np.clip(best_recipe[2] + np.random.normal(0, 0.3), 0.0, 5.0)
            speed = int(np.clip(best_recipe[3] + np.random.normal(0, 200), 1000, 6000))

        pce = simulate_pce(conc, ratio, additive, speed)
        elapsed = time.time() - t0

        X_observed.append([conc, ratio, additive, speed])
        Y_observed.append(pce)
        iteration_times.append(elapsed * 1000)
        pce_history.append(pce)

        if pce > best_pce:
            best_pce = pce
            best_recipe = [conc, ratio, additive, speed]

        best_history.append(best_pce)

        progress.progress((i + 1) / n_iterations)
        status.markdown(f"**Iteration {i+1}/{n_iterations}** | PCE: {pce:.2f}% | Best: {best_pce:.2f}%")

    progress.empty()
    status.empty()

    st.success(f"Optimization complete! Best PCE: **{best_pce:.2f}%** in {n_iterations} iterations")

    # ─── Results KPIs ───
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Best PCE", f"{best_pce:.2f}%")
    r2.metric("Mean PCE", f"{np.mean(Y_observed):.2f}%")
    r3.metric("Std PCE", f"{np.std(Y_observed):.2f}%")
    r4.metric("Avg Latency", f"{np.mean(iteration_times):.1f} ms")

    # ─── Best Recipe ───
    st.subheader("Best Recipe Found")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Molar Conc", f"{best_recipe[0]:.3f} M")
    b2.metric("DMF:DMSO", f"{best_recipe[1]:.3f}")
    b3.metric("Additive", f"{best_recipe[2]:.2f} vol%")
    b4.metric("Spin Speed", f"{best_recipe[3]} RPM")

    st.divider()

    # ─── Convergence Plot ───
    tab1, tab2, tab3 = st.tabs(["📈 Convergence", "🗺️ Parameter Space", "📊 Distributions"])

    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
            subplot_titles=("PCE per Iteration", "Best PCE (Convergence)"))

        fig.add_trace(go.Scatter(
            x=list(range(1, n_iterations + 1)), y=pce_history,
            mode="markers+lines", name="PCE",
            marker=dict(size=8, color=pce_history, colorscale="Viridis", showscale=True, colorbar=dict(title="PCE %")),
            line=dict(width=1, color="rgba(255,255,255,0.3)"),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=list(range(1, n_iterations + 1)), y=best_history,
            mode="lines", name="Best",
            line=dict(width=3, color="#00c878"),
            fill="tozeroy", fillcolor="rgba(0,200,120,0.1)",
        ), row=2, col=1)

        fig.update_layout(
            template="plotly_dark", height=550, showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        X = np.array(X_observed)
        fig2 = make_subplots(rows=2, cols=3, vertical_spacing=0.15, horizontal_spacing=0.08,
            subplot_titles=("Conc vs Ratio", "Conc vs Additive", "Conc vs Speed",
                           "Ratio vs Additive", "Ratio vs Speed", "Additive vs Speed"))

        pairs = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
        names = ["Conc (M)", "Ratio", "Additive (%)", "Speed (RPM)"]

        for idx, (i, j) in enumerate(pairs):
            r = idx // 3 + 1
            c = idx % 3 + 1
            fig2.add_trace(go.Scatter(
                x=X[:, i], y=X[:, j], mode="markers",
                marker=dict(size=8, color=Y_observed, colorscale="Viridis",
                           showscale=(idx == 0), colorbar=dict(title="PCE %") if idx == 0 else None),
                showlegend=False,
            ), row=r, col=c)
            fig2.update_xaxes(title_text=names[i], row=r, col=c)
            fig2.update_yaxes(title_text=names[j], row=r, col=c)

        fig2.update_layout(
            template="plotly_dark", height=600,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        fig3 = make_subplots(rows=1, cols=4, subplot_titles=("Molar Conc", "Solvent Ratio", "Additive", "Spin Speed"))
        colors = ["#FFD700", "#00c878", "#00BFFF", "#FF6347"]

        for i in range(4):
            fig3.add_trace(go.Histogram(
                x=X[:, i], nbinsx=15,
                marker_color=colors[i], opacity=0.8, showlegend=False,
            ), row=1, col=i+1)

        fig3.update_layout(
            template="plotly_dark", height=300,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ─── API Reference ───
st.subheader("🔗 SIBO API — SaaS Endpoints")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
**Endpoints**
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/sessions` | Create session |
| `POST` | `/v1/sessions/{id}/ask` | Get recipe |
| `POST` | `/v1/sessions/{id}/tell` | Report result |
| `GET` | `/v1/sessions/{id}/status` | Progress |
| `GET` | `/v1/sessions/{id}/best` | Best recipe |
| `GET` | `/v1/sessions/{id}/export` | Export log |
""")

with col2:
    st.markdown("""
**SaaS Tiers**
| Tier | Asks/Day | Sessions | Price |
|------|----------|----------|-------|
| Starter | 100 | 1 | Free |
| Pro | 1,000 | 10 | $99/mo |
| Enterprise | Unlimited | 999 | Custom |

**Auth:** `X-API-Key` header
""")

st.code("""
# Quick Start
curl -X POST https://api.primenergeia.com/v1/sessions \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "perovskite-run-1"}'

# Get next recipe
curl -X POST https://api.primenergeia.com/v1/sessions/{id}/ask \\
  -H "X-API-Key: YOUR_KEY"

# Report result
curl -X POST https://api.primenergeia.com/v1/sessions/{id}/tell \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"molar_conc": 1.15, "solvent_ratio": 0.65, "additive_loading": 2.0, "spin_speed": 4000, "pce": 21.3}'
""", language="bash")

st.caption("PRIMEnergeia S.A.S. - SIBO API | Bayesian Optimization for Perovskite Solar Fabrication")
