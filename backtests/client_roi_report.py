"""
PRIMEnergeia — Client ROI Report Generator
=============================================
Generates a CLIENT-FACING sales report showing the grid operator's
savings when using PRIMEngine vs their current naive dispatch.

This is a SALES TOOL: it shows the CLIENT's ROI, not ours.

OUR revenue = the license fee they pay us.
THEIR value = the dispatch savings we generate for them.

Usage:
    python backtests/client_roi_report.py

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import sys
import os
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "markets"))

from data.data_loader import load_ercot_csv
from markets.ercot.dispatch_ercot import run_ercot_backtest, BatteryState


# ═══════════════════════════════════════════════════════════════
#  PRICING: 25% VALUE SHARE MODEL
# ═══════════════════════════════════════════════════════════════
VALUE_SHARE_RATE = 0.25  # 25% of incremental revenue generated

LICENSE_TIERS = {
    "Pilot":      {"min_annual": 0,         "max_mw": 50,   "duration": "90 days"},
    "Growth":     {"min_annual": 50_000,    "max_mw": 200,  "duration": "Annual"},
    "Scale":      {"min_annual": 500_000,   "max_mw": 1000, "duration": "Annual"},
    "Enterprise": {"min_annual": 2_000_000, "max_mw": 99999, "duration": "Annual"},
}


def run_client_report(fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                      client_name: str = "ACME Energy"):
    """Generate a client-facing ROI report."""

    dataset = load_ercot_csv()

    # ── Run HJB-optimized dispatch ──
    hjb_result = run_ercot_backtest(
        da_prices=dataset.da_prices,
        rt_prices=dataset.rt_prices,
        fleet_mw=fleet_mw, battery_mwh=battery_mwh,
    )

    # ── Run naive TOU dispatch (client's current approach) ──
    naive_battery = BatteryState(capacity_mwh=battery_mwh)
    naive_revenue = 0.0
    naive_charge_cost = 0.0

    for h in range(dataset.hours):
        hour_of_day = h % 24
        price = dataset.rt_prices[h]

        if hour_of_day in range(0, 7) and naive_battery.soc < 0.9:
            _, energy = naive_battery.charge(naive_battery.max_charge_mw, 1.0)
            naive_charge_cost += naive_battery.max_charge_mw * price
        elif hour_of_day in range(14, 21) and naive_battery.soc > 0.15:
            _, energy = naive_battery.discharge(naive_battery.max_discharge_mw, 1.0)
            naive_revenue += naive_battery.max_discharge_mw * price

    naive_net = naive_revenue - naive_charge_cost

    # ── Client's savings (what they care about) ──
    client_savings_weekly = hjb_result.net_profit_usd - naive_net
    annual_factor = 52  # weeks per year
    client_savings_annual = client_savings_weekly * annual_factor

    # ── PRIMEnergeia's fee: 25% of client savings ──
    # Determine tier by fleet size
    tier_name = "Pilot"
    for name, info in LICENSE_TIERS.items():
        if fleet_mw <= info["max_mw"]:
            tier_name = name
            break
    else:
        tier_name = "Enterprise"

    tier = LICENSE_TIERS[tier_name]
    value_share_fee = client_savings_annual * VALUE_SHARE_RATE
    our_annual_fee = max(value_share_fee, tier["min_annual"])

    # Client's ROI on our fee
    client_net_after_fee = client_savings_annual - our_annual_fee
    client_roi = client_net_after_fee / max(1, our_annual_fee)

    # ── Arbitrage quality ──
    charge_prices = [dataset.rt_prices[h] for h in range(dataset.hours)
                     if hjb_result.strategy[h] == "CHARGE"]
    discharge_prices = [dataset.rt_prices[h] for h in range(dataset.hours)
                        if hjb_result.strategy[h] == "DISCHARGE"]

    avg_buy = np.mean(charge_prices) if charge_prices else 0
    avg_sell = np.mean(discharge_prices) if discharge_prices else 0

    # ═══════════════════════════════════════════════════════════
    #  CLIENT-FACING REPORT
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'═'*70}")
    print(f"  PRIMEngine — Client ROI Report")
    print(f"  Prepared for: {client_name}")
    print(f"{'═'*70}")
    print(f"  Fleet: {fleet_mw} MW | Battery: {battery_mwh} MWh | Market: ERCOT")
    print(f"  Analysis Period: {dataset.dates[0]} to {dataset.dates[-1]} ({dataset.hours}h)")
    print(f"{'═'*70}")

    print(f"\n  📊 YOUR CURRENT PERFORMANCE (Naive TOU Schedule)")
    print(f"  {'─'*50}")
    print(f"    Strategy:        Charge 0-6h, Discharge 14-20h")
    print(f"    Weekly Net:      ${naive_net:>14,.2f}")
    print(f"    Annual (proj):   ${naive_net * annual_factor:>14,.0f}")

    print(f"\n  ⚡ WITH PRIMEngine (HJB-Optimal Dispatch)")
    print(f"  {'─'*50}")
    print(f"    Strategy:        Two-pass lookahead, spike-aware")
    print(f"    Weekly Net:      ${hjb_result.net_profit_usd:>14,.2f}")
    print(f"    Annual (proj):   ${hjb_result.net_profit_usd * annual_factor:>14,.0f}")

    print(f"\n  {'═'*50}")
    print(f"  💰 YOUR ADDITIONAL SAVINGS WITH PRIMEngine")
    print(f"  {'═'*50}")
    print(f"    Weekly Uplift:   ${client_savings_weekly:>14,.2f}")
    print(f"    Annual Uplift:   ${client_savings_annual:>14,.0f}")
    print(f"    Improvement:     {(client_savings_weekly / max(1, naive_net)) * 100:>13.1f}%")

    print(f"\n  💳 PRIMEngine FEE ({tier_name} Tier — 25% Value Share)")
    print(f"  {'─'*50}")
    print(f"    Value Share (25%): ${value_share_fee:>14,.0f}")
    print(f"    Minimum Commit:    ${tier['min_annual']:>14,.0f}")
    print(f"    Your Annual Fee:   ${our_annual_fee:>14,.0f}")
    print(f"    YOU KEEP (75%):    ${client_net_after_fee:>14,.0f}")
    if client_roi > 0:
        print(f"    YOUR NET ROI:      {client_roi:>13.0f}x")
    else:
        print(f"    YOUR NET ROI:      N/A")

    print(f"\n  🔬 HOW WE DO IT")
    print(f"  {'─'*50}")
    print(f"    Avg Buy Price:   ${avg_buy:>8.2f}/MWh")
    print(f"    Avg Sell Price:  ${avg_sell:>8.2f}/MWh")
    print(f"    Spread Ratio:    {avg_sell / max(1, avg_buy):>7.1f}x")
    print(f"    Battery Impact:  {(hjb_result.battery_soh_start - hjb_result.battery_soh_end)*100:.3f}% SOH/week")

    print(f"\n{'═'*70}")
    print(f"  Contact: sales@primenergeia.com | primenergeia.com")
    print(f"{'═'*70}\n")

    return {
        "client_savings_annual": client_savings_annual,
        "our_annual_fee": our_annual_fee,
        "client_roi": client_roi,
    }


def run_saas_revenue_model():
    """Show PRIMEnergeia's revenue projection with 25% value share."""

    print(f"\n{'═'*70}")
    print(f"  PRIMEnergeia — SaaS Revenue Model (25% Value Share)")
    print(f"{'═'*70}")
    print(f"\n  PRICING MODEL: 25% of incremental revenue generated")
    print(f"  {'─'*50}")
    for tier, info in LICENSE_TIERS.items():
        print(f"    {tier:<12}  Min ${info['min_annual']:>10,.0f}/yr  (≤{info['max_mw']} MW, {info['duration']})")

    # Avg revenue per client by tier (based on typical portfolio sizes)
    avg_uplift = {
        "Growth":     2_000_000,   # 50 MW client: ~$2M uplift → $500K fee
        "Scale":      15_000_000,  # 300 MW client: ~$15M uplift → $3.75M fee
        "Enterprise": 60_000_000,  # 1 GW+ client: ~$60M uplift → $15M fee
    }

    print(f"\n  REVENUE PROJECTIONS (by client count)")
    print(f"  {'─'*50}")
    print(f"  {'Year':<8} {'Growth':<10} {'Scale':<10} {'Enterprise':<12} {'Total ARR':<16} {'Our Rev':<14}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*12} {'─'*16} {'─'*14}")

    scenarios = [
        {"name": "Yr 1",  "Growth": 5,  "Scale": 2,  "Enterprise": 0},
        {"name": "Yr 2",  "Growth": 12, "Scale": 5,  "Enterprise": 1},
        {"name": "Yr 3",  "Growth": 20, "Scale": 10, "Enterprise": 3},
        {"name": "Yr 5",  "Growth": 40, "Scale": 25, "Enterprise": 8},
    ]

    for s in scenarios:
        total_rev = 0
        for tier in ["Growth", "Scale", "Enterprise"]:
            count = s.get(tier, 0)
            fee = avg_uplift[tier] * VALUE_SHARE_RATE  # 25%
            total_rev += count * fee

        print(f"  {s['name']:<8} {s.get('Growth',0):<10} {s.get('Scale',0):<10} {s.get('Enterprise',0):<12} {'':>4}${total_rev:>12,.0f}")

    print(f"\n  UNIT ECONOMICS")
    print(f"  {'─'*50}")
    print(f"    Revenue model:            25% of client's uplift")
    print(f"    Avg Growth client fee:     ${avg_uplift['Growth'] * 0.25:>10,.0f}/yr")
    print(f"    Avg Scale client fee:      ${avg_uplift['Scale'] * 0.25:>10,.0f}/yr")
    print(f"    Avg Enterprise client fee: ${avg_uplift['Enterprise'] * 0.25:>10,.0f}/yr")
    print(f"    AWS cost/client:           ~$5,000/yr")
    print(f"    Gross margin:              ~99%")
    print(f"    CAC (est):                 ~$25,000")
    print(f"    LTV (Scale, 3yr):          ~$11,250,000")
    print(f"    LTV/CAC:                   450x")

    print(f"\n{'═'*70}\n")


if __name__ == "__main__":
    metrics = run_client_report(
        fleet_mw=100, battery_mwh=400,
        client_name="Demo Grid Operator",
    )
    run_saas_revenue_model()
