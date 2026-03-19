# PRIMEnergeia — ROI Analysis & Revenue Projections

## Executive Summary

PRIMEnergeia recovers capital lost through suboptimal power injection by solving the HJB optimal control equation in real-time. This document presents validated results and projections for national expansion.

---

## 1. Validated Results — Node VZA-400

**Period:** March 2026 (operational cycle)  
**Node capacity:** 100 MW  
**Algorithm:** HJB Stochastic Dynamic Control v8.0-MPS

| Metric | Value |
|--------|-------|
| Instability events detected | 6 |
| Frequency deviation (avg, mitigated) | 0.042 Hz |
| Asset protection index | 99.96% |
| **Total capital rescued** | **$231,243 USD** |
| Client net savings (75%) | $173,432 USD |
| PRIMEnergeia fee (25%) | $57,811 USD |

### How Capital Recovery Works

```
Capital Rescued = Σ [ (P_optimal - P_actual) × PML × Δt ]
```

Where:
- **P_optimal** = Theoretical maximum injection trajectory (HJB solution)
- **P_actual** = Current suboptimal injection (legacy control system)
- **PML** = Local Marginal Price at the interconnection node (USD/MWh)
- **Δt** = Time interval (15-minute CENACE settlement periods)

The gap between `P_optimal` and `P_actual` represents capital that evaporates every settlement interval. PRIMEnergeia closes this gap.

---

## 2. Revenue Model per Node

| Revenue Stream | Per Node / Month | Annual |
|---------------|-----------------|--------|
| Implementation fee (one-time) | $50,000 | $50,000 |
| Royalty (25% of rescued capital) | ~$57,811 | ~$693,732 |
| **Total Year 1** | | **~$743,732** |
| **Recurring (Year 2+)** | | **~$693,732** |

---

## 3. 10-Node National Expansion Model

Based on VZA-400 baseline performance, scaled by node capacity and regional PML volatility.

| Node | Capacity | PML Volatility | Est. Monthly Rescue | PRIMEnergeia Fee (25%) |
|------|----------|---------------|---------------------|----------------------|
| 05-VZA-400 | 100 MW | High | $231,243 | $57,811 |
| 04-MTY-400 | 100 MW | High | $218,000 | $54,500 |
| 03-GDL-400 | 100 MW | Medium | $195,000 | $48,750 |
| 07-HER-230 | 80 MW | Very High | $245,000 | $61,250 |
| 01-QRO-230 | 80 MW | Medium | $165,000 | $41,250 |
| 06-SLP-400 | 100 MW | Medium | $178,000 | $44,500 |
| 08-MXL-230 | 80 MW | High | $202,000 | $50,500 |
| 08-ENS-230 | 80 MW | High | $189,000 | $47,250 |
| 07-NAV-230 | 60 MW | Medium | $142,000 | $35,500 |
| 07-CUM-115 | 40 MW | Low | $98,000 | $24,500 |

### Aggregate Projections

| Metric | Monthly | Annual |
|--------|---------|--------|
| **Total capital rescued (10 nodes)** | **$1,863,243** | **$22,358,916** |
| **PRIMEnergeia revenue (25% royalty)** | **$465,811** | **$5,589,732** |
| Implementation fees (one-time) | — | $500,000 |
| **Total Year 1 Revenue** | | **$6,089,732** |
| **Recurring Revenue (Year 2+)** | | **$5,589,732** |

---

## 4. Cost Structure

| Item | Cost |
|------|------|
| Cloud infrastructure (GCP) | ~$2,000/month |
| Development & maintenance | Internal |
| Hardware modifications required | **$0** (pure software layer) |

**Gross margin:** > 95%

---

## 5. Risk-Adjusted Scenarios

| Scenario | Assumption | Annual Revenue |
|----------|-----------|----------------|
| **Conservative** | 50% of projected rescue per node | $2,794,866 |
| **Base** | VZA-400 validated performance | $5,589,732 |
| **Optimistic** | Higher PML volatility (+20%) | $6,707,678 |

---

## 6. Key Assumptions & Disclaimers

- Projections are based on VZA-400 validated performance, scaled by node capacity
- PML volatility varies by region; Sonora nodes (07-*) have historically higher volatility due to solar intermittency
- Actual capital recovery depends on quality of telemetry data and hardware integration
- 15-minute CENACE settlement intervals used for all calculations
- All figures in USD at current exchange rates

---

**PRIMEnergeia S.A.S.** | Lead Computational Physicist: Diego Córdoba Urrutia
