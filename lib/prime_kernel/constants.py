"""
PRIME-Kernel — Universal Constants
====================================
Physics, market, and engine constants shared across all SBUs.
Single source of truth: change here, propagates everywhere.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np


class PhysicsConstants:
    """Fundamental physics constants used across PRIMEnergeia."""

    # Thermodynamics
    BOLTZMANN_EV = 8.617333e-5       # eV/K
    BOLTZMANN_J = 1.380649e-23       # J/K
    PLANCK = 6.62607015e-34          # J·s
    AVOGADRO = 6.02214076e23         # mol⁻¹
    UNIVERSAL_GAS = 8.314462         # J/(mol·K)
    ROOM_TEMP_K = 300.0              # 27 °C
    STEFAN_BOLTZMANN = 5.670374e-8   # W/(m²·K⁴)

    # Hydrogen
    H2_LHV_KWH_KG = 33.3            # kWh/kg (Lower Heating Value)
    H2_HHV_KWH_KG = 39.4            # kWh/kg (Higher Heating Value)
    H2_DENSITY_KG_M3 = 0.0899       # kg/m³ at STP
    H2_MOLAR_MASS = 2.016e-3        # kg/mol
    H2O_PER_H2 = 9.0                # kg water per kg H₂ produced

    # Ammonia (NH₃)
    NH3_LHV_MJ_KG = 18.6            # MJ/kg
    NH3_LHV_KWH_KG = 5.17           # kWh/kg
    NH3_STOICH_H2 = 5.67            # kg NH₃ per kg H₂ (theoretical)
    NH3_MOLAR_MASS = 17.031e-3       # kg/mol
    NH3_DENSITY_KG_M3 = 0.73        # kg/m³ at STP

    # Perovskite / Solar
    ACTIVATION_GRAIN = 0.45          # eV — grain growth activation
    ACTIVATION_DEFECT = 0.35         # eV — defect annealing activation
    AM15G_IRRADIANCE = 1000.0        # W/m² standard test condition
    SHOCKLEY_QUEISSER_LIMIT = 0.337  # Single-junction theoretical max η

    # Battery / Electrochemistry
    FARADAY = 96485.33               # C/mol
    ELECTRON_CHARGE = 1.602176e-19   # C

    @staticmethod
    def carnot_efficiency(t_hot_k: float, t_cold_k: float) -> float:
        """Maximum theoretical thermodynamic efficiency."""
        t_hot = np.asarray(t_hot_k, dtype=float)
        t_cold = np.asarray(t_cold_k, dtype=float)
        if np.any(t_hot <= 0) or np.any(t_cold <= 0):
            raise ValueError("Temperatures must be in Kelvin (positive).")
        return float(np.maximum(1 - t_cold / t_hot, 0))

    @staticmethod
    def arrhenius_rate(prefactor: float, activation_ev: float, temp_k: float) -> float:
        """Arrhenius rate: k = A * exp(-Ea / kB*T)."""
        return prefactor * np.exp(-activation_ev / (PhysicsConstants.BOLTZMANN_EV * temp_k))


class MarketConstants:
    """Electricity market parameters for multi-market operations."""

    # Grid frequency standards
    FREQ_60HZ = 60.0    # Americas (SEN, ERCOT)
    FREQ_50HZ = 50.0    # Europe (MIBEL, ENTSO-E)

    # Market definitions
    MARKETS = {
        "SEN": {
            "name": "Sistema Eléctrico Nacional",
            "region": "México 🇲🇽",
            "frequency_hz": 60.0,
            "nodes": 30,
            "pricing": "PML",
            "operator": "CENACE",
            "currency": "USD",
            "voltage_kv": 230.0,
        },
        "ERCOT": {
            "name": "Electric Reliability Council of Texas",
            "region": "Texas 🇺🇸",
            "frequency_hz": 60.0,
            "nodes": 22,
            "pricing": "LMP",
            "operator": "ERCOT",
            "currency": "USD",
            "price_cap_usd": 5000.0,
            "voltage_kv": 345.0,
        },
        "MIBEL": {
            "name": "Mercado Ibérico de Electricidad",
            "region": "España-Portugal 🇪🇸🇵🇹",
            "frequency_hz": 50.0,
            "nodes": 20,
            "pricing": "OMIE Pool",
            "operator": "OMIE",
            "currency": "EUR",
            "voltage_kv": 400.0,
        },
    }

    # Pricing benchmarks
    GRID_PRICE_USD_MWH = 65.0        # Baseline grid price
    H2_PRICE_USD_KG = 4.50           # Green hydrogen market price
    NH3_PRICE_USD_KG = 0.45          # Ammonia market price

    # PRIMEnergeia commercial terms
    DEPLOYMENT_FEE_USD = 50_000      # Per node
    ROYALTY_RATE = 0.25              # 25% of capital rescued
    CONTRACT_MONTHS = 12             # Standard contract length

    @classmethod
    def total_addressable_nodes(cls) -> int:
        return sum(m["nodes"] for m in cls.MARKETS.values())

    @classmethod
    def projected_annual_revenue(cls, rescue_per_node_month_usd: float = 180_000) -> dict:
        """Project annual revenue across all markets."""
        projections = {}
        for market_id, market in cls.MARKETS.items():
            annual_rescue = market["nodes"] * rescue_per_node_month_usd * 12
            projections[market_id] = {
                "nodes": market["nodes"],
                "annual_rescue_usd": annual_rescue,
                "prime_revenue_usd": annual_rescue * cls.ROYALTY_RATE,
                "currency": market["currency"],
            }
        return projections


class EngineConstants:
    """Engine fleet specifications — AICE, PEM, HYP."""

    ENGINES = {
        "AICE-G1": {
            "name": "Ammonia Internal Combustion Engine",
            "fuel": "NH₃",
            "rated_kw": 335.0,
            "efficiency": 0.44,
            "waste_heat_fraction": 0.65,
            "fuel_consumption_kg_kwh": 3.6 / (0.44 * 18.6),  # kg NH₃ per kWh
            "emissions": "Near-zero NOx with SCR",
            "sbu": "PRIME Power",
        },
        "PEM-PB-50": {
            "name": "PEM Fuel Cell Stack",
            "fuel": "H₂",
            "rated_kw": 50.0,
            "efficiency": 0.55,
            "waste_heat_fraction": 0.40,
            "fuel_consumption_kg_kwh": 3.6 / (0.55 * 120.0),  # kg H₂ per kWh
            "emissions": "Zero (H₂O only)",
            "sbu": "PRIME Power",
        },
        "HY-P100": {
            "name": "Hydrogen Gas Turbine",
            "fuel": "H₂",
            "rated_kw": 100.0,
            "efficiency": 0.38,
            "waste_heat_fraction": 0.80,
            "fuel_consumption_kg_kwh": 3.6 / (0.38 * 120.0),  # kg H₂ per kWh
            "emissions": "Zero CO₂, trace NOx",
            "sbu": "PRIME Power",
        },
    }

    @classmethod
    def total_fleet_capacity_kw(cls, n_aice: int = 3, n_pem: int = 5, n_hyp: int = 2) -> float:
        return (n_aice * cls.ENGINES["AICE-G1"]["rated_kw"] +
                n_pem * cls.ENGINES["PEM-PB-50"]["rated_kw"] +
                n_hyp * cls.ENGINES["HY-P100"]["rated_kw"])

    @classmethod
    def fuel_cost_per_kwh(cls, engine_id: str, fuel_price_usd_kg: float = None) -> float:
        """Calculate fuel cost per kWh of electrical output."""
        eng = cls.ENGINES[engine_id]
        if fuel_price_usd_kg is None:
            if eng["fuel"] == "H₂":
                fuel_price_usd_kg = 4.50
            else:
                fuel_price_usd_kg = 0.45
        return eng["fuel_consumption_kg_kwh"] * fuel_price_usd_kg
