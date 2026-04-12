"""
PRIME-Kernel — Shared Core Library
====================================
Common physics, control, and telemetry modules shared across
all PRIMEnergeia Strategic Business Units (SBUs).

SBUs:
  🔌 PRIME Grid    — VZA-400 (public CENACE data), HJB frequency control, SCADA
  ⚡ PRIME Power   — PRIMEngines (AICE, PEM, HYP), Battery, Wind
  ♻️ PRIME Circular — PRIMEcycle panel recycling
  📈 PRIME Quant   — Eureka Sovereign VIX-regime allocation
  🧪 PRIME Materials — Granas perovskite-Si tandem suite

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

__version__ = "1.0.0"
__author__ = "Diego Córdoba Urrutia"
__org__ = "PRIMEnergeia S.A.S."

from prime_kernel.constants import PhysicsConstants, MarketConstants, EngineConstants
from prime_kernel.telemetry import PRIMELogger, PRIMETelemetry

SBU_REGISTRY = {
    "PRIME Grid": {
        "repos": ["PRIMEnergeia-Sovereign", "PRIMStack"],
        "tam_usd": 48_000_000,
        "model": "Enterprise Contracts + Royalties",
        "status": "LIVE",
    },
    "PRIME Power": {
        "repos": ["PRIMEngines-AICE", "PRIMEngines-PEM", "PRIMEngines-HYP",
                  "PRIMEnergeia-Battery", "PRIM-Wind"],
        "tam_usd": 25_000_000,
        "model": "IP Licensing to Manufacturers",
        "status": "LIVE",
    },
    "PRIME Circular": {
        "repos": ["PRIMEcycle"],
        "tam_usd": 8_000_000,
        "model": "Carbon Credits + Consulting",
        "status": "ACTIVE",
    },
    "PRIME Quant": {
        "repos": ["Eureka-Sovereign"],
        "tam_usd": 15_000_000,
        "model": "Fund Management + Hedge Fund",
        "status": "LIVE",
    },
    "PRIME Materials": {
        "repos": ["Granas-Sovereign", "Granas-Optics", "Granas-SDL",
                  "Granas-CFRP", "Granas-GHB", "Granas-Albedo",
                  "Granas-ETFE", "Granas-TOPCon", "Granas-Blueprint",
                  "Granas-Metrics", "Granas-Scale"],
        "tam_usd": 120_000_000,
        "model": "Deep Tech IP + Patents",
        "status": "R&D",
    },
}
