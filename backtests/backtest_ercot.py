"""
ERCOT Historical Backtest — Proof of Value
=============================================
Runs the PRIMEngine co-optimizer against real ERCOT price data
and produces a detailed report comparing HJB-optimized dispatch
against a naive flat-dispatch baseline.

This is the moment of truth: does the optimizer actually save money?

Usage:
    python backtests/backtest_ercot.py

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import sys
import os
import numpy as np

# Resolve project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "markets"))

from data.data_loader import load_ercot_csv
from markets.ercot.dispatch_ercot import run_ercot_backtest


def run_backtest(fleet_mw: float = 100.0, battery_mwh: float = 400.0):
    """Run full 7-day backtest against ERCOT historical data."""

    # ── Load real price data ──
    dataset = load_ercot_csv()
    print(f"\n{'='*70}")
    print(f"  ERCOT HISTORICAL BACKTEST — PROOF OF VALUE")
    print(f"{'='*70}")
    print(f"  Data Source:    {os.path.basename(dataset.source_file)}")
    print(f"  Period:         {dataset.dates[0]} to {dataset.dates[-1]}")
    print(f"  Hours:          {dataset.hours}")
    print(f"  Fleet:          {fleet_mw} MW | Battery: {battery_mwh} MWh")
    print(f"{'='*70}")

    # ── Data Statistics ──
    stats = dataset.stats
    print(f"\n  📊 PRICE DATA STATISTICS")
    print(f"  {'─'*40}")
    print(f"  DAM Average:     ${stats['da_mean']:>8.2f} /MWh")
    print(f"  DAM Range:       ${stats['da_min']:>8.2f} — ${stats['da_max']:>8.2f}")
    print(f"  DAM Std Dev:     ${stats['da_std']:>8.2f}")
    print(f"  RTM Average:     ${stats['rt_mean']:>8.2f} /MWh")
    print(f"  RTM Range:       ${stats['rt_min']:>8.2f} — ${stats['rt_max']:>8.2f}")
    print(f"  Spread (RT-DA):  ${stats['spread_mean']:>8.2f} avg")
    print(f"  Spike Hours:     {stats['spike_hours']} (RT > $200/MWh)")

    # ── Run Co-Optimizer ──
    result = run_ercot_backtest(
        da_prices=dataset.da_prices,
        rt_prices=dataset.rt_prices,
        fleet_mw=fleet_mw,
        battery_mwh=battery_mwh,
    )

    # ── Compute Naive Baseline (same battery, dumb schedule) ──
    # Naive strategy: charge at night (0-6h), discharge at afternoon (14-20h)
    # No price awareness — just a fixed time-of-use schedule
    from markets.ercot.dispatch_ercot import BatteryState
    naive_battery = BatteryState(capacity_mwh=battery_mwh)
    naive_revenue = 0.0
    naive_charge_cost = 0.0
    naive_strategies = []

    for h in range(dataset.hours):
        hour_of_day = h % 24
        price = dataset.rt_prices[h]

        if hour_of_day in range(0, 7) and naive_battery.soc < 0.9:
            # Naive: always charge at night
            _, energy = naive_battery.charge(naive_battery.max_charge_mw, 1.0)
            naive_charge_cost += naive_battery.max_charge_mw * price
            naive_strategies.append("CHARGE")
        elif hour_of_day in range(14, 21) and naive_battery.soc > 0.15:
            # Naive: always discharge in afternoon
            _, energy = naive_battery.discharge(naive_battery.max_discharge_mw, 1.0)
            naive_revenue += naive_battery.max_discharge_mw * price
            naive_strategies.append("DISCHARGE")
        else:
            naive_strategies.append("IDLE")

    naive_net = naive_revenue - naive_charge_cost

    # HJB strategy detailed breakdown
    charge_hours = sum(1 for s in result.strategy if s == "CHARGE")
    discharge_hours = sum(1 for s in result.strategy if s == "DISCHARGE")
    hold_hours = sum(1 for s in result.strategy if s == "HOLD+AS")

    # ── Results ──
    print(f"\n  ⚡ CO-OPTIMIZATION RESULTS")
    print(f"  {'─'*40}")
    print(f"  Strategy Breakdown:")
    print(f"    CHARGE:      {charge_hours:>4} hours ({100*charge_hours/dataset.hours:.0f}%)")
    print(f"    DISCHARGE:   {discharge_hours:>4} hours ({100*discharge_hours/dataset.hours:.0f}%)")
    print(f"    HOLD+AS:     {hold_hours:>4} hours ({100*hold_hours/dataset.hours:.0f}%)")
    print(f"")
    print(f"  Revenue:")
    print(f"    Energy Revenue:      ${result.energy_revenue_usd:>14,.2f}")
    print(f"    Ancillary Revenue:   ${result.ancillary_revenue_usd:>14,.2f}")
    print(f"    Total Revenue:       ${result.total_revenue_usd:>14,.2f}")
    print(f"    Degradation Cost:    ${result.degradation_cost_usd:>14,.2f}")
    print(f"    Net Profit (HJB):    ${result.net_profit_usd:>14,.2f}")
    print(f"")
    print(f"  Baseline (Naive Time-of-Use Schedule):")
    naive_ch = sum(1 for s in naive_strategies if s == "CHARGE")
    naive_dch = sum(1 for s in naive_strategies if s == "DISCHARGE")
    print(f"    Strategy:  Charge 0-6h, Discharge 14-20h")
    print(f"    Cycles:    {naive_ch} charge / {naive_dch} discharge hours")
    print(f"    Revenue:             ${naive_revenue:>14,.2f}")
    print(f"    Charge Cost:         ${naive_charge_cost:>14,.2f}")
    print(f"    Net Profit (Naive):  ${naive_net:>14,.2f}")

    # ── The Key Metric ──
    savings_vs_naive = result.net_profit_usd - naive_net
    savings_pct = (savings_vs_naive / max(1, abs(naive_net))) * 100

    print(f"\n  {'='*40}")
    print(f"  🎯 KEY RESULT")
    print(f"  {'='*40}")

    if savings_vs_naive > 0:
        print(f"  HJB Optimization OUTPERFORMS naive by:")
        print(f"    ${savings_vs_naive:>14,.2f}  ({savings_pct:+.1f}%)")
    else:
        print(f"  HJB Optimization UNDERPERFORMS naive by:")
        print(f"    ${abs(savings_vs_naive):>14,.2f}  ({savings_pct:.1f}%)")

    # ── Annual Projection ──
    annual_factor = 8760 / dataset.hours
    annual_hjb = result.net_profit_usd * annual_factor
    annual_naive = naive_net * annual_factor
    annual_savings = savings_vs_naive * annual_factor
    license_cost = 200000  # $200K/yr API tier

    print(f"\n  📈 ANNUAL PROJECTION (extrapolated)")
    print(f"  {'─'*40}")
    print(f"    HJB Net Profit:      ${annual_hjb:>14,.0f} /yr")
    print(f"    Naive Net Profit:    ${annual_naive:>14,.0f} /yr")
    print(f"    Optimization Uplift: ${annual_savings:>14,.0f} /yr")
    print(f"    PRIMEngine License:  ${license_cost:>14,.0f} /yr")
    if annual_savings > 0:
        print(f"    ROI Multiple:        {annual_savings/license_cost:>13.1f}x")
    else:
        print(f"    ROI Multiple:        N/A (underperforms)")

    # ── Battery Health ──
    annual_soh_loss = (result.battery_soh_start - result.battery_soh_end) * annual_factor
    print(f"\n  🔋 BATTERY HEALTH")
    print(f"  {'─'*40}")
    print(f"    SOH Start:  {result.battery_soh_start:.4f}")
    print(f"    SOH End:    {result.battery_soh_end:.4f}")
    print(f"    Weekly Loss: {(result.battery_soh_start - result.battery_soh_end)*100:.3f}%")
    print(f"    Projected Annual Loss: {annual_soh_loss*100:.2f}%")
    print(f"    Estimated Battery Life: {1.0/max(0.001, annual_soh_loss*3.33):.1f} years")

    # ── Price Arbitrage Analysis ──
    charge_prices = []
    discharge_prices = []
    for h in range(dataset.hours):
        if result.strategy[h] == "CHARGE":
            charge_prices.append(dataset.rt_prices[h])
        elif result.strategy[h] == "DISCHARGE":
            discharge_prices.append(dataset.rt_prices[h])

    if charge_prices and discharge_prices:
        avg_buy = np.mean(charge_prices)
        avg_sell = np.mean(discharge_prices)
        spread = avg_sell - avg_buy
        print(f"\n  💰 PRICE ARBITRAGE")
        print(f"  {'─'*40}")
        print(f"    Avg Buy Price:   ${avg_buy:>8.2f} /MWh")
        print(f"    Avg Sell Price:  ${avg_sell:>8.2f} /MWh")
        print(f"    Avg Spread:      ${spread:>8.2f} /MWh")
        print(f"    Spread Ratio:    {avg_sell/max(1,avg_buy):.1f}x")

    print(f"\n{'='*70}")
    print(f"  Backtest complete. Data: {dataset.source_file}")
    print(f"{'='*70}\n")

    return result, dataset


if __name__ == "__main__":
    run_backtest()
