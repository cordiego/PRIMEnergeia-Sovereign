# PRIMEnergeia — Shadow Mode Daily Report

**Document:** SHADOW-RPT-[DAY_NUMBER]  
**Date:** [DATE]  
**Plant:** [PLANT_NAME] — [NODE_ID]  
**Deployment day:** [DAY] of 20  
**Mode:** READ-ONLY (Shadow)

---

## Summary

| Metric | Today | Cumulative |
|--------|-------|------------|
| Measurement intervals | [N_INTERVALS] | [TOTAL_INTERVALS] |
| Avg. frequency deviation | ±[FREQ_DEV] Hz | ±[FREQ_DEV_CUM] Hz |
| Avg. dispatch gap (optimal − actual) | [GAP] MW | [GAP_CUM] MW |
| Avg. LMP during gaps | $[LMP]/MWh | $[LMP_CUM]/MWh |
| **Shadow savings (today)** | **$[TODAY_SAVINGS]** | |
| **Shadow savings (cumulative)** | | **$[CUM_SAVINGS]** |
| HJB solver avg. latency | [LATENCY] ms | [LATENCY_CUM] ms |
| System uptime | [UPTIME]% | [UPTIME_CUM]% |

> **Translation:** Your plant left **$[TODAY_SAVINGS]** on the table today. Our software was watching.

---

## Hourly Breakdown

| Hour | Actual MW | Optimal MW | Gap | LMP ($/MWh) | Shadow $ |
|------|-----------|------------|-----|-------------|----------|
| 00:00 | [MW] | [MW] | [GAP] | [LMP] | $[AMT] |
| 01:00 | [MW] | [MW] | [GAP] | [LMP] | $[AMT] |
| 02:00 | [MW] | [MW] | [GAP] | [LMP] | $[AMT] |
| ... | ... | ... | ... | ... | ... |
| 23:00 | [MW] | [MW] | [GAP] | [LMP] | $[AMT] |
| **Total** | | | **[GAP]** | **[LMP]** | **$[TOTAL]** |

---

## System Health

| Check | Status |
|-------|--------|
| SCADA connection | ✅ Connected ([PROTOCOL]) |
| Frequency data quality | ✅ [QUALITY]% valid readings |
| Voltage data quality | ✅ [QUALITY]% valid readings |
| Power data quality | ✅ [QUALITY]% valid readings |
| Market price feed | ✅ [PRICE_SOURCE] |
| Edge server health | ✅ CPU [CPU]%, RAM [RAM]%, Disk [DISK]% |
| Write operations | 🔒 DISABLED (shadow mode) |

---

## What This Means

- **If control had been active today**, we estimate **$[TODAY_SAVINGS]** in additional revenue
- After [SHADOW_DAYS] days of shadow observation, cumulative potential: **$[CUM_SAVINGS]**
- Annualized projection from shadow data: **$[ANNUAL_FROM_SHADOW]**

---

**No setpoints were written. No plant operations were affected.**

*PRIMEnergeia S.A.S. — Shadow Report [DAY_NUMBER]* ⚡
