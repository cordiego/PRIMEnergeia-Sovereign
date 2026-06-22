"""
PRIMStack — Unified Plant Model
==================================
Integrates all PRIMEnergeia subsystems into one plant-level
energy + material + thermal flow model.

Subsystems:
  1. Solar Farm (Granas perovskite-Si tandem panels)
  2. Wind Farm  (PRIM-Wind offshore + electrolyzer)
  3. Electrolyzer (PEM electrolysis: H₂O → H₂)
  4. H₂ Storage  (compressed gas tanks)
  5. NH₃ Synthesis (Haber-Bosch from H₂ + N₂)
  6. NH₃ Storage  (refrigerated tanks)
  7. Engine Fleet: A-ICE (NH₃), PEM-FC (H₂), HY-P100 (H₂ turbine)
  8. Battery BESS (grid buffer)
  9. PRIMEcycle  (panel recycling → material recovery)
  10. Waste Heat Bus (engine exhaust → annealing)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# Configuration & Sizing
# ─────────────────────────────────────────────────────────────
@dataclass
class PlantConfig:
    """Plant sizing parameters."""
    # Solar
    solar_capacity_mw: float = 50.0          # Granas panel farm
    solar_degradation_pct_yr: float = 0.5    # Annual degradation
    panel_lifetime_yr: int = 30

    # Wind
    wind_capacity_mw: float = 100.0
    wind_capacity_factor: float = 0.42

    # Electrolyzer
    electrolyzer_capacity_mw: float = 25.0
    electrolyzer_efficiency: float = 0.70    # kWh_H2 / kWh_elec (HHV)
    h2_energy_density_kwh_kg: float = 33.3   # LHV

    # H₂ Storage
    h2_tank_capacity_kg: float = 5000.0
    h2_initial_kg: float = 2500.0

    # NH₃ Synthesis (Haber-Bosch)
    nh3_synth_capacity_kg_h: float = 200.0
    nh3_synth_efficiency: float = 0.65       # kg_NH3 / kg_H2 (theoretical: 5.67)
    nh3_stoich_ratio: float = 5.67           # kg NH₃ per kg H₂

    # NH₃ Storage
    nh3_tank_capacity_kg: float = 20000.0
    nh3_initial_kg: float = 10000.0

    # Engine Fleet
    n_aice: int = 3                          # 3× A-ICE-G1 (335 kW each)
    n_pem: int = 5                           # 5× PEM-PB-50 (50 kW each)
    n_hyp: int = 2                           # 2× HY-P100 (100 kW each)
    aice_rated_kw: float = 335.0
    pem_rated_kw: float = 50.0
    hyp_rated_kw: float = 100.0

    # Battery
    bess_capacity_mwh: float = 400.0
    bess_initial_soc: float = 0.50
    bess_efficiency: float = 0.92            # Round-trip

    # Recycling
    primecycle_capacity_modules_yr: int = 50000
    panel_weight_kg: float = 22.0

    # Economics
    grid_price_usd_mwh: float = 65.0
    h2_price_usd_kg: float = 4.50
    nh3_price_usd_kg: float = 0.45

    # Waste Heat
    engine_waste_heat_fraction: float = 0.55  # 55% of fuel energy → heat
    anneal_heat_requirement_kw: float = 50.0  # kW needed for continuous annealing


# ─────────────────────────────────────────────────────────────
# Plant State
# ─────────────────────────────────────────────────────────────
@dataclass
class PlantState:
    """Full plant state at a given timestep."""
    # Storage levels
    h2_stored_kg: float = 2500.0
    nh3_stored_kg: float = 10000.0
    battery_soc: float = 0.50           # 0-1

    # Generation (current timestep)
    solar_generation_mw: float = 0.0
    wind_generation_mw: float = 0.0

    # Panel fleet
    panel_age_yr: float = 0.0
    panel_degradation_pct: float = 0.0
    panels_recycled_cumulative: int = 0

    # Engine fleet health
    aice_stress_pct: float = 0.0
    pem_degradation_uv: float = 0.0
    hyp_blade_life_pct: float = 100.0

    # Thermal bus
    waste_heat_available_kw: float = 0.0

    # Economics
    cumulative_revenue_usd: float = 0.0
    cumulative_fuel_cost_usd: float = 0.0
    cumulative_h2_produced_kg: float = 0.0
    cumulative_nh3_produced_kg: float = 0.0

    # Grid
    grid_export_mw: float = 0.0
    grid_import_mw: float = 0.0


# ─────────────────────────────────────────────────────────────
# Subsystem Models
# ─────────────────────────────────────────────────────────────
class SolarModel:
    """Granas perovskite-Si tandem solar farm."""

    @staticmethod
    def generation(capacity_mw: float, hour: int, degradation_pct: float,
                   cloud_factor: float = 1.0) -> float:
        """Solar output at given hour (0-23), MW."""
        # Simple solar profile: bell curve peaking at noon
        hour_angle = (hour - 12) / 6.0
        irradiance = max(0, np.cos(hour_angle * np.pi / 2)) ** 1.3
        effective_capacity = capacity_mw * (1 - degradation_pct / 100)
        return effective_capacity * irradiance * cloud_factor

    @staticmethod
    def annual_degradation(age_yr: float, rate_pct_yr: float) -> float:
        """Cumulative panel degradation."""
        return min(50.0, age_yr * rate_pct_yr)


class WindModel:
    """PRIM-Wind offshore farm."""

    @staticmethod
    def generation(capacity_mw: float, hour: int, season: str = "annual") -> float:
        """Wind output — varies by hour and season."""
        # Wind profile: stronger at night, seasonal variation
        night_boost = 1.0 + 0.15 * np.cos((hour - 3) * np.pi / 12)
        season_factors = {"winter": 1.2, "spring": 1.0, "summer": 0.8, "fall": 1.1, "annual": 1.0}
        factor = season_factors.get(season, 1.0) * night_boost
        # Stochastic component
        base_cf = 0.42
        return capacity_mw * base_cf * factor * (0.9 + 0.2 * np.random.random())


class ElectrolyzerModel:
    """PEM electrolyzer: electricity → H₂."""

    @staticmethod
    def produce_h2(power_mw: float, capacity_mw: float, efficiency: float) -> Dict:
        """H₂ production from electrical input."""
        actual_power = min(power_mw, capacity_mw)
        h2_energy_mwh = actual_power * efficiency
        h2_kg = h2_energy_mwh * 1000 / 33.3  # 33.3 kWh/kg H₂
        water_kg = h2_kg * 9.0  # 9 kg water per kg H₂
        return {
            "h2_produced_kg": h2_kg,
            "power_consumed_mw": actual_power,
            "water_consumed_kg": water_kg,
            "efficiency_pct": efficiency * 100,
        }


class HaberBoschModel:
    """NH₃ synthesis from H₂ + N₂."""

    @staticmethod
    def synthesize(h2_available_kg: float, capacity_kg_h: float,
                   stoich_ratio: float = 5.67) -> Dict:
        """NH₃ production. N₂ + 3H₂ → 2NH₃."""
        max_nh3 = h2_available_kg * stoich_ratio
        nh3_produced = min(max_nh3, capacity_kg_h)
        h2_consumed = nh3_produced / stoich_ratio
        electricity_kwh = nh3_produced * 0.5  # ~0.5 kWh/kg NH₃ for compression
        return {
            "nh3_produced_kg": nh3_produced,
            "h2_consumed_kg": h2_consumed,
            "electricity_kwh": electricity_kwh,
        }


class EngineFleet:
    """Dispatches the 3 engine types based on fuel availability and demand."""

    @staticmethod
    def dispatch(demand_kw: float, h2_available_kg: float, nh3_available_kg: float,
                 config: PlantConfig) -> Dict:
        """
        Optimal engine dispatch.

        Priority: PEM (highest efficiency) → HYP (medium) → AICE (bulk power)
        Constrained by: fuel availability, fleet capacity
        """
        remaining = demand_kw
        result = {
            "pem_power_kw": 0, "pem_h2_kg_h": 0, "pem_count": 0,
            "hyp_power_kw": 0, "hyp_h2_kg_h": 0, "hyp_count": 0,
            "aice_power_kw": 0, "aice_nh3_kg_h": 0, "aice_count": 0,
            "total_power_kw": 0, "waste_heat_kw": 0,
        }

        # 1. PEM first (η ≈ 55%, clean, quiet)
        if remaining > 0 and h2_available_kg > 1:
            pem_capacity = config.n_pem * config.pem_rated_kw
            pem_power = min(remaining, pem_capacity)
            pem_h2 = pem_power * 3.6 / (0.55 * 120.0)  # kg/h
            if pem_h2 <= h2_available_kg:
                result["pem_power_kw"] = pem_power
                result["pem_h2_kg_h"] = pem_h2
                result["pem_count"] = min(config.n_pem, int(np.ceil(pem_power / config.pem_rated_kw)))
                remaining -= pem_power
                h2_available_kg -= pem_h2

        # 2. HYP next (η ≈ 38%, fast ramp)
        if remaining > 0 and h2_available_kg > 1:
            hyp_capacity = config.n_hyp * config.hyp_rated_kw
            hyp_power = min(remaining, hyp_capacity)
            hyp_h2 = hyp_power * 3.6 / (0.38 * 120.0)  # kg/h
            if hyp_h2 <= h2_available_kg:
                result["hyp_power_kw"] = hyp_power
                result["hyp_h2_kg_h"] = hyp_h2
                result["hyp_count"] = min(config.n_hyp, int(np.ceil(hyp_power / config.hyp_rated_kw)))
                remaining -= hyp_power
                result["waste_heat_kw"] += hyp_power * 0.8  # High waste heat

        # 3. AICE for bulk (η ≈ 44%, NH₃ fuel)
        if remaining > 0 and nh3_available_kg > 5:
            aice_capacity = config.n_aice * config.aice_rated_kw
            aice_power = min(remaining, aice_capacity)
            aice_nh3 = aice_power * 3.6 / (0.44 * 18.6)  # kg/h
            if aice_nh3 <= nh3_available_kg:
                result["aice_power_kw"] = aice_power
                result["aice_nh3_kg_h"] = aice_nh3
                result["aice_count"] = min(config.n_aice, int(np.ceil(aice_power / config.aice_rated_kw)))
                remaining -= aice_power
                result["waste_heat_kw"] += aice_power * 0.65  # EGT waste heat

        result["total_power_kw"] = demand_kw - remaining
        return result


class WasteHeatBus:
    """Recovers engine waste heat for perovskite annealing."""

    @staticmethod
    def recover(waste_heat_kw: float, anneal_demand_kw: float) -> Dict:
        """Route waste heat to annealing process."""
        recovered = min(waste_heat_kw, anneal_demand_kw)
        surplus = max(0, waste_heat_kw - anneal_demand_kw)
        savings_kwh = recovered  # 1:1 thermal replacement
        return {
            "heat_to_anneal_kw": recovered,
            "heat_surplus_kw": surplus,
            "electricity_saved_kwh": savings_kwh,
            "anneal_coverage_pct": recovered / anneal_demand_kw * 100 if anneal_demand_kw > 0 else 0,
        }


class RecyclingModel:
    """PRIMEcycle — matches recycling throughput to degradation rate."""

    @staticmethod
    def annual_replacement_need(total_panels: int, age_yr: float,
                                 lifetime_yr: int = 30) -> Dict:
        """How many panels need recycling/replacement this year."""
        # Weibull failure model (shape=4, scale=lifetime)
        if age_yr < 1:
            failure_rate = 0.001
        else:
            shape = 4.0
            failure_rate = (shape / lifetime_yr) * (age_yr / lifetime_yr) ** (shape - 1)

        panels_to_replace = int(total_panels * min(failure_rate, 0.15))
        return {
            "panels_to_replace": panels_to_replace,
            "recycling_throughput_needed": panels_to_replace,
            "material_recovered_kg": panels_to_replace * 18.0,  # ~18 kg recoverable per panel
            "value_recovered_usd": panels_to_replace * 12.50,   # Avg recovery value
        }


# ─────────────────────────────────────────────────────────────
# Plant Simulator
# ─────────────────────────────────────────────────────────────
class PRIMStackPlant:
    """
    Unified plant simulator.

    Runs hourly dispatch over a configurable time horizon,
    tracking all energy, material, and economic flows.
    """

    def __init__(self, config: PlantConfig = None):
        self.config = config or PlantConfig()
        self.solar = SolarModel()
        self.wind = WindModel()
        self.electrolyzer = ElectrolyzerModel()
        self.haber_bosch = HaberBoschModel()
        self.engines = EngineFleet()
        self.waste_heat = WasteHeatBus()
        self.recycling = RecyclingModel()

    def simulate_hour(self, state: PlantState, hour: int,
                      grid_demand_kw: float = 500.0,
                      cloud_factor: float = 1.0) -> Tuple[PlantState, Dict]:
        """Simulate one hour of plant operation."""
        cfg = self.config
        metrics = {}

        # ─── GENERATION ───
        solar_mw = self.solar.generation(cfg.solar_capacity_mw, hour,
                                          state.panel_degradation_pct, cloud_factor)
        wind_mw = self.wind.generation(cfg.wind_capacity_mw, hour)
        total_gen_mw = solar_mw + wind_mw
        total_gen_kw = total_gen_mw * 1000

        state.solar_generation_mw = solar_mw
        state.wind_generation_mw = wind_mw

        # ─── DEMAND ALLOCATION ───
        surplus_kw = total_gen_kw - grid_demand_kw

        # If surplus: electrolyze → H₂
        elec_result = {"h2_produced_kg": 0, "power_consumed_mw": 0}
        hb_result = {"nh3_produced_kg": 0, "h2_consumed_kg": 0}

        if surplus_kw > 0:
            # Charge battery first
            battery_headroom = (1 - state.battery_soc) * cfg.bess_capacity_mwh * 1000
            battery_charge = min(surplus_kw, battery_headroom * 0.25)  # Max 25% C-rate
            state.battery_soc += battery_charge / (cfg.bess_capacity_mwh * 1000) * cfg.bess_efficiency
            state.battery_soc = min(1.0, state.battery_soc)
            surplus_kw -= battery_charge

            # Remaining surplus → electrolyzer
            if surplus_kw > 100:
                elec_result = self.electrolyzer.produce_h2(
                    surplus_kw / 1000, cfg.electrolyzer_capacity_mw, cfg.electrolyzer_efficiency)
                h2_new = elec_result["h2_produced_kg"]
                state.h2_stored_kg = min(cfg.h2_tank_capacity_kg, state.h2_stored_kg + h2_new)
                state.cumulative_h2_produced_kg += h2_new

                # Convert excess H₂ to NH₃ if H₂ storage is getting full
                if state.h2_stored_kg > cfg.h2_tank_capacity_kg * 0.8:
                    h2_for_nh3 = min(state.h2_stored_kg * 0.1, cfg.nh3_synth_capacity_kg_h / cfg.nh3_stoich_ratio)
                    hb_result = self.haber_bosch.synthesize(h2_for_nh3, cfg.nh3_synth_capacity_kg_h)
                    state.h2_stored_kg -= hb_result["h2_consumed_kg"]
                    state.nh3_stored_kg = min(cfg.nh3_tank_capacity_kg,
                                              state.nh3_stored_kg + hb_result["nh3_produced_kg"])
                    state.cumulative_nh3_produced_kg += hb_result["nh3_produced_kg"]

            # Export remaining to grid
            state.grid_export_mw = max(0, surplus_kw / 1000)
            state.grid_import_mw = 0
            revenue = state.grid_export_mw * cfg.grid_price_usd_mwh
            state.cumulative_revenue_usd += revenue

        else:
            # Deficit: discharge battery → start engines
            deficit_kw = -surplus_kw

            # Battery first
            battery_available = state.battery_soc * cfg.bess_capacity_mwh * 1000
            battery_discharge = min(deficit_kw, battery_available * 0.25)
            state.battery_soc -= battery_discharge / (cfg.bess_capacity_mwh * 1000)
            state.battery_soc = max(0.1, state.battery_soc)  # Preserve 10% SOC
            deficit_kw -= battery_discharge

            # Engines for remaining deficit
            engine_result = {"total_power_kw": 0, "waste_heat_kw": 0,
                             "pem_h2_kg_h": 0, "aice_nh3_kg_h": 0, "hyp_h2_kg_h": 0}
            if deficit_kw > 10:
                engine_result = self.engines.dispatch(
                    deficit_kw, state.h2_stored_kg, state.nh3_stored_kg, cfg)

                # Consume fuel
                total_h2 = engine_result["pem_h2_kg_h"] + engine_result["hyp_h2_kg_h"]
                state.h2_stored_kg = max(0, state.h2_stored_kg - total_h2)
                state.nh3_stored_kg = max(0, state.nh3_stored_kg - engine_result["aice_nh3_kg_h"])

                # Waste heat recovery
                heat_result = self.waste_heat.recover(
                    engine_result["waste_heat_kw"], cfg.anneal_heat_requirement_kw)
                state.waste_heat_available_kw = heat_result["heat_to_anneal_kw"]

                # Engine wear
                state.aice_stress_pct += 0.001 * engine_result.get("aice_count", 0)
                state.pem_degradation_uv += 0.1 * engine_result.get("pem_count", 0)
                state.hyp_blade_life_pct -= 0.0001 * engine_result.get("hyp_count", 0)

            state.grid_export_mw = 0
            state.grid_import_mw = max(0, (deficit_kw - engine_result["total_power_kw"]) / 1000)

            metrics["engine_dispatch"] = engine_result

        # ─── METRICS ───
        metrics.update({
            "hour": hour,
            "solar_mw": solar_mw,
            "wind_mw": wind_mw,
            "total_gen_mw": total_gen_mw,
            "h2_stored_kg": state.h2_stored_kg,
            "nh3_stored_kg": state.nh3_stored_kg,
            "battery_soc": state.battery_soc,
            "h2_produced_kg": elec_result["h2_produced_kg"],
            "nh3_produced_kg": hb_result["nh3_produced_kg"],
            "grid_export_mw": state.grid_export_mw,
            "grid_import_mw": state.grid_import_mw,
            "waste_heat_kw": state.waste_heat_available_kw,
        })

        return state, metrics

    def simulate_day(self, state: PlantState = None,
                     grid_demand_kw: float = 500.0) -> Tuple[PlantState, List[Dict]]:
        """Simulate 24 hours of plant operation."""
        if state is None:
            state = PlantState(
                h2_stored_kg=self.config.h2_initial_kg,
                nh3_stored_kg=self.config.nh3_initial_kg,
                battery_soc=self.config.bess_initial_soc,
            )
        hourly = []
        for h in range(24):
            state, metrics = self.simulate_hour(state, h, grid_demand_kw)
            hourly.append(metrics)
        return state, hourly

    def simulate_year(self, state: PlantState = None,
                      grid_demand_kw: float = 500.0) -> Dict:
        """Simulate full year (365 days × 24 hours)."""
        if state is None:
            state = PlantState(
                h2_stored_kg=self.config.h2_initial_kg,
                nh3_stored_kg=self.config.nh3_initial_kg,
                battery_soc=self.config.bess_initial_soc,
            )

        daily_summaries = []
        for day in range(365):
            state, hourly = self.simulate_day(state, grid_demand_kw)

            daily_solar = sum(m["solar_mw"] for m in hourly)
            daily_wind = sum(m["wind_mw"] for m in hourly)
            daily_h2 = sum(m["h2_produced_kg"] for m in hourly)
            daily_export = sum(m["grid_export_mw"] for m in hourly)

            daily_summaries.append({
                "day": day,
                "solar_mwh": daily_solar,
                "wind_mwh": daily_wind,
                "h2_produced_kg": daily_h2,
                "grid_export_mwh": daily_export,
                "h2_stored_kg": state.h2_stored_kg,
                "nh3_stored_kg": state.nh3_stored_kg,
                "battery_soc": state.battery_soc,
            })

            # Annual degradation tick
            if day % 365 == 364:
                state.panel_age_yr += 1
                state.panel_degradation_pct = SolarModel.annual_degradation(
                    state.panel_age_yr, self.config.solar_degradation_pct_yr)

        # Recycling assessment
        total_panels = int(self.config.solar_capacity_mw * 1e6 / 400)  # ~400W per panel
        recycle = self.recycling.annual_replacement_need(total_panels, state.panel_age_yr)

        return {
            "final_state": state,
            "total_solar_gwh": sum(d["solar_mwh"] for d in daily_summaries) / 1000,
            "total_wind_gwh": sum(d["wind_mwh"] for d in daily_summaries) / 1000,
            "total_h2_produced_tonnes": state.cumulative_h2_produced_kg / 1000,
            "total_nh3_produced_tonnes": state.cumulative_nh3_produced_kg / 1000,
            "total_grid_revenue_usd": state.cumulative_revenue_usd,
            "panel_degradation_pct": state.panel_degradation_pct,
            "recycling_need": recycle,
            "engine_health": {
                "aice_stress_pct": state.aice_stress_pct,
                "pem_degradation_uV": state.pem_degradation_uv,
                "hyp_blade_life_pct": state.hyp_blade_life_pct,
            },
            "daily_summaries": daily_summaries,
        }

    def plant_summary(self) -> Dict:
        """Static plant sizing summary."""
        cfg = self.config
        total_engine_kw = (cfg.n_aice * cfg.aice_rated_kw +
                           cfg.n_pem * cfg.pem_rated_kw +
                           cfg.n_hyp * cfg.hyp_rated_kw)
        return {
            "solar_mw": cfg.solar_capacity_mw,
            "wind_mw": cfg.wind_capacity_mw,
            "total_renewable_mw": cfg.solar_capacity_mw + cfg.wind_capacity_mw,
            "electrolyzer_mw": cfg.electrolyzer_capacity_mw,
            "engine_fleet_kw": total_engine_kw,
            "engine_fleet_breakdown": {
                "aice": f"{cfg.n_aice}× {cfg.aice_rated_kw:.0f} kW = {cfg.n_aice * cfg.aice_rated_kw:.0f} kW",
                "pem": f"{cfg.n_pem}× {cfg.pem_rated_kw:.0f} kW = {cfg.n_pem * cfg.pem_rated_kw:.0f} kW",
                "hyp": f"{cfg.n_hyp}× {cfg.hyp_rated_kw:.0f} kW = {cfg.n_hyp * cfg.hyp_rated_kw:.0f} kW",
            },
            "bess_mwh": cfg.bess_capacity_mwh,
            "h2_storage_kg": cfg.h2_tank_capacity_kg,
            "nh3_storage_kg": cfg.nh3_tank_capacity_kg,
            "fuel_type": "Zero CO₂ (Green H₂ + Green NH₃)",
        }


if __name__ == "__main__":
    plant = PRIMStackPlant()
    summary = plant.plant_summary()
    print(f"\n{'='*60}")
    print(f" PRIMStack — Unified Plant Summary")
    print(f"{'='*60}")
    for k, v in summary.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")

    print(f"\n Simulating 24h...")
    state, hourly = plant.simulate_day()
    print(f"  Final H₂: {state.h2_stored_kg:.0f} kg")
    print(f"  Final NH₃: {state.nh3_stored_kg:.0f} kg")
    print(f"  Battery SOC: {state.battery_soc:.1%}")
    print(f"  Revenue: ${state.cumulative_revenue_usd:.0f}")
    print(f"{'='*60}")
