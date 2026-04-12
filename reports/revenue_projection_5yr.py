#!/usr/bin/env python3
"""
PRIMEnergeia — 5-Year Revenue Projection Report (PDF)
=======================================================
Generates an executive-grade PDF with 5-year revenue projections
across all 17 global electricity markets and 5 business divisions.

Usage:
    python reports/revenue_projection_5yr.py
    python reports/revenue_projection_5yr.py --output /path/to/report.pdf

PRIMEnergeia S.A.S. — Diego Córdoba Urrutia
"""

import os
import sys
import io
import tempfile
import argparse
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fpdf import FPDF
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ═══════════════════════════════════════════════════════════════
#  GLOBAL MARKET DEFINITIONS — 17 ISOs, ~1,700 GW
# ═══════════════════════════════════════════════════════════════
GLOBAL_MARKETS = {
    "ERCOT":    {"name": "ERCOT",              "region": "Texas, USA",           "flag": "US",  "capacity_gw":  85, "currency": "USD", "rescue_per_gw_M": 0.84},
    "PJM":      {"name": "PJM Interconnection","region": "US East (13 states)",  "flag": "US",  "capacity_gw": 180, "currency": "USD", "rescue_per_gw_M": 0.55},
    "CAISO":    {"name": "California ISO",     "region": "California, USA",      "flag": "US",  "capacity_gw":  80, "currency": "USD", "rescue_per_gw_M": 0.70},
    "MISO":     {"name": "MISO",               "region": "US Midwest",           "flag": "US",  "capacity_gw": 190, "currency": "USD", "rescue_per_gw_M": 0.45},
    "SPP":      {"name": "Southwest Power Pool","region": "US Central",          "flag": "US",  "capacity_gw":  65, "currency": "USD", "rescue_per_gw_M": 0.40},
    "NYISO":    {"name": "New York ISO",       "region": "New York, USA",        "flag": "US",  "capacity_gw":  35, "currency": "USD", "rescue_per_gw_M": 0.75},
    "ISONE":    {"name": "ISO New England",    "region": "New England, USA",     "flag": "US",  "capacity_gw":  30, "currency": "USD", "rescue_per_gw_M": 0.68},
    "IESO":     {"name": "Ontario IESO",       "region": "Ontario, Canada",      "flag": "CA",  "capacity_gw":  38, "currency": "CAD", "rescue_per_gw_M": 0.35},
    "AESO":     {"name": "Alberta ESO",        "region": "Alberta, Canada",      "flag": "CA",  "capacity_gw":  17, "currency": "CAD", "rescue_per_gw_M": 0.50},
    "SEN":      {"name": "SEN / CENACE",       "region": "Mexico",               "flag": "MX",  "capacity_gw":  75, "currency": "USD", "rescue_per_gw_M": 0.86},
    "MIBEL":    {"name": "MIBEL / OMIE",       "region": "Spain + Portugal",     "flag": "ES",  "capacity_gw": 110, "currency": "EUR", "rescue_per_gw_M": 0.47},
    "EPEX":     {"name": "EPEX SPOT",          "region": "Germany",              "flag": "DE",  "capacity_gw": 220, "currency": "EUR", "rescue_per_gw_M": 0.42},
    "EPEX_FR":  {"name": "EPEX France",        "region": "France",               "flag": "FR",  "capacity_gw": 130, "currency": "EUR", "rescue_per_gw_M": 0.40},
    "NORDPOOL": {"name": "Nord Pool",          "region": "Nordics (NO/SE/FI/DK)","flag": "EU",  "capacity_gw": 100, "currency": "EUR", "rescue_per_gw_M": 0.38},
    "ELEXON":   {"name": "Elexon / BMRS",      "region": "United Kingdom",       "flag": "GB",  "capacity_gw":  80, "currency": "GBP", "rescue_per_gw_M": 0.52},
    "NEM":      {"name": "NEM / AEMO",         "region": "Australia",            "flag": "AU",  "capacity_gw":  55, "currency": "AUD", "rescue_per_gw_M": 0.60},
    "JEPX":     {"name": "JEPX",               "region": "Japan",                "flag": "JP",  "capacity_gw": 280, "currency": "JPY", "rescue_per_gw_M": 0.30},
}

# Approximate FX to USD
FX_TO_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74, "AUD": 0.65, "JPY": 0.0067}

ROYALTY_RATE = 0.25   # 25% value share
DEPLOYMENT_FEE_PER_NODE_USD = 50_000

# ═══════════════════════════════════════════════════════════════
#  5-YEAR ROLLOUT PLAN — Node-level market onboarding
# ═══════════════════════════════════════════════════════════════
# Fraction of each market's addressable capacity captured per year
ROLLOUT_FRACTIONS = {
    # Year 1: 3 launch markets only
    1: {"SEN": 0.12, "ERCOT": 0.10, "MIBEL": 0.08},
    # Year 2: +4 US ISOs
    2: {"SEN": 0.20, "ERCOT": 0.18, "MIBEL": 0.14,
        "PJM": 0.04, "CAISO": 0.05, "NYISO": 0.05, "ISONE": 0.05},
    # Year 3: +3 more
    3: {"SEN": 0.28, "ERCOT": 0.25, "MIBEL": 0.20,
        "PJM": 0.08, "CAISO": 0.10, "NYISO": 0.10, "ISONE": 0.10,
        "MISO": 0.03, "SPP": 0.03, "IESO": 0.04},
    # Year 4: +Europe & Canada
    4: {"SEN": 0.35, "ERCOT": 0.32, "MIBEL": 0.26,
        "PJM": 0.14, "CAISO": 0.16, "NYISO": 0.14, "ISONE": 0.14,
        "MISO": 0.06, "SPP": 0.06, "IESO": 0.08, "AESO": 0.06,
        "EPEX": 0.03, "EPEX_FR": 0.03, "NORDPOOL": 0.03, "ELEXON": 0.04},
    # Year 5: Full global footprint
    5: {"SEN": 0.42, "ERCOT": 0.38, "MIBEL": 0.32,
        "PJM": 0.20, "CAISO": 0.22, "NYISO": 0.18, "ISONE": 0.18,
        "MISO": 0.10, "SPP": 0.10, "IESO": 0.12, "AESO": 0.10,
        "EPEX": 0.06, "EPEX_FR": 0.05, "NORDPOOL": 0.06, "ELEXON": 0.08,
        "NEM": 0.05, "JEPX": 0.03},
}

# ═══════════════════════════════════════════════════════════════
#  DIVISION REVENUE MODEL (Non-Grid Divisions)
# ═══════════════════════════════════════════════════════════════
#  Grid revenue computed from market model above.
#  Other divisions modeled independently.
NON_GRID_DIVISIONS = {
    "PRIME Quant (Eureka)":   {"yr": [1.5,  3.2,  5.8,  9.0, 14.0], "color": "#ff6b35"},
    "PRIME Power (Engines)":  {"yr": [0.8,  2.5,  5.0,  8.5, 13.0], "color": "#fbc02d"},
    "PRIME Circular":         {"yr": [0.3,  0.8,  1.8,  3.5,  6.0], "color": "#ab47bc"},
    "PRIME Materials (Granas)":{"yr":[0.2,  0.5,  1.5,  4.0,  8.0], "color": "#66bb6a"},
}


# ═══════════════════════════════════════════════════════════════
#  REVENUE COMPUTATION ENGINE
# ═══════════════════════════════════════════════════════════════

def compute_grid_revenue() -> dict:
    """Compute PRIME Grid revenue per year and per market."""
    yearly = {}
    for yr in range(1, 6):
        fracs = ROLLOUT_FRACTIONS[yr]
        market_rev = {}
        for mkt_id, mkt in GLOBAL_MARKETS.items():
            frac = fracs.get(mkt_id, 0.0)
            if frac <= 0:
                continue
            cap_gw = mkt["capacity_gw"]
            rescue_local = cap_gw * frac * mkt["rescue_per_gw_M"]  # $M in local currency
            fx = FX_TO_USD.get(mkt["currency"], 1.0)
            rescue_usd_M = rescue_local * fx
            prime_rev_M = rescue_usd_M * ROYALTY_RATE
            market_rev[mkt_id] = {
                "frac": frac,
                "rescue_usd_M": rescue_usd_M,
                "prime_rev_M": prime_rev_M,
            }
        yearly[yr] = market_rev
    return yearly


def compute_total_projections():
    """Build complete 5-year projections across all divisions."""
    grid = compute_grid_revenue()

    years = list(range(1, 6))
    grid_rev = [sum(m["prime_rev_M"] for m in grid[yr].values()) for yr in years]

    # Cost model
    cost_M = [3.5, 6.0, 10.0, 16.0, 22.0]      # COGS + S&M + G&A
    infra_M = [0.5, 1.2, 2.5, 4.0, 6.0]          # Cloud + compliance

    total_rev_by_div = {"PRIME Grid": grid_rev}
    for div, data in NON_GRID_DIVISIONS.items():
        total_rev_by_div[div] = data["yr"]

    total_rev = [sum(total_rev_by_div[d][i] for d in total_rev_by_div) for i in range(5)]
    total_cost = [cost_M[i] + infra_M[i] for i in range(5)]
    ebitda = [total_rev[i] - total_cost[i] for i in range(5)]
    margin = [ebitda[i] / total_rev[i] * 100 if total_rev[i] > 0 else 0 for i in range(5)]
    cumulative = list(np.cumsum(total_rev))

    return {
        "years": years,
        "grid": grid,
        "grid_rev": grid_rev,
        "div_rev": total_rev_by_div,
        "total_rev": total_rev,
        "total_cost": total_cost,
        "ebitda": ebitda,
        "margin": margin,
        "cumulative": cumulative,
    }


# ═══════════════════════════════════════════════════════════════
#  CHART GENERATION  (matplotlib, dark theme)
# ═══════════════════════════════════════════════════════════════

def chart_stacked_divisions(proj) -> io.BytesIO:
    """Stacked area chart — revenue by division over 5 years."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#00d1ff", "#ff6b35", "#fbc02d", "#ab47bc", "#66bb6a"]
    labels = list(proj["div_rev"].keys())
    data = np.array([proj["div_rev"][d] for d in labels])
    x = proj["years"]

    ax.stackplot(x, data, labels=labels, colors=colors, alpha=0.85)
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Revenue ($M USD)", fontsize=12)
    ax.set_title("PRIMEnergeia — 5-Year Revenue by Division", fontsize=15, pad=12, color="#00d1ff")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Yr {y}" for y in x])
    ax.grid(alpha=0.12)

    # Total rev annotation
    for i, yr in enumerate(x):
        ax.annotate(f"${proj['total_rev'][i]:.0f}M",
                     xy=(yr, proj["total_rev"][i]),
                     xytext=(0, 8), textcoords="offset points",
                     ha="center", fontsize=9, color="white", fontweight="bold")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_market_expansion(proj) -> io.BytesIO:
    """Horizontal bar chart showing revenue by ISO in Year 5."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 7))

    yr5 = proj["grid"][5]
    sorted_mkts = sorted(yr5.items(), key=lambda kv: kv[1]["prime_rev_M"], reverse=True)
    names = [f"{mid} ({GLOBAL_MARKETS[mid]['region']})" for mid, _ in sorted_mkts]
    values = [v["prime_rev_M"] for _, v in sorted_mkts]

    # Color by continent
    cmap = {"US": "#00d1ff", "MX": "#ff6b35", "CA": "#fbc02d",
            "ES": "#ff3333", "DE": "#66bb6a", "FR": "#ab47bc",
            "EU": "#ab47bc", "GB": "#00ffcc", "AU": "#e91e63", "JP": "#f44336"}
    bar_colors = [cmap.get(GLOBAL_MARKETS[mid]["flag"], "#888888") for mid, _ in sorted_mkts]

    bars = ax.barh(names, values, color=bar_colors, alpha=0.88, height=0.65)
    ax.set_xlabel("PRIME Revenue ($M USD)", fontsize=12)
    ax.set_title("Year 5 — PRIME Grid Revenue by Market (17 ISOs)", fontsize=14, pad=12, color="#00d1ff")
    ax.invert_yaxis()
    ax.grid(alpha=0.1, axis="x")

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"${val:.1f}M", va="center", fontsize=9, color="white")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_cumulative_scenarios(proj) -> io.BytesIO:
    """Cumulative revenue with conservative / base / optimistic bands."""
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 5.5))

    x = proj["years"]
    base = np.array(proj["cumulative"])
    conservative = base * 0.60
    optimistic = base * 1.25

    ax.fill_between(x, conservative, optimistic, alpha=0.12, color="#00d1ff", label="Range (60%–125%)")
    ax.plot(x, optimistic, "--", color="#00ffcc", lw=1.2, alpha=0.6, label="Optimistic (+25%)")
    ax.plot(x, base, "-o", color="#00d1ff", lw=2.5, markersize=7, label="Base Case")
    ax.plot(x, conservative, "--", color="#ff6b35", lw=1.2, alpha=0.6, label="Conservative (60%)")

    for i, yr in enumerate(x):
        ax.annotate(f"${base[i]:.0f}M", xy=(yr, base[i]),
                     xytext=(0, 12), textcoords="offset points",
                     ha="center", fontsize=10, color="#00d1ff", fontweight="bold")

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Cumulative Revenue ($M USD)", fontsize=12)
    ax.set_title("PRIMEnergeia — Cumulative Revenue (Risk-Adjusted Scenarios)", fontsize=14, pad=12, color="#00d1ff")
    ax.legend(frameon=False, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Yr {y}" for y in x])
    ax.grid(alpha=0.12)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
#  PDF GENERATION
# ═══════════════════════════════════════════════════════════════

def _save_chart(buf) -> str:
    """Write chart buffer to temp file, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(buf.read())
    tmp.close()
    return tmp.name


def generate_pdf(output_path: str = None) -> str:
    """Generate the full 5-year projection PDF report."""

    proj = compute_total_projections()
    total_gw = sum(m["capacity_gw"] for m in GLOBAL_MARKETS.values())
    now = datetime.now()

    # ── Charts ──
    chart1 = _save_chart(chart_stacked_divisions(proj))
    chart2 = _save_chart(chart_market_expansion(proj))
    chart3 = _save_chart(chart_cumulative_scenarios(proj))

    output_path = output_path or os.path.join(
        PROJECT_ROOT, "reports",
        f"PRIMEnergeia_5yr_Revenue_Projection_{now.strftime('%Y%m%d')}.pdf"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        pdf = FPDF()

        # ═════════════ PAGE 1 — COVER ═════════════
        pdf.add_page()
        pdf.set_fill_color(10, 15, 26)
        pdf.rect(0, 0, 210, 297, "F")

        pdf.ln(50)
        pdf.set_font("Arial", "B", 36)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 18, "PRIMEnergeia S.A.S.", 0, 1, "C")

        pdf.set_font("Arial", "", 18)
        pdf.set_text_color(0, 255, 204)
        pdf.cell(0, 12, "5-Year Revenue Projection", 0, 1, "C")

        pdf.ln(5)
        pdf.set_font("Arial", "", 14)
        pdf.set_text_color(200, 200, 200)
        pdf.cell(0, 10, f"17 Global Markets  |  {total_gw:,} GW Total Capacity", 0, 1, "C")
        pdf.cell(0, 10, "5 Divisions  |  25% Value Share Model", 0, 1, "C")

        pdf.ln(15)
        pdf.set_font("Arial", "I", 11)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8, f"Report Date: {now.strftime('%B %d, %Y')}", 0, 1, "C")
        pdf.cell(0, 8, "Prepared by Diego Cordoba Urrutia — Lead Computational Physicist", 0, 1, "C")

        pdf.ln(30)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 5,
            "CONFIDENTIAL — This document contains proprietary financial projections. "
            "Distribution is restricted to authorized recipients. Projections are based on "
            "VZA-400 SEN public CENACE data model, market-specific capacity and pricing "
            "characteristics, and the PRIMEnergeia 25% value share pricing model.",
            align="C"
        )

        # ═════════════ PAGE 2 — EXECUTIVE SUMMARY ═════════════
        pdf.add_page()
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 12, "Executive Summary", 0, 1, "L")
        pdf.ln(3)

        yr5_total = proj["total_rev"][4]
        yr5_grid = proj["grid_rev"][4]
        yr1_total = proj["total_rev"][0]
        cum5 = proj["cumulative"][4]
        yr5_ebitda = proj["ebitda"][4]
        yr5_margin = proj["margin"][4]

        pdf.set_font("Arial", "", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, (
            f"PRIMEnergeia projects total revenue growing from ${yr1_total:.0f}M in Year 1 to "
            f"${yr5_total:.0f}M in Year 5, generating ${cum5:.0f}M in cumulative revenue over the "
            f"projection period. The PRIME Grid division alone reaches ${yr5_grid:.0f}M by Year 5 "
            f"across 17 global electricity markets representing {total_gw:,} GW of installed capacity."
            f"\n\n"
            f"Year 5 EBITDA is projected at ${yr5_ebitda:.0f}M ({yr5_margin:.0f}% margin), driven by "
            f"the capital-light SaaS model with >95% gross margins. Revenue is anchored by the "
            f"VZA-400 public CENACE data model in Mexico's SEN, which projected $231,243 USD in recoverable capital "
            f"operational cycle using real-time HJB stochastic optimal control."
        ))
        pdf.ln(5)

        # Key metrics table
        pdf.set_font("Arial", "B", 13)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 10, "Key Metrics", 0, 1, "L")

        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(95, 9, "Metric", 1, 0, "C", True)
        pdf.cell(95, 9, "Value", 1, 1, "C", True)

        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(0, 0, 0)
        metrics = [
            ("Total Addressable Markets", f"17 ISOs / {total_gw:,} GW"),
            ("Year 1 Revenue", f"${yr1_total:.1f}M USD"),
            ("Year 5 Revenue", f"${yr5_total:.0f}M USD"),
            ("5-Year Cumulative Revenue", f"${cum5:.0f}M USD"),
            ("Year 5 EBITDA", f"${yr5_ebitda:.0f}M ({yr5_margin:.0f}% margin)"),
            ("Year 5 Grid Markets Active", f"{len(proj['grid'][5])} of 17"),
            ("Pricing Model", "25% of capital rescued (value share)"),
            ("Deployment Fee", "$50,000 per node"),
            ("Market Reference (Public Data)", "$231,243 projected @ VZA-400 (SEN, public CENACE data)"),
            ("Gross Margin", ">95% (pure software, no hardware)"),
        ]
        for label, value in metrics:
            pdf.cell(95, 8, label, 1, 0, "L")
            pdf.cell(95, 8, value, 1, 1, "R")

        # ═════════════ PAGE 3 — DIVISION BREAKDOWN + CHART ═════════════
        pdf.add_page()
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 12, "Revenue by Division", 0, 1, "L")
        pdf.ln(2)

        # Division table
        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        col_w = [52, 28, 28, 28, 28, 28]
        headers = ["Division", "Yr 1", "Yr 2", "Yr 3", "Yr 4", "Yr 5"]
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 8, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(0, 0, 0)
        for div_name, rev_list in proj["div_rev"].items():
            pdf.cell(col_w[0], 7, div_name, 1, 0, "L")
            for j, v in enumerate(rev_list):
                pdf.cell(col_w[j+1], 7, f"${v:.1f}M", 1, 0, "R")
            pdf.ln()

        # Totals row
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(col_w[0], 8, "TOTAL", 1, 0, "L")
        for j in range(5):
            pdf.cell(col_w[j+1], 8, f"${proj['total_rev'][j]:.0f}M", 1, 0, "R")
        pdf.ln()
        pdf.ln(4)

        # Stacked area chart
        pdf.image(chart1, x=5, w=198)

        # ═════════════ PAGE 4 — GLOBAL MARKET DETAIL ═════════════
        pdf.add_page()
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 12, "Global Market Expansion — 17 ISOs", 0, 1, "L")
        pdf.ln(2)

        # Market table
        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 8)
        mcols = [28, 42, 18, 18, 22, 22, 22]
        mheaders = ["Market", "Region", "GW", "Cur.", "Yr 1 Rev", "Yr 3 Rev", "Yr 5 Rev"]
        for i, h in enumerate(mheaders):
            pdf.cell(mcols[i], 7, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(0, 0, 0)
        for mkt_id, mkt in GLOBAL_MARKETS.items():
            pdf.cell(mcols[0], 6, mkt_id, 1, 0, "L")
            pdf.cell(mcols[1], 6, mkt["region"][:22], 1, 0, "L")
            pdf.cell(mcols[2], 6, str(mkt["capacity_gw"]), 1, 0, "R")
            pdf.cell(mcols[3], 6, mkt["currency"], 1, 0, "C")

            for yr_idx in [1, 3, 5]:
                rev = proj["grid"][yr_idx].get(mkt_id, {}).get("prime_rev_M", 0)
                pdf.cell(mcols[4 + [1,3,5].index(yr_idx)], 6,
                         f"${rev:.1f}M" if rev > 0 else "—", 1, 0, "R")
            pdf.ln()

        # Totals
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(mcols[0]+mcols[1], 7, "TOTAL GRID", 1, 0, "L")
        pdf.cell(mcols[2], 7, f"{total_gw}", 1, 0, "R")
        pdf.cell(mcols[3], 7, "", 1, 0, "C")
        for yr_idx in [1, 3, 5]:
            total = sum(m["prime_rev_M"] for m in proj["grid"][yr_idx].values())
            pdf.cell(mcols[4 + [1,3,5].index(yr_idx)], 7, f"${total:.0f}M", 1, 0, "R")
        pdf.ln()
        pdf.ln(4)

        # Market expansion chart
        pdf.image(chart2, x=5, w=198)

        # ═════════════ PAGE 5 — P&L + SCENARIOS ═════════════
        pdf.add_page()
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 12, "Financial Projections & Scenarios", 0, 1, "L")
        pdf.ln(2)

        # P&L Table
        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        pcols = [52, 28, 28, 28, 28, 28]
        pheaders = ["", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
        for i, h in enumerate(pheaders):
            pdf.cell(pcols[i], 8, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(0, 0, 0)
        pnl_rows = [
            ("Total Revenue ($M)", proj["total_rev"]),
            ("  - PRIME Grid", proj["grid_rev"]),
        ]
        for div, data in NON_GRID_DIVISIONS.items():
            pnl_rows.append((f"  - {div}", data["yr"]))
        pnl_rows += [
            ("Operating Costs ($M)", proj["total_cost"]),
            ("EBITDA ($M)", proj["ebitda"]),
            ("EBITDA Margin (%)", proj["margin"]),
            ("Cumulative Rev ($M)", list(proj["cumulative"])),
        ]

        for label, values in pnl_rows:
            is_bold = label in ("Total Revenue ($M)", "EBITDA ($M)", "Cumulative Rev ($M)")
            if is_bold:
                pdf.set_font("Arial", "B", 9)
                pdf.set_text_color(0, 209, 255)
            else:
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(0, 0, 0)

            pdf.cell(pcols[0], 7, label, 1, 0, "L")
            for j, v in enumerate(values):
                if "%" in label:
                    txt = f"{v:.0f}%"
                else:
                    txt = f"${v:.1f}M"
                pdf.cell(pcols[j+1], 7, txt, 1, 0, "R")
            pdf.ln()

        pdf.ln(4)

        # Scenario table
        pdf.set_font("Arial", "B", 13)
        pdf.set_text_color(0, 209, 255)
        pdf.cell(0, 10, "Risk-Adjusted Scenarios (Year 5)", 0, 1, "L")

        pdf.set_fill_color(10, 15, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(60, 9, "Scenario", 1, 0, "C", True)
        pdf.cell(40, 9, "Assumption", 1, 0, "C", True)
        pdf.cell(45, 9, "Year 5 Revenue", 1, 0, "C", True)
        pdf.cell(45, 9, "5-Year Cumulative", 1, 1, "C", True)

        pdf.set_font("Arial", "", 10)
        scenarios = [
            ("Conservative", "60% of base", 0.60),
            ("Base Case", "Validated model", 1.00),
            ("Optimistic", "+25% growth", 1.25),
        ]
        for name, assumption, mult in scenarios:
            pdf.set_text_color(0, 0, 0)
            pdf.cell(60, 8, name, 1, 0, "L")
            pdf.cell(40, 8, assumption, 1, 0, "C")
            pdf.cell(45, 8, f"${yr5_total * mult:.0f}M", 1, 0, "R")
            pdf.cell(45, 8, f"${cum5 * mult:.0f}M", 1, 1, "R")

        pdf.ln(4)

        # Cumulative chart
        pdf.image(chart3, x=5, w=198)

        # ═════════════ FOOTER ═════════════
        pdf.ln(5)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 4, (
            "Assumptions: Revenue per GW is market-specific, based on price volatility profiles "
            "and VZA-400 public CENACE data model rescue rates. FX rates: EUR/USD=1.08, GBP/USD=1.27, "
            "CAD/USD=0.74, AUD/USD=0.65, JPY/USD=0.0067. Rollout assumes phased market entry "
            "with regulatory approvals. Past performance does not guarantee future results."
        ))
        pdf.ln(2)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "PRIMEnergeia S.A.S. — Soberania Energetica Global", 0, 1, "C")

        pdf.output(output_path)
        print(f"\n{'='*60}")
        print(f"  5-Year Revenue Projection Report Generated")
        print(f"  {output_path}")
        print(f"  Size: {os.path.getsize(output_path) / 1024:.1f} KB")
        print(f"{'='*60}\n")

    finally:
        for f in [chart1, chart2, chart3]:
            try:
                os.unlink(f)
            except OSError:
                pass

    return output_path


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 5-Year Revenue Projection PDF")
    parser.add_argument("--output", help="Output PDF path")
    args = parser.parse_args()
    generate_pdf(output_path=args.output)
