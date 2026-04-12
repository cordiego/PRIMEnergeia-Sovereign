# PRIMEnergeia — Dashboard Operations Guide

**Document:** PRE-DEPLOY-006  
**Version:** 1.0  
**Prepared for:** [CLIENT_NAME] Operations Team  
**Dashboard URL:** [DASHBOARD_URL]  
**Prepared by:** PRIMEnergeia S.A.S.

---

## 1. Accessing the Dashboard

| Item | Value |
|------|-------|
| URL | [DASHBOARD_URL] |
| Login | Provided separately via secure channel |
| Browser | Chrome, Firefox, or Edge (latest) |
| Mobile | Responsive — works on tablet and phone |

---

## 2. Dashboard Pages — What Each One Shows

### Command Center (Home)
- **System status:** ONLINE / OFFLINE / SHADOW
- **Frequency gauge:** Real-time plant frequency vs. nominal
- **Capital rescued counter:** Running total since deployment
- **Market context:** Current LMP, market status

### Grid Control
- **HJB dispatch trajectory:** Optimal vs. actual MW over time
- **Frequency stability:** f(t) with RoCoF overlay
- **Synthetic inertia injection:** Control signal u(t)
- **Mode indicator:** HOLD / CHARGE / DISCHARGE

### Grid Outputs
- **Integration status:** Protocol connection health (OPC UA / Modbus / IEC 61850)
- **Dispatch schedule:** Hourly setpoint plan
- **Export formats:** CSV, JSON, API for downstream systems

### Capital Recovery
- **Monthly savings table:** Recoverable capital by month
- **Baseline comparison:** Pre vs. post PRIMEnergeia performance
- **Invoice preview:** Current month's projected royalty

---

## 3. Operator Override

**You always have control.** The software never overrides your safety systems.

### How to override from your HMI:
1. Set the **Operator Override** tag to `TRUE` on your SCADA HMI
2. PRIMEnergeia immediately stops writing setpoints
3. Dashboard shows: `⚠️ OPERATOR OVERRIDE ACTIVE`
4. Your manual controls take full priority
5. To restore: set Operator Override back to `FALSE`

### How to override from the dashboard:
1. Navigate to **Grid Control** page
2. Click the **SHADOW MODE** toggle in the sidebar
3. Software switches to read-only observation
4. No setpoints are written until you re-enable

> **Important:** Operator Override from SCADA HMI always takes priority over dashboard settings.

---

## 4. Exporting Reports

### Monthly Performance Report
1. Navigate to **Capital Recovery** page
2. Select date range
3. Click **Export PDF** or **Export CSV**
4. Report includes: intervals, gaps, prices, capital, methodology

### Setpoint Audit Trail
1. Navigate to **Grid Outputs** page
2. Select **Audit Log** tab
3. Download CSV of every setpoint written (timestamp, value, mode)
4. Required for regulatory compliance (NERC CIP / Código de Red)

---

## 5. Understanding the Metrics

| Metric | What It Means | Healthy Range |
|--------|---------------|---------------|
| **Frequency (Hz)** | Grid frequency at your bus | 59.95–60.05 Hz (60 Hz grids) |
| **RoCoF (Hz/s)** | Rate of Change of Frequency | < ±0.5 Hz/s |
| **Dispatch Gap (MW)** | Optimal − Actual injection | Will trend toward 0 over time |
| **LMP ($/MWh)** | Real-time market price at your node | Varies by market |
| **Capital Rescued ($)** | Cumulative revenue recovered | Should grow daily |
| **Solver Latency (ms)** | Time for HJB computation | < 1.0 ms typical |
| **System Uptime (%)** | Software availability | Target: > 99.5% |

---

## 6. Troubleshooting

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Dashboard shows "DISCONNECTED" | SCADA network issue or edge server offline | Check ethernet connection on edge server |
| Frequency reading stuck | SCADA tag path changed or sensor fault | Contact PRIMEnergeia support |
| "BAD" data quality indicator | Sensor returning invalid data | Check plant metering equipment |
| Capital counter not increasing | LMP very low or dispatch already optimal | Normal during low-price hours |
| Solver latency > 10 ms | Edge server CPU overloaded | Contact PRIMEnergeia support |

---

## 7. Support

| Priority | Response Time | Contact |
|----------|---------------|---------|
| **P1** — System offline, no setpoints | < 4 hours | diego@primenergeia.com + phone |
| **P2** — Degraded performance | < 24 hours | diego@primenergeia.com |
| **P3** — Question or feature request | < 72 hours | diego@primenergeia.com |

---

*PRIMEnergeia S.A.S. — Grid Optimization Division* ⚡
