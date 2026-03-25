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
#  LICENSE PRICING (what PRIMEnergeia charges)
# ═══════════════════════════════════════════════════════════════
LICENSE_TIERS = {
    "Pilot":      {"annual_fee": 0,       "duration": "90 days", "markets": 1},
    "Dashboard":  {"annual_fee": 15_000,  "duration": "Annual",  "markets": 3},
    "API":        {"annual_fee": 200_000, "duration": "Annual",  "markets": 3},
    "Enterprise": {"annual_fee": 500_000, "duration": "Annual",  "markets": 3},
}


def run_client_report(fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                      client_name: str = "ACME Energy", license_tier: str = "API"):
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

    # ── PRIMEnergeia's revenue (what WE care about) ──
    license = LICENSE_TIERS[license_tier]
    our_annual_fee = license["annual_fee"]

    # Client's ROI on our license
    client_roi = client_savings_annual / max(1, our_annual_fee)

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

    print(f"\n  💳 PRIMEngine LICENSE ({license_tier} Tier)")
    print(f"  {'─'*50}")
    print(f"    Annual Fee:      ${our_annual_fee:>14,.0f}")
    if client_roi > 0:
        print(f"    YOUR ROI:        {client_roi:>13.0f}x")
        print(f"    Payback Period:  {12 / max(0.01, client_roi):>11.1f} months")
    else:
        print(f"    YOUR ROI:        N/A (optimizer underperforms)")

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
    """Show PRIMEnergeia's revenue projection by client count."""

    print(f"\n{'═'*70}")
    print(f"  PRIMEnergeia — SaaS Revenue Model")
    print(f"{'═'*70}")
    print(f"\n  LICENSE PRICING")
    print(f"  {'─'*50}")
    for tier, info in LICENSE_TIERS.items():
        fee = info['annual_fee']
        print(f"    {tier:<12}  ${fee:>10,.0f}/yr  ({info['duration']}, {info['markets']} markets)")

    print(f"\n  REVENUE PROJECTIONS (by client count)")
    print(f"  {'─'*50}")
    print(f"  {'Clients':<10} {'Pilot':<10} {'Dashboard':<12} {'API':<12} {'Enterprise':<12} {'Total ARR':<14}")
    print(f"  {'─'*10} {'─'*10} {'─'*12} {'─'*12} {'─'*12} {'─'*14}")

    scenarios = [
        {"name": "Yr 1",  "pilot": 10, "dashboard": 5,  "api": 2,  "enterprise": 0},
        {"name": "Yr 2",  "pilot": 20, "dashboard": 15, "api": 8,  "enterprise": 2},
        {"name": "Yr 3",  "pilot": 30, "dashboard": 30, "api": 20, "enterprise": 5},
        {"name": "Yr 5",  "pilot": 50, "dashboard": 50, "api": 50, "enterprise": 15},
    ]

    for s in scenarios:
        pilot_rev = s["pilot"] * LICENSE_TIERS["Pilot"]["annual_fee"]
        dash_rev = s["dashboard"] * LICENSE_TIERS["Dashboard"]["annual_fee"]
        api_rev = s["api"] * LICENSE_TIERS["API"]["annual_fee"]
        ent_rev = s["enterprise"] * LICENSE_TIERS["Enterprise"]["annual_fee"]
        total = pilot_rev + dash_rev + api_rev + ent_rev

        print(f"  {s['name']:<10} {s['pilot']:<10} {s['dashboard']:<12} {s['api']:<12} {s['enterprise']:<12} ${total:>12,.0f}")

    print(f"\n  UNIT ECONOMICS")
    print(f"  {'─'*50}")
    print(f"    AWS hosting cost/client:   ~$2,000/yr")
    print(f"    Support cost/client:       ~$5,000/yr")
    print(f"    Gross margin (API tier):   ~96%")
    print(f"    Gross margin (Enterprise): ~99%")
    print(f"    CAC (est):                 ~$15,000")
    print(f"    LTV (API, 3yr):            ~$600,000")
    print(f"    LTV/CAC:                   40x")

    print(f"\n{'═'*70}\n")


if __name__ == "__main__":
    # Client report
    metrics = run_client_report(
        fleet_mw=100, battery_mwh=400,
        client_name="Demo Grid Operator", license_tier="API",
    )

    # Our revenue model
    run_saas_revenue_model()
