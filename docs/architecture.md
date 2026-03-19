# PRIMEnergeia Architecture

## System Layers

```
┌─────────────────────────────────────────────────┐
│               DASHBOARD LAYER                    │
│  Streamlit SCADA UI (dashboard/)                 │
├─────────────────────────────────────────────────┤
│            ORCHESTRATION LAYER                   │
│  Multi-node coordination (orchestration/)        │
├─────────────────────────────────────────────────┤
│               CORE LAYER                         │
│  HJB Solver │ DRL Auto-Healing │ PML Engine     │
│  (core/)                                         │
├─────────────────────────────────────────────────┤
│             PHYSICS LAYER                        │
│  Swing Equation │ Synthetic Inertia │ CUDA/MPS  │
│  (physics/)                                      │
├─────────────────────────────────────────────────┤
│               DATA LAYER                         │
│  CENACE Node Telemetry (data/nodos/)             │
└─────────────────────────────────────────────────┘
```

## Control Flow

1. **Telemetry ingestion** — Node CSVs or real-time PMU data feed into the physics layer
2. **Swing Equation solve** — `motor_fisica_soberana.py` integrates the frequency dynamics
3. **HJB control** — `core/software_core.py` computes optimal reactive power injection
4. **Auto-healing** — `core/auto_healing_core.py` uses DRL for self-repair on frequency excursions
5. **Orchestration** — `orchestration/` coordinates actions across all 10+ nodes
6. **Dashboard** — `dashboard/` renders real-time SCADA visualization via Streamlit
