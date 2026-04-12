# PRIMEnergeia — Data Transfer Request

**Document:** PRE-DEPLOY-002  
**Date:** [DATE]  
**Prepared for:** [CLIENT_NAME]  
**Prepared by:** Diego Córdoba, PRIMEnergeia S.A.S.  
**NDA Reference:** [NDA_NUMBER] dated [NDA_DATE]

---

## Purpose

To run our baseline analysis, we need **90 days of historical operating data** from your plant. This data will be used exclusively to calculate your recoverable capital and will not be shared with any third party.

---

## Requested Data

### Required (minimum for baseline analysis)

| # | Data Field | Format | Example |
|---|-----------|--------|---------|
| 1 | **Timestamp** | ISO 8601 or Unix | `2026-01-15T14:30:00` |
| 2 | **Actual MW injected** | Float, per interval | `87.3` |
| 3 | **Market clearing price** (LMP / PML) | Float, $/MWh or MXN/MWh | `47.20` |

### Strongly recommended (improves analysis accuracy)

| # | Data Field | Format | Example |
|---|-----------|--------|---------|
| 4 | Theoretical / scheduled MW | Float, per interval | `92.1` |
| 5 | Reactive power (MVAR) | Float, per interval | `12.4` |
| 6 | Frequency (Hz) | Float, per interval | `59.998` |
| 7 | Voltage (kV) | Float, per interval | `115.2` |
| 8 | Day-ahead price | Float, $/MWh | `52.10` |
| 9 | Real-time price | Float, $/MWh | `47.20` |

### Optional (enables advanced optimization)

| # | Data Field | Format | Example |
|---|-----------|--------|---------|
| 10 | Battery SOC (%) | Float | `72.5` |
| 11 | Solar irradiance (W/m²) | Float | `847.0` |
| 12 | Wind speed (m/s) | Float | `8.3` |
| 13 | Ambient temperature (°C) | Float | `32.1` |
| 14 | Curtailment events | Boolean flag | `TRUE` |

---

## Format Requirements

- **File format:** CSV (preferred), Excel (.xlsx), or JSON
- **Interval:** Match your settlement interval (5-min, 15-min, or hourly)
- **Period:** Minimum 90 days, ideally 12 months
- **File size:** Typically 10–500 MB depending on interval and fields
- **Column headers:** Include headers in row 1 (any language — we auto-detect)

### Accepted column naming conventions

Our system auto-detects the following market formats:

| Market | Expected columns |
|--------|-----------------|
| **ERCOT** | `dam_lmp`, `rtm_lmp`, `timestamp` |
| **SEN (CENACE)** | `Actual_MW`, `Theoretical_MW`, `PML_USD`, `Fecha` |
| **MIBEL** | `OMIE_pool`, `timestamp`, `MW_actual` |
| **Custom** | Any — we'll map it manually |

---

## Transfer Methods (choose one)

| Method | Details |
|--------|---------|
| **Secure file share** (preferred) | We'll provide a private upload link |
| **Email attachment** | diego@primenergeia.com (for files < 25 MB) |
| **SFTP** | We'll provide credentials to our secure server |
| **USB drive** | Physical handoff during site visit |
| **API export** | If your historian has a REST API, we can pull directly |

---

## Data Security

- All data is covered under our mutual NDA ([NDA_NUMBER])
- Data is stored encrypted at rest (AES-256) and in transit (TLS 1.3)
- Data is used exclusively for your baseline analysis
- Data is deleted upon request or 90 days after contract termination
- We do not share data with any third party, including the ISO

---

## Timeline

| Step | When |
|------|------|
| You send data | Within 3 business days of this request |
| We confirm receipt & validate | Within 24 hours of receiving data |
| We deliver Baseline Report | Within 48 hours of validated data |

---

**Questions about data formats?** Contact Diego Córdoba — diego@primenergeia.com

*PRIMEnergeia S.A.S. — Grid Optimization Division* ⚡
