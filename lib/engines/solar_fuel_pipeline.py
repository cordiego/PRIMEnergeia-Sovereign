"""
Granas Solar Fuel Pipeline — Sun → H₂ → NH₃ → Engine
=======================================================
Complete physics-based pipeline modeling Granas perovskite/TOPCon
solar modules producing electricity → PEM electrolysis (H₂O → H₂)
→ optional Haber-Bosch (H₂ + N₂ → NH₃) → fuel dispatch to engines.

Pipeline:
  ☀️ Solar Irradiance
  → 🔋 Granas 2.1×3.4m Modules (50S×2P, ~2,092 W STC each)
  → ⚡ DC Bus (inverter/rectifier losses)
  → 💧 PEM Electrolyzer Stack (H₂O → H₂ + ½O₂)
  → ⚗️ Haber-Bosch Reactor (3H₂ + N₂ → 2NH₃) [optional]
  → 🚀 Engine Fuel Tanks:
       A-ICE-G1  (NH₃, 335 kW)
       PEM-PB-50 (H₂,  50  kW)
       HY-P100   (H₂, 100  kW)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

# ─────────────────────────────────────────────────────────────
# Physical Constants
# ─────────────────────────────────────────────────────────────
F = 96_485.0          # Faraday constant (C/mol)
R_GAS = 8.314        # Universal gas constant (J/mol·K)
MW_H2 = 2.016e-3     # Molar mass H₂ (kg/mol)
MW_NH3 = 17.031e-3   # Molar mass NH₃ (kg/mol)
MW_H2O = 18.015e-3   # Molar mass H₂O (kg/mol)
MW_N2 = 28.014e-3    # Molar mass N₂ (kg/mol)
LHV_H2 = 33.33       # Lower heating value H₂ (kWh/kg)
HHV_H2 = 39.4        # Higher heating value H₂ (kWh/kg)
LHV_NH3 = 5.17       # Lower heating value NH₃ (kWh/kg)
HHV_NH3 = 6.25       # Higher heating value NH₃ (kWh/kg)
STOICH_H2O = 9.0     # kg H₂O per kg H₂ produced
HOURS_PER_YEAR = 8760


# ═══════════════════════════════════════════════════════════════
# Granas Module Structure Feed
# ═══════════════════════════════════════════════════════════════
@dataclass
class GranasStructureFeed:
    """
    Granas 2.1m × 3.4m module structure feeding into the fuel pipeline.

    Exposes the physical architecture: diamond vertex tessellation,
    CFRP skeleton, 50S×2P electrical configuration, and per-module
    power characteristics that determine total charging capacity.
    """
    # ── Blueprint Geometry ────────────────────────────────────
    module_width_m: float = 2.1
    module_height_m: float = 3.4
    active_fraction: float = 0.874       # 87.4% active (CFRP skeleton ~12.6%)
    n_subcells: int = 100                # 10×10 grid
    n_series: int = 50
    n_parallel: int = 2
    subcell_width_cm: float = 21.0
    subcell_height_cm: float = 34.0

    # ── Cell Parameters (tandem perovskite/TOPCon) ────────────
    cell_voc_mV: float = 1132.0          # Voc per cell (mV)
    cell_jsc_mA_cm2: float = 37.0        # Jsc per cell (mA/cm²)
    fill_factor: float = 0.80
    tandem_pce_pct: float = 34.65        # Combined tandem PCE (%)
    perovskite_pce_pct: float = 20.78
    topcon_pce_pct: float = 13.80

    # ── Operating Conditions ──────────────────────────────────
    irradiance_W_m2: float = 1000.0      # STC
    capacity_factor: float = 0.22        # Mexico average

    # ── Physical Properties ───────────────────────────────────
    weight_per_m2_kg: float = 5.0        # CFRP + cell stack
    junction_temp_C: float = 42.0        # Green cooling

    @property
    def total_area_m2(self) -> float:
        return self.module_width_m * self.module_height_m  # 7.14 m²

    @property
    def active_area_m2(self) -> float:
        return self.total_area_m2 * self.active_fraction  # 6.24 m²

    @property
    def active_area_cm2(self) -> float:
        return self.active_area_m2 * 10_000

    @property
    def subcell_active_cm2(self) -> float:
        return self.subcell_width_cm * self.subcell_height_cm * self.active_fraction

    @property
    def module_voc_V(self) -> float:
        """Module open-circuit voltage (50 cells series)."""
        return self.n_series * self.cell_voc_mV / 1000.0

    @property
    def cell_isc_A(self) -> float:
        """Cell short-circuit current."""
        return self.cell_jsc_mA_cm2 * self.subcell_active_cm2 / 1000.0

    @property
    def module_isc_A(self) -> float:
        """Module short-circuit current (2 parallel strings)."""
        return self.n_parallel * self.cell_isc_A

    @property
    def peak_power_W(self) -> float:
        """Module peak power at STC (W)."""
        return (self.tandem_pce_pct / 100.0) * self.irradiance_W_m2 * self.active_area_m2

    @property
    def annual_energy_kWh(self) -> float:
        """Annual energy production per module (kWh)."""
        return self.peak_power_W * self.capacity_factor * HOURS_PER_YEAR / 1000.0

    @property
    def weight_kg(self) -> float:
        return self.weight_per_m2_kg * self.total_area_m2

    def structure_summary(self) -> Dict[str, Any]:
        """Full structure summary for dashboard display."""
        return {
            "module_dimensions": f"{self.module_width_m} × {self.module_height_m} m",
            "total_area_m2": round(self.total_area_m2, 2),
            "active_area_m2": round(self.active_area_m2, 2),
            "active_fraction_pct": round(self.active_fraction * 100, 1),
            "n_subcells": self.n_subcells,
            "tessellation": "10×10 grid, 21×34 cm sub-cells",
            "config": f"{self.n_series}S × {self.n_parallel}P",
            "cell_voc_mV": round(self.cell_voc_mV, 1),
            "module_voc_V": round(self.module_voc_V, 2),
            "cell_jsc_mA_cm2": round(self.cell_jsc_mA_cm2, 1),
            "cell_isc_A": round(self.cell_isc_A, 2),
            "module_isc_A": round(self.module_isc_A, 2),
            "fill_factor": self.fill_factor,
            "tandem_pce_pct": round(self.tandem_pce_pct, 2),
            "perovskite_pce_pct": round(self.perovskite_pce_pct, 2),
            "topcon_pce_pct": round(self.topcon_pce_pct, 2),
            "peak_power_W": round(self.peak_power_W, 1),
            "annual_energy_kWh": round(self.annual_energy_kWh, 1),
            "junction_temp_C": self.junction_temp_C,
            "weight_kg": round(self.weight_kg, 1),
        }


# ═══════════════════════════════════════════════════════════════
# PEM Solar Electrolyzer
# ═══════════════════════════════════════════════════════════════
@dataclass
class SolarElectrolyzer:
    """
    PEM electrolysis stack driven by Granas solar input.

    Reaction: 2H₂O(l) → 2H₂(g) + O₂(g)
    E° = 1.229 V | ΔG° = +237.2 kJ/mol

    Stack: Nafion 212 membrane, IrO₂ anode, Pt/C cathode.
    """
    n_cells: int = 80                    # Cells in stack
    active_area_cm2: float = 500.0       # Active area per cell (cm²)
    temperature_C: float = 80            # Operating temperature (°C)
    pressure_bar: float = 30             # H₂ outlet pressure (bar)
    membrane_thickness_um: float = 50    # Nafion 212 (μm)
    membrane_conductivity: float = 0.10  # S/cm at 80°C
    contact_resistance: float = 0.02     # Ω·cm²
    bop_efficiency: float = 0.92         # Balance of plant efficiency

    @property
    def T_K(self) -> float:
        return self.temperature_C + 273.15

    def reversible_voltage(self) -> float:
        """Nernst reversible voltage (V)."""
        E0 = 1.229
        delta_s = -163.0  # J/(mol·K)
        e_rev = (E0
                 - (delta_s / (2 * F)) * (self.T_K - 298.15)
                 + (R_GAS * self.T_K / (2 * F)) * np.log(self.pressure_bar))
        return e_rev

    def thermoneutral_voltage(self) -> float:
        """Thermoneutral voltage (V)."""
        delta_h = 286e3 - 10.0 * (self.T_K - 298.15)
        return delta_h / (2 * F)

    def cell_voltage(self, current_density_A_cm2: float) -> float:
        """Total cell voltage at given current density."""
        j = current_density_A_cm2
        e_rev = self.reversible_voltage()

        # Activation overpotential (Tafel kinetics)
        eta_act_a = 0.060 * np.log10(max(j, 1e-10) / 1e-7)   # IrO₂ OER
        eta_act_c = 0.030 * np.log10(max(j, 1e-10) / 1e-3)   # Pt/C HER
        eta_act = max(0, eta_act_a) + max(0, eta_act_c)

        # Ohmic overpotential
        r_mem = (self.membrane_thickness_um * 1e-4) / self.membrane_conductivity
        eta_ohm = j * (r_mem + self.contact_resistance)

        # Mass transport
        j_lim = 4.0  # A/cm²
        if j < j_lim * 0.99:
            eta_mt = (R_GAS * self.T_K / (2 * F)) * np.log(j_lim / max(j_lim - j, 0.04))
        else:
            eta_mt = 0.5

        return e_rev + eta_act + eta_ohm + eta_mt

    def cell_efficiency(self, current_density_A_cm2: float) -> float:
        """Cell-level voltage efficiency (%)."""
        v_cell = self.cell_voltage(current_density_A_cm2)
        e_tn = self.thermoneutral_voltage()
        return min(100, e_tn / v_cell * 100) if v_cell > 0 else 0

    def system_efficiency(self, current_density_A_cm2: float) -> float:
        """System-level efficiency including BoP (%)."""
        return self.cell_efficiency(current_density_A_cm2) * self.bop_efficiency

    def h2_production(self, power_kW: float) -> Dict[str, float]:
        """
        Calculate H₂ production from available electrical power.

        Returns dict with all production metrics.
        """
        # Find operating current density from available power
        # P = V_cell × I_total = V_cell × j × A_cell × n_cells
        # Iterate to find j matching available power
        j_opt = self._find_current_density(power_kW)
        v_cell = self.cell_voltage(j_opt)
        I_total = j_opt * self.active_area_cm2 * self.n_cells  # Amperes
        actual_power_kW = v_cell * I_total / 1000

        # Faraday's law
        mol_h2_s = I_total / (2 * F)
        h2_kg_h = mol_h2_s * MW_H2 * 3600
        h2_kg_day = h2_kg_h * 24
        h2o_kg_h = h2_kg_h * STOICH_H2O
        kwh_per_kg_h2 = actual_power_kW / max(h2_kg_h, 1e-10)

        cell_eff = self.cell_efficiency(j_opt)
        sys_eff = self.system_efficiency(j_opt)

        return {
            "current_density_A_cm2": round(j_opt, 3),
            "cell_voltage_V": round(v_cell, 4),
            "stack_current_A": round(I_total, 1),
            "power_consumed_kW": round(actual_power_kW, 2),
            "h2_kg_h": round(h2_kg_h, 4),
            "h2_kg_day": round(h2_kg_day, 2),
            "h2o_consumption_kg_h": round(h2o_kg_h, 2),
            "kwh_per_kg_h2": round(kwh_per_kg_h2, 2),
            "cell_efficiency_pct": round(cell_eff, 2),
            "system_efficiency_pct": round(sys_eff, 2),
            "o2_kg_h": round(h2_kg_h * 8, 3),    # O₂ co-product
            "n_cells": self.n_cells,
            "stack_temp_C": self.temperature_C,
            "h2_pressure_bar": self.pressure_bar,
        }

    def _find_current_density(self, power_kW: float) -> float:
        """Find current density that consumes given power (bisection)."""
        j_low, j_high = 0.01, 3.8
        target_W = power_kW * 1000

        for _ in range(50):
            j_mid = (j_low + j_high) / 2
            v = self.cell_voltage(j_mid)
            p = v * j_mid * self.active_area_cm2 * self.n_cells
            if p < target_W:
                j_low = j_mid
            else:
                j_high = j_mid

        return (j_low + j_high) / 2

    def polarization_curve(self, n_points: int = 60) -> List[Dict[str, float]]:
        """Generate polarization curve data for plotting."""
        j_arr = np.linspace(0.05, 3.5, n_points)
        results = []
        for j in j_arr:
            v = self.cell_voltage(j)
            eff = self.cell_efficiency(j)
            mol_h2 = (j * self.active_area_cm2 * self.n_cells) / (2 * F)
            h2_kg_h = mol_h2 * MW_H2 * 3600
            power_kW = v * j * self.active_area_cm2 * self.n_cells / 1000
            results.append({
                "j_A_cm2": round(float(j), 3),
                "v_cell_V": round(float(v), 4),
                "efficiency_pct": round(float(eff), 2),
                "h2_kg_h": round(float(h2_kg_h), 4),
                "power_kW": round(float(power_kW), 2),
            })
        return results


# ═══════════════════════════════════════════════════════════════
# Haber-Bosch Reactor  (H₂ + N₂ → NH₃)
# ═══════════════════════════════════════════════════════════════
@dataclass
class HaberBoschReactor:
    """
    Green Haber-Bosch NH₃ synthesis from solar H₂.

    Reaction: 3H₂ + N₂ → 2NH₃
    ΔH = -92.4 kJ/mol

    Uses electrocatalytic NRR approach (Mo-N₄ single-site catalyst)
    at ambient temperature/moderate pressure for decentralized production.
    """
    conversion_efficiency: float = 0.85   # H₂ → NH₃ conversion (%)
    energy_per_kg_nh3_kWh: float = 0.50   # Electrical energy for NRR (kWh/kg NH₃)
    pressure_bar: float = 50              # Operating pressure (bar)
    temperature_C: float = 25             # Ambient NRR (vs 450°C classical HB)
    catalyst: str = "Mo-N₄/PG-MoSA-BC"   # Single-atom catalyst
    co2_emission_kg_per_t_nh3: float = 0  # Zero-carbon

    def nh3_from_h2(self, h2_kg_h: float) -> Dict[str, float]:
        """
        Calculate NH₃ production from available H₂ flow.

        Stoichiometry: 3H₂ + N₂ → 2NH₃
        Mass ratio: 6.048 kg H₂ → 34.06 kg NH₃
        Effective: 1 kg H₂ → 5.63 kg NH₃ (at 100% conversion)
        """
        # Stoichiometric mass ratio
        h2_per_nh3 = (3 * MW_H2) / (2 * MW_NH3)  # 0.1777 kg H₂ / kg NH₃
        nh3_stoich = h2_kg_h / h2_per_nh3     # Theoretical maximum
        nh3_actual = nh3_stoich * self.conversion_efficiency

        # N₂ requirement
        n2_per_nh3 = MW_N2 / (2 * MW_NH3)     # 0.822 kg N₂ / kg NH₃
        n2_kg_h = nh3_actual * n2_per_nh3

        # H₂ consumed (rest remains as H₂ product)
        h2_consumed = nh3_actual * h2_per_nh3
        h2_remaining = max(0, h2_kg_h - h2_consumed)

        # Electrical power for NRR
        power_kW = nh3_actual * self.energy_per_kg_nh3_kWh

        # Energy content
        nh3_energy_kWh_h = nh3_actual * LHV_NH3

        return {
            "h2_input_kg_h": round(h2_kg_h, 4),
            "h2_consumed_kg_h": round(h2_consumed, 4),
            "h2_remaining_kg_h": round(h2_remaining, 4),
            "n2_consumed_kg_h": round(n2_kg_h, 3),
            "nh3_produced_kg_h": round(nh3_actual, 4),
            "nh3_produced_kg_day": round(nh3_actual * 24, 2),
            "nh3_energy_kWh_h": round(nh3_energy_kWh_h, 3),
            "nrr_power_kW": round(power_kW, 3),
            "conversion_efficiency_pct": round(self.conversion_efficiency * 100, 1),
            "process_temp_C": self.temperature_C,
            "process_pressure_bar": self.pressure_bar,
            "co2_kg_per_t_nh3": self.co2_emission_kg_per_t_nh3,
            "catalyst": self.catalyst,
        }


# ═══════════════════════════════════════════════════════════════
# Engine Fuel Specs  (consumption models for each engine)
# ═══════════════════════════════════════════════════════════════
@dataclass
class EngineFuelSpec:
    """Fuel consumption model for a single engine."""
    name: str
    model: str
    fuel_type: str               # "H₂" or "NH₃"
    rated_power_kW: float
    thermal_efficiency: float    # BTE or stack efficiency
    fuel_lhv_kWh_kg: float       # LHV of fuel (kWh/kg)
    tank_capacity_kg: float      # Onboard fuel tank (kg)
    startup_time_s: float
    trl: int
    sectors: str

    @property
    def fuel_rate_kg_h(self) -> float:
        """Fuel consumption at rated power (kg/h)."""
        return self.rated_power_kW / (self.thermal_efficiency * self.fuel_lhv_kWh_kg)

    def fuel_rate_at_load(self, load_pct: float) -> float:
        """Fuel consumption at partial load (kg/h)."""
        load = max(0.05, min(1.0, load_pct / 100.0))
        # Part-load penalty: efficiency drops ~15% at 20% load
        load_eff = self.thermal_efficiency * (0.85 + 0.15 * load)
        return (self.rated_power_kW * load) / (load_eff * self.fuel_lhv_kWh_kg)

    def runtime_h(self, fuel_available_kg: float, load_pct: float = 100) -> float:
        """Hours of operation from given fuel quantity."""
        rate = self.fuel_rate_at_load(load_pct)
        return fuel_available_kg / max(rate, 1e-10)

    def fill_time_h(self, charging_rate_kg_h: float) -> float:
        """Time to fill tank from empty (hours)."""
        return self.tank_capacity_kg / max(charging_rate_kg_h, 1e-10)


# Pre-configured engine specs
ENGINE_SPECS = {
    "A-ICE-G1": EngineFuelSpec(
        name="A-ICE-G1",
        model="Ammonia ICE",
        fuel_type="NH₃",
        rated_power_kW=335.0,
        thermal_efficiency=0.42,
        fuel_lhv_kWh_kg=LHV_NH3,
        tank_capacity_kg=500.0,       # 500 kg NH₃ tank
        startup_time_s=30,
        trl=5,
        sectors="Trucks, Marine, Rail, F1",
    ),
    "PEM-PB-50": EngineFuelSpec(
        name="PEM-PB-50",
        model="PEM Fuel Cell",
        fuel_type="H₂",
        rated_power_kW=50.0,
        thermal_efficiency=0.60,
        fuel_lhv_kWh_kg=LHV_H2,
        tank_capacity_kg=5.0,         # 5 kg H₂ at 700 bar
        startup_time_s=5,
        trl=6,
        sectors="Light Vehicles, UAV, Drones",
    ),
    "HY-P100": EngineFuelSpec(
        name="HY-P100",
        model="H₂ Gas Turbine — Long Range",
        fuel_type="H₂",
        rated_power_kW=500.0,
        thermal_efficiency=0.42,
        fuel_lhv_kWh_kg=LHV_H2,
        tank_capacity_kg=200.0,       # 200 kg H₂ (long range)
        startup_time_s=120,
        trl=4,
        sectors="Trans-oceanic, Intercontinental, Long-haul Aviation",
    ),
}


# ═══════════════════════════════════════════════════════════════
# Vehicle Profiles  (how each vehicle uses Granas fuel)
# ═══════════════════════════════════════════════════════════════
@dataclass
class VehicleProfile:
    """Vehicle application profile mapping an engine to a mobility use case."""
    name: str
    vehicle_type: str              # Truck, Ship, Aircraft, Drone, F1
    emoji: str
    engine: str                    # ENGINE_SPECS key
    n_engines: int                 # Number of engines in this vehicle
    cruise_speed_kmh: float        # Cruising speed (km/h)
    drag_factor: float             # km per kWh at wheels (vehicle-specific)
    tank_scale: float              # Multiplier on engine tank capacity
    payload_kg: float              # Useful payload (kg)
    mission: str                   # Typical mission description

    def total_tank_kg(self) -> float:
        """Total fuel capacity on vehicle (kg)."""
        spec = ENGINE_SPECS[self.engine]
        return spec.tank_capacity_kg * self.tank_scale * self.n_engines

    def total_power_kW(self) -> float:
        """Total propulsion power (kW)."""
        return ENGINE_SPECS[self.engine].rated_power_kW * self.n_engines

    def fuel_rate_cruise_kg_h(self, load_pct: float = 75) -> float:
        """Fuel consumption at cruise (kg/h)."""
        spec = ENGINE_SPECS[self.engine]
        return spec.fuel_rate_at_load(load_pct) * self.n_engines

    def range_km(self, load_pct: float = 75) -> float:
        """Maximum range at cruise load (km)."""
        spec = ENGINE_SPECS[self.engine]
        fuel_kg = self.total_tank_kg()
        rate_kg_h = self.fuel_rate_cruise_kg_h(load_pct)
        runtime_h = fuel_kg / max(rate_kg_h, 1e-10)
        return runtime_h * self.cruise_speed_kmh

    def endurance_h(self, load_pct: float = 75) -> float:
        """Maximum endurance at cruise (hours)."""
        return self.total_tank_kg() / max(self.fuel_rate_cruise_kg_h(load_pct), 1e-10)

    def modules_for_daily_mission(self, missions_per_day: float = 1.0) -> int:
        """Number of Granas modules needed to fuel daily missions."""
        spec = ENGINE_SPECS[self.engine]
        fuel_per_mission = self.total_tank_kg() * 0.8  # 80% depth of discharge
        daily_fuel_kg = fuel_per_mission * missions_per_day
        # At peak production (100 modules ≈ estimates from hub)
        # Scale linearly: each module produces ~proportional H₂/NH₃
        # Rough: 1 module STC → ~0.02 kg H₂/h or ~0.06 kg NH₃/h  (from pipeline)
        if spec.fuel_type == "H₂":
            kg_per_module_h = 0.02   # approximate from PEM at 2 kW input
        else:
            kg_per_module_h = 0.06   # approximate NH₃ from HB
        sun_hours = 8  # effective sun hours per day
        daily_per_module = kg_per_module_h * sun_hours
        return max(1, int(np.ceil(daily_fuel_kg / max(daily_per_module, 1e-10))))

    def profile_summary(self) -> Dict[str, Any]:
        """Full vehicle profile for dashboard display."""
        spec = ENGINE_SPECS[self.engine]
        return {
            "vehicle": self.name,
            "type": self.vehicle_type,
            "emoji": self.emoji,
            "engine": self.engine,
            "engine_model": spec.model,
            "n_engines": self.n_engines,
            "total_power_kW": round(self.total_power_kW(), 1),
            "fuel_type": spec.fuel_type,
            "total_tank_kg": round(self.total_tank_kg(), 1),
            "cruise_speed_kmh": self.cruise_speed_kmh,
            "fuel_rate_cruise_kg_h": round(self.fuel_rate_cruise_kg_h(), 3),
            "range_km": round(self.range_km(), 0),
            "endurance_h": round(self.endurance_h(), 1),
            "payload_kg": self.payload_kg,
            "mission": self.mission,
            "granas_modules_daily": self.modules_for_daily_mission(),
            "trl": spec.trl,
        }


# Pre-configured vehicle fleet
VEHICLE_FLEET = {
    "Long-Haul Truck": VehicleProfile(
        name="Long-Haul Truck",
        vehicle_type="Truck",
        emoji="🚛",
        engine="A-ICE-G1",
        n_engines=1,
        cruise_speed_kmh=90,
        drag_factor=0.8,
        tank_scale=1.0,               # 500 kg NH₃
        payload_kg=25_000,
        mission="Mexico City → Monterrey (900 km) overnight freight",
    ),
    "Trans-oceanic Vessel": VehicleProfile(
        name="Trans-oceanic Vessel",
        vehicle_type="Ship",
        emoji="🚢",
        engine="HY-P100",
        n_engines=8,                   # 8× 500 kW = 4 MW
        cruise_speed_kmh=30,           # ~16 knots
        drag_factor=1.2,
        tank_scale=5.0,               # 8,000 kg H₂ total
        payload_kg=50_000,
        mission="Veracruz → Rotterdam trans-Atlantic (9,000 km)",
    ),
    "Regional Aircraft": VehicleProfile(
        name="Regional Aircraft",
        vehicle_type="Aircraft",
        emoji="✈️",
        engine="HY-P100",
        n_engines=2,                   # 2× 500 kW = 1 MW
        cruise_speed_kmh=550,
        drag_factor=1.5,
        tank_scale=1.5,               # 600 kg H₂ total
        payload_kg=5_000,             # 50 pax
        mission="CDMX → Cancún (1,500 km) zero-emission regional flight",
    ),
    "Surveillance Drone": VehicleProfile(
        name="Surveillance Drone",
        vehicle_type="Drone",
        emoji="🛸",
        engine="PEM-PB-50",
        n_engines=1,
        cruise_speed_kmh=80,
        drag_factor=3.5,
        tank_scale=1.0,               # 5 kg H₂
        payload_kg=15,
        mission="8-hour persistent ISR / agricultural monitoring",
    ),
    "Zero-Carbon F1": VehicleProfile(
        name="Zero-Carbon F1",
        vehicle_type="F1",
        emoji="🏎️",
        engine="A-ICE-G1",
        n_engines=1,
        cruise_speed_kmh=220,
        drag_factor=0.5,
        tank_scale=0.2,               # 100 kg NH₃ (race-weight)
        payload_kg=80,                # Driver
        mission="305 km Grand Prix — zero-carbon lap record",
    ),
}


# ═══════════════════════════════════════════════════════════════
# PEM Transport Integration (fuel cell → existing transport)
# ═══════════════════════════════════════════════════════════════
@dataclass
class PEMTransportIntegration:
    """
    PEM fuel cell integration into existing transport platforms.

    Models how PEM-PB-50 stacks (50 kW each) scale and integrate into
    real-world vehicles, replacing ICE/battery powertrains with
    Granas H₂ fuel cell systems.
    """
    name: str
    category: str
    emoji: str
    base_platform: str
    n_stacks: int                      # PEM-PB-50 stacks (50 kW each)
    stack_efficiency: float
    h2_tank_kg: float
    tank_pressure_bar: int
    curb_weight_kg: float
    payload_kg: float
    cruise_speed_kmh: float
    energy_consumption_kWh_km: float   # Energy at wheels per km
    refuel_time_min: float
    retrofit_complexity: str
    existing_platforms: str

    @property
    def total_power_kW(self) -> float:
        return self.n_stacks * 50.0

    @property
    def usable_power_kW(self) -> float:
        return self.total_power_kW * self.stack_efficiency

    @property
    def range_km(self) -> float:
        h2_energy = self.h2_tank_kg * LHV_H2
        useful_energy = h2_energy * self.stack_efficiency
        return useful_energy / max(self.energy_consumption_kWh_km, 1e-10)

    @property
    def fuel_rate_kg_h(self) -> float:
        power_cruise = self.energy_consumption_kWh_km * self.cruise_speed_kmh
        return power_cruise / (self.stack_efficiency * LHV_H2)

    @property
    def endurance_h(self) -> float:
        return self.h2_tank_kg / max(self.fuel_rate_kg_h, 1e-10)

    @property
    def km_per_kg_h2(self) -> float:
        return self.range_km / max(self.h2_tank_kg, 1e-10)

    @property
    def co2_avoided_per_fill_kg(self) -> float:
        diesel_equiv_L = self.range_km * 0.08
        return diesel_equiv_L * 2.68

    def granas_modules_per_fill(self) -> int:
        h2_per_module_day = 0.02 * 8
        return max(1, int(np.ceil(self.h2_tank_kg / max(h2_per_module_day, 1e-10))))

    def profile_summary(self) -> Dict[str, Any]:
        return {
            "name": self.name, "category": self.category, "emoji": self.emoji,
            "base_platform": self.base_platform,
            "n_stacks": self.n_stacks,
            "total_power_kW": round(self.total_power_kW, 0),
            "stack_efficiency_pct": round(self.stack_efficiency * 100, 1),
            "h2_tank_kg": self.h2_tank_kg,
            "tank_pressure_bar": self.tank_pressure_bar,
            "range_km": round(self.range_km, 0),
            "endurance_h": round(self.endurance_h, 1),
            "fuel_rate_kg_h": round(self.fuel_rate_kg_h, 3),
            "km_per_kg_h2": round(self.km_per_kg_h2, 1),
            "refuel_time_min": self.refuel_time_min,
            "co2_avoided_kg": round(self.co2_avoided_per_fill_kg, 1),
            "granas_modules_per_fill": self.granas_modules_per_fill(),
            "retrofit_complexity": self.retrofit_complexity,
            "existing_platforms": self.existing_platforms,
        }


PEM_TRANSPORT_FLEET = {
    "H₂ Sedan": PEMTransportIntegration(
        name="H₂ Sedan", category="Sedan", emoji="🚗",
        base_platform="Mid-size sedan (Mirai-class)",
        n_stacks=2, stack_efficiency=0.60, h2_tank_kg=5.6,
        tank_pressure_bar=700, curb_weight_kg=1_950, payload_kg=400,
        cruise_speed_kmh=110, energy_consumption_kWh_km=0.18,
        refuel_time_min=5, retrofit_complexity="Medium",
        existing_platforms="Toyota Mirai, Hyundai Nexo, Honda Clarity",
    ),
    "H₂ SUV": PEMTransportIntegration(
        name="H₂ SUV", category="SUV", emoji="🚙",
        base_platform="Full-size SUV / pickup",
        n_stacks=3, stack_efficiency=0.58, h2_tank_kg=8.0,
        tank_pressure_bar=700, curb_weight_kg=2_400, payload_kg=600,
        cruise_speed_kmh=100, energy_consumption_kWh_km=0.24,
        refuel_time_min=6, retrofit_complexity="Medium",
        existing_platforms="Hyundai Nexo XL, BMW iX5 H₂, Land Rover FCEV",
    ),
    "City Bus": PEMTransportIntegration(
        name="City Bus", category="Bus", emoji="🚌",
        base_platform="12m city transit bus",
        n_stacks=4, stack_efficiency=0.55, h2_tank_kg=35.0,
        tank_pressure_bar=350, curb_weight_kg=13_500, payload_kg=7_000,
        cruise_speed_kmh=40, energy_consumption_kWh_km=0.80,
        refuel_time_min=12, retrofit_complexity="Low",
        existing_platforms="MAN Lion's City H₂, Toyota Sora, CaetanoBus",
    ),
    "Delivery Van": PEMTransportIntegration(
        name="Delivery Van", category="Van", emoji="🚐",
        base_platform="Last-mile delivery van",
        n_stacks=2, stack_efficiency=0.58, h2_tank_kg=6.0,
        tank_pressure_bar=700, curb_weight_kg=3_200, payload_kg=1_500,
        cruise_speed_kmh=60, energy_consumption_kWh_km=0.30,
        refuel_time_min=5, retrofit_complexity="Low",
        existing_platforms="Mercedes Sprinter FCEV, Stellantis, Renault Master H₂",
    ),
    "Warehouse Forklift": PEMTransportIntegration(
        name="Warehouse Forklift", category="Forklift", emoji="🏗️",
        base_platform="3-ton counterbalance forklift",
        n_stacks=1, stack_efficiency=0.55, h2_tank_kg=1.5,
        tank_pressure_bar=350, curb_weight_kg=4_500, payload_kg=3_000,
        cruise_speed_kmh=15, energy_consumption_kWh_km=0.50,
        refuel_time_min=3, retrofit_complexity="Low",
        existing_platforms="Toyota Material Handling, Plug Power, Linde H₂",
    ),
    "Commuter Train": PEMTransportIntegration(
        name="Commuter Train", category="Train", emoji="🚆",
        base_platform="2-car regional DMU replacement",
        n_stacks=8, stack_efficiency=0.55, h2_tank_kg=80.0,
        tank_pressure_bar=350, curb_weight_kg=75_000, payload_kg=15_000,
        cruise_speed_kmh=80, energy_consumption_kWh_km=2.50,
        refuel_time_min=20, retrofit_complexity="High",
        existing_platforms="Alstom Coradia iLint, Siemens Mireo Plus H",
    ),
    "Harbor Ferry": PEMTransportIntegration(
        name="Harbor Ferry", category="Ferry", emoji="⛴️",
        base_platform="50-pax harbor/river ferry",
        n_stacks=6, stack_efficiency=0.55, h2_tank_kg=50.0,
        tank_pressure_bar=350, curb_weight_kg=40_000, payload_kg=5_000,
        cruise_speed_kmh=20, energy_consumption_kWh_km=3.00,
        refuel_time_min=15, retrofit_complexity="Medium",
        existing_platforms="Norled MF Hydra, CMB Hydrocat, FPS Waal",
    ),
    "Airport Shuttle": PEMTransportIntegration(
        name="Airport Shuttle", category="Shuttle", emoji="🚎",
        base_platform="Autonomous PRT / shuttle",
        n_stacks=1, stack_efficiency=0.58, h2_tank_kg=3.0,
        tank_pressure_bar=350, curb_weight_kg=3_000, payload_kg=1_200,
        cruise_speed_kmh=30, energy_consumption_kWh_km=0.25,
        refuel_time_min=3, retrofit_complexity="Low",
        existing_platforms="Toyota e-Palette H₂, Navya, EasyMile",
    ),
}


# ═══════════════════════════════════════════════════════════════
# Granas Charging Hub  (multi-module solar field → fuel)
# ═══════════════════════════════════════════════════════════════
@dataclass
class GranasChargingHub:
    """
    A field of Granas modules powering a hydrogen/ammonia production facility.

    Wires together:
      Granas Structure → Solar DC → Electrolyzer → H₂ → Haber-Bosch → NH₃ → Engines
    """
    n_modules: int = 100                  # Number of Granas 2.1×3.4m modules
    module: GranasStructureFeed = field(default_factory=GranasStructureFeed)
    electrolyzer: SolarElectrolyzer = field(default_factory=SolarElectrolyzer)
    reactor: HaberBoschReactor = field(default_factory=HaberBoschReactor)
    mode: str = "H₂ + NH₃"              # "H₂ Only", "H₂ + NH₃", "Full Fleet"

    # ── Power conversion efficiencies ─────────────────────────
    inverter_efficiency: float = 0.975    # DC-AC inverter
    rectifier_efficiency: float = 0.98    # AC-DC rectifier
    dc_dc_efficiency: float = 0.985       # DC-DC converter to electrolyzer
    compression_efficiency: float = 0.92  # H₂ compression to storage pressure

    # ── Storage ───────────────────────────────────────────────
    h2_tank_capacity_kg: float = 500.0    # H₂ storage (kg, 350 bar)
    nh3_tank_capacity_kg: float = 5000.0  # NH₃ storage (kg, 10 bar)
    h2_tank_level_kg: float = 0.0         # Current H₂ buffer (kg)
    nh3_tank_level_kg: float = 0.0        # Current NH₃ buffer (kg)

    # ── Solar fraction to electrolysis ────────────────────────
    solar_to_h2_fraction: float = 0.80    # % of solar power → electrolysis (rest → grid)

    def total_solar_capacity_kW(self) -> float:
        """Total peak solar capacity (kW)."""
        return self.n_modules * self.module.peak_power_W / 1000.0

    def total_solar_area_m2(self) -> float:
        """Total solar field area (m²)."""
        return self.n_modules * self.module.total_area_m2

    def total_solar_area_ha(self) -> float:
        """Total solar field area (hectares)."""
        return self.total_solar_area_m2() / 10_000

    def annual_energy_MWh(self) -> float:
        """Total annual solar energy (MWh)."""
        return self.n_modules * self.module.annual_energy_kWh / 1000.0

    def wire_efficiency(self) -> float:
        """Combined power conversion efficiency (solar DC → electrolyzer DC)."""
        return self.inverter_efficiency * self.rectifier_efficiency * self.dc_dc_efficiency

    def effective_electrolyzer_power_kW(self) -> float:
        """Power available at electrolyzer after conversion losses (kW)."""
        solar_kW = self.total_solar_capacity_kW()
        return solar_kW * self.solar_to_h2_fraction * self.wire_efficiency()

    def _autoscale_electrolyzer(self, power_kW: float) -> None:
        """
        Auto-scale electrolyzer stack to absorb available power.

        Sizes n_cells and active_area_cm2 so the stack can absorb
        the full power input at optimal current density (~2.0 A/cm²).
        This matches the industrial-scale approach in the PRIMEnergeia
        H₂ page (page 8), which operates at MW-scale electrolysis.

        Rule: P = V_cell × j × A_cell × n_cells
              → A_cell × n_cells = P / (V_cell × j)

        At j=2.0 A/cm², V_cell ≈ 1.85V:
          Stack Area = P_W / (1.85 × 2.0) = P_W / 3.7 cm²

        We distribute this across cells of 1,000 cm² each (industrial grade).
        """
        TARGET_J = 2.0         # Optimal current density (A/cm²)
        CELL_AREA = 1000.0     # Industrial PEM cell area (cm²)
        V_APPROX = 1.85        # Approximate cell voltage at 2 A/cm²

        power_W = power_kW * 1000
        if power_W < 100:
            return  # Too small to bother

        # Total stack area needed
        total_area_cm2 = power_W / (V_APPROX * TARGET_J)

        # Number of cells (min 10, max 500 per stack)
        n_cells = max(10, min(500, int(total_area_cm2 / CELL_AREA)))

        # Adjust cell area to exactly match
        if n_cells > 0:
            actual_cell_area = total_area_cm2 / n_cells
            actual_cell_area = max(200, min(5000, actual_cell_area))  # Clamp
        else:
            actual_cell_area = CELL_AREA

        self.electrolyzer.n_cells = n_cells
        self.electrolyzer.active_area_cm2 = actual_cell_area

    def run_pipeline(self, irradiance_factor: float = 1.0) -> Dict[str, Any]:
        """
        Execute the full solar-to-fuel pipeline at a given irradiance factor.

        Parameters
        ----------
        irradiance_factor : float
            Fraction of peak irradiance (0–1). 1.0 = STC (1000 W/m²).

        Returns
        -------
        Dict with complete pipeline metrics.
        """
        # ── Stage 1: Granas Solar Field ──────────────────────
        solar_kW = self.total_solar_capacity_kW() * irradiance_factor
        solar_annual_MWh = self.annual_energy_MWh() * irradiance_factor

        # ── Stage 2: Power Conversion Losses ─────────────────
        wire_eff = self.wire_efficiency()
        electrolyzer_kW = solar_kW * self.solar_to_h2_fraction * wire_eff
        grid_export_kW = solar_kW * (1 - self.solar_to_h2_fraction)
        conversion_loss_kW = solar_kW * self.solar_to_h2_fraction * (1 - wire_eff)

        # ── Stage 3: PEM Electrolysis (H₂O → H₂) ────────────
        # Auto-scale electrolyzer stack to match available power
        # (page 8 operates at MW scale — stack must grow with hub)
        if electrolyzer_kW > 0.1:
            self._autoscale_electrolyzer(electrolyzer_kW)
            h2_data = self.electrolyzer.h2_production(electrolyzer_kW)
        else:
            h2_data = {
                "current_density_A_cm2": 0, "cell_voltage_V": 0,
                "stack_current_A": 0, "power_consumed_kW": 0,
                "h2_kg_h": 0, "h2_kg_day": 0, "h2o_consumption_kg_h": 0,
                "kwh_per_kg_h2": 0, "cell_efficiency_pct": 0,
                "system_efficiency_pct": 0, "o2_kg_h": 0,
                "n_cells": self.electrolyzer.n_cells,
                "stack_temp_C": self.electrolyzer.temperature_C,
                "h2_pressure_bar": self.electrolyzer.pressure_bar,
            }

        h2_kg_h = h2_data["h2_kg_h"]
        h2_after_compression = h2_kg_h  # mass conserved, energy cost tracked

        # ── Stage 4: Haber-Bosch (H₂ → NH₃) [optional] ──────
        if self.mode in ("H₂ + NH₃", "Full Fleet"):
            # Split H₂: send fraction to HB, keep rest as H₂ fuel
            h2_to_hb_fraction = 0.50 if self.mode == "Full Fleet" else 0.60
            h2_to_hb = h2_kg_h * h2_to_hb_fraction
            h2_direct = h2_kg_h * (1 - h2_to_hb_fraction)
            nh3_data = self.reactor.nh3_from_h2(h2_to_hb)
            # Any H₂ not converted returns to H₂ pool
            h2_direct += nh3_data["h2_remaining_kg_h"]
        else:
            h2_direct = h2_kg_h
            h2_to_hb = 0
            nh3_data = {
                "h2_input_kg_h": 0, "h2_consumed_kg_h": 0,
                "h2_remaining_kg_h": 0, "n2_consumed_kg_h": 0,
                "nh3_produced_kg_h": 0, "nh3_produced_kg_day": 0,
                "nh3_energy_kWh_h": 0, "nrr_power_kW": 0,
                "conversion_efficiency_pct": 0, "process_temp_C": 0,
                "process_pressure_bar": 0, "co2_kg_per_t_nh3": 0,
                "catalyst": "N/A",
            }

        nh3_kg_h = nh3_data["nh3_produced_kg_h"]

        # ── Stage 5: Engine Fuel Dispatch ─────────────────────
        engine_readiness = {}
        for name, spec in ENGINE_SPECS.items():
            fuel_available = nh3_kg_h if spec.fuel_type == "NH₃" else h2_direct
            rate = spec.fuel_rate_kg_h
            fill_time = spec.fill_time_h(fuel_available)
            runtime_day = fuel_available * 24 / max(rate, 1e-10) if fuel_available > 0 else 0
            fuel_cost_h = fuel_available * (3.50 if spec.fuel_type == "H₂" else 0.80) if fuel_available > 0 else 0

            engine_readiness[name] = {
                "engine": name,
                "model": spec.model,
                "fuel_type": spec.fuel_type,
                "rated_power_kW": spec.rated_power_kW,
                "fuel_rate_rated_kg_h": round(rate, 3),
                "fuel_available_kg_h": round(fuel_available, 4),
                "tank_capacity_kg": spec.tank_capacity_kg,
                "fill_time_h": round(fill_time, 2),
                "runtime_from_1day_charge_h": round(runtime_day, 2),
                "trl": spec.trl,
                "sectors": spec.sectors,
            }

        # ── Overall Efficiencies ──────────────────────────────
        solar_to_wire_eff = wire_eff * 100
        wire_to_h2_eff = h2_data["system_efficiency_pct"]
        overall_h2_eff = solar_to_wire_eff * wire_to_h2_eff / 100 if wire_to_h2_eff > 0 else 0

        if nh3_kg_h > 0 and h2_kg_h > 0:
            hb_eff = (nh3_kg_h * LHV_NH3) / (h2_to_hb * LHV_H2) * 100
        else:
            hb_eff = 0

        h2_energy_kWh_h = h2_direct * LHV_H2
        nh3_energy_kWh_h = nh3_kg_h * LHV_NH3
        total_fuel_energy = h2_energy_kWh_h + nh3_energy_kWh_h
        overall_solar_to_fuel = (total_fuel_energy / max(solar_kW, 1e-10)) * 100

        return {
            # ── Granas Structure Feed ─────────────────────────
            "granas_structure": self.module.structure_summary(),
            "n_modules": self.n_modules,
            "field_area_m2": round(self.total_solar_area_m2(), 1),
            "field_area_ha": round(self.total_solar_area_ha(), 3),

            # ── Solar ─────────────────────────────────────────
            "solar_peak_kW": round(solar_kW, 2),
            "solar_annual_MWh": round(solar_annual_MWh, 2),
            "irradiance_factor": irradiance_factor,

            # ── Power Conversion ──────────────────────────────
            "wire_efficiency_pct": round(solar_to_wire_eff, 2),
            "electrolyzer_input_kW": round(electrolyzer_kW, 2),
            "grid_export_kW": round(grid_export_kW, 2),
            "conversion_loss_kW": round(conversion_loss_kW, 2),

            # ── Electrolysis ──────────────────────────────────
            "electrolysis": h2_data,

            # ── Haber-Bosch ───────────────────────────────────
            "haber_bosch": nh3_data,

            # ── Fuel Totals ───────────────────────────────────
            "h2_output_kg_h": round(h2_direct, 4),
            "h2_output_kg_day": round(h2_direct * 24, 2),
            "nh3_output_kg_h": round(nh3_kg_h, 4),
            "nh3_output_kg_day": round(nh3_kg_h * 24, 2),
            "h2_energy_kWh_h": round(h2_energy_kWh_h, 2),
            "nh3_energy_kWh_h": round(nh3_energy_kWh_h, 2),

            # ── Efficiencies ──────────────────────────────────
            "solar_to_wire_eff_pct": round(solar_to_wire_eff, 2),
            "wire_to_h2_eff_pct": round(wire_to_h2_eff, 2),
            "overall_h2_eff_pct": round(overall_h2_eff, 2),
            "hb_conversion_eff_pct": round(hb_eff, 2),
            "overall_solar_to_fuel_pct": round(overall_solar_to_fuel, 2),

            # ── Engine Readiness ──────────────────────────────
            "engines": engine_readiness,

            # ── Storage ───────────────────────────────────────
            "h2_tank_capacity_kg": self.h2_tank_capacity_kg,
            "nh3_tank_capacity_kg": self.nh3_tank_capacity_kg,
            "h2_fill_time_h": round(self.h2_tank_capacity_kg / max(h2_direct, 1e-10), 2),
            "nh3_fill_time_h": round(self.nh3_tank_capacity_kg / max(nh3_kg_h, 1e-10), 2),

            # ── Environmental ─────────────────────────────────
            "co2_per_kg_h2": 0.0,
            "co2_per_kg_nh3": 0.0,
            "co2_avoided_vs_smr_kg_h": round(h2_direct * 9.3, 2),
            "co2_avoided_vs_hb_kg_h": round(nh3_kg_h * 1.6, 3),

            # ── Mode ──────────────────────────────────────────
            "mode": self.mode,
        }

    def hourly_profile(self, n_hours: int = 24) -> List[Dict[str, float]]:
        """
        Generate 24-hour charging profile with solar irradiance curve.

        Models a clear-sky day with sunrise at 6:00, sunset at 18:00.
        """
        profile = []
        for h in range(n_hours):
            if 6 <= h <= 18:
                # Solar bell curve
                irr = max(0, np.sin((h - 6) * np.pi / 12))
            else:
                irr = 0.0

            result = self.run_pipeline(irradiance_factor=irr)
            profile.append({
                "hour": h,
                "irradiance_factor": round(irr, 3),
                "solar_kW": result["solar_peak_kW"],
                "electrolyzer_kW": result["electrolyzer_input_kW"],
                "h2_kg_h": result["h2_output_kg_h"],
                "nh3_kg_h": result["nh3_output_kg_h"],
                "grid_export_kW": result["grid_export_kW"],
            })
        return profile

    def optimize_continuous(
        self,
        engines_active: Dict[str, int] = None,
        engine_load_pct: float = 75.0,
        sun_hours: float = 12.0,
        night_hours: float = 12.0,
        safety_margin: float = 1.15,
    ) -> Dict[str, Any]:
        """
        Find the optimal configuration for continuous day/night operation.

        Solves: H₂/NH₃ produced in `sun_hours` ≥ H₂/NH₃ consumed in `night_hours`

        Parameters
        ----------
        engines_active : dict
            Number of each engine running at night.
        engine_load_pct : float
            Engine load during night (%).
        sun_hours : float
            Effective sun hours per day (default 12 for clear sky).
        night_hours : float
            Hours engines operate at night (default 12).
        safety_margin : float
            Over-provision factor (1.15 = 15% extra capacity for weather).

        Returns
        -------
        Dict with optimal module count, tank sizes, and full breakdown.
        """
        if engines_active is None:
            engines_active = {"A-ICE-G1": 1, "PEM-PB-50": 1, "HY-P100": 1}

        # ── Step 1: Calculate night fuel demand ───────────────
        h2_demand_night = 0.0
        nh3_demand_night = 0.0
        engine_breakdown = {}

        for name, n_active in engines_active.items():
            if n_active == 0:
                continue
            spec = ENGINE_SPECS[name]
            rate = spec.fuel_rate_at_load(engine_load_pct) * n_active
            total_kg = rate * night_hours

            if spec.fuel_type == "H₂":
                h2_demand_night += total_kg
            else:
                nh3_demand_night += total_kg

            engine_breakdown[name] = {
                "n_active": n_active,
                "fuel_type": spec.fuel_type,
                "rate_kg_h": round(rate, 3),
                "total_night_kg": round(total_kg, 2),
                "power_kW": round(spec.rated_power_kW * (engine_load_pct/100) * n_active, 1),
            }

        h2_demand_night *= safety_margin
        nh3_demand_night *= safety_margin

        # ── Step 2: Binary search for module count ────────────
        # Find N modules where day production ≥ night demand
        original_n = self.n_modules

        lo, hi = 1, 50_000
        optimal_n = hi

        for _ in range(30):  # bisection
            mid = (lo + hi) // 2
            self.n_modules = mid

            # Average production over sun hours (use bell curve integral)
            # Average irradiance factor over 12h bell = 2/π ≈ 0.637
            avg_irr = 2.0 / np.pi
            r = self.run_pipeline(irradiance_factor=avg_irr)

            h2_produced_day = r["h2_output_kg_h"] * sun_hours
            nh3_produced_day = r["nh3_output_kg_h"] * sun_hours

            h2_ok = h2_produced_day >= h2_demand_night or h2_demand_night < 0.01
            nh3_ok = nh3_produced_day >= nh3_demand_night or nh3_demand_night < 0.01

            if h2_ok and nh3_ok:
                optimal_n = mid
                hi = mid
            else:
                lo = mid + 1

        self.n_modules = optimal_n

        # ── Step 3: Run final pipeline at optimal ─────────────
        avg_irr = 2.0 / np.pi
        final = self.run_pipeline(irradiance_factor=avg_irr)
        h2_day = final["h2_output_kg_h"] * sun_hours
        nh3_day = final["nh3_output_kg_h"] * sun_hours

        # Optimal tank = night demand (buffer for weather)
        opt_h2_tank = max(50, h2_demand_night * 1.2)   # 20% headroom
        opt_nh3_tank = max(100, nh3_demand_night * 1.2)

        # ── Step 4: Metrics ───────────────────────────────────
        solar_kW = self.total_solar_capacity_kW()
        field_ha = self.total_solar_area_ha()
        annual_MWh = self.annual_energy_MWh()

        # Cost estimates
        module_cost = optimal_n * 450   # ~$450/module (Granas tandem)
        electrolyzer_cost = solar_kW * 0.80 * 810  # $810/kW PEM
        tank_cost = opt_h2_tank * 500 + opt_nh3_tank * 50  # $500/kg H₂, $50/kg NH₃
        total_capex = module_cost + electrolyzer_cost + tank_cost

        self.n_modules = original_n  # restore

        return {
            "status": "✅ Continuous operation achievable",
            "optimal_modules": optimal_n,
            "solar_capacity_kW": round(solar_kW, 1),
            "solar_capacity_MW": round(solar_kW / 1000, 2),
            "field_area_ha": round(field_ha, 2),
            "annual_solar_MWh": round(annual_MWh, 1),

            "sun_hours": sun_hours,
            "night_hours": night_hours,
            "safety_margin_pct": round((safety_margin - 1) * 100, 0),
            "engine_load_pct": engine_load_pct,

            "h2_produced_day_kg": round(h2_day, 2),
            "h2_demand_night_kg": round(h2_demand_night, 2),
            "h2_surplus_kg": round(h2_day - h2_demand_night, 2),
            "nh3_produced_day_kg": round(nh3_day, 2),
            "nh3_demand_night_kg": round(nh3_demand_night, 2),
            "nh3_surplus_kg": round(nh3_day - nh3_demand_night, 2),

            "optimal_h2_tank_kg": round(opt_h2_tank, 0),
            "optimal_nh3_tank_kg": round(opt_nh3_tank, 0),

            "engines": engine_breakdown,

            "capex_modules_usd": round(module_cost, 0),
            "capex_electrolyzer_usd": round(electrolyzer_cost, 0),
            "capex_tanks_usd": round(tank_cost, 0),
            "capex_total_usd": round(total_capex, 0),

            "avg_h2_rate_kg_h": round(final["h2_output_kg_h"], 3),
            "avg_nh3_rate_kg_h": round(final["nh3_output_kg_h"], 3),
        }

    def scaling_analysis(self, module_counts: List[int] = None) -> List[Dict[str, Any]]:
        """
        Parametric sweep: N modules → fuel production rates.
        """
        if module_counts is None:
            module_counts = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

        results = []
        original_n = self.n_modules
        for n in module_counts:
            self.n_modules = n
            r = self.run_pipeline(irradiance_factor=1.0)
            results.append({
                "n_modules": n,
                "solar_kW": r["solar_peak_kW"],
                "solar_MW": round(r["solar_peak_kW"] / 1000, 2),
                "h2_kg_h": r["h2_output_kg_h"],
                "h2_kg_day": r["h2_output_kg_day"],
                "nh3_kg_h": r["nh3_output_kg_h"],
                "nh3_kg_day": r["nh3_output_kg_day"],
                "area_ha": r["field_area_ha"],
                "aice_runtime_h_day": r["engines"]["A-ICE-G1"]["runtime_from_1day_charge_h"],
                "pem_runtime_h_day": r["engines"]["PEM-PB-50"]["runtime_from_1day_charge_h"],
                "hyp_runtime_h_day": r["engines"]["HY-P100"]["runtime_from_1day_charge_h"],
            })
        self.n_modules = original_n
        return results

    def day_night_cycle(
        self,
        engine_load_pct: float = 75.0,
        engines_active: Dict[str, int] = None,
        h2_tank_start_pct: float = 0.0,
        nh3_tank_start_pct: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Simulate a full 24-hour day/night cycle.

        DAY  (06:00–18:00): Granas solar → electrolyzer → H₂/NH₃ fills tanks
        NIGHT (18:00–06:00): Engines draw from tanks → mobility (km, kWh)

        Parameters
        ----------
        engine_load_pct : float
            Engine load during night operation (%).
        engines_active : dict
            How many of each engine are active at night.
            Default: {"A-ICE-G1": 1, "PEM-PB-50": 1, "HY-P100": 1}
        h2_tank_start_pct : float
            H₂ tank starting level (% of capacity).
        nh3_tank_start_pct : float
            NH₃ tank starting level (% of capacity).

        Returns
        -------
        List of hourly state dicts with tank levels, production,
        consumption, mobility, and engine status.
        """
        if engines_active is None:
            engines_active = {"A-ICE-G1": 1, "PEM-PB-50": 1, "HY-P100": 1}

        # Mobility assumptions (km/kWh delivered to wheels)
        MOBILITY_KM_PER_KWH = {
            "A-ICE-G1": 0.8,    # Heavy truck: ~0.8 km/kWh
            "PEM-PB-50": 3.5,   # Light vehicle/drone: ~3.5 km/kWh
            "HY-P100": 1.2,     # Marine/gen: ~1.2 km/kWh
        }

        # Initialize tank levels (kg)
        h2_level = self.h2_tank_capacity_kg * h2_tank_start_pct / 100.0
        nh3_level = self.nh3_tank_capacity_kg * nh3_tank_start_pct / 100.0

        cycle = []
        cumulative_km = {name: 0.0 for name in ENGINE_SPECS}
        cumulative_kWh = {name: 0.0 for name in ENGINE_SPECS}
        cumulative_fuel = {name: 0.0 for name in ENGINE_SPECS}

        for h in range(24):
            is_day = 6 <= h < 18
            if is_day:
                # ── DAYTIME: Solar charges tanks ──────────────
                irr = max(0, np.sin((h - 6) * np.pi / 12))
                r = self.run_pipeline(irradiance_factor=irr)
                h2_produced = r["h2_output_kg_h"]
                nh3_produced = r["nh3_output_kg_h"]
                solar_kW = r["solar_peak_kW"]

                # Fill tanks (capped at capacity)
                h2_level = min(self.h2_tank_capacity_kg, h2_level + h2_produced)
                nh3_level = min(self.nh3_tank_capacity_kg, nh3_level + nh3_produced)

                engine_state = {}
                for name in ENGINE_SPECS:
                    engine_state[name] = {
                        "status": "⏸️ Standby",
                        "fuel_consumed_kg": 0.0,
                        "power_delivered_kW": 0.0,
                        "km_this_hour": 0.0,
                    }
            else:
                # ── NIGHTTIME: Engines consume fuel ──────────
                irr = 0.0
                solar_kW = 0.0
                h2_produced = 0.0
                nh3_produced = 0.0

                engine_state = {}
                for name, spec in ENGINE_SPECS.items():
                    n_active = engines_active.get(name, 0)
                    if n_active == 0:
                        engine_state[name] = {
                            "status": "⏸️ Standby",
                            "fuel_consumed_kg": 0.0,
                            "power_delivered_kW": 0.0,
                            "km_this_hour": 0.0,
                        }
                        continue

                    fuel_rate = spec.fuel_rate_at_load(engine_load_pct) * n_active
                    power_out = spec.rated_power_kW * (engine_load_pct / 100) * n_active

                    # Check fuel availability
                    if spec.fuel_type == "NH₃":
                        available = nh3_level
                        actual_fuel = min(fuel_rate, available)
                        nh3_level = max(0, nh3_level - actual_fuel)
                    else:
                        available = h2_level
                        actual_fuel = min(fuel_rate, available)
                        h2_level = max(0, h2_level - actual_fuel)

                    # Actual power (proportional to fuel delivered)
                    delivery_ratio = actual_fuel / max(fuel_rate, 1e-10)
                    actual_power = power_out * delivery_ratio

                    # Mobility: km driven this hour
                    km_kwh = MOBILITY_KM_PER_KWH.get(name, 1.0)
                    km_h = actual_power * km_kwh

                    # Empty tank?
                    if actual_fuel < 0.001:
                        status = "🔴 Empty Tank"
                    elif delivery_ratio < 0.5:
                        status = "🟡 Low Fuel"
                    else:
                        status = f"🟢 Running ({n_active}×)"

                    cumulative_km[name] += km_h
                    cumulative_kWh[name] += actual_power
                    cumulative_fuel[name] += actual_fuel

                    engine_state[name] = {
                        "status": status,
                        "fuel_consumed_kg": round(actual_fuel, 4),
                        "power_delivered_kW": round(actual_power, 2),
                        "km_this_hour": round(km_h, 2),
                    }

            h2_soc = (h2_level / self.h2_tank_capacity_kg) * 100
            nh3_soc = (nh3_level / self.nh3_tank_capacity_kg) * 100

            cycle.append({
                "hour": h,
                "phase": "☀️ DAY — Charging" if is_day else "🌙 NIGHT — Mobility",
                "is_day": is_day,
                "irradiance_factor": round(irr, 3),
                "solar_kW": round(solar_kW, 2),
                "h2_produced_kg": round(h2_produced, 4),
                "nh3_produced_kg": round(nh3_produced, 4),
                "h2_tank_kg": round(h2_level, 2),
                "h2_tank_soc_pct": round(h2_soc, 1),
                "nh3_tank_kg": round(nh3_level, 2),
                "nh3_tank_soc_pct": round(nh3_soc, 1),
                "engines": engine_state,
                "cumulative_km": {k: round(v, 1) for k, v in cumulative_km.items()},
                "cumulative_kWh": {k: round(v, 1) for k, v in cumulative_kWh.items()},
                "cumulative_fuel_kg": {k: round(v, 3) for k, v in cumulative_fuel.items()},
            })

        return cycle


# ═══════════════════════════════════════════════════════════════
# Charging Metrics (all metrics exposure)
# ═══════════════════════════════════════════════════════════════
@dataclass
class ChargingMetrics:
    """
    Comprehensive charging hub metrics extracted from pipeline results.

    Provides all metrics in a flat, dashboard-friendly format.
    """

    @staticmethod
    def extract(pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all charging metrics from a pipeline run."""
        r = pipeline_result
        e = r["electrolysis"]
        hb = r["haber_bosch"]

        return {
            # ── Capacity ──────────────────────────────────────
            "solar_capacity_kW": r["solar_peak_kW"],
            "solar_capacity_MW": round(r["solar_peak_kW"] / 1000, 3),
            "n_granas_modules": r["n_modules"],
            "field_area_m2": r["field_area_m2"],
            "field_area_ha": r["field_area_ha"],
            "annual_solar_MWh": r["solar_annual_MWh"],

            # ── Electrolyzer ──────────────────────────────────
            "electrolyzer_input_kW": r["electrolyzer_input_kW"],
            "electrolyzer_cells": e["n_cells"],
            "current_density_A_cm2": e["current_density_A_cm2"],
            "cell_voltage_V": e["cell_voltage_V"],
            "stack_temp_C": e["stack_temp_C"],
            "h2_pressure_bar": e["h2_pressure_bar"],

            # ── Production Rates ──────────────────────────────
            "h2_rate_kg_h": r["h2_output_kg_h"],
            "h2_rate_kg_day": r["h2_output_kg_day"],
            "nh3_rate_kg_h": r["nh3_output_kg_h"],
            "nh3_rate_kg_day": r["nh3_output_kg_day"],
            "h2o_consumption_kg_h": e["h2o_consumption_kg_h"],
            "o2_coproduct_kg_h": e["o2_kg_h"],

            # ── Energy Metrics ────────────────────────────────
            "kwh_per_kg_h2": e["kwh_per_kg_h2"],
            "h2_energy_content_kWh_h": r["h2_energy_kWh_h"],
            "nh3_energy_content_kWh_h": r["nh3_energy_kWh_h"],
            "total_fuel_energy_kWh_h": round(r["h2_energy_kWh_h"] + r["nh3_energy_kWh_h"], 2),
            "grid_export_kW": r["grid_export_kW"],
            "conversion_loss_kW": r["conversion_loss_kW"],

            # ── Efficiency Chain ──────────────────────────────
            "solar_to_wire_eff_pct": r["solar_to_wire_eff_pct"],
            "wire_to_h2_eff_pct": r["wire_to_h2_eff_pct"],
            "overall_h2_eff_pct": r["overall_h2_eff_pct"],
            "hb_conversion_eff_pct": r["hb_conversion_eff_pct"],
            "overall_solar_to_fuel_pct": r["overall_solar_to_fuel_pct"],
            "cell_efficiency_pct": e["cell_efficiency_pct"],
            "system_efficiency_pct": e["system_efficiency_pct"],

            # ── Storage ───────────────────────────────────────
            "h2_tank_capacity_kg": r["h2_tank_capacity_kg"],
            "nh3_tank_capacity_kg": r["nh3_tank_capacity_kg"],
            "h2_fill_time_h": r["h2_fill_time_h"],
            "nh3_fill_time_h": r["nh3_fill_time_h"],

            # ── Environmental ─────────────────────────────────
            "co2_per_kg_h2": 0.0,
            "co2_per_kg_nh3": 0.0,
            "co2_avoided_vs_smr_kg_h": r["co2_avoided_vs_smr_kg_h"],
            "co2_avoided_vs_hb_kg_h": r["co2_avoided_vs_hb_kg_h"],

            # ── Engine Readiness ──────────────────────────────
            "engines": r["engines"],
        }
