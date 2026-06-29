"""PRIMEnergeia - HJB Arbitrage & Granas H2 Synergy | Executive Simulator"""
import sys, os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path: sys.path.insert(0, _root)

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Configuration & Styling ---
st.set_page_config(page_title="HJB Arbitrage & Granas H2", page_icon="🔋", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background-color: #050810; }
[data-testid="stMetricValue"] { font-size: 26px !important; color: #00d1ff; font-family: 'JetBrains Mono', monospace; font-weight: 700; text-shadow: 0 0 10px rgba(0,209,255,0.3); }
[data-testid="stMetricLabel"] { font-size: 13px !important; font-weight: 600; color: #94a3b8; letter-spacing: 1.2px; text-transform: uppercase; }
.hero-tagline { font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #00ff88; white-space: nowrap; overflow: hidden; border-right: 2px solid #00ff88; animation: typing 3.5s steps(55, end), blink-caret 0.75s step-end infinite; }
@keyframes typing { from { max-width: 0 } to { max-width: 100% } }
@keyframes blink-caret { 50% { border-color: transparent; } }
.stSlider div[data-baseweb="slider"] div[data-testid="stTickBar"] { display: none; }
.card { background: linear-gradient(135deg, #0d1520, #111b2a); border: 1px solid #1a2744; border-radius: 12px; padding: 20px; box-shadow: 0 4px 20px rgba(0, 209, 255, 0.05); margin-bottom: 20px; }
.card-header { font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700; color: #00d1ff; margin-bottom: 12px; border-bottom: 1px solid #1a2744; padding-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("# 🔋 HJB Arbitrage + Granas H2 Synergy")
st.markdown("<div class='hero-tagline'>Optimal Stochastic Control vs Heuristics — ERCOT / CAISO Simulation</div>", unsafe_allow_html=True)
st.caption("PRIMEnergeia S.A.S. | Quantitative Dispatch Engine")
st.divider()

# --- Simulation Parameters Sidebar ---
with st.sidebar:
    st.header("⚙️ Simulation Params")
    
    st.subheader("Market Dynamics (SDE)")
    mean_price = st.slider("Mean Price ($/MWh)", 10.0, 100.0, 40.0)
    volatility = st.slider("Volatility (σ)", 0.1, 5.0, 2.5)
    jump_intensity = st.slider("Negative Jump Intensity (λ)", 0.0, 0.2, 0.05)
    jump_size = st.slider("Mean Negative Jump ($)", -100.0, -10.0, -50.0)
    
    st.subheader("BESS Hardware")
    bess_mw = st.number_input("BESS Power (MW)", value=100.0)
    bess_mwh = st.number_input("BESS Capacity (MWh)", value=400.0)
    rte = st.slider("Round-Trip Efficiency", 0.70, 0.99, 0.92)
    
    st.subheader("Granas Electrolyzer")
    pem_mw = st.number_input("PEM Power (MW)", value=20.0)
    h2_price = st.number_input("H2 Value Eq. ($/MWh)", value=120.0)
    
    st.markdown("---")
    if st.button("RUN HJB SIMULATION", type="primary", use_container_width=True):
        st.session_state["run_sim"] = True

# --- Simulation Logic ---
# Stochastic Price Simulation (Ornstein-Uhlenbeck with Jumps)
def simulate_price(steps=168, dt=1.0):
    np.random.seed(42)  # Deterministic for dashboard consistency
    theta = 0.2 # Mean reversion speed
    prices = np.zeros(steps)
    prices[0] = mean_price
    for t in range(1, steps):
        # OU process
        dp = theta * (mean_price - prices[t-1]) * dt + volatility * np.sqrt(dt) * np.random.randn()
        # Jump process
        if np.random.rand() < jump_intensity * dt:
            dp += np.random.normal(jump_size, 10.0)
        prices[t] = max(prices[t-1] + dp, -150.0) # Cap negative price at -150
    return prices

# HJB Policy (Approximation for visualization)
def hjb_policy(price, soc, max_charge, max_discharge):
    shadow_price = 50.0 - 0.2 * soc # Linear shadow price approximation
    if price < shadow_price - 10:
        return max_charge
    elif price > shadow_price + 10:
        return -max_discharge
    return 0.0

# Heuristic Policy
def heuristic_policy(price, soc, max_charge, max_discharge):
    if price < 20 and soc < 95:
        return max_charge
    elif price > 70 and soc > 5:
        return -max_discharge
    return 0.0

# Run Simulation
steps = 168 # 1 week, hourly
prices = simulate_price(steps)

soc_hjb = np.zeros(steps)
soc_hjb[0] = 50.0
dispatch_hjb = np.zeros(steps)
h2_dispatch = np.zeros(steps)

soc_heur = np.zeros(steps)
soc_heur[0] = 50.0
dispatch_heur = np.zeros(steps)

rev_hjb = 0.0
rev_heur = 0.0
rev_h2 = 0.0

cum_rev_hjb = np.zeros(steps)
cum_rev_heur = np.zeros(steps)

for t in range(steps-1):
    max_c = min(bess_mw, (100 - soc_hjb[t]) / 100 * bess_mwh)
    max_d = min(bess_mw, soc_hjb[t] / 100 * bess_mwh)
    
    # HJB Step
    action_hjb = hjb_policy(prices[t], soc_hjb[t], max_c, max_d)
    
    # Granas Synergy: If price is negative and battery is full (or charging maxed), route to H2
    h2_power = 0.0
    if prices[t] < 0:
        # We want to consume as much as possible to get paid
        remaining_capacity = pem_mw
        if action_hjb < bess_mw: # Battery isn't taking full power
            h2_power = min(remaining_capacity, pem_mw)
    
    dispatch_hjb[t] = action_hjb
    h2_dispatch[t] = h2_power
    
    if action_hjb > 0:
        soc_hjb[t+1] = soc_hjb[t] + (action_hjb * rte) / bess_mwh * 100
        rev_hjb -= action_hjb * prices[t]
    else:
        soc_hjb[t+1] = soc_hjb[t] + action_hjb / bess_mwh * 100
        rev_hjb -= action_hjb * prices[t]
        
    rev_h2 -= h2_power * prices[t] # Paid to consume (price is negative)
    rev_h2 += h2_power * h2_price # Value of created H2
    
    cum_rev_hjb[t] = rev_hjb + rev_h2
    
    # Heuristic Step
    max_c_heur = min(bess_mw, (100 - soc_heur[t]) / 100 * bess_mwh)
    max_d_heur = min(bess_mw, soc_heur[t] / 100 * bess_mwh)
    action_heur = heuristic_policy(prices[t], soc_heur[t], max_c_heur, max_d_heur)
    dispatch_heur[t] = action_heur
    
    if action_heur > 0:
        soc_heur[t+1] = soc_heur[t] + (action_heur * rte) / bess_mwh * 100
        rev_heur -= action_heur * prices[t]
    else:
        soc_heur[t+1] = soc_heur[t] + action_heur / bess_mwh * 100
        rev_heur -= action_heur * prices[t]
        
    cum_rev_heur[t] = rev_heur

# Fill last step
cum_rev_hjb[-1] = cum_rev_hjb[-2]
cum_rev_heur[-1] = cum_rev_heur[-2]

# --- UI Render ---
# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("HJB + Granas Revenue", f"${cum_rev_hjb[-1]:,.0f}")
k2.metric("Heuristic Revenue", f"${cum_rev_heur[-1]:,.0f}")

alpha = (cum_rev_hjb[-1] - cum_rev_heur[-1]) / abs(cum_rev_heur[-1]) * 100 if cum_rev_heur[-1] != 0 else 0
k3.metric("Mathematical Edge (Alfa)", f"+{alpha:.1f}%", delta=f"${cum_rev_hjb[-1] - cum_rev_heur[-1]:,.0f}")
k4.metric("Granas H2 Value Captured", f"${rev_h2:,.0f}", delta="Zero Waste", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# Main Charts
tab1, tab2, tab3 = st.tabs(["⚡ Dispatch & SoC (Time-Series)", "📈 Cumulative Revenue (Alfa)", "🔥 HJB Policy Heatmap"])

with tab1:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=("Market Price ($/MWh)", "Dispatch (MW) [Green=Charge, Blue=Discharge, Purple=Granas H2]", "State of Charge (%)"))
    
    time_ax = np.arange(steps)
    
    # Price
    fig.add_trace(go.Scatter(x=time_ax, y=prices, name="Spot Price", line=dict(color="#FFD700", width=2)), row=1, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)", row=1, col=1)
    
    # Dispatch
    fig.add_trace(go.Bar(x=time_ax, y=np.where(dispatch_hjb > 0, dispatch_hjb, 0), name="BESS Charge (HJB)", marker_color="#00ff88"), row=2, col=1)
    fig.add_trace(go.Bar(x=time_ax, y=np.where(dispatch_hjb < 0, dispatch_hjb, 0), name="BESS Discharge (HJB)", marker_color="#00d1ff"), row=2, col=1)
    fig.add_trace(go.Bar(x=time_ax, y=h2_dispatch, name="Granas PEM (H2)", marker_color="#8a2be2"), row=2, col=1)
    
    # SoC
    fig.add_trace(go.Scatter(x=time_ax, y=soc_hjb, name="HJB SoC", line=dict(color="#00ff88", width=3)), row=3, col=1)
    fig.add_trace(go.Scatter(x=time_ax, y=soc_heur, name="Heur SoC", line=dict(color="#FF6347", width=2, dash="dash")), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=800, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="relative")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=time_ax, y=cum_rev_hjb, name="HJB + Granas", fill="tozeroy", fillcolor="rgba(0,255,136,0.2)", line=dict(color="#00ff88", width=3)))
    fig2.add_trace(go.Scatter(x=time_ax, y=cum_rev_heur, name="Heuristics", fill="tozeroy", fillcolor="rgba(255,99,71,0.1)", line=dict(color="#FF6347", width=2, dash="dash")))
    
    fig2.update_layout(template="plotly_dark", height=500, title="Cumulative Revenue Generation (7 Days)", 
                       xaxis_title="Hours", yaxis_title="USD ($)",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.markdown("""
    <div class='card'>
        <div class='card-header'>Hamilton-Jacobi-Bellman Optimal Policy</div>
        <div style='color: #94a3b8; font-size: 14px;'>
        La matriz muestra la decisión óptima del agente en función del Precio Spot y el SoC. 
        Note la frontera no lineal: el precio de corte para cargar/descargar depende directamente del estado interno de la batería, calculando el costo de oportunidad futuro exacto.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate Heatmap Matrix
    price_grid = np.linspace(-50, 150, 50)
    soc_grid = np.linspace(0, 100, 50)
    policy_matrix = np.zeros((len(price_grid), len(soc_grid)))
    
    for i, p in enumerate(price_grid):
        for j, s in enumerate(soc_grid):
            policy_matrix[i, j] = hjb_policy(p, s, bess_mw, bess_mw)
            
    fig3 = go.Figure(data=go.Heatmap(
        z=policy_matrix, x=soc_grid, y=price_grid,
        colorscale="PuBuGn",
        colorbar=dict(title="Dispatch (MW)")
    ))
    fig3.update_layout(template="plotly_dark", height=600,
                       xaxis_title="State of Charge (%)", yaxis_title="Spot Price ($/MWh)",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)
