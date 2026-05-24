#!/usr/bin/env python3
"""
3-Month Investment Simulation: $1200 in VIXM + KMLM
Simulation period: Dec 26, 2025 → Mar 26, 2026
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import math

# ── Configuration ──────────────────────────────────────────────
TOTAL_INVESTMENT = 1200.0
TICKERS = ["VIXM", "KMLM"]
ALLOCATION = {t: TOTAL_INVESTMENT / len(TICKERS) for t in TICKERS}  # $600 each

SIM_START = datetime(2025, 12, 26)
SIM_END   = datetime(2026, 3, 26)

# ── Fetch historical prices via Yahoo Finance v8 ──────────────
def fetch_prices(ticker, start_dt, end_dt):
    """Fetch daily close prices from Yahoo Finance."""
    p1 = int((start_dt - timedelta(days=5)).timestamp())
    p2 = int((end_dt + timedelta(days=1)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={p1}&period2={p2}&interval=1d"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        prices = {}
        for ts, c in zip(timestamps, closes):
            if c is not None:
                dt = datetime.utcfromtimestamp(ts).date()
                prices[dt] = round(c, 4)
        return prices
    except Exception as e:
        print(f"⚠  Could not fetch {ticker} from Yahoo Finance: {e}")
        return None

# ── Fallback: synthetic simulation using known characteristics ─
def synthetic_simulation():
    """
    Use known ETF characteristics to build a realistic Monte-Carlo-style
    deterministic simulation (seeded) when live data is unavailable.
    
    VIXM (ProShares VIX Mid-Term Futures ETF):
      - Tracks S&P 500 VIX Mid-Term Futures Index
      - Known for negative roll yield / contango decay
      - Annualized vol ~25-35%, typical drift ~ -15% to -25%/yr
      - Recent price range: ~$17-22
      
    KMLM (KFA Mount Lucas Managed Futures Index Strategy ETF):
      - Trend-following managed futures
      - Lower vol ~10-15%, can trend positively in volatile regimes
      - Recent price range: ~$26-30
    """
    import random
    random.seed(42)
    
    start_prices = {"VIXM": 19.50, "KMLM": 27.80}
    
    params = {
        "VIXM": {"annual_drift": -0.18, "annual_vol": 0.30},
        "KMLM": {"annual_drift":  0.06, "annual_vol": 0.12},
    }
    
    all_prices = {}
    trading_days = []
    
    current = SIM_START
    while current <= SIM_END:
        if current.weekday() < 5:
            trading_days.append(current.date())
        current += timedelta(days=1)
    
    for ticker in TICKERS:
        p = params[ticker]
        daily_drift = p["annual_drift"] / 252
        daily_vol = p["annual_vol"] / math.sqrt(252)
        
        price = start_prices[ticker]
        prices = {}
        for day in trading_days:
            z = random.gauss(0, 1)
            ret = daily_drift + daily_vol * z
            price *= (1 + ret)
            prices[day] = round(price, 4)
        
        all_prices[ticker] = prices
    
    return all_prices, trading_days

# ── Run simulation ────────────────────────────────────────────
def run_simulation():
    print("=" * 70)
    print("  3-MONTH INVESTMENT SIMULATION")
    print(f"  Portfolio: ${TOTAL_INVESTMENT:.0f} → ${ALLOCATION['VIXM']:.0f} VIXM + ${ALLOCATION['KMLM']:.0f} KMLM")
    print(f"  Period: {SIM_START.strftime('%b %d, %Y')} → {SIM_END.strftime('%b %d, %Y')}")
    print("=" * 70)
    
    live_data = {}
    use_live = True
    for ticker in TICKERS:
        prices = fetch_prices(ticker, SIM_START, SIM_END)
        if prices and len(prices) > 10:
            live_data[ticker] = prices
        else:
            use_live = False
            break
    
    if use_live:
        print("\n📡  Using LIVE market data from Yahoo Finance\n")
        common_days = sorted(set(live_data[TICKERS[0]].keys()) & set(live_data[TICKERS[1]].keys()))
        all_prices = live_data
        trading_days = common_days
        data_source = "LIVE"
    else:
        print("\n🔬  Using SYNTHETIC simulation (GBM model with realistic parameters)\n")
        all_prices, trading_days = synthetic_simulation()
        data_source = "SYNTHETIC"
    
    if not trading_days:
        print("ERROR: No trading days generated.")
        return
    
    # ── Calculate shares purchased on day 1 ───────────────────
    day0 = trading_days[0]
    shares = {}
    cost_basis = {}
    
    print("┌─────────────────────────────────────────────────────┐")
    print("│  INITIAL PURCHASE                                   │")
    print("├─────────────────────────────────────────────────────┤")
    for ticker in TICKERS:
        buy_price = all_prices[ticker][day0]
        s = ALLOCATION[ticker] / buy_price
        shares[ticker] = s
        cost_basis[ticker] = buy_price
        print(f"│  {ticker}: {s:.4f} shares @ ${buy_price:.2f} = ${ALLOCATION[ticker]:.2f}  │")
    print("└─────────────────────────────────────────────────────┘")
    
    # ── Weekly snapshots ──────────────────────────────────────
    print(f"\n{'─'*90}")
    print(f"  WEEKLY PERFORMANCE TRACKER")
    print(f"{'─'*90}")
    header = f"{'Date':<14}"
    for t in TICKERS:
        header += f"  {t+' Price':<12}{t+' Value':<12}{t+' %':<10}"
    header += f"{'Total':<12}{'Total %':<10}"
    print(header)
    print("─" * 90)
    
    monthly = {}
    
    for i, day in enumerate(trading_days):
        month_key = day.strftime("%Y-%m")
        
        values = {}
        total = 0
        for ticker in TICKERS:
            price = all_prices[ticker][day]
            val = shares[ticker] * price
            values[ticker] = (price, val)
            total += val
        
        if month_key not in monthly:
            monthly[month_key] = {"first": None, "last": None}
        if monthly[month_key]["first"] is None:
            monthly[month_key]["first"] = (day, values, total)
        monthly[month_key]["last"] = (day, values, total)
        
        if i % 5 == 0 or day == trading_days[-1]:
            row = f"{day.strftime('%Y-%m-%d'):<14}"
            for t in TICKERS:
                price, val = values[t]
                pct = ((val - ALLOCATION[t]) / ALLOCATION[t]) * 100
                row += f"  ${price:<10.2f}${val:<10.2f}{pct:>+7.2f}%  "
            total_pct = ((total - TOTAL_INVESTMENT) / TOTAL_INVESTMENT) * 100
            row += f"${total:<10.2f}{total_pct:>+7.2f}%"
            print(row)
    
    # ── Final Summary ─────────────────────────────────────────
    last_day = trading_days[-1]
    final_total = 0
    
    print(f"\n{'='*70}")
    print("  FINAL RESULTS")
    print(f"{'='*70}\n")
    
    results = []
    for ticker in TICKERS:
        final_price = all_prices[ticker][last_day]
        final_value = shares[ticker] * final_price
        pnl = final_value - ALLOCATION[ticker]
        pct = (pnl / ALLOCATION[ticker]) * 100
        final_total += final_value
        results.append((ticker, cost_basis[ticker], final_price, shares[ticker], 
                        ALLOCATION[ticker], final_value, pnl, pct))
    
    for ticker, cb, fp, sh, invested, fv, pnl, pct in results:
        direction = "📈" if pnl >= 0 else "📉"
        print(f"  {direction} {ticker}")
        print(f"     Buy Price:    ${cb:.2f}")
        print(f"     Final Price:  ${fp:.2f}")
        print(f"     Shares:       {sh:.4f}")
        print(f"     Invested:     ${invested:.2f}")
        print(f"     Final Value:  ${fv:.2f}")
        print(f"     P&L:          ${pnl:+.2f} ({pct:+.2f}%)")
        print()
    
    total_pnl = final_total - TOTAL_INVESTMENT
    total_pct = (total_pnl / TOTAL_INVESTMENT) * 100
    
    print(f"  {'─'*50}")
    icon = "✅" if total_pnl >= 0 else "🔴"
    print(f"  {icon} PORTFOLIO TOTAL")
    print(f"     Invested:     ${TOTAL_INVESTMENT:.2f}")
    print(f"     Final Value:  ${final_total:.2f}")
    print(f"     Net P&L:      ${total_pnl:+.2f} ({total_pct:+.2f}%)")
    
    days_held = (last_day - day0).days
    if days_held > 0 and final_total > 0:
        ann_return = ((final_total / TOTAL_INVESTMENT) ** (365.0 / days_held) - 1) * 100
        print(f"     Annualized:   {ann_return:+.2f}%")
    
    print(f"\n  📊 Data Source: {data_source}")
    if data_source == "SYNTHETIC":
        print("  ⚠  Synthetic model uses GBM with realistic vol/drift parameters.")
        print("     VIXM: ~30% annual vol, ~-18% drift (contango decay)")
        print("     KMLM: ~12% annual vol, ~+6% drift (trend-following)")
    print(f"  📅 Holding Period: {days_held} calendar days ({len(trading_days)} trading days)")
    print()
    
    # ── Monthly breakdown ─────────────────────────────────────
    print(f"{'='*70}")
    print("  MONTHLY BREAKDOWN")
    print(f"{'='*70}")
    for mk in sorted(monthly.keys()):
        m = monthly[mk]
        _, _, start_total = m["first"]
        end_day, end_vals, end_total = m["last"]
        if mk == sorted(monthly.keys())[0]:
            base = TOTAL_INVESTMENT
        else:
            prev_mk = sorted(monthly.keys())[sorted(monthly.keys()).index(mk) - 1]
            _, _, base = monthly[prev_mk]["last"]
        
        month_ret = ((end_total - base) / base) * 100 if base > 0 else 0
        print(f"\n  {end_day.strftime('%B %Y')}:")
        for t in TICKERS:
            p, v = end_vals[t]
            print(f"    {t}: ${p:.2f} (value: ${v:.2f})")
        print(f"    Portfolio: ${end_total:.2f} (month return: {month_ret:+.2f}%)")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    run_simulation()
