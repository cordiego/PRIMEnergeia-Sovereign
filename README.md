# ⚡ PRIMEnergeia Sovereign

**Sovereign Grid Control System for the Mexican National Electric System (SEN)**

PRIMEnergeia is a computational physics platform that optimizes energy grid operations through stochastic control theory, Hamilton-Jacobi-Bellman (HJB) optimal control, and deep reinforcement learning. Designed for real-time frequency stabilization, harmonic compensation, and fiduciary capital recovery across CENACE-regulated nodes.

---

## Architecture

```
PRIMEnergeia-Sovereign/
├── dashboard/       → Streamlit dashboards (SCADA-grade UI)
├── core/            → Core algorithms (HJB solver, DRL auto-healing, software engine)
├── physics/         → Grid physics (Swing Equation, synthetic inertia, CUDA/MPS motors)
├── orchestration/   → Multi-node orchestrators (30-node expansion, GCP deployment)
├── manifiestos/     → Report generators (fiduciary manifiestos, Nobel-tier white papers)
├── platforms/       → SaaS & control platforms (real-time, patrimonial, sovereign)
├── data/nodos/      → CENACE node datasets (10 regional nodes)
├── lib/             → Shared utilities (Carnot efficiency, thermodynamic functions)
├── scripts/         → Utility scripts (dataset generation, monitoring, billing)
├── docs/            → Technical documentation
├── tests/           → Test suite
└── notebooks/       → Research notebooks
```

## Core Modules

| Module | Description |
|--------|-------------|
| **`core/software_core.py`** | Stochastic vector synthesis, PML market simulation, fiduciary recovery engine |
| **`core/auto_healing_core.py`** | Deep RL actor-critic (HJB Critic + Auto-Healing Actor) for grid self-repair |
| **`physics/motor_fisica_soberana.py`** | Swing Equation solver with synthetic inertia injection |
| **`physics/motor_cuda_mps_v8.py`** | GPU-accelerated physics engine (CUDA/Apple MPS) |
| **`orchestration/orquestador_expansion_30nodos.py`** | 30-node national grid expansion orchestrator |
| **`dashboard/dashboard_primenergeia.py`** | Primary SCADA-grade Streamlit control dashboard |

## Active Nodes

| Node ID | Location | Type |
|---------|----------|------|
| 05-VZA-400 | Valle de México | Master |
| 01-QRO-230 | Querétaro | Regional |
| 03-GDL-400 | Guadalajara | Regional |
| 04-MTY-400 | Monterrey | Regional |
| 06-SLP-400 | San Luis Potosí | Regional |
| 07-HER-230 | Hermosillo | Sonora Hub |
| 07-NAV-230 | Navojoa | Sonora |
| 07-CUM-115 | Ciudad Obregón | Sonora |
| 08-ENS-230 | Ensenada | Baja California |
| 08-MXL-230 | Mexicali | Baja California |

## Setup

```bash
# Clone
git clone https://github.com/cordiego/PRIMEnergeia-Sovereign.git
cd PRIMEnergeia-Sovereign

# Install dependencies
pip install -r requirements.txt

# Launch the dashboard
streamlit run dashboard/dashboard_primenergeia.py
```

## Mathematical Foundation

The core optimization solves the Hamilton-Jacobi-Bellman equation:

```
V_t + min_u { L(x, u) + ∇V · f(x, u) } = 0
```

Where:
- **V(x, t)** — Value function (minimum cost-to-go)
- **u** — Control action (reactive power injection, synthetic inertia)
- **L(x, u)** — Running cost (frequency deviation penalty + PML exposure)
- **f(x, u)** — Grid dynamics (Swing Equation with stochastic load perturbation)

---

**PRIMEnergeia S.A.S.** | Lead Computational Physicist: Diego Córdoba  
*Soberanía Energética para México*
