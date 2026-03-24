# ⚡ PRIMEnergeia Sovereign

### Intelligent Multi-Market Grid Control That Recovers Lost Capital

[![Live Dashboard](https://img.shields.io/badge/🔴_LIVE_DEMO-Streamlit_Cloud-00d1ff?style=for-the-badge)](https://primenergeia-sovereign.streamlit.app)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](#license)
[![Markets](https://img.shields.io/badge/Markets-SEN_|_ERCOT_|_MIBEL-fbc02d?style=for-the-badge)](#markets)

---

> **$231,243 USD** in capital recovered at a single node (VZA-400) through optimal frequency control.  
> **72 nodes** across **3 international markets** — SEN 🇲🇽 · ERCOT 🇺🇸 · MIBEL 🇪🇸🇵🇹  
> **~$48M USD** projected annual recurring revenue.

---

## The Problem

Electric grids worldwide lose millions annually through **suboptimal power injection**. When frequency deviates from nominal (50/60 Hz), grid operators apply penalties. When generators fail to track local prices, capital is left on the table. Current control systems are reactive — they respond to instability *after* it happens.

## The Solution

PRIMEnergeia solves the **Hamilton-Jacobi-Bellman optimal control equation** in real-time to predict and prevent frequency deviations *before* they trigger penalties. The result: capital that was previously dissipated is now recovered and returned to the asset operator.

```
V_t + min_u { L(x, u) + ∇V · f(x, u) } = 0
```

| What It Does | How |
|---|---|
| **Predicts** frequency excursions | Stochastic grid dynamics model |
| **Injects** synthetic inertia proactively | HJB optimal control law |
| **Eliminates** operator penalties | Real-time Swing Equation solver |
| **Captures** price arbitrage | Market-aware dispatch optimization |
| **Self-heals** after disturbances | Deep RL actor-critic neural network |

---

## Markets

The unified dashboard includes a **sidebar market selector** to switch between all three markets in real-time.

| Market | Country | Frequency | Nodes | Pricing | THD Standard | Accent |
|--------|---------|-----------|-------|---------|-------------|--------|
| **SEN** | 🇲🇽 Mexico | 60 Hz | 30 | PML / CENACE | Código de Red (≤5%) | Cyan |
| **ERCOT** | 🇺🇸 Texas | 60 Hz | 22 | LMP ($5k cap) | IEEE 519 (≤5%) | Orange |
| **MIBEL** | 🇪🇸🇵🇹 Iberian | 50 Hz | 20 | OMIE Pool (EUR) | EN 50160 (≤8%) | Gold |

### Key Differences

- **ERCOT** — Islanded grid, lower inertia (H=4.5s), higher volatility, $5,000/MWh scarcity cap
- **SEN** — 9 CENACE regions, 15-min settlement, Código de Red compliance
- **MIBEL** — 50 Hz ENTSO-E grid, higher inertia (H=6.0s), OMIE pool pricing in EUR

---

## Proven Results — Node VZA-400 (SEN, Valle de México)

| Metric | Value |
|--------|-------|
| **Capital Rescued** | **$231,243 USD** |
| Client Net Savings (75%) | $173,432 USD |
| PRIMEnergeia Fee (25%) | $57,811 USD |
| Frequency Stability | 99.96% |
| System Latency | < 0.5 ms |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│               DASHBOARD LAYER                    │
│  Unified Streamlit SCADA — Market Selector      │
│  (dashboard/ + markets/)                         │
├─────────────────────────────────────────────────┤
│           MARKET ENGINES LAYER                   │
│  SEN (30 nodes) │ ERCOT (22 nodes) │ MIBEL (20)│
│  (markets/sen/  │  markets/ercot/  │  mibel/)   │
├─────────────────────────────────────────────────┤
│               CORE LAYER                         │
│  HJB Solver │ DRL Auto-Healing │ Price Engine   │
│  (core/)                                         │
├─────────────────────────────────────────────────┤
│          OPTIMIZATION LAYER (Granas)             │
│  Bayesian Optimization │ GP Surrogate │ 6D PCE  │
│  (optimization/)                                 │
├─────────────────────────────────────────────────┤
│             PHYSICS LAYER                        │
│  Swing Eq (50/60 Hz) │ Synthetic Inertia │ GPU  │
│  (physics/ + markets/*/physics_*.py)             │
├─────────────────────────────────────────────────┤
│               DATA LAYER                         │
│  Market Telemetry (data/ + market_config.py)     │
└─────────────────────────────────────────────────┘
```

| Module | Description |
|--------|-------------|
| `dashboard/dashboard_primenergeia.py` | Unified multi-market SCADA dashboard with sidebar selector |
| `markets/market_config.py` | Shared market configuration dataclasses (all 72 nodes) |
| `markets/ercot/` | ERCOT physics, orchestrator, standalone dashboard |
| `markets/sen/` | SEN physics, orchestrator, standalone dashboard |
| `markets/mibel/` | MIBEL physics (50 Hz), orchestrator, standalone dashboard |
| `core/software_core.py` | Stochastic vector synthesis, price simulation, fiduciary recovery |
| `core/auto_healing_core.py` | Deep RL actor-critic (HJB Critic + Auto-Healing Actor) |
| `physics/motor_fisica_soberana.py` | Base Swing Equation solver with synthetic inertia injection |
| `optimization/granas_bayesian.py` | Bayesian Optimization engine for perovskite (Granas) ink recipes |
| `optimization/granas_visualizer.py` | Convergence, landscape, parallel coordinates, Pareto front plots |
| `optimization/granas_dashboard.py` | Streamlit dashboard for interactive Granas optimization |

## Quick Start

```bash
git clone https://github.com/cordiego/PRIMEnergeia-Sovereign.git
cd PRIMEnergeia-Sovereign
pip install -r requirements.txt
streamlit run dashboard/dashboard_primenergeia.py

# Granas Optimizer
streamlit run optimization/granas_dashboard.py

# Run Granas BO from CLI
python -m optimization.granas_bayesian
```

## Granas — Perovskite Bayesian Optimization

The `optimization/` module uses **Bayesian Optimization** with Gaussian Process surrogate models to find the optimal perovskite ink recipe for PRIMEnergeia Granas™ solar cells. The physics-informed objective models:

- **Crystallization kinetics** — LaMer nucleation, Scherrer grain-size estimation
- **Defect density** — Urbach-tail passivation via additives (Cl⁻, GuaBr, MACl)
- **Shockley-Queisser-bounded PCE** — capped at practical champion ~25.8%

**6D Search Space:** Molar concentration, DMSO:DMF ratio, spin speed, additive %, annealing temperature, annealing time.

## Documentation

- 📋 [Executive Brief (ES)](docs/EXECUTIVE_BRIEF.md) — Propuesta de valor para directivos
- 💰 [Product Catalog](docs/PRODUCT_CATALOG.md) — 5 SBUs, $216M TAM, pricing models
- 📊 [ROI Analysis](docs/ROI_ANALYSIS.md) — Multi-market revenue projections (~$48M ARR)
- 🏗️ [Architecture](docs/architecture.md) — System design & control flow

---

## License

**Proprietary** — All rights reserved. See [LICENSE](LICENSE).

This software is the intellectual property of PRIMEnergeia S.A.S. Unauthorized copying, distribution, or use is strictly prohibited.

---

**PRIMEnergeia S.A.S.** | Lead Computational Physicist: Diego Córdoba Urrutia  
*Soberanía Energética Global* ⚡🇲🇽🇺🇸🇪🇸🇵🇹
