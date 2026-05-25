# PRIMEnergeia — Validation Report

**Document:** PRE-DEPLOY-005  
**Date:** [DATE]  
**Prepared for:** [CLIENT_NAME] — [PLANT_NAME]  
**ISO Node:** [NODE_ID] ([MARKET_NAME])  
**Deployment days covered:** Days 8–15  
**Prepared by:** Diego Córdoba, CEO — PRIMEnergeia S.A.S.

---

> **Result:** In 8 days of observation and bounded control, PRIMEnergeia recovered **$[TOTAL_RECOVERED]** in capital at [PLANT_NAME] — with zero safety incidents, zero operator overrides triggered, and [UPTIME]% system uptime.

---

## 1. Shadow Mode Results (Days 8–10)

*Software observed plant operations in read-only mode. No setpoints were written.*

| Day | Intervals | Avg. Gap (MW) | Avg. LMP | Shadow Savings |
|-----|-----------|---------------|----------|----------------|
| [DAY_8] | [N] | [GAP] MW | $[LMP] | $[AMT] |
| [DAY_9] | [N] | [GAP] MW | $[LMP] | $[AMT] |
| [DAY_10] | [N] | [GAP] MW | $[LMP] | $[AMT] |
| **Subtotal** | **[N]** | **[GAP] MW** | **$[LMP]** | **$[SHADOW_TOTAL]** |

---

## 2. Bounded Control Results (Days 13–15)

*Software wrote optimized setpoints within a ±5% permissive band, rate-limited to [RAMP] MW/sec.*

| Day | Setpoints Written | Avg. Correction | Revenue Uplift | Freq. Std Dev Δ |
|-----|-------------------|-----------------|----------------|-----------------|
| [DAY_13] | [N] | +[MW] MW | $[AMT] | [PCT]% |
| [DAY_14] | [N] | +[MW] MW | $[AMT] | [PCT]% |
| [DAY_15] | [N] | +[MW] MW | $[AMT] | [PCT]% |
| **Subtotal** | **[N]** | **+[MW] MW** | **$[BOUNDED_TOTAL]** | **[PCT]%** |

---

## 3. Combined Results

| Metric | Shadow (3 days) | Bounded (3 days) | Total (8 days) |
|--------|----------------|------------------|----------------|
| Capital identified / recovered | $[SHADOW] | $[BOUNDED] | **$[TOTAL]** |
| Annualized projection | $[S_ANN] | $[B_ANN] | **$[T_ANN]** |
| Avg. solver latency | [S_MS] ms | [B_MS] ms | [T_MS] ms |
| System uptime | [S_UP]% | [B_UP]% | [T_UP]% |
| Safety incidents | 0 | 0 | **0** |
| Operator overrides | N/A | 0 | **0** |

---

## 4. Safety & Compliance

| Control | Configuration | Result |
|---------|---------------|--------|
| Permissive band | ±5.0% of current dispatch | ✅ All setpoints within band |
| Maximum MW setpoint | [MAX] MW | ✅ Never exceeded |
| Minimum MW setpoint | [MIN] MW | ✅ Never breached |
| Ramp rate limit | [RAMP] MW/sec | ✅ All ramps within limit |
| Operator override | Enabled, priority over software | ✅ Never triggered |
| Safety interlock bypass | Not possible by design | ✅ All interlocks preserved |
| Frequency impact | N/A | ✅ Std dev reduced by [PCT]% |

---

## 5. Deployment Recommendation

Based on 8 days of validated performance:

| Criteria | Threshold | Actual | Status |
|----------|-----------|--------|--------|
| Annual projected recovery | > $150K | $[T_ANN] | ✅ |
| System uptime | > 99% | [T_UP]% | ✅ |
| Safety incidents | 0 | 0 | ✅ |
| Solver latency | < 100 ms | [T_MS] ms | ✅ |
| Data quality | > 95% | [QUALITY]% | ✅ |

### **Recommendation: ✅ PROCEED TO FULL DEPLOYMENT**

---

## 6. Proposed Full Deployment Terms

| Component | Detail |
|-----------|--------|
| **Control mode** | Full autonomous (±15% band, [RAMP_FULL] MW/sec ramp) |
| **Deployment fee** | $50,000 (one-time) |
| **Royalty** | 25% of monthly recovered capital |
| **Performance baseline** | [BASELINE_METRIC] established from Days 8–15 data |
| **Contract term** | 12 months, auto-renew |
| **Dashboard** | 24/7 real-time access at [DASHBOARD_URL] |
| **Support** | Business hours, < 4 hour response for P1 issues |

---

Diego Córdoba  
CEO, PRIMEnergeia S.A.S.  
diego@primenergeia.com

*PRIMEnergeia — Week 1: We learned. Week 2: We watched. Week 3: We proved it.* ⚡
