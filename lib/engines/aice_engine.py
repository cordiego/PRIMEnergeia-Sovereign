#!/usr/bin/env python3
"""
PRIMEngines A-ICE-G1 — Ammonia Internal Combustion Engine Simulator
====================================================================
PRIMEnergeia S.A.S. | PRIMEngines Division

Physics-based simulation of a spark-ignited ammonia ICE with:
  - Dual-fuel combustion model (NH₃ + H₂ pilot)
  - Torque / power / BSFC maps across RPM × load
  - NOx formation (Zeldovich mechanism) + SCR reduction
  - Thermal management (coolant, oil, intercooler)
  - Drive-cycle energy consumption (VECTO / EPA)

Reference: Valera-Medina et al., Progress in Energy & Combustion Science (2018)
"""

import math
import json
from dataclasses import dataclass, field, asdict

try:
    from power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS
except ImportError:
    from lib.engines.power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS
from typing import List, Dict, Optional, Tuple

# ============================================================
#  ENGINE SPECIFICATION
# ============================================================

@dataclass
class AICESpec:
    """A-ICE-G1 engine specification."""
    name: str = "PRIMEngines A-ICE-G1"
    configuration: str = "V8 60° Spark-Ignited"
    displacement_L: float = 12.8          # Liters
    bore_mm: float = 130.0
    stroke_mm: float = 120.0
    compression_ratio: float = 14.5       # Higher than gasoline for NH₃
    cylinders: int = 8
    valves_per_cyl: int = 4

    # Performance
    rated_power_kw: float = 335.0         # 450 HP
    rated_rpm: int = 2100
    max_torque_nm: float = 1800.0
    max_torque_rpm: int = 1400
    idle_rpm: int = 600

    # Fuel system
    primary_fuel: str = "Anhydrous NH₃ (liquid)"
    pilot_fuel: str = "Green H₂ (5-10% energy share)"
    injection: str = "Direct injection, 350 bar"
    h2_pilot_fraction: float = 0.08       # 8% energy from H₂ pilot

    # Emissions control
    aftertreatment: str = "SCR + ASC + DOC"
    nox_target_gpkwh: float = 0.40        # Euro VI compliant

    # Physical
    dry_weight_kg: float = 680.0
    length_mm: float = 1250
    width_mm: float = 980
    height_mm: float = 1100

    # Generator / Inverter (genset mode)
    generator_efficiency: float = 0.95
    inverter_enabled: bool = False        # True = genset mode (mech → elec)

    # Thermal
    coolant_temp_c: float = 90.0
    max_exhaust_temp_c: float = 650.0

    def cylinder_volume_cc(self) -> float:
        return math.pi / 4 * (self.bore_mm / 10) ** 2 * (self.stroke_mm / 10)


# ============================================================
#  AMMONIA FUEL PROPERTIES
# ============================================================

@dataclass
class NH3Properties:
    """Thermophysical properties of anhydrous ammonia."""
    molecular_weight: float = 17.031      # g/mol
    lhv_mj_kg: float = 18.6              # MJ/kg  (vs 42.7 for diesel)
    hhv_mj_kg: float = 22.5
    density_liquid_kg_m3: float = 682.0   # @ 20°C, 8.6 bar
    boiling_point_c: float = -33.3
    autoignition_temp_c: float = 651.0    # Much higher than diesel (210°C)
    laminar_flame_speed_cm_s: float = 7.0 # Very slow (vs 40 cm/s for H₂)
    flammability_range_pct: Tuple[float, float] = (15.0, 28.0)  # vol% in air
    octane_number: float = 130.0          # Excellent knock resistance
    stoichiometric_afr: float = 6.04      # vs 14.7 for gasoline
    adiabatic_flame_temp_k: float = 1800  # Lower than hydrocarbons

@dataclass
class H2Properties:
    """Properties of hydrogen pilot fuel."""
    lhv_mj_kg: float = 120.0
    laminar_flame_speed_cm_s: float = 290.0  # Fast — helps ignite NH₃
    autoignition_temp_c: float = 500.0
    density_kg_m3: float = 0.0899


# ============================================================
#  COMBUSTION MODEL
# ============================================================

class CombustionModel:
    """
    Zero-dimensional two-zone combustion model for NH₃/H₂ dual fuel.
    Uses Wiebe function for mass fraction burned.
    """

    def __init__(self, spec: AICESpec, nh3: NH3Properties = None, h2: H2Properties = None):
        self.spec = spec
        self.nh3 = nh3 or NH3Properties()
        self.h2 = h2 or H2Properties()

    def wiebe_mfb(self, theta: float, theta_start: float, duration: float,
                  a: float = 5.0, m: float = 2.0) -> float:
        """Wiebe mass fraction burned."""
        if theta < theta_start:
            return 0.0
        x = (theta - theta_start) / duration
        if x > 1.0:
            return 1.0
        return 1.0 - math.exp(-a * x ** (m + 1))

    def brake_thermal_efficiency(self, rpm: int, load_pct: float) -> float:
        """
        BTE map for NH₃/H₂ dual-fuel engine.
        Peak BTE ~42% at rated torque, drops at low load due to
        NH₃'s slow flame speed requiring richer mixtures.
        """
        # Normalized RPM and load
        n = rpm / self.spec.rated_rpm
        l = load_pct / 100.0

        # Base efficiency (Otto cycle with NH₃ corrections)
        gamma = 1.35  # specific heat ratio for NH₃/air
        eta_otto = 1 - (1 / self.spec.compression_ratio) ** (gamma - 1)

        # Mechanical efficiency drops at high RPM
        eta_mech = 0.92 - 0.08 * (n - 0.7) ** 2

        # Combustion efficiency — NH₃ has incomplete combustion at low loads
        eta_comb = 0.95 - 0.15 * (1 - l) ** 2
        # H₂ pilot improves low-load combustion
        h2_boost = self.spec.h2_pilot_fraction * 0.8 * (1 - l)
        eta_comb = min(0.98, eta_comb + h2_boost)

        # Pumping losses at part load
        eta_pump = 1.0 - 0.05 * (1 - l)

        # Heat transfer losses (worse at low speed)
        eta_ht = 0.88 + 0.04 * n

        bte = eta_otto * eta_mech * eta_comb * eta_pump * eta_ht
        return round(max(0.15, min(0.44, bte)), 4)

    def torque_at_rpm(self, rpm: int, load_pct: float = 100.0) -> float:
        """Torque (Nm) at given RPM and load percentage."""
        n = rpm / self.spec.rated_rpm

        # Torque curve shape — peak at max_torque_rpm
        n_peak = self.spec.max_torque_rpm / self.spec.rated_rpm
        if n <= n_peak:
            shape = 0.85 + 0.15 * (n / n_peak)
        else:
            shape = 1.0 - 0.15 * ((n - n_peak) / (1.0 - n_peak)) ** 1.5

        torque = self.spec.max_torque_nm * shape * (load_pct / 100.0)
        return round(max(0, torque), 1)

    def power_at_rpm(self, rpm: int, load_pct: float = 100.0) -> float:
        """Power (kW) at given RPM and load."""
        torque = self.torque_at_rpm(rpm, load_pct)
        return round(torque * rpm * 2 * math.pi / 60000, 1)

    def bsfc(self, rpm: int, load_pct: float) -> float:
        """Brake Specific Fuel Consumption (g/kWh) — NH₃ equivalent."""
        bte = self.brake_thermal_efficiency(rpm, load_pct)
        if bte <= 0:
            return 999.9
        # BSFC = 3600 / (BTE × LHV)
        bsfc = 3600 / (bte * self.nh3.lhv_mj_kg)
        return round(bsfc, 1)

    def fuel_flow_kg_h(self, rpm: int, load_pct: float) -> float:
        """Total fuel flow (kg/h) at operating point."""
        power = self.power_at_rpm(rpm, load_pct)
        bsfc_val = self.bsfc(rpm, load_pct)
        return round(power * bsfc_val / 1000, 2)

    def nh3_flow_kg_h(self, rpm: int, load_pct: float) -> float:
        """NH₃ fuel flow (kg/h)."""
        total = self.fuel_flow_kg_h(rpm, load_pct)
        # Energy-weighted mass split:
        #   NH₃ energy fraction = 1 - h2_pilot_fraction (by energy)
        #   Convert to mass: m_nh3/LHV_nh3 gives energy, so
        #   mass_frac_nh3 = (E_nh3/LHV_nh3) / (E_nh3/LHV_nh3 + E_h2/LHV_h2)
        e_nh3 = 1 - self.spec.h2_pilot_fraction  # 0.92
        e_h2 = self.spec.h2_pilot_fraction         # 0.08
        nh3_mass_frac = (e_nh3 / self.nh3.lhv_mj_kg) / (
            e_nh3 / self.nh3.lhv_mj_kg + e_h2 / self.h2.lhv_mj_kg
        )
        return round(total * nh3_mass_frac, 2)

    def h2_flow_kg_h(self, rpm: int, load_pct: float) -> float:
        """H₂ pilot fuel flow (kg/h)."""
        total = self.fuel_flow_kg_h(rpm, load_pct)
        e_nh3 = 1 - self.spec.h2_pilot_fraction
        e_h2 = self.spec.h2_pilot_fraction
        h2_mass_frac = (e_h2 / self.h2.lhv_mj_kg) / (
            e_nh3 / self.nh3.lhv_mj_kg + e_h2 / self.h2.lhv_mj_kg
        )
        return round(total * h2_mass_frac, 3)


# ============================================================
#  NOx MODEL (Extended Zeldovich)
# ============================================================

class NOxModel:
    """
    Thermal NOx formation using extended Zeldovich mechanism.
    Ammonia combustion produces both thermal NOx AND fuel NOx
    from nitrogen in NH₃. SCR aftertreatment reduces exhaust NOx.
    """

    def __init__(self, scr_efficiency: float = 0.95):
        self.scr_efficiency = scr_efficiency

    def thermal_nox_ppm(self, peak_temp_k: float, residence_time_ms: float = 2.0) -> float:
        """Zeldovich thermal NOx (ppm) from peak cycle temperature."""
        if peak_temp_k < 1600:
            return 0.0
        # Exponential temperature dependence
        nox = 4500 * math.exp(-21500 / peak_temp_k) * (residence_time_ms / 2.0)
        return round(nox, 1)

    def fuel_nox_ppm(self, equivalence_ratio: float, nh3_n_conversion: float = 0.25) -> float:
        """
        Fuel-bound nitrogen NOx from NH₃.
        ~25% of fuel-N converts to NOx at typical conditions.
        """
        # NH₃ is 82.3% N by mass
        n_content = 0.823
        nox = 3000 * n_content * nh3_n_conversion * equivalence_ratio
        return round(nox, 1)

    def engine_out_nox(self, rpm: int, load_pct: float, peak_temp_k: float = None) -> float:
        """Total engine-out NOx (g/kWh)."""
        if peak_temp_k is None:
            peak_temp_k = 1700 + 300 * (load_pct / 100)

        thermal = self.thermal_nox_ppm(peak_temp_k)
        fuel = self.fuel_nox_ppm(equivalence_ratio=0.9 + 0.2 * load_pct / 100)

        # Convert ppm to g/kWh (approximate)
        total_gpkwh = (thermal + fuel) * 0.0015 * (1 + 0.3 * load_pct / 100)
        return round(total_gpkwh, 2)

    def tailpipe_nox(self, rpm: int, load_pct: float) -> float:
        """Post-SCR tailpipe NOx (g/kWh)."""
        engine_out = self.engine_out_nox(rpm, load_pct)
        return round(engine_out * (1 - self.scr_efficiency), 3)


# ============================================================
#  THERMAL MANAGEMENT
# ============================================================

@dataclass
class ThermalState:
    """Engine thermal state."""
    coolant_temp_c: float = 90.0
    oil_temp_c: float = 95.0
    exhaust_temp_c: float = 450.0
    intercooler_outlet_c: float = 45.0
    egt_spread_c: float = 15.0        # Max cylinder-to-cylinder spread


class ThermalModel:
    """Simplified thermal management model."""

    def __init__(self, spec: AICESpec):
        self.spec = spec

    def exhaust_temp(self, rpm: int, load_pct: float) -> float:
        """Exhaust gas temperature (°C)."""
        base = 250 + 350 * (load_pct / 100) ** 0.8
        rpm_correction = 50 * (rpm / self.spec.rated_rpm - 0.5)
        return round(min(self.spec.max_exhaust_temp_c, base + rpm_correction), 1)

    def heat_rejection_kw(self, power_kw: float, bte: float) -> Dict[str, float]:
        """Heat rejection breakdown (kW)."""
        if bte <= 0 or power_kw <= 0:
            return {"coolant": 0, "oil": 0, "exhaust": 0, "radiation": 0}

        total_fuel_energy = power_kw / bte
        waste = total_fuel_energy - power_kw

        return {
            "coolant": round(waste * 0.35, 1),
            "oil": round(waste * 0.08, 1),
            "exhaust": round(waste * 0.50, 1),
            "radiation": round(waste * 0.07, 1),
        }

    def compute_state(self, rpm: int, load_pct: float, ambient_c: float = 25.0) -> ThermalState:
        """Compute full thermal state."""
        return ThermalState(
            coolant_temp_c=round(75 + 20 * (load_pct / 100), 1),
            oil_temp_c=round(80 + 25 * (load_pct / 100), 1),
            exhaust_temp_c=self.exhaust_temp(rpm, load_pct),
            intercooler_outlet_c=round(ambient_c + 20 + 10 * (load_pct / 100), 1),
            egt_spread_c=round(5 + 15 * (load_pct / 100) ** 0.5, 1),
        )


# ============================================================
#  FULL ENGINE SIMULATOR
# ============================================================

class AICESimulator:
    """Complete A-ICE-G1 engine simulation."""

    def __init__(self, spec: AICESpec = None):
        self.spec = spec or AICESpec()
        self.combustion = CombustionModel(self.spec)
        self.nox = NOxModel(scr_efficiency=0.95)
        self.thermal = ThermalModel(self.spec)
        self.nh3 = NH3Properties()
        # Inverter for genset mode
        if self.spec.inverter_enabled:
            self.inverter = InverterModel(preset="aice_genset_335kw")
        else:
            self.inverter = None

    def operating_point(self, rpm: int, load_pct: float, ambient_c: float = 25.0) -> dict:
        """Compute all outputs at a single operating point."""
        torque = self.combustion.torque_at_rpm(rpm, load_pct)
        power = self.combustion.power_at_rpm(rpm, load_pct)
        bte = self.combustion.brake_thermal_efficiency(rpm, load_pct)
        bsfc_val = self.combustion.bsfc(rpm, load_pct)
        nh3_flow = self.combustion.nh3_flow_kg_h(rpm, load_pct)
        h2_flow = self.combustion.h2_flow_kg_h(rpm, load_pct)
        nox_out = self.nox.engine_out_nox(rpm, load_pct)
        nox_tail = self.nox.tailpipe_nox(rpm, load_pct)
        thermal_state = self.thermal.compute_state(rpm, load_pct, ambient_c)
        heat_rej = self.thermal.heat_rejection_kw(power, bte)

        # Genset mode: generator + inverter chain
        if self.inverter is not None:
            p_generator = power * self.spec.generator_efficiency
            inv_result = self.inverter.ac_output(p_generator, ambient_c)
            electrical_kw = inv_result["ac_power_kw"]
            inverter_eta = inv_result["efficiency"]
            reactive_kvar = inv_result["reactive_available_kvar"]
        else:
            electrical_kw = None
            inverter_eta = None
            reactive_kvar = None

        result = {
            "rpm": rpm,
            "load_pct": load_pct,
            "torque_nm": torque,
            "power_kw": power,
            "power_hp": round(power * 1.341, 1),
            "bte_pct": round(bte * 100, 2),
            "bsfc_g_kwh": bsfc_val,
            "nh3_flow_kg_h": nh3_flow,
            "h2_flow_kg_h": h2_flow,
            "total_fuel_kg_h": round(nh3_flow + h2_flow, 2),
            "nox_engine_out_gpkwh": nox_out,
            "nox_tailpipe_gpkwh": nox_tail,
            "co2_gpkwh": 0.0,  # Zero carbon fuel
            "exhaust": {
                "temp_c": thermal_state.exhaust_temp_c,
                "egt_spread_c": thermal_state.egt_spread_c,
            },
            "thermal": {
                "coolant_c": thermal_state.coolant_temp_c,
                "oil_c": thermal_state.oil_temp_c,
                "intercooler_c": thermal_state.intercooler_outlet_c,
                "heat_rejection_kw": heat_rej,
            },
        }

        # Add electrical output fields if genset mode
        if electrical_kw is not None:
            result["electrical_power_kw"] = round(electrical_kw, 1)
            result["generator_efficiency_pct"] = round(self.spec.generator_efficiency * 100, 1)
            result["inverter_efficiency_pct"] = round(inverter_eta * 100, 1) if inverter_eta else None
            result["reactive_available_kvar"] = reactive_kvar

        return result

    def full_map(self, rpm_range: range = None, load_range: range = None) -> List[dict]:
        """Generate full engine performance map."""
        if rpm_range is None:
            rpm_range = range(self.spec.idle_rpm, self.spec.rated_rpm + 100, 100)
        if load_range is None:
            load_range = range(10, 101, 10)

        results = []
        for rpm in rpm_range:
            for load in load_range:
                results.append(self.operating_point(rpm, load))
        return results

    def drive_cycle(self, speed_profile_kmh: List[float], dt_s: float = 1.0,
                    vehicle_mass_kg: float = 40000, cd: float = 0.6,
                    frontal_area_m2: float = 10.0, crr: float = 0.007) -> dict:
        """
        Simulate a drive cycle.
        Returns total energy, fuel consumption, and emissions.
        """
        total_energy_kwh = 0
        total_nh3_kg = 0
        total_h2_kg = 0
        total_nox_g = 0
        total_distance_km = 0

        for speed in speed_profile_kmh:
            v = speed / 3.6  # m/s

            # Road load power
            f_aero = 0.5 * 1.225 * cd * frontal_area_m2 * v ** 2
            f_roll = crr * vehicle_mass_kg * 9.81
            f_total = f_aero + f_roll
            power_kw = max(0.1, f_total * v / 1000)

            # Map to engine RPM/load (simplified — assume gear ratio gives ~1400 RPM at cruise)
            rpm = int(min(self.spec.rated_rpm, max(self.spec.idle_rpm,
                         800 + speed * 8)))
            load_pct = min(100, max(5, power_kw / self.spec.rated_power_kw * 100))

            op = self.operating_point(rpm, load_pct)

            total_energy_kwh += power_kw * dt_s / 3600
            total_nh3_kg += op["nh3_flow_kg_h"] * dt_s / 3600
            total_h2_kg += op["h2_flow_kg_h"] * dt_s / 3600
            total_nox_g += op["nox_tailpipe_gpkwh"] * power_kw * dt_s / 3600
            total_distance_km += speed * dt_s / 3600

        return {
            "distance_km": round(total_distance_km, 1),
            "energy_kwh": round(total_energy_kwh, 1),
            "nh3_consumed_kg": round(total_nh3_kg, 2),
            "h2_consumed_kg": round(total_h2_kg, 3),
            "total_fuel_kg": round(total_nh3_kg + total_h2_kg, 2),
            "fuel_economy_kg_100km": round((total_nh3_kg + total_h2_kg) / max(0.1, total_distance_km) * 100, 2),
            "nox_total_g": round(total_nox_g, 2),
            "co2_total_g": 0.0,
        }


# ============================================================
#  CLI
# ============================================================

def main():
    sim = AICESimulator()

    print(f"\n{'='*65}")
    print(f"  {sim.spec.name} — Ammonia Engine Simulator")
    print(f"  PRIMEnergeia S.A.S. | PRIMEngines Division")
    print(f"{'='*65}")
    print(f"  Config:       {sim.spec.configuration}")
    print(f"  Displacement: {sim.spec.displacement_L} L / {sim.spec.cylinders} cyl")
    print(f"  Rated Power:  {sim.spec.rated_power_kw} kW ({sim.spec.rated_power_kw * 1.341:.0f} HP)")
    print(f"  Max Torque:   {sim.spec.max_torque_nm} Nm @ {sim.spec.max_torque_rpm} RPM")
    print(f"  Fuel:         {sim.spec.primary_fuel} + {sim.spec.pilot_fuel}")
    print(f"  CR:           {sim.spec.compression_ratio}:1")
    print(f"  Aftertreat:   {sim.spec.aftertreatment}")
    print(f"{'='*65}\n")

    # Performance map at key points
    print(f"  {'RPM':>5} {'Load%':>6} {'Torque':>8} {'Power':>8} {'BTE':>6} {'BSFC':>7} {'NH₃':>7} {'NOx':>7}")
    print(f"  {'':>5} {'':>6} {'(Nm)':>8} {'(kW)':>8} {'(%)':>6} {'(g/kWh)':>7} {'(kg/h)':>7} {'(g/kWh)':>7}")
    print(f"  {'─'*60}")

    for rpm in [800, 1000, 1200, 1400, 1600, 1800, 2000, 2100]:
        for load in [25, 50, 75, 100]:
            op = sim.operating_point(rpm, load)
            print(f"  {rpm:>5} {load:>5}%  {op['torque_nm']:>7.0f}  {op['power_kw']:>7.1f}  "
                  f"{op['bte_pct']:>5.1f}  {op['bsfc_g_kwh']:>6.1f}  {op['nh3_flow_kg_h']:>6.1f}  "
                  f"{op['nox_tailpipe_gpkwh']:>6.3f}")
        print()

    # Simulated highway cycle
    print(f"\n  DRIVE CYCLE — 40-ton truck, 100 km @ 80 km/h")
    print(f"  {'─'*50}")
    cycle = [80.0] * 4500  # 4500s at 80 km/h ≈ 100 km
    result = sim.drive_cycle(cycle, dt_s=1.0)
    for k, v in result.items():
        print(f"  {k:<25} {v}")

    # Export
    export = {
        "engine": asdict(sim.spec),
        "fuel_nh3": asdict(sim.nh3),
        "rated_point": sim.operating_point(sim.spec.rated_rpm, 100),
        "drive_cycle_100km": result,
    }
    with open("aice_g1_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to aice_g1_results.json")


if __name__ == "__main__":
    main()
