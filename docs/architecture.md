# PRIMEnergeia Architecture — Multi-Market System

## System Layers

```
┌─────────────────────────────────────────────────┐
│               DASHBOARD LAYER                    │
│  Unified Streamlit SCADA — Market Selector      │
│  17 Global ISOs — 1,700+ GW coverage            │
│  (dashboard/ + markets/)                         │
├─────────────────────────────────────────────────┤
│           MARKET ENGINES LAYER                   │
│  Per-market physics (50/60 Hz), orchestrators,  │
│  pricing adapters (PML / LMP / OMIE Pool)       │
│  (markets/{sen,ercot,mibel}/)                    │
├─────────────────────────────────────────────────┤
│            SHARED CONFIG LAYER                   │
│  market_config.py — 17 ISO definitions,          │
│  grid physics params, regulatory standards      │
│  (markets/market_config.py)                      │
├─────────────────────────────────────────────────┤
│               CORE LAYER                         │
│  HJB Solver │ DRL Auto-Healing │ Price Engine   │
│  (core/)                                         │
├─────────────────────────────────────────────────┤
│          OPTIMIZATION LAYER (Granas)             │
│  Bayesian Opt │ GP Surrogate │ 6D Perovskite   │
│  (optimization/)                                 │
├─────────────────────────────────────────────────┤
│             PHYSICS LAYER                        │
│  Swing Equation │ Synthetic Inertia │ CUDA/MPS  │
│  (physics/ + markets/*/physics_*.py)             │
├─────────────────────────────────────────────────┤
│               DATA LAYER                         │
│  Market Telemetry + Node CSVs (data/)            │
└─────────────────────────────────────────────────┘
```

## Market-Specific Parameters

| Parameter | SEN 🇲🇽 | ERCOT 🇺🇸 | MIBEL 🇪🇸🇵🇹 |
|-----------|---------|----------|------------|
| Frequency | 60 Hz | 60 Hz | **50 Hz** |
| Inertia H | 5.0 s | 4.5 s | 6.0 s |
| Damping D | 2.0 | 1.8 | 2.5 |
| Pricing | PML | LMP | OMIE Pool |
| Currency | USD | USD | EUR |
| Settlement | 15-min | 5-min RT | Hourly |
| THD Std | Código de Red | IEEE 519 | EN 50160 |
| THD Limit | ≤5% | ≤5% | ≤8% |
| Penalty Threshold | ±0.05 Hz | ±0.03 Hz | ±0.04 Hz |
| Nodes | 30 | 22 | 20 |

> **Note:** In addition to the 3 core markets above, PRIMEnergeia now supports **14 additional ISOs** via `fetch_global_markets.py`: PJM, CAISO, MISO, SPP, NYISO, ISONE, IESO, AESO, EPEX (DE/FR), Nord Pool, Elexon, NEM, JEPX.

## Control Flow

1. **Market selection** — Sidebar selector loads market-specific config (physics, pricing, nodes)
2. **Telemetry ingestion** — Node CSVs or real-time PMU data feed into the physics layer
3. **Swing Equation solve** — Market-tuned physics engine (50 or 60 Hz) integrates frequency dynamics
4. **HJB control** — Optimal control law computes reactive power injection u*(x)
5. **Auto-healing** — DRL actor-critic for self-repair on frequency excursions
6. **Orchestration** — Per-market orchestrators coordinate across all nodes
7. **Financial engine** — Market-specific pricing (PML/LMP/Pool) calculates capital recovery
8. **Dashboard** — Unified 6-tab SCADA visualization renders all markets with dynamic theming

## Granas Optimization Layer

The `optimization/` module adds Bayesian Optimization for perovskite (Granas™) solar cell fabrication:

1. **GP Surrogate** — Gaussian Process models the 6D ink-recipe → PCE response surface
2. **Acquisition** — EI/PI/LCB selects the next most informative experiment
3. **Physics Model** — Crystallization kinetics, Scherrer grain size, defect density, SQ-bounded PCE
4. **Multi-Objective** — Joint optimization of PCE + T80 stability
5. **Warm Start** — Seed from prior lab experiments via CSV
6. **Dashboard** — Interactive Streamlit UI for optimization control and visualization
