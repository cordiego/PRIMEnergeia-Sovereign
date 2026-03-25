#!/usr/bin/env python3
"""
PRIMEnergeia — Backtest Report Generator
==========================================
Takes real (or proxy) ERCOT prices + co-optimizer backtest results
and generates a client-facing savings report with defensible methodology.

Usage:
    python generate_backtest_report.py                        # Default data
    python generate_backtest_report.py --file data/ercot/ercot_real_houston.csv
    python generate_backtest_report.py --fleet 200 --battery 800

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import argparse
import tempfile
import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from data.data_loader import load_dataset
from markets.ercot.dispatch_ercot import run_ercot_backtest, CoOptResult


def generate_backtest_report(filepath: str = None, fleet_mw: float = 100.0,
                              battery_mwh: float = 400.0,
                              output_path: str = None) -> str:
    """
    Full pipeline: load data → backtest → generate client report PDF.

    Returns path to generated PDF.
    """
    # ─── Load Data ──────────────────────────────────────
    if filepath is None:
        # Find any ERCOT data in the data directory
        ercot_dir = os.path.join(PROJECT_ROOT, "data", "ercot")
        candidates = [f for f in os.listdir(ercot_dir)
                      if f.endswith('.csv') and ('real' in f.lower() or 'proxy' in f.lower())]
        if candidates:
            filepath = os.path.join(ercot_dir, sorted(candidates)[-1])
        else:
            filepath = os.path.join(ercot_dir, "ercot_historical.csv")

    ds = load_dataset(filepath=filepath, market="ercot")
    is_proxy = "PROXY" in os.path.basename(filepath).upper()

    # ─── Run Backtest ───────────────────────────────────
    result = run_ercot_backtest(
        da_prices=ds.da_prices,
        rt_prices=ds.rt_prices,
        fleet_mw=fleet_mw,
        battery_mwh=battery_mwh,
    )

    # ─── Generate Charts ────────────────────────────────
    plt.style.use('dark_background')

    # Chart 1: Price + Dispatch Timeline
    fig1, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12),
                                          gridspec_kw={'height_ratios': [2, 1.5, 1]})

    # Show last 7 days for detail
    show_hours = min(168, len(result.da_prices))
    x = np.arange(show_hours)
    da_show = result.da_prices[-show_hours:]
    rt_show = result.rt_prices[-show_hours:]
    dispatch_show = result.dispatch_mw[-show_hours:]
    soc_show = result.battery_soc[-(show_hours + 1):]

    ax1.fill_between(x, da_show, rt_show, alpha=0.15, color='#ff6b35', label='DA/RT Spread')
    ax1.plot(x, da_show, color='#00d1ff', lw=1.5, label='Day-Ahead LMP', alpha=0.9)
    ax1.plot(x, rt_show, color='#ff6b35', lw=1, label='Real-Time LMP', alpha=0.7)
    ax1.set_title(f"ERCOT Price & Dispatch - Last {show_hours // 24} Days", fontsize=14, pad=10)
    ax1.set_ylabel("Price ($/MWh)")
    ax1.legend(loc='upper right', frameon=False)
    ax1.grid(alpha=0.1)

    # Dispatch bars
    colors = ['#ff3333' if d < 0 else '#00ffcc' for d in dispatch_show]
    ax2.bar(x, dispatch_show, color=colors, alpha=0.8, width=1.0)
    ax2.axhline(y=0, color='white', lw=0.5, alpha=0.3)
    ax2.set_ylabel("Dispatch (MW)")
    ax2.set_title("Battery Dispatch: Charge (red) / Discharge (green)", fontsize=11)
    ax2.grid(alpha=0.1)

    # SOC trajectory
    ax3.fill_between(range(len(soc_show)), soc_show * 100, alpha=0.3, color='#fbc02d')
    ax3.plot(range(len(soc_show)), soc_show * 100, color='#fbc02d', lw=2)
    ax3.set_ylabel("SOC (%)")
    ax3.set_xlabel("Hour")
    ax3.set_ylim(0, 105)
    ax3.grid(alpha=0.1)

    plt.tight_layout()
    chart1_buf = io.BytesIO()
    fig1.savefig(chart1_buf, format='png', dpi=180, bbox_inches='tight')
    plt.close(fig1)
    chart1_buf.seek(0)

    # Chart 2: Revenue Breakdown
    fig2, (ax4, ax5) = plt.subplots(1, 2, figsize=(14, 5))

    # Revenue waterfall
    categories = ['Energy\nRevenue', 'Ancillary\nServices', 'Total\nRevenue',
                   'Degradation\nCost', 'Net\nProfit']
    values = [result.energy_revenue_usd, result.ancillary_revenue_usd,
              result.total_revenue_usd, -result.degradation_cost_usd,
              result.net_profit_usd]
    bar_colors = ['#00d1ff', '#00ffcc', '#fbc02d', '#ff3333', '#00ff88']
    ax4.bar(categories, values, color=bar_colors, alpha=0.85)
    ax4.set_title("Revenue Breakdown ($)", fontsize=13)
    for i, v in enumerate(values):
        ax4.text(i, v + max(values) * 0.02, f"${v:,.0f}", ha='center', fontsize=9,
                 color='white')
    ax4.grid(alpha=0.1, axis='y')

    # Strategy pie
    strat_counts = Counter(result.strategy)
    labels = list(strat_counts.keys())
    sizes = list(strat_counts.values())
    pie_colors = ['#00d1ff', '#00ffcc', '#ff6b35', '#fbc02d'][:len(labels)]
    ax5.pie(sizes, labels=labels, colors=pie_colors, autopct='%1.1f%%',
            startangle=90, textprops={'color': 'white', 'fontsize': 10})
    ax5.set_title("Strategy Distribution", fontsize=13)

    plt.tight_layout()
    chart2_buf = io.BytesIO()
    fig2.savefig(chart2_buf, format='png', dpi=180, bbox_inches='tight',
                 facecolor='#0a0f1a')
    plt.close(fig2)
    chart2_buf.seek(0)

    # ─── Generate PDF ───────────────────────────────────
    output_path = output_path or os.path.join(
        PROJECT_ROOT, "reports",
        f"PRIMEnergeia_Backtest_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write charts to temp files
    chart1_tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    chart1_tmp.write(chart1_buf.read())
    chart1_tmp.close()

    chart2_tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    chart2_tmp.write(chart2_buf.read())
    chart2_tmp.close()

    try:
        pdf = FPDF()
        pdf.add_page()

        # Header
        pdf.set_font("Arial", 'B', 28)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 15, "PRIMEnergeia", 0, 1, 'L')

        pdf.set_font("Arial", '', 14)
        pdf.set_text_color(0, 255, 204)
        pdf.cell(0, 8, "ERCOT Co-Optimization Backtest Report", 0, 1, 'L')

        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(150, 150, 150)
        data_label = "[PROXY DATA]" if is_proxy else "[REAL MARKET DATA]"
        pdf.cell(0, 5, (
            f"{data_label} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"Fleet: {fleet_mw} MW | Battery: {battery_mwh} MWh"
        ), 0, 1, 'L')
        pdf.ln(8)

        # Executive Summary
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "Executive Summary", 0, 1, 'L')

        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(0, 0, 0)

        days = result.hours // 24
        pdf.multi_cell(0, 7, (
            f"Over a {days}-day backtest period ({result.hours} hours), the PRIMEnergeia "
            f"HJB co-optimizer generated ${result.net_profit_usd:,.2f} net profit from a "
            f"{fleet_mw} MW / {battery_mwh} MWh battery storage system in the ERCOT market. "
            f"\n\n"
            f"This represents a {result.uplift_pct:.1f}% improvement over the flat-dispatch "
            f"baseline of ${result.baseline_revenue_usd:,.2f}. Battery health degraded from "
            f"{result.battery_soh_start:.4f} to {result.battery_soh_end:.4f} ({(result.battery_soh_start - result.battery_soh_end) * 100:.2f}% capacity loss)."
        ))
        pdf.ln(5)

        # Methodology
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "Methodology", 0, 1, 'L')

        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 6, (
            "The co-optimizer uses a two-pass lookahead strategy:\n\n"
            "Pass 1: For each 24-hour window, rank hours by Day-Ahead LMP. Assign the bottom "
            "N hours as CHARGE and the top N hours as DISCHARGE (N = battery capacity / max "
            "discharge rate). Any hour with RT price > $100/MWh is also flagged for discharge.\n\n"
            "Pass 2: Execute the schedule respecting physical constraints (SOC limits 5%-95%, "
            "max charge/discharge rate, roundtrip efficiency 88%). During HOLD periods, "
            "the battery provides Responsive Reserve Service (RRS) at 30% capacity.\n\n"
            "Degradation is tracked using a linear cycle-aging model: 0.015% capacity loss "
            "per full equivalent cycle, with a 70% SOH floor."
        ))
        pdf.ln(5)

        # Results Table
        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 10, "Metric", 1, 0, 'C', True)
        pdf.cell(90, 10, "Value", 1, 1, 'C', True)

        rows = [
            ("Energy Revenue", f"${result.energy_revenue_usd:,.2f}"),
            ("Ancillary Services Revenue", f"${result.ancillary_revenue_usd:,.2f}"),
            ("Total Gross Revenue", f"${result.total_revenue_usd:,.2f}"),
            ("Battery Degradation Cost", f"-${result.degradation_cost_usd:,.2f}"),
            ("NET PROFIT", f"${result.net_profit_usd:,.2f}"),
            ("Flat Baseline Revenue", f"${result.baseline_revenue_usd:,.2f}"),
            ("Optimizer Uplift", f"{result.uplift_pct:.1f}%"),
            ("Battery SOH (start -> end)", f"{result.battery_soh_start:.4f} -> {result.battery_soh_end:.4f}"),
            ("Analysis Period", f"{result.hours} hours ({days} days)"),
        ]

        pdf.set_font("Arial", '', 11)
        for i, (label, value) in enumerate(rows):
            if label == "NET PROFIT":
                pdf.set_text_color(0, 255, 136)
                pdf.set_font("Arial", 'B', 11)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 11)
            pdf.cell(100, 9, label, 1, 0, 'L')
            pdf.cell(90, 9, value, 1, 1, 'R')

        pdf.ln(5)

        # Charts
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 10, "Price & Dispatch Analysis", 0, 1, 'L')
        pdf.image(chart1_tmp.name, x=5, w=200)

        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Revenue Breakdown & Strategy", 0, 1, 'L')
        pdf.image(chart2_tmp.name, x=5, w=200)

        # Disclaimer
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(120, 120, 120)
        if is_proxy:
            pdf.multi_cell(0, 4, (
                "DISCLAIMER: This report uses PROXY price data generated from documented "
                "ERCOT market patterns. It is NOT based on actual ERCOT settlement prices. "
                "Results are illustrative of the optimizer's capabilities. For a definitive "
                "savings analysis, repeat this backtest with real ERCOT MIS data."
            ))
        else:
            pdf.multi_cell(0, 4, (
                "This report uses real ERCOT settlement point prices. Past performance "
                "does not guarantee future results. Battery degradation model uses "
                "simplified linear aging. Actual results may vary based on operational "
                "constraints, market conditions, and asset-specific parameters."
            ))

        # Footer
        pdf.ln(3)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 4, "PRIMEnergeia S.A.S. - Grid Optimization Division - HJB Co-Optimizer v2.0", 0, 1, 'C')

        pdf.output(output_path)
        print(f"\n✅ Report generated: {output_path}")
        print(f"   Size: {os.path.getsize(output_path) / 1024:.1f} KB")

    finally:
        os.unlink(chart1_tmp.name)
        os.unlink(chart2_tmp.name)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate ERCOT backtest report")
    parser.add_argument("--file", help="Path to ERCOT price CSV")
    parser.add_argument("--fleet", type=float, default=100.0, help="Fleet MW (default: 100)")
    parser.add_argument("--battery", type=float, default=400.0, help="Battery MWh (default: 400)")
    parser.add_argument("--output", help="Output PDF path")
    args = parser.parse_args()

    generate_backtest_report(
        filepath=args.file,
        fleet_mw=args.fleet,
        battery_mwh=args.battery,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
