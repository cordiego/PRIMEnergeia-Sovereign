# Changelog

All notable changes to PRIMEnergeia-Sovereign will be documented in this file.

## [1.0.0] — 2026-03-24

### 🏢 Enterprise Consolidation
- Organized 24 repositories into 5 Strategic Business Units (SBUs)
- Created **PRIME-Kernel** v1.0.0 — shared IP core (HJB solver, physics constants, telemetry)
- Created **PRIMStack** — unified plant integrator with multi-timescale HJB controller

### ⚙️ Physics Engines
- Audited and corrected simulation models across AICE, PEM, HYP, Battery, PRIMEcycle, and Wind
- Added HJB optimal control + BOM/manufacturing modules to **PRIMEngines-AICE**
- Fixed thermodynamic formulas, fuel utilization, and degradation rates

### 🔬 Granas Materials Suite
- Integrated 10 Granas satellite repos (Albedo, Blueprint, CFRP, ETFE, GHB, Metrics, Scale, SDL, TOPCon, Optics)
- Pinned dependencies and added `.gitignore` across all Granas repos
- Added cross-reference documentation linking all Granas products

### 📈 Eureka Trading
- Fixed daily trade notification bugs (Telegram parse_mode, retry logic, cache key)
- Updated GitHub Actions workflow for scheduled daily signals dispatch

### 🖥️ Dashboard & Deployment
- Consolidated three Streamlit apps (PRIMEnergeia, Eureka, Granas) into single multi-page app
- Created CEO-level executive dashboard (PRIME-Dashboard)
- Hardened GitHub profile with sales infrastructure

### 🧪 Quality & Polish
- Added pytest smoke tests to 5 skeleton repos (Battery, Wind, Cycle, HYP, PEM)
- Added professional READMEs to all repos missing them
- Tagged all 23 repos with GitHub Topics and descriptions
- Added MIT LICENSE to 19 repos

---

© 2026 PRIMEnergeia S.A.S. — Sovereign Clean Energy Intelligence
