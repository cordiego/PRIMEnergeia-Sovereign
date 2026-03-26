#!/usr/bin/env python3
"""
PRIMEngines HY-P100 — Hydrogen Gas Turbine Simulator
======================================================
PRIMEnergeia S.A.S. | PRIMEngines Division

Brayton-cycle micro gas turbine simulation for H₂ fuel:
  - Ideal/real Brayton cycle thermodynamics
  - Compressor & turbine polytropic efficiency maps
  - H₂ combustor model (lean premixed, low-NOx)
  - Part-load performance (VGV + fuel scheduling)
  - Heat recovery (CHP mode)
  - Ramp-rate capability for grid peaking

Reference: Lefebvre & Ballal, "Gas Turbine Combustion" (2010)
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import List, Dict

try:
    from power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS
except ImportError:
    from lib.engines.power_electronics import InverterModel, InverterSpec, INVERTER_PRESETS

# ============================================================
#  TURBINE SPECIFICATION
# ============================================================

@dataclass
class HYP100Spec:
    """HY-P100 hydrogen micro gas turbine specification."""
    name: str = "PRIMEngines HY-P100"
    rated_power_kw: float = 100.0
    electrical_efficiency_pct: float = 33.0  # ISO conditions
    chp_efficiency_pct: float = 85.0         # With heat recovery
    turbine_inlet_temp_c: float = 1050.0     # TIT
    exhaust_temp_c: float = 280.0
    pressure_ratio: float = 7.5
    mass_flow_kg_s: float = 0.85

    # Compressor
    compressor_stages: int = 2               # Centrifugal
    compressor_polytropic_eff: float = 0.85
    compressor_surge_margin_pct: float = 15.0

    # Turbine
    turbine_stages: int = 1                  # Radial inflow
    turbine_polytropic_eff: float = 0.88

    # Combustor
    combustor_type: str = "Lean Premixed (DLE)"
    combustor_efficiency: float = 0.995
    nox_15pct_o2_ppm: float = 15.0           # @ 15% O₂

    # Generator
    generator_type: str = "Permanent Magnet (high-speed)"
    generator_speed_rpm: int = 70000
    generator_efficiency: float = 0.96
    inverter_efficiency: float = 0.98

    # Physical
    weight_kg: float = 350.0
    length_mm: float = 1800
    width_mm: float = 800
    height_mm: float = 900

    # Fuel
    fuel: str = "Green H₂"
    h2_lhv_mj_kg: float = 120.0

    # Ramp rate
    cold_start_min: float = 5.0
    hot_start_min: float = 1.0
    ramp_rate_pct_s: float = 10.0   # 10%/second


# ============================================================
#  BRAYTON CYCLE MODEL
# ============================================================

class BraytonCycle:
    """
    Real Brayton cycle with polytropic compression/expansion.
    Accounts for pressure drops, mechanical losses, and generator efficiency.
    """

    # Gas properties
    Cp_air = 1.005     # kJ/kg·K
    gamma_air = 1.4
    Cp_exhaust = 1.15  # kJ/kg·K (H₂ combustion products — mostly N₂ + H₂O)
    gamma_exhaust = 1.33

    def __init__(self, spec: HYP100Spec):
        self.spec = spec
        # Power electronics model for generator → inverter → grid
        self.inverter = InverterModel(preset="h2_turbine_100kw")

    def compressor_outlet_temp(self, t_inlet_k: float, pr: float = None) -> float:
        """Compressor discharge temperature (K)."""
        if pr is None:
            pr = self.spec.pressure_ratio
        eta_p = self.spec.compressor_polytropic_eff
        exponent = (self.gamma_air - 1) / (self.gamma_air * eta_p)
        return t_inlet_k * pr ** exponent

    def turbine_outlet_temp(self, t_inlet_k: float, pr: float = None) -> float:
        """Turbine exhaust temperature (K)."""
        if pr is None:
            pr = self.spec.pressure_ratio
        # Account for combustor pressure drop (~3%)
        pr_turbine = pr * 0.97
        eta_p = self.spec.turbine_polytropic_eff
        exponent = self.gamma_exhaust * eta_p / (self.gamma_exhaust - 1)
        return t_inlet_k / (pr_turbine ** (1 / exponent))

    def cycle_efficiency(self, t_ambient_k: float = 288.15, load_pct: float = 100) -> dict:
        """
        Full cycle calculation at given ambient conditions and load.
        Returns detailed thermodynamic state points.
        """
        T1 = t_ambient_k  # Compressor inlet

        # Adjust TIT for part load (fuel scheduling)
        tit_full = self.spec.turbine_inlet_temp_c + 273.15
        tit = tit_full * (0.7 + 0.3 * load_pct / 100)  # Reduce TIT at part load
        T3 = tit

        # Part-load pressure ratio (VGV adjustment)
        pr = self.spec.pressure_ratio * (0.6 + 0.4 * load_pct / 100)

        # State points
        T2 = self.compressor_outlet_temp(T1, pr)  # Compressor outlet
        T4 = self.turbine_outlet_temp(T3, pr)      # Turbine outlet

        # Specific work
        w_compressor = self.Cp_air * (T2 - T1)           # kJ/kg
        w_turbine = self.Cp_exhaust * (T3 - T4)           # kJ/kg
        q_in = self.Cp_exhaust * (T3 - T2) * self.spec.combustor_efficiency  # Heat input

        # Net specific work
        w_net = w_turbine - w_compressor
        if w_net <= 0 or q_in <= 0:
            return {"error": "Cycle not viable at this condition"}

        # Mass flow at part load
        m_dot = self.spec.mass_flow_kg_s * (load_pct / 100) ** 0.8

        # Gross shaft power
        p_shaft = w_net * m_dot  # kW

        # Mechanical / generator losses
        p_generator = p_shaft * 0.98 * self.spec.generator_efficiency  # 2% mech loss
        # Inverter DC→AC conversion (load-dependent efficiency)
        inv_result = self.inverter.ac_output(p_generator)
        p_electrical = inv_result["ac_power_kw"]

        # Thermal efficiency
        eta_thermal = w_net / q_in
        eta_electrical = p_electrical / (q_in * m_dot)

        # Fuel consumption
        h2_flow = q_in * m_dot / (self.spec.h2_lhv_mj_kg * 1000)  # kg/s
        heat_rate = 3600 / max(0.01, eta_electrical)  # kJ/kWh

        # Exhaust heat available for CHP
        exhaust_heat_kw = self.Cp_exhaust * m_dot * (T4 - T1 - 20)  # Cool to near ambient

        return {
            "ambient_c": round(T1 - 273.15, 1),
            "load_pct": load_pct,
            "pressure_ratio": round(pr, 2),
            "T1_compressor_inlet_c": round(T1 - 273.15, 1),
            "T2_compressor_outlet_c": round(T2 - 273.15, 1),
            "T3_turbine_inlet_c": round(T3 - 273.15, 1),
            "T4_turbine_outlet_c": round(T4 - 273.15, 1),
            "w_compressor_kj_kg": round(w_compressor, 1),
            "w_turbine_kj_kg": round(w_turbine, 1),
            "w_net_kj_kg": round(w_net, 1),
            "q_in_kj_kg": round(q_in, 1),
            "mass_flow_kg_s": round(m_dot, 3),
            "shaft_power_kw": round(p_shaft, 1),
            "electrical_power_kw": round(p_electrical, 1),
            "thermal_efficiency_pct": round(eta_thermal * 100, 1),
            "electrical_efficiency_pct": round(eta_electrical * 100, 1),
            "heat_rate_kj_kwh": round(heat_rate, 0),
            "h2_flow_kg_s": round(h2_flow, 5),
            "h2_flow_kg_h": round(h2_flow * 3600, 2),
            "exhaust_heat_kw": round(exhaust_heat_kw, 1),
            "chp_efficiency_pct": round((p_electrical + exhaust_heat_kw) / (q_in * m_dot) * 100, 1),
            "nox_ppm_15_o2": round(self.spec.nox_15pct_o2_ppm * (load_pct / 100) ** 0.7, 1),
            "co2_g_kwh": 0.0,
        }

    def ramp_profile(self, start_pct: float, end_pct: float,
                     ramp_rate: float = None) -> List[dict]:
        """Generate load ramp profile (time series)."""
        if ramp_rate is None:
            ramp_rate = self.spec.ramp_rate_pct_s  # %/second

        dt = 0.1  # 100ms timestep
        current_load = start_pct
        direction = 1 if end_pct > start_pct else -1
        profile = []

        t = 0
        while (direction == 1 and current_load < end_pct) or \
              (direction == -1 and current_load > end_pct):
            current_load += direction * ramp_rate * dt
            current_load = max(0, min(100, current_load))
            result = self.cycle_efficiency(load_pct=current_load)
            result["time_s"] = round(t, 1)
            profile.append(result)
            t += dt

        return profile


def main():
    spec = HYP100Spec()
    cycle = BraytonCycle(spec)

    print(f"\n{'='*65}")
    print(f"  {spec.name} — H₂ Gas Turbine Simulator")
    print(f"  PRIMEnergeia S.A.S. | PRIMEngines Division")
    print(f"{'='*65}")
    print(f"  PR:     {spec.pressure_ratio}:1")
    print(f"  TIT:    {spec.turbine_inlet_temp_c}°C")
    print(f"  Gen:    {spec.generator_type} @ {spec.generator_speed_rpm:,} RPM")
    print(f"  Fuel:   {spec.fuel}")
    print(f"  Weight: {spec.weight_kg} kg")
    print(f"  Ramp:   {spec.ramp_rate_pct_s}%/s")
    print(f"{'='*65}\n")

    print(f"  {'Load':>5} {'PR':>5} {'TIT°C':>6} {'Exh°C':>6} {'Pelec':>6} {'η_el':>5} {'η_CHP':>6} {'H₂ kg/h':>8} {'NOx':>5}")
    print(f"  {'─'*62}")

    for load in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        r = cycle.cycle_efficiency(load_pct=load)
        print(f"  {load:>4}%  {r['pressure_ratio']:>4.1f}  {r['T3_turbine_inlet_c']:>5.0f}  "
              f"{r['T4_turbine_outlet_c']:>5.0f}  {r['electrical_power_kw']:>5.1f}  "
              f"{r['electrical_efficiency_pct']:>4.1f}  {r['chp_efficiency_pct']:>5.1f}  "
              f"{r['h2_flow_kg_h']:>7.2f}  {r['nox_ppm_15_o2']:>4.1f}")

    # Ramp test
    print(f"\n  RAMP TEST: 20% → 100% load")
    print(f"  {'─'*40}")
    ramp = cycle.ramp_profile(20, 100)
    print(f"  Ramp time: {ramp[-1]['time_s']:.1f} seconds ({len(ramp)} points)")
    print(f"  Final power: {ramp[-1]['electrical_power_kw']:.1f} kW")

    # Ambient correction
    print(f"\n  AMBIENT CORRECTION")
    print(f"  {'─'*40}")
    for temp_c in [-10, 0, 15, 30, 45]:
        r = cycle.cycle_efficiency(t_ambient_k=temp_c + 273.15, load_pct=100)
        print(f"  {temp_c:>4}°C: {r['electrical_power_kw']:>6.1f} kW  η={r['electrical_efficiency_pct']:.1f}%")

    export = {
        "spec": asdict(spec),
        "iso_rated": cycle.cycle_efficiency(load_pct=100),
        "part_load": [cycle.cycle_efficiency(load_pct=l) for l in range(10, 101, 10)],
    }
    with open("hyp100_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to hyp100_results.json")


if __name__ == "__main__":
    main()

