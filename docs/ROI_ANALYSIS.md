# PRIMEnergeia — Multi-Market ROI Analysis & Revenue Projections

## Executive Summary

PRIMEnergeia recovers capital lost through suboptimal power injection by solving the HJB optimal control equation in real-time. This document presents validated results from SEN (Mexico) and projections for international expansion into ERCOT (Texas) and MIBEL (Iberian Peninsula).

---

## 1. Validated Results — Node VZA-400 (SEN Mexico)

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

### Recovery Formula

```
Capital Rescued = Σ [ (P_optimal - P_actual) × Market_Price × Δt ]
```

---

## 2. Market-Specific Revenue Models

### 2.1 SEN — Sistema Eléctrico Nacional (Mexico 🇲🇽)

| Parameter | Value |
|-----------|-------|
| Grid frequency | 60 Hz |
| Pricing mechanism | PML (Precios Marginales Locales) |
| Settlement | 15-min CENACE intervals |
| THD standard | Código de Red (≤5%) |
| Nodes deployed | **30** |
| Currency | USD |

| Metric | Monthly | Annual |
|--------|---------|--------|
| **Total capital rescued** | **$5,394,243** | **$64,730,916** |
| **PRIMEnergeia revenue (25%)** | **$1,348,561** | **$16,182,729** |
| Implementation fees (one-time) | — | $1,500,000 |
| **Total Year 1** | | **$17,682,729** |

---

### 2.2 ERCOT — Electric Reliability Council of Texas (USA 🇺🇸)

| Parameter | Value |
|-----------|-------|
| Grid frequency | 60 Hz |
| Pricing mechanism | LMP (Locational Marginal Price) |
| Settlement | 5-min RT / 15-min DA |
| Scarcity cap | **$5,000/MWh** |
| THD standard | IEEE 519 (≤5%) |
| Nodes planned | **22** |
| Currency | USD |

ERCOT's islanded grid has **lower inertia (H ≈ 4.5s)** due to high wind/solar penetration, creating more frequent excursion events and higher per-event rescue potential — especially during summer peaks and winter storms.

| Node | Zone | Capacity | LMP Volatility | Est. Monthly Rescue | PRIMEnergeia Fee (25%) |
|------|------|----------|---------------|---------------------|----------------------|
| HOU-345-01 | Houston | 120 MW | Very High | $385,000 | $96,250 |
| NTH-345-01 | North (DFW) | 120 MW | High | $342,000 | $85,500 |
| AUS-345-01 | South (Austin) | 100 MW | High | $298,000 | $74,500 |
| STH-345-01 | South (SA) | 100 MW | High | $285,000 | $71,250 |
| WST-345-01 | West (Permian) | 100 MW | Very High | $365,000 | $91,250 |
| PNH-345-01 | Panhandle | 80 MW | Very High | $310,000 | $77,500 |
| EST-345-01 | East | 80 MW | Medium | $242,000 | $60,500 |
| FWS-345-01 | Far West | 80 MW | High | $268,000 | $67,000 |
| *Other 14 nodes* | Various | 880 MW | Medium–High | $3,480,000 | $870,000 |

| Metric | Monthly | Annual |
|--------|---------|--------|
| **Total capital rescued (22 nodes)** | **$5,975,000** | **$71,700,000** |
| **PRIMEnergeia revenue (25%)** | **$1,493,750** | **$17,925,000** |
| Implementation fees (one-time) | — | $1,100,000 |
| **Total Year 1** | | **$19,025,000** |

> **Key advantage:** ERCOT's $5,000/MWh scarcity price cap means a single storm event can generate 10–50× normal rescue revenue at affected nodes.

---

### 2.3 MIBEL — Mercado Ibérico de Electricidad (Spain + Portugal 🇪🇸🇵🇹)

| Parameter | Value |
|-----------|-------|
| Grid frequency | **50 Hz** (ENTSO-E) |
| Pricing mechanism | OMIE Day-Ahead Pool + Intraday Auctions |
| Settlement | Hourly |
| THD standard | EN 50160 (≤8%) |
| Nodes planned | **20** |
| Currency | **EUR** |

MIBEL operates on the ENTSO-E Continental synchronous area with higher system inertia (H ≈ 6.0s), resulting in fewer but larger excursion events. Pricing is through the OMIE pool market, with REE (Spain) and REN (Portugal) as TSOs.

| Node | Zone | Capacity | Pool Volatility | Est. Monthly Rescue | PRIMEnergeia Fee (25%) |
|------|------|----------|----------------|---------------------|----------------------|
| ES-MAD-400 | Spain Central | 150 MW | High | €425,000 | €106,250 |
| ES-BCN-400 | Spain North | 120 MW | High | €348,000 | €87,000 |
| ES-SEV-400 | Spain South | 100 MW | Very High | €312,000 | €78,000 |
| PT-LIS-400 | Portugal South | 100 MW | High | €295,000 | €73,750 |
| ES-VAL-400 | Spain Central | 100 MW | Medium | €268,000 | €67,000 |
| PT-PRT-400 | Portugal North | 80 MW | Medium | €215,000 | €53,750 |
| ES-BIL-400 | Spain North | 100 MW | Medium | €248,000 | €62,000 |
| *Other 13 nodes* | Various | 700 MW | Medium | €2,185,000 | €546,250 |

| Metric | Monthly | Annual |
|--------|---------|--------|
| **Total capital rescued (20 nodes)** | **€4,296,000** | **€51,552,000** |
| **PRIMEnergeia revenue (25%)** | **€1,074,000** | **€12,888,000** |
| Implementation fees (one-time) | — | €1,000,000 |
| **Total Year 1** | | **€13,888,000** |

---

## 3. Global Aggregate — All Markets

| Market | Nodes | Annual Rescue | Annual Revenue (25%) | Currency |
|--------|-------|--------------|---------------------|----------|
| **SEN** 🇲🇽 | 30 | $64,730,916 | $16,182,729 | USD |
| **ERCOT** 🇺🇸 | 22 | $71,700,000 | $17,925,000 | USD |
| **MIBEL** 🇪🇸🇵🇹 | 20 | €51,552,000 | €12,888,000 | EUR |
| **TOTAL** | **72** | **~$188M** | **~$47M** | |

> Note: MIBEL figures in EUR. At EUR/USD ≈ 1.08, MIBEL ≈ $13.9M USD, bringing the total to **~$48M USD annual recurring revenue**.

---

## 4. Cost Structure

| Item | Cost |
|------|------|
| Cloud infrastructure (multi-region GCP/AWS) | ~$15,000/month |
| Regional compliance & legal | ~$200,000/year |
| Development & maintenance | Internal |
| Hardware modifications required | **$0** (pure software) |

**Gross margin:** > 95%

---

## 5. Risk-Adjusted Scenarios (All Markets Combined)

| Scenario | Assumption | Annual Revenue |
|----------|-----------|----------------|
| **Conservative** | 50% of projected rescue | ~$24M |
| **Base** | Validated SEN performance extrapolated | ~$48M |
| **Optimistic** | Higher volatility + scarcity events (+20%) | ~$57M |

---

## 6. Key Assumptions & Disclaimers

- SEN projections based on VZA-400 validated performance, scaled by capacity
- ERCOT projections reflect higher LMP volatility and scarcity pricing events
- MIBEL projections account for OMIE pool dynamics and 50 Hz grid specifics
- **ERCOT advantage:** Islanded grid with lower inertia → more frequent rescue events
- **MIBEL consideration:** Higher system inertia → larger but less frequent events
- Actual capital recovery depends on telemetry quality and hardware integration
- Exchange rate: EUR/USD ≈ 1.08 (subject to FX risk for MIBEL revenue)

---

**PRIMEnergeia S.A.S.** | Lead Computational Physicist: Diego Córdoba Urrutia  
*Soberanía Energética Global* ⚡🇲🇽🇺🇸🇪🇸🇵🇹
