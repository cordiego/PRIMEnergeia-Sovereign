# PRIMEnergeia Architecture — Multi-Market System

## System Layers

```
┌─────────────────────────────────────────────────┐
│               DASHBOARD LAYER                    │
│  Unified Streamlit SCADA — Market Selector      │
│  SEN 🇲🇽 │ ERCOT 🇺🇸 │ MIBEL 🇪🇸🇵🇹              │
│  (dashboard/ + markets/)                         │
├─────────────────────────────────────────────────┤
│           MARKET ENGINES LAYER                   │
│  Per-market physics (50/60 Hz), orchestrators,  │
│  pricing adapters (PML / LMP / OMIE Pool)       │
│  (markets/{sen,ercot,mibel}/)                    │
├─────────────────────────────────────────────────┤
│            SHARED CONFIG LAYER                   │
│  market_config.py — 72 node definitions,        │
│  grid physics params, regulatory standards      │
│  (markets/market_config.py)                      │
├─────────────────────────────────────────────────┤
│               CORE LAYER                         │
│  HJB Solver │ DRL Auto-Healing │ Price Engine   │
│  (core/)                                         │
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

## Control Flow

1. **Market selection** — Sidebar selector loads market-specific config (physics, pricing, nodes)
2. **Telemetry ingestion** — Node CSVs or real-time PMU data feed into the physics layer
3. **Swing Equation solve** — Market-tuned physics engine (50 or 60 Hz) integrates frequency dynamics
4. **HJB control** — Optimal control law computes reactive power injection u*(x)
5. **Auto-healing** — DRL actor-critic for self-repair on frequency excursions
6. **Orchestration** — Per-market orchestrators coordinate across all nodes (22–30 per market)
7. **Financial engine** — Market-specific pricing (PML/LMP/Pool) calculates capital recovery
8. **Dashboard** — Unified 6-tab SCADA visualization renders all markets with dynamic theming
