# PRIMEnergeia — Technical Methodology

## Co-Optimization Engine

### Objective
Maximize net revenue from a battery energy storage system (BESS) operating in the ERCOT wholesale electricity market by optimally timing charge/discharge cycles across day-ahead (DA) and real-time (RT) settlement.

### Algorithm: Two-Pass Lookahead

**Pass 1 — Schedule Construction**
For each 24-hour planning window:
1. Rank all hours by Day-Ahead LMP
2. Assign the **N cheapest hours** as CHARGE windows (N = battery MWh / max charge MW)
3. Assign the **N most expensive hours** as DISCHARGE windows
4. Flag any hour with DA price > $100/MWh as an additional DISCHARGE candidate
5. Assign remaining hours as HOLD + Ancillary Services (RRS at 30% capacity)

**Pass 2 — Constrained Execution**
Execute the schedule hour-by-hour, respecting physical constraints:
- SOC limits: 5% – 95%
- Max charge/discharge rate: capacity_MWh / 4 (4-hour system)
- Round-trip efficiency: 88% (split equally between charge/discharge)
- If a scheduled action would violate SOC limits, revert to HOLD+AS

### Battery Degradation Model
- **Cycle aging:** 0.015% capacity loss per full equivalent cycle
- **Full cycle definition:** energy throughput equal to 2× rated capacity
- **SOH floor:** 70% (end-of-life threshold)
- **Degradation cost:** SOH loss × battery replacement cost ($150/kWh)

### Revenue Streams
1. **Energy Arbitrage:** Buy low (charge at cheap hours), sell high (discharge at peak)
2. **Ancillary Services:** Responsive Reserve Service (RRS) during HOLD hours at 20 MW

### Baseline Methodology
The **flat-dispatch baseline** represents a naive operator:
- Constant output at 50% of fleet capacity
- 30% capacity factor
- Revenue = fleet_MW × 0.5 × avg_RT_price × hours × 0.3

**Uplift = (Optimized Revenue - Baseline) / Baseline × 100%**

### Savings Claim
The report claims: *"The optimizer would have earned X% more than flat dispatch."*

This is NOT a claim about savings vs. the client's actual dispatch — it is a claim about **optimizer performance vs. a naive strategy**, which is verifiable and defensible.

## Data Sources

| Source | Type | Frequency | Coverage |
|--------|------|-----------|----------|
| gridstatus (Python) | Real ERCOT SPP | Hourly (DA), 15-min (RT) | 2019–present |
| ERCOT MIS | Real ERCOT SPP | Hourly | 2019–present |
| Proxy Generator | Pattern-based synthetic | Hourly | Any period |

### Proxy Data Methodology
When real data is unavailable, the proxy generator uses:
- **Seasonal baselines** from ERCOT annual reports (Summer $55, Winter $38, Spring $28, Fall $32)
- **Hourly shape** from documented ERCOT load curves (duck curve, evening peak)
- **Weekend discount** of 20%
- **Spike probability** of 3% during summer peak hours (multiplier 3–15×)
- **RT deviation** from DA using Student's t-distribution (df=4, σ=12%)

Proxy data is clearly labelled as `[PROXY DATA]` in all outputs and reports.

## Limitations
1. The optimizer has **perfect foresight** of DA prices (known constraint in backtesting)
2. Battery degradation uses a **simplified linear model** (real degradation is nonlinear)
3. **No transmission constraints** — assumes perfect grid connectivity
4. **No ancillary service clearing** — assumes all bids are accepted
5. Forward-looking results depend on **market conditions remaining similar** to historical
