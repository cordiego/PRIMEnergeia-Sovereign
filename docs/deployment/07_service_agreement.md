# PRIMEnergeia — Grid Optimization Service Agreement

**Document:** CONTRACT-001  
**Effective Date:** [DATE]  
**Between:**  
- **Provider:** PRIMEnergeia S.A.S., represented by Diego Córdoba, CEO  
- **Client:** [CLIENT_LEGAL_NAME], represented by [CLIENT_REP_NAME], [TITLE]

---

## 1. Service Description

PRIMEnergeia S.A.S. ("Provider") will deploy and operate its proprietary HJB-optimal dispatch control software ("the Software") at Client's power generation facility ("the Plant") at [PLANT_NAME], ISO Node [NODE_ID], [MARKET] market.

### 1.1 Scope of Service

The Provider will:
- Deploy the Software on a dedicated edge server connected to Client's SCADA network
- Configure protocol adapters for Client's specific SCADA system ([PROTOCOL])
- Operate the HJB optimal control solver in real-time to maximize dispatch efficiency
- Provide 24/7 dashboard access with real-time telemetry and capital recovery tracking
- Deliver monthly performance reports
- Provide technical support per the SLA in Section 5

### 1.2 What the Software Does NOT Do

- Modify, replace, or bypass any existing plant safety/protection systems
- Access any systems outside the agreed SCADA measurement and control tags
- Share Client data with any third party
- Override operator commands (operator override always takes precedence)

---

## 2. Fees

### 2.1 Deployment Fee

| Item | Amount |
|------|--------|
| One-time deployment fee | **$50,000 USD** |
| Includes: site assessment, tag mapping, edge server configuration, 4-week deployment, training | |
| Due: upon contract execution | |

### 2.2 Performance Royalty

| Item | Amount |
|------|--------|
| Monthly royalty on recovered capital | **25%** |
| Calculation: 25% × (Optimal_MW − Actual_Baseline_MW) × LMP × Δt, summed over all intervals | |
| Baseline: established during deployment Week 2–3 | |
| Due: monthly, within 30 days of invoice | |
| Minimum monthly royalty | **$0** (performance-based — if we don't recover capital, you don't pay) |

### 2.3 Billing Methodology

- Capital recovered is calculated using the same methodology visible on Client's dashboard
- Both parties have access to the same data and calculations (full transparency)
- Any disputed intervals are excluded from that month's invoice pending resolution
- Provider will issue invoices by the 5th business day of each month

---

## 3. Performance Metrics

### 3.1 Baseline

The performance baseline will be established from data collected during the deployment period (Days 8–15) and documented in the Validation Report (PRE-DEPLOY-005).

### 3.2 Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| System uptime | ≥ 99.5% | Monthly |
| Solver latency | < 100 ms (avg) | Continuous |
| Safety incidents caused by Software | 0 | Continuous |
| Operator override responsiveness | < 100 ms | Continuous |

### 3.3 Performance Review

- Monthly reports delivered by the 5th business day of each month
- Quarterly business reviews to assess performance and optimization opportunities
- Annual contract review 30 days before renewal date

---

## 4. Data & Security

### 4.1 Data Ownership

- All plant operational data remains the exclusive property of Client
- Provider may use anonymized, aggregated data for system improvement
- Provider will not share Client data with any third party

### 4.2 Data Security

| Measure | Implementation |
|---------|---------------|
| Encryption at rest | AES-256 |
| Encryption in transit | TLS 1.3 |
| Access control | Role-based, minimum privilege |
| Audit logging | All access and setpoint writes logged |
| Data retention | Duration of contract + 90 days post-termination |
| Data deletion | Upon Client request or 90 days post-termination |

### 4.3 Compliance

Provider's software and deployment practices comply with:
- NERC CIP (North American markets)
- Código de Red (Mexico / CENACE)
- EN 50160 / ENTSO-E requirements (European markets)
- Applicable local cybersecurity regulations

---

## 5. Support & SLA

| Priority | Definition | Response Time | Resolution Target |
|----------|-----------|---------------|-------------------|
| **P1** | System offline, no setpoints being written | 4 hours | 24 hours |
| **P2** | Degraded performance or data quality issues | 24 hours | 72 hours |
| **P3** | Questions, feature requests, reports | 72 hours | Best effort |

- Support is provided via email (diego@primenergeia.com) and phone
- On-site visits included: up to 2 per year at no additional cost
- Remote monitoring is continuous

---

## 6. Term & Termination

### 6.1 Term

- Initial term: **12 months** from the Effective Date
- Auto-renews for successive 12-month periods unless either party provides 60 days' written notice

### 6.2 Termination

Either party may terminate this Agreement:
- For convenience: with 60 days' written notice
- For cause: if the other party materially breaches and fails to cure within 30 days of written notice
- Immediately: if required by regulatory order

### 6.3 Upon Termination

- Provider will remove all software from Client's systems within 10 business days
- Provider will delete all Client data within 90 days (or sooner upon request)
- No termination fees apply
- Any outstanding royalties remain due for services rendered prior to termination

---

## 7. Limitation of Liability

- Provider's total liability shall not exceed the total fees paid by Client in the 12 months preceding the claim
- Provider is not liable for: market price fluctuations, ISO policy changes, force majeure events, or actions taken by Client's operators that override the Software's recommendations
- Client acknowledges that projected financial outcomes are estimates based on historical analysis and are not guaranteed

---

## 8. Signatures

### Provider

| | |
|-|-|
| **Name:** | Diego Córdoba |
| **Title:** | CEO, PRIMEnergeia S.A.S. |
| **Date:** | |
| **Signature:** | |

### Client

| | |
|-|-|
| **Name:** | [CLIENT_REP_NAME] |
| **Title:** | [TITLE] |
| **Organization:** | [CLIENT_LEGAL_NAME] |
| **Date:** | |
| **Signature:** | |

---

*PRIMEnergeia S.A.S. — Grid Optimization Division* ⚡
