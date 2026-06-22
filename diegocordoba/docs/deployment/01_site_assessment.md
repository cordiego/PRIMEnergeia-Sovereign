# PRIMEnergeia — Site Assessment Questionnaire

**Document:** PRE-DEPLOY-001  
**Date:** [DATE]  
**Prepared for:** [CLIENT_NAME]  
**Prepared by:** Diego Córdoba, PRIMEnergeia S.A.S.

---

## Purpose

This questionnaire helps us understand your plant's control infrastructure so we can configure our optimization software for a seamless, zero-hardware deployment. All information provided is covered under our mutual NDA.

Estimated time to complete: **15 minutes**

---

## Section A — Plant Identification

| # | Question | Your Answer |
|---|----------|-------------|
| A1 | Plant name and location | |
| A2 | ISO / market operator (CENACE, ERCOT, CAISO, MIBEL, etc.) | |
| A3 | ISO node ID (e.g., 05-VZA-400, HOU-345-01) | |
| A4 | Plant rated capacity (MW) | |
| A5 | Primary generation type (Gas, Solar, Wind, Hydro, BESS, Hybrid) | |
| A6 | Battery storage installed? If yes, capacity (MWh) | |

## Section B — SCADA / Control Systems

| # | Question | Your Answer |
|---|----------|-------------|
| B1 | SCADA / DCS vendor (ABB, Siemens, GE, Schneider, Honeywell, Yokogawa, other) | |
| B2 | SCADA software version | |
| B3 | Does your SCADA have an OPC UA server? (Yes / No / Unsure) | |
| B4 | Does your SCADA support Modbus TCP? (Yes / No / Unsure) | |
| B5 | Does your SCADA support IEC 61850? (Yes / No / Unsure) | |
| B6 | Can you provide a tag list export? (CSV/Excel of all measurement points) | |

## Section C — Network & Infrastructure

| # | Question | Your Answer |
|---|----------|-------------|
| C1 | SCADA network type (Ethernet, Serial, Fiber) | |
| C2 | SCADA network IP range (e.g., 192.168.1.0/24) | |
| C3 | Is there a DMZ between IT and OT networks? | |
| C4 | Is there a companion PC or edge server available on the OT network? | |
| C5 | If no edge server, can we deploy a small rack-mount unit? (1U, 1 ethernet cable) | |
| C6 | VPN or remote access available to OT network? | |

## Section D — Data & Metering

| # | Question | Your Answer |
|---|----------|-------------|
| D1 | Data historian software (OSIsoft PI, Honeywell PHD, Wonderware, other, none) | |
| D2 | Settlement interval (5-min, 15-min, hourly) | |
| D3 | Revenue meter manufacturer and model | |
| D4 | Can you export 90 days of historical data? (Actual MW, prices, timestamps) | |
| D5 | Do you have an API connection to the ISO for real-time prices? | |

## Section E — Operations & Compliance

| # | Question | Your Answer |
|---|----------|-------------|
| E1 | Number of control room operators per shift | |
| E2 | Do operators currently adjust dispatch manually or via AGC? | |
| E3 | Cybersecurity standard followed (NERC CIP, ISO 27001, Código de Red, other) | |
| E4 | Required approval process for new software on OT network | |
| E5 | Preferred contact for technical integration (name, role, email) | |

---

## What Happens Next

1. We review your answers and prepare a **tag mapping configuration** (1–2 days)
2. You transfer **90 days of historical data** via secure file share
3. We run a **backtest analysis** and deliver a baseline savings report within 48 hours
4. If the projected savings exceed $150K/year, we proceed to **Week 2: Shadow Mode**

---

**Questions?** Contact Diego Córdoba — diego@primenergeia.com

*PRIMEnergeia S.A.S. — We read your data, solve the math, and send back money.* ⚡
