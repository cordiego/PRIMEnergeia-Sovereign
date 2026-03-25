"""PRIMEnergeia — Multi-Market Co-Optimization Dashboard"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "markets"))

from markets.ercot.dispatch_ercot import run_ercot_backtest, run_ercot_coopt
from markets.sen.dispatch_sen import run_sen_coopt
from markets.mibel.dispatch_mibel import run_mibel_coopt

# Try loading real data
try:
    from data.data_loader import load_ercot_csv
    REAL_DATA = True
except Exception:
    REAL_DATA = False

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
</style>""", unsafe_allow_html=True)

st.header("⚡ Multi-Market Co-Optimization")
st.caption("Day-Ahead / Real-Time Price Arbitrage with Battery Degradation Tracking | PRIMEnergeia S.A.S.")

st.markdown("""
**Two-Pass Lookahead** strategy: pre-scans daily prices → assigns optimal charge/discharge slots → 
executes with battery SOC constraints. Validated against documented ERCOT heat wave data.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════
c1, c2, c3 = st.columns(3)
market = c1.selectbox("Market", ["ERCOT (Texas)", "SEN (Mexico)", "MIBEL (Iberia)"])
fleet_mw = c2.number_input("Fleet Capacity (MW)", min_value=10, max_value=10000, value=100, step=10)
battery_mwh = c3.number_input("Battery Storage (MWh)", min_value=10, max_value=20000, value=400, step=50)

c4, c5 = st.columns(2)
hours = c4.slider("Optimization Horizon (hours)", 24, 168, 24, 24)
use_real_data = c5.checkbox("Use Historical Data (ERCOT only)", value=REAL_DATA and "ERCOT" in market)

st.divider()

# ═══════════════════════════════════════════════════════════════
#  RUN OPTIMIZATION
# ═══════════════════════════════════════════════════════════════
if st.button("🚀 Run Co-Optimization", type="primary", use_container_width=True):
    with st.spinner("Running two-pass lookahead optimization..."):

        if "ERCOT" in market:
            if use_real_data and REAL_DATA:
                dataset = load_ercot_csv()
                result = run_ercot_backtest(
                    da_prices=dataset.da_prices[:hours],
                    rt_prices=dataset.rt_prices[:hours],
                    fleet_mw=fleet_mw, battery_mwh=battery_mwh,
                )
                data_label = "📂 Historical (Aug 2023 Heat Wave)"
            else:
                result = run_ercot_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
                data_label = "🔮 Simulated"
            currency = "$"
            net_profit = result.net_profit_usd
            total_rev = result.total_revenue_usd
            energy_rev = result.energy_revenue_usd
            anc_rev = result.ancillary_revenue_usd
            deg_cost = result.degradation_cost_usd
        elif "SEN" in market:
            result = run_sen_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
            data_label = "🔮 Simulated"
            currency = "MXN$"
            net_profit = result.net_profit_mxn
            total_rev = result.total_revenue_mxn
            energy_rev = result.energy_revenue_mxn
            anc_rev = result.cel_revenue_mxn
            deg_cost = result.degradation_cost_mxn
        else:
            result = run_mibel_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
            data_label = "🔮 Simulated"
            currency = "€"
            net_profit = result.net_profit_eur
            total_rev = result.total_revenue_eur
            energy_rev = result.energy_revenue_eur
            anc_rev = result.carbon_savings_eur
            deg_cost = result.degradation_cost_eur

    # ═══════════════════════════════════════════════════════════
    #  METRICS
    # ═══════════════════════════════════════════════════════════
    st.success(f"Optimization complete — {data_label}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net Profit", f"{currency}{net_profit:,.0f}")
    m2.metric("Energy Revenue", f"{currency}{energy_rev:,.0f}")
    m3.metric("Uplift vs Baseline", f"{result.uplift_pct:+.1f}%")
    m4.metric("Battery SOH", f"{result.battery_soh_end:.4f}",
              delta=f"{(result.battery_soh_end - result.battery_soh_start)*100:.3f}%")

    m5, m6, m7, m8 = st.columns(4)
    if "ERCOT" in market:
        m5.metric("Ancillary Rev", f"{currency}{anc_rev:,.0f}")
    elif "SEN" in market:
        m5.metric("CEL Credits", f"{currency}{anc_rev:,.0f}")
    else:
        m5.metric("Carbon Savings", f"{currency}{anc_rev:,.0f}")
    m6.metric("Degradation Cost", f"{currency}{deg_cost:,.0f}")
    m7.metric("Total Revenue", f"{currency}{total_rev:,.0f}")

    charge_h = sum(1 for s in result.strategy if "CHARGE" in s or "CARGA" in s)
    discharge_h = sum(1 for s in result.strategy if "DISCHARGE" in s or "DESCARGA" in s)
    m8.metric("Cycles", f"{charge_h}h↑ / {discharge_h}h↓")

    st.divider()

    # ═══════════════════════════════════════════════════════════
    #  CHARTS
    # ═══════════════════════════════════════════════════════════
    hrs = list(range(result.hours))

    # Price + Dispatch chart
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=["DA vs RT Prices", "Dispatch Schedule (MW)", "Battery SOC"],
        vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3],
    )

    # Prices
    fig.add_trace(go.Scatter(
        x=hrs, y=list(result.da_prices), name="DA Price",
        line=dict(color="#3b82f6", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=hrs, y=list(result.rt_prices), name="RT Price",
        line=dict(color="#ef4444", width=1.5),
    ), row=1, col=1)

    # Dispatch bars (green = discharge, red = charge)
    colors = ["#22c55e" if d > 0 else "#ef4444" if d < 0 else "#94a3b8" for d in result.dispatch_mw]
    fig.add_trace(go.Bar(
        x=hrs, y=list(result.dispatch_mw), name="Dispatch",
        marker_color=colors,
    ), row=2, col=1)

    # SOC
    fig.add_trace(go.Scatter(
        x=list(range(len(result.battery_soc))),
        y=[s * 100 for s in result.battery_soc],
        name="SOC %", fill="tozeroy",
        line=dict(color="#8b5cf6", width=2),
        fillcolor="rgba(139,92,246,0.2)",
    ), row=3, col=1)

    fig.update_layout(
        height=700, template="plotly_dark",
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=50, r=20, t=40, b=30),
    )
    fig.update_yaxes(title_text="$/MWh", row=1, col=1)
    fig.update_yaxes(title_text="MW", row=2, col=1)
    fig.update_yaxes(title_text="SOC %", row=3, col=1)
    fig.update_xaxes(title_text="Hour", row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Strategy breakdown
    st.subheader("📊 Strategy Breakdown")
    strategy_counts = {}
    for s in result.strategy:
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    cols = st.columns(len(strategy_counts))
    for i, (strat, count) in enumerate(sorted(strategy_counts.items(), key=lambda x: -x[1])):
        pct = 100 * count / result.hours
        cols[i].metric(strat, f"{count}h", f"{pct:.0f}%")

    # Price arbitrage
    charge_prices = [result.rt_prices[h] for h in range(result.hours)
                     if "CHARGE" in result.strategy[h] or "CARGA" in result.strategy[h]]
    discharge_prices = [result.rt_prices[h] for h in range(result.hours)
                        if "DISCHARGE" in result.strategy[h] or "DESCARGA" in result.strategy[h]]

    if charge_prices and discharge_prices:
        avg_buy = np.mean(charge_prices)
        avg_sell = np.mean(discharge_prices)
        st.subheader("💰 Price Arbitrage")
        a1, a2, a3 = st.columns(3)
        a1.metric("Avg Buy", f"{currency}{avg_buy:.2f}/MWh")
        a2.metric("Avg Sell", f"{currency}{avg_sell:.2f}/MWh")
        a3.metric("Spread Ratio", f"{avg_sell/max(1, avg_buy):.1f}x")
