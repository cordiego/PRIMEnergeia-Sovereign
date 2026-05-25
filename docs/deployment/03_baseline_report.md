# PRIMEnergeia — Baseline Savings Report

**Document:** PRE-DEPLOY-003  
**Date:** [DATE]  
**Prepared for:** [CLIENT_NAME] — [PLANT_NAME]  
**ISO Node:** [NODE_ID] ([MARKET_NAME])  
**Prepared by:** Diego Córdoba, CEO — PRIMEnergeia S.A.S.

---

> **Executive Summary:** Analysis of [90] days of historical dispatch data at [PLANT_NAME] reveals **$[AMOUNT] in recoverable capital per year** through HJB-optimal dispatch control. No hardware modifications required.

---

## 1. Data Analyzed

| Parameter | Value |
|-----------|-------|
| Data period | [START_DATE] to [END_DATE] |
| Total intervals | [N_INTERVALS] |
| Interval resolution | [INTERVAL] minutes |
| Plant rated capacity | [CAPACITY] MW |
| ISO market | [MARKET] |
| Node ID | [NODE_ID] |
| Data quality score | [QUALITY]% (rows with valid MW + price data) |

---

## 2. Methodology

### How we calculate recoverable capital

For each interval *i*, we compute:

```
Δ Capital_i = (Optimal_MW_i − Actual_MW_i) × LMP_i × Δt
```

Where:
- **Optimal_MW** is the dispatch trajectory computed by the Hamilton-Jacobi-Bellman (HJB) optimal control solver
- **Actual_MW** is the plant's recorded injection
- **LMP** is the locational marginal price at your node
- **Δt** is the interval duration in hours (e.g., 0.25 for 15-min intervals)

The HJB solver minimizes the value function:

```
V_t + min_u { L(x, u) + ∇V · f(x, u) } = 0
```

Subject to the Swing Equation constraint:

```
df/dt = (Pm − Pe − D·Δf) / 2H
```

This is mathematically provable optimal — not a heuristic or ML approximation.

### What we do NOT include

- Intervals where `Optimal_MW < Actual_MW` (we only count upside)
- Intervals during curtailment events (flagged and excluded)
- Revenue from ancillary services (separate analysis available)
- Speculative price forecasts (we use actual historical prices only)

---

## 3. Results

### 3.1 Summary

| Metric | Value |
|--------|-------|
| Avg. dispatch gap (Optimal − Actual) | **[AVG_GAP] MW** |
| Avg. LMP during gap intervals | **$[AVG_LMP]/MWh** |
| Total capital recovered (analysis period) | **$[TOTAL_RECOVERED]** |
| **Projected annual recovery** | **$[ANNUAL_PROJECTED]** |
| 95% confidence interval | $[CI_LOW] — $[CI_HIGH] |
| Peak single-day recovery | $[PEAK_DAY] ([PEAK_DATE]) |
| Intervals with recoverable capital | [PCT_INTERVALS]% of total |

### 3.2 Monthly Breakdown

| Month | Avg. Gap (MW) | Avg. LMP ($/MWh) | Capital Recovered |
|-------|---------------|-------------------|-------------------|
| [MONTH_1] | [GAP] | [LMP] | $[AMOUNT] |
| [MONTH_2] | [GAP] | [LMP] | $[AMOUNT] |
| [MONTH_3] | [GAP] | [LMP] | $[AMOUNT] |
| **Total** | **[GAP]** | **[LMP]** | **$[TOTAL]** |

### 3.3 Distribution of Dispatch Gaps

```
  Dispatch Gap Distribution (MW)
  ──────────────────────────────────────
  0.0–0.5 MW  ████████████████████  42%   ← Within noise
  0.5–1.0 MW  ██████████████       28%   ← Recoverable
  1.0–2.0 MW  ████████             16%   ← High value
  2.0–5.0 MW  █████                10%   ← Peak events
  5.0+ MW     ██                    4%   ← Curtailment/outage
```

---

## 4. What This Means

### Without PRIMEnergeia (current state)
- Your plant dispatches based on [AGC / manual operator adjustment / fixed schedule]
- On average, you inject [AVG_GAP] MW below optimal per interval
- At $[AVG_LMP]/MWh, this gap costs you **$[DAILY_LOSS] per day**

### With PRIMEnergeia (projected)
- Our HJB solver computes optimal setpoints every [1] second
- Software automatically adjusts dispatch within your SCADA's permissive band
- **Zero hardware changes** — software only, one ethernet cable

### Financial comparison

| | Annual Revenue (Current) | Annual Revenue (+ PRIMEnergeia) | Delta |
|----|----|----|----|
| Energy sales | $[CURRENT] | $[OPTIMIZED] | +$[DELTA] |
| Penalty avoidance | $0 | $[PENALTIES] | +$[PENALTIES] |
| **Total** | **$[CURRENT]** | **$[TOTAL_OPT]** | **+$[ANNUAL_PROJECTED]** |

---

## 5. Deployment Recommendation

| Criteria | Status |
|----------|--------|
| Projected annual recovery > $150K | ✅ $[ANNUAL_PROJECTED] |
| Data quality sufficient | ✅ [QUALITY]% |
| SCADA protocol supported | ✅ [PROTOCOL] |
| Deployment recommendation | **✅ PROCEED TO SHADOW MODE** |

### Proposed next steps

| Step | Timeline | Description |
|------|----------|-------------|
| 1 | Days 6–7 | Edge server deployment + protocol adapter configuration |
| 2 | Days 8–10 | Shadow mode (read-only, 3 days) |
| 3 | Day 11 | Shadow results review with your operations team |
| 4 | Days 12–15 | Bounded control validation (±5% band) |
| 5 | Days 16–20 | Full deployment + dashboard handover |

---

## 6. Important Disclaimers

1. **All projections are based on historical data.** Actual results will vary based on market conditions, plant availability, and operational constraints.
2. **No proprietary deployment data was used.** This analysis uses data provided by [CLIENT_NAME] under NDA [NDA_NUMBER].
3. **Past performance does not guarantee future results.** The projected annual recovery is a statistical estimate based on [90] days of observed dispatch patterns.
4. **PRIMEnergeia does not guarantee specific financial outcomes.** Our service agreement includes performance metrics measured against an agreed baseline, not absolute dollar targets.

---

**Ready to proceed?** We can begin Week 2 (Shadow Mode) within [3 business days] of your approval.

Diego Córdoba  
CEO, PRIMEnergeia S.A.S.  
diego@primenergeia.com

*PRIMEnergeia — Mathematically provable optimal dispatch.* ⚡
