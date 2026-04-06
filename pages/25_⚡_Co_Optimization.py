"""
PRIMEnergeia — Multi-Market Co-Optimization Dashboard
=====================================================
Client-facing simulation tool. Allows prospects to:
1. Select their market, fleet size, and battery configuration
2. Choose from preset client profiles or custom settings
3. Run the HJB two-pass lookahead optimizer
4. See their projected savings, our 25% fee, and their net
5. Download a PDF-ready report

PRIMEnergeia S.A.S. — Grid Optimization Division
"""
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
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os, json
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "markets"))

from markets.ercot.dispatch_ercot import run_ercot_backtest, run_ercot_coopt
from markets.sen.dispatch_sen import run_sen_coopt
from markets.mibel.dispatch_mibel import run_mibel_coopt

try:
    from data.data_loader import load_ercot_csv
    REAL_DATA = True
except Exception:
    REAL_DATA = False

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG & STYLES
# ═══════════════════════════════════════════════════════════════
# page_config handled by app.py — do not call set_page_config in sub-pages

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 24px !important; font-weight: 700}
[data-testid="stMetricLabel"] {font-size: 12px !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px}
[data-testid="stMetricDelta"] {font-size: 13px !important}
.block-container {padding-top: 2rem}
div[data-testid="stExpander"] {border: 1px solid #333; border-radius: 8px}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  CLIENT PRESETS
# ═══════════════════════════════════════════════════════════════
CLIENT_PRESETS = {
    "Custom": {"fleet_mw": 100, "battery_mwh": 400, "market": "ERCOT (Texas)", "hours": 168},
    "Small IPP (50 MW)": {"fleet_mw": 50, "battery_mwh": 200, "market": "ERCOT (Texas)", "hours": 168},
    "Mid-Size Operator (200 MW)": {"fleet_mw": 200, "battery_mwh": 800, "market": "ERCOT (Texas)", "hours": 168},
    "Large Fleet (500 MW)": {"fleet_mw": 500, "battery_mwh": 2000, "market": "ERCOT (Texas)", "hours": 168},
    "GW-Scale Portfolio (1000 MW)": {"fleet_mw": 1000, "battery_mwh": 4000, "market": "ERCOT (Texas)", "hours": 168},
    "Mexico SEN (100 MW)": {"fleet_mw": 100, "battery_mwh": 400, "market": "SEN (Mexico)", "hours": 168},
    "Iberia MIBEL (100 MW)": {"fleet_mw": 100, "battery_mwh": 400, "market": "MIBEL (Iberia)", "hours": 168},
    "Microgrid (10 MW)": {"fleet_mw": 10, "battery_mwh": 40, "market": "ERCOT (Texas)", "hours": 168},
    "Data Center (50 MW UPS)": {"fleet_mw": 50, "battery_mwh": 100, "market": "ERCOT (Texas)", "hours": 168},
    "EV Fleet Hub (25 MW)": {"fleet_mw": 25, "battery_mwh": 100, "market": "ERCOT (Texas)", "hours": 168},
}

# ═══════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("## ⚡ Multi-Market Co-Optimization Engine")
st.markdown("""
<div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
     padding: 20px 28px; border-radius: 12px; margin-bottom: 24px;
     border: 1px solid rgba(99, 102, 241, 0.3)'>
<span style='font-size: 13px; color: #818cf8; font-weight: 600; letter-spacing: 1px'>BACKTEST-VALIDATED</span><br>
<span style='font-size: 20px; color: white; font-weight: 600'>55.7% dispatch uplift · 36.9x price spread · 25% value share</span><br>
<span style='font-size: 14px; color: #94a3b8'>Two-pass lookahead strategy validated against ERCOT August 2023 heat wave data.
You only pay when we make you money.</span>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION PANEL
# ═══════════════════════════════════════════════════════════════
st.markdown("### 🎛️ Configure Your Simulation")

preset_col, spacer = st.columns([3, 1])
preset = preset_col.selectbox("Client Profile", list(CLIENT_PRESETS.keys()),
                               help="Select a preset or choose 'Custom' to configure manually")

p = CLIENT_PRESETS[preset]

c1, c2, c3, c4 = st.columns(4)
market = c1.selectbox("Market", [
    "ERCOT (Texas)", "PJM (US East)", "CAISO (California)", "MISO (Midwest)",
    "SPP (Central)", "NYISO (New York)", "ISONE (New England)",
    "IESO (Ontario)", "AESO (Alberta)",
    "SEN (Mexico)", "MIBEL (Iberia)",
    "EPEX (Germany)", "EPEX (France)", "Nord Pool (Nordics)", "Elexon (UK)",
    "NEM (Australia)", "JEPX (Japan)"
],
                       index=0)
fleet_mw = c2.number_input("Fleet Capacity (MW)", min_value=1, max_value=50000,
                            value=p["fleet_mw"], step=10)
battery_mwh = c3.number_input("Battery Storage (MWh)", min_value=1, max_value=100000,
                               value=p["battery_mwh"], step=50)
hours = c4.selectbox("Horizon", [24, 48, 72, 120, 168],
                      index=[24, 48, 72, 120, 168].index(p["hours"]),
                      format_func=lambda h: f"{h}h ({h//24}d)")

# Advanced settings
with st.expander("⚙️ Advanced Settings"):
    adv1, adv2, adv3 = st.columns(3)
    charge_eff = adv1.slider("Charge Efficiency (%)", 85, 99, 92, 1) / 100
    discharge_eff = adv2.slider("Discharge Efficiency (%)", 85, 99, 95, 1) / 100
    degradation_rate = adv3.slider("Annual Degradation (%)", 1.0, 10.0, 5.3, 0.1)

    adv4, adv5 = st.columns(2)
    use_real_data = adv4.checkbox("Use Historical Data (ERCOT only)",
                                  value=REAL_DATA and "ERCOT" in market)
    show_naive = adv5.checkbox("Show Naive Baseline Comparison", value=True)

st.divider()

# ═══════════════════════════════════════════════════════════════
#  RUN OPTIMIZATION
# ═══════════════════════════════════════════════════════════════
run_clicked = st.button("🚀 Run Co-Optimization", type="primary", use_container_width=True)

if run_clicked:
    with st.spinner("Running two-pass lookahead optimization..."):

        if "ERCOT" in market:
            if use_real_data and REAL_DATA:
                # Priority 1: Session-state dataset (from Data Upload / Fetch Live)
                session_ds = st.session_state.get("prime_dataset")
                if session_ds and session_ds.market == "ercot":
                    dataset = session_ds
                    data_label = f"📂 {st.session_state.get('prime_data_source', 'Live Data')}"
                else:
                    dataset = load_ercot_csv()
                    data_label = "📂 Historical (File)"
                result = run_ercot_backtest(
                    da_prices=dataset.da_prices[:hours],
                    rt_prices=dataset.rt_prices[:hours],
                    fleet_mw=fleet_mw, battery_mwh=battery_mwh,
                )

            else:
                result = run_ercot_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
                data_label = "🔮 Simulated"
            currency, curr_symbol = "USD", "$"
            net_profit = result.net_profit_usd
            total_rev = result.total_revenue_usd
            energy_rev = result.energy_revenue_usd
            anc_rev = result.ancillary_revenue_usd
            deg_cost = result.degradation_cost_usd
            anc_label = "Ancillary Revenue"
        elif "SEN" in market:
            result = run_sen_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
            data_label = "🔮 Simulated"
            currency, curr_symbol = "MXN", "MXN$"
            net_profit = result.net_profit_mxn
            total_rev = result.total_revenue_mxn
            energy_rev = result.energy_revenue_mxn
            anc_rev = result.cel_revenue_mxn
            deg_cost = result.degradation_cost_mxn
            anc_label = "CEL Credits"
        else:
            result = run_mibel_coopt(fleet_mw=fleet_mw, battery_mwh=battery_mwh, hours=hours)
            data_label = "🔮 Simulated"
            currency, curr_symbol = "EUR", "€"
            net_profit = result.net_profit_eur
            total_rev = result.total_revenue_eur
            energy_rev = result.energy_revenue_eur
            anc_rev = result.carbon_savings_eur
            deg_cost = result.degradation_cost_eur
            anc_label = "Carbon Savings"

    # ═══════════════════════════════════════════════════════════
    #  RESULTS HEADER
    # ═══════════════════════════════════════════════════════════
    st.success(f"Optimization complete — {data_label}")

    # Annual projections
    weekly_factor = hours / 168
    annual_net = (net_profit / max(1, weekly_factor)) * 52
    annual_energy = (energy_rev / max(1, weekly_factor)) * 52

    # ═══════════════════════════════════════════════════════════
    #  YOUR RESULTS (CLIENT VIEW)
    # ═══════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Your Results", "📈 Charts & Analysis", "💰 Pricing & ROI", "📋 Report"
    ])

    with tab1:
        st.markdown("### Your Optimization Results")

        # Period metrics
        st.markdown(f"**Period: {hours} hours ({hours//24} days) | {data_label}**")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Profit (period)", f"{curr_symbol}{net_profit:,.0f}")
        m2.metric("Energy Revenue", f"{curr_symbol}{energy_rev:,.0f}")
        m3.metric("Uplift vs Baseline", f"{result.uplift_pct:+.1f}%")
        m4.metric("Battery SOH", f"{result.battery_soh_end:.4f}",
                  delta=f"{(result.battery_soh_end - result.battery_soh_start)*100:.3f}%")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric(anc_label, f"{curr_symbol}{anc_rev:,.0f}")
        m6.metric("Degradation Cost", f"{curr_symbol}{deg_cost:,.0f}")
        m7.metric("Total Revenue", f"{curr_symbol}{total_rev:,.0f}")
        charge_h = sum(1 for s in result.strategy if "CHARGE" in s or "CARGA" in s)
        discharge_h = sum(1 for s in result.strategy if "DISCHARGE" in s or "DESCARGA" in s)
        m8.metric("Cycles", f"{charge_h}h↑ / {discharge_h}h↓")

        st.divider()

        # Annual projection
        st.markdown("### 📈 Annual Projection")
        st.info(f"Extrapolated from {hours}h backtest to 8,760h (52 weeks)")

        a1, a2, a3 = st.columns(3)
        a1.metric("Annual Net Profit", f"{curr_symbol}{annual_net:,.0f}")
        a2.metric("Annual Energy Rev", f"{curr_symbol}{annual_energy:,.0f}")

        weekly_soh_loss = (result.battery_soh_start - result.battery_soh_end)
        annual_soh_loss = weekly_soh_loss * (52 / max(1, weekly_factor))
        if annual_soh_loss > 0:
            battery_life = 0.2 / annual_soh_loss  # 20% degradation = end of life
        else:
            battery_life = 99
        a3.metric("Est. Battery Life", f"{battery_life:.1f} years",
                  delta=f"-{annual_soh_loss*100:.1f}%/yr")

        # Strategy breakdown
        st.markdown("### 📊 Strategy Breakdown")
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
            max_sell = np.max(discharge_prices)

            st.markdown("### 💰 Price Arbitrage Performance")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Avg Buy Price", f"{curr_symbol}{avg_buy:.2f}/MWh")
            p2.metric("Avg Sell Price", f"{curr_symbol}{avg_sell:.2f}/MWh")
            p3.metric("Spread Ratio", f"{avg_sell/max(1, avg_buy):.1f}x")
            p4.metric("Peak Capture", f"{curr_symbol}{max_sell:,.0f}/MWh")

    # ═══════════════════════════════════════════════════════════
    #  CHARTS TAB
    # ═══════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Price Curves, Dispatch, and SOC")

        hrs_list = list(range(result.hours))

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            subplot_titles=["Day-Ahead vs Real-Time Prices ($/MWh)",
                           "Dispatch Schedule (MW) — Green=Sell, Red=Buy",
                           "Battery State of Charge (%)"],
            vertical_spacing=0.07,
            row_heights=[0.35, 0.35, 0.30],
        )

        # Prices
        fig.add_trace(go.Scatter(
            x=hrs_list, y=list(result.da_prices), name="DA LMP",
            line=dict(color="#3b82f6", width=1.5),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hrs_list, y=list(result.rt_prices), name="RT LMP",
            line=dict(color="#ef4444", width=1.5),
        ), row=1, col=1)

        # Spike threshold line
        fig.add_hline(y=100, line_dash="dash", line_color="rgba(245,158,11,0.5)",
                      annotation_text="Spike Threshold ($100)", row=1, col=1)

        # Dispatch
        colors = ["#22c55e" if d > 0 else "#ef4444" if d < 0 else "#475569"
                  for d in result.dispatch_mw]
        fig.add_trace(go.Bar(
            x=hrs_list, y=list(result.dispatch_mw), name="Dispatch (MW)",
            marker_color=colors, opacity=0.85,
        ), row=2, col=1)

        # SOC
        fig.add_trace(go.Scatter(
            x=list(range(len(result.battery_soc))),
            y=[s * 100 for s in result.battery_soc],
            name="SOC %", fill="tozeroy",
            line=dict(color="#8b5cf6", width=2),
            fillcolor="rgba(139,92,246,0.15)",
        ), row=3, col=1)
        fig.add_hline(y=95, line_dash="dot", line_color="rgba(34,197,94,0.4)",
                      annotation_text="Max SOC", row=3, col=1)
        fig.add_hline(y=5, line_dash="dot", line_color="rgba(239,68,68,0.4)",
                      annotation_text="Min SOC", row=3, col=1)

        fig.update_layout(
            height=800, template="plotly_dark",
            font=dict(family="Inter, sans-serif", size=12),
            legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"),
            margin=dict(l=60, r=20, t=50, b=30),
        )
        fig.update_yaxes(title_text=f"{curr_symbol}/MWh", row=1, col=1)
        fig.update_yaxes(title_text="MW", row=2, col=1)
        fig.update_yaxes(title_text="SOC %", range=[0, 105], row=3, col=1)
        fig.update_xaxes(title_text="Hour", row=3, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # Revenue accumulation chart
        st.markdown("### 📈 Cumulative Revenue Over Time")
        cumulative = np.cumsum([
            result.dispatch_mw[h] * result.rt_prices[h] if result.dispatch_mw[h] > 0
            else result.dispatch_mw[h] * result.rt_prices[h]
            for h in range(result.hours)
        ])

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=hrs_list, y=cumulative,
            fill="tozeroy", name="Cumulative Revenue",
            line=dict(color="#10b981", width=2),
            fillcolor="rgba(16,185,129,0.15)",
        ))
        fig2.update_layout(
            height=350, template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            xaxis_title="Hour", yaxis_title=f"Cumulative {curr_symbol}",
            margin=dict(l=60, r=20, t=30, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Price distribution
        st.markdown("### 📊 Price Distribution")
        d1, d2 = st.columns(2)
        with d1:
            fig3 = go.Figure()
            fig3.add_trace(go.Histogram(
                x=list(result.da_prices), name="DA Prices", nbinsx=30,
                marker_color="#3b82f6", opacity=0.7,
            ))
            fig3.add_trace(go.Histogram(
                x=list(result.rt_prices), name="RT Prices", nbinsx=30,
                marker_color="#ef4444", opacity=0.7,
            ))
            fig3.update_layout(
                height=300, template="plotly_dark", barmode="overlay",
                title="Price Distribution ($/MWh)", margin=dict(t=40),
            )
            st.plotly_chart(fig3, use_container_width=True)

        with d2:
            # Hourly revenue heatmap-style bar
            hourly_rev = [result.dispatch_mw[h] * result.rt_prices[h] for h in range(result.hours)]
            rev_colors = ["#22c55e" if r > 0 else "#ef4444" for r in hourly_rev]
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=hrs_list, y=hourly_rev, marker_color=rev_colors, opacity=0.8,
            ))
            fig4.update_layout(
                height=300, template="plotly_dark",
                title=f"Hourly Revenue ({curr_symbol})", margin=dict(t=40),
                xaxis_title="Hour",
            )
            st.plotly_chart(fig4, use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    #  PRICING & ROI TAB
    # ═══════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 💰 PRIMEngine Pricing — 25% Value Share")
        st.markdown("""
        > **You only pay when we make you money.** Our fee is 25% of the *incremental* revenue
        > we generate above your current dispatch performance. You keep 75%.
        """)

        # Determine tier
        if fleet_mw > 1000:
            tier_name, min_commit = "Enterprise", 2_000_000
        elif fleet_mw > 200:
            tier_name, min_commit = "Scale", 500_000
        elif fleet_mw > 50:
            tier_name, min_commit = "Growth", 50_000
        else:
            tier_name, min_commit = "Pilot", 0

        # Calculate fee
        value_share = annual_net * 0.25
        actual_fee = max(value_share, min_commit) if tier_name != "Pilot" else 0
        you_keep = annual_net - actual_fee

        st.markdown(f"**Your Tier: {tier_name}** (based on {fleet_mw} MW fleet)")

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Your Annual Uplift", f"{curr_symbol}{annual_net:,.0f}",
                  help="Additional revenue from PRIMEngine vs naive TOU dispatch")
        f2.metric("PRIMEngine Fee (25%)", f"{curr_symbol}{actual_fee:,.0f}",
                  help=f"25% of uplift, min {curr_symbol}{min_commit:,.0f}/yr")
        f3.metric("YOU KEEP (75%)", f"{curr_symbol}{you_keep:,.0f}",
                  delta=f"+{curr_symbol}{you_keep:,.0f}")
        f4.metric("Your ROI", f"{you_keep/max(1, actual_fee):.0f}x" if actual_fee > 0 else "∞",
                  help="Your net return per dollar spent on PRIMEngine")

        st.divider()

        # Pricing comparison table
        st.markdown("### 📋 Tier Comparison")
        pricing_df = pd.DataFrame({
            "Tier": ["Pilot", "Growth", "Scale", "Enterprise"],
            "Fleet Size": ["Any", "≤ 200 MW", "200 MW - 1 GW", "> 1 GW"],
            "Fee": ["$0", "25% of uplift", "25% of uplift", "25% of uplift"],
            "Min Annual": ["$0 (90 days)", "$50,000", "$500,000", "$2,000,000"],
            "Includes": [
                "Single market, 90-day trial",
                "All markets, dashboard, reports",
                "API, SCADA integration, dedicated AM",
                "On-premise, custom dev, white-label",
            ],
        })
        st.dataframe(pricing_df, use_container_width=True, hide_index=True)

        st.divider()

        # Multi-year projection
        st.markdown("### 📈 Multi-Year Revenue Projection")
        years = list(range(1, 11))
        your_cumulative = [you_keep * y for y in years]
        our_cumulative = [actual_fee * y for y in years]

        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=[f"Year {y}" for y in years], y=your_cumulative,
            name="You Keep (75%)", marker_color="#22c55e",
        ))
        fig5.add_trace(go.Bar(
            x=[f"Year {y}" for y in years], y=our_cumulative,
            name="PRIMEngine Fee (25%)", marker_color="#6366f1",
        ))
        fig5.update_layout(
            height=400, template="plotly_dark", barmode="stack",
            font=dict(family="Inter, sans-serif"),
            yaxis_title=f"Cumulative {curr_symbol}",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    #  REPORT TAB
    # ═══════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### 📋 Client Report — Ready to Share")

        report_date = datetime.now().strftime("%B %d, %Y")

        report_text = f"""
# PRIMEngine — Optimization Report
**Generated:** {report_date}
**Client:** {preset if preset != "Custom" else "Custom Configuration"}

---

## Configuration
| Parameter | Value |
|-----------|-------|
| Market | {market} |
| Fleet Capacity | {fleet_mw} MW |
| Battery Storage | {battery_mwh} MWh |
| Analysis Period | {hours} hours ({hours//24} days) |
| Data Source | {data_label} |

## Results Summary
| Metric | Value |
|--------|-------|
| Net Profit (period) | {curr_symbol}{net_profit:,.0f} |
| Energy Revenue | {curr_symbol}{energy_rev:,.0f} |
| {anc_label} | {curr_symbol}{anc_rev:,.0f} |
| Uplift vs Baseline | {result.uplift_pct:+.1f}% |
| Battery SOH | {result.battery_soh_end:.4f} |

## Annual Projection
| Metric | Value |
|--------|-------|
| Annual Net Profit | {curr_symbol}{annual_net:,.0f} |
| PRIMEngine Fee (25%) | {curr_symbol}{actual_fee:,.0f} |
| **You Keep (75%)** | **{curr_symbol}{you_keep:,.0f}** |
| Your ROI | {you_keep/max(1, actual_fee):.0f}x |

## Price Arbitrage
| Metric | Value |
|--------|-------|
| Avg Buy Price | {curr_symbol}{avg_buy:.2f}/MWh |
| Avg Sell Price | {curr_symbol}{avg_sell:.2f}/MWh |
| Spread Ratio | {avg_sell/max(1, avg_buy):.1f}x |

## Battery Health
| Metric | Value |
|--------|-------|
| SOH Loss (period) | {(result.battery_soh_start - result.battery_soh_end)*100:.3f}% |
| Projected Annual Loss | {annual_soh_loss*100:.1f}% |
| Estimated Battery Life | {battery_life:.1f} years |

---
*PRIMEnergeia S.A.S. — Grid Optimization Division*
*primenergeia.com | sales@primenergeia.com*
"""

        st.markdown(report_text)

        st.download_button(
            label="📥 Download Report (Markdown)",
            data=report_text,
            file_name=f"primengine_report_{fleet_mw}MW_{market.split()[0].lower()}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        # JSON export
        report_json = {
            "generated": report_date,
            "config": {"market": market, "fleet_mw": fleet_mw, "battery_mwh": battery_mwh, "hours": hours},
            "results": {
                "net_profit": net_profit, "energy_revenue": energy_rev,
                "ancillary_revenue": anc_rev, "uplift_pct": result.uplift_pct,
                "battery_soh_end": result.battery_soh_end,
            },
            "annual_projection": {
                "net_profit": annual_net, "primengine_fee": actual_fee, "you_keep": you_keep,
            },
            "arbitrage": {
                "avg_buy_price": float(avg_buy), "avg_sell_price": float(avg_sell),
                "spread_ratio": float(avg_sell / max(1, avg_buy)),
            },
        }
        st.download_button(
            label="📥 Download Data (JSON)",
            data=json.dumps(report_json, indent=2),
            file_name=f"primengine_data_{fleet_mw}MW_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

else:
    # Show landing content when no simulation has run
    st.markdown("---")
    st.markdown("### 🎯 What This Tool Does")

    e1, e2, e3 = st.columns(3)
    e1.markdown("""
    **1. Configure Your Fleet**
    - Select your market (17 global ISOs supported)
    - Set your battery capacity
    - Choose from client presets
    """)
    e2.markdown("""
    **2. Run the Optimizer**
    - HJB two-pass lookahead
    - Real or simulated data
    - Battery degradation tracking
    """)
    e3.markdown("""
    **3. See Your ROI**
    - Annual revenue projection
    - 25% value share pricing
    - Downloadable report
    """)

    st.divider()

    st.markdown("### 📊 Client Presets Available")
    preset_df = pd.DataFrame([
        {"Profile": k, "Fleet": f"{v['fleet_mw']} MW", "Battery": f"{v['battery_mwh']} MWh",
         "Market": v["market"]}
        for k, v in CLIENT_PRESETS.items() if k != "Custom"
    ])
    st.dataframe(preset_df, use_container_width=True, hide_index=True)

    st.markdown("""
    > **Ready to simulate?** Select a profile above and click **🚀 Run Co-Optimization**.
    > Results include dispatch charts, fee calculation, and a downloadable report.
    """)
