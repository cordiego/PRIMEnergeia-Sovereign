#!/usr/bin/env python3
"""
PRIM Wind — Hydrogen-Ready Wind Farm Simulator
=================================================
PRIMEnergeia S.A.S. | PRIM Wind Division

Wind energy + green H₂ production model:
  - IEC 61400 power curve modeling
  - Weibull wind distribution + AEP calculation
  - Wake effects (Jensen / Park model)
  - PEM electrolyzer coupling for green H₂
  - Site assessment (capacity factor mapping)
  - Financial model (PPA, H₂ sales, RECs)

Reference: Manwell, McGowan & Rogers, "Wind Energy Explained" (2009)
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

# ============================================================
#  TURBINE SPECIFICATION
# ============================================================

@dataclass
class TurbineSpec:
    """15 MW offshore wind turbine specification (IEA reference)."""
    name: str = "PRIM-WT-15"
    rated_power_kw: float = 15000.0
    rotor_diameter_m: float = 236.0
    hub_height_m: float = 150.0
    cut_in_ms: float = 3.0
    rated_wind_ms: float = 10.5
    cut_out_ms: float = 25.0
    iec_class: str = "IB"

    # Aerodynamics
    max_cp: float = 0.485           # Power coefficient at optimal TSR
    optimal_tsr: float = 9.0        # Tip-speed ratio
    max_tip_speed_ms: float = 95.0

    # Drive train
    drivetrain: str = "Direct-Drive PMG"
    generator_efficiency: float = 0.97
    converter_efficiency: float = 0.98

    # Physical
    nacelle_mass_t: float = 500.0
    rotor_mass_t: float = 280.0
    tower_mass_t: float = 1200.0

    @property
    def swept_area_m2(self) -> float:
        return math.pi / 4 * self.rotor_diameter_m ** 2


# ============================================================
#  WIND RESOURCE MODEL
# ============================================================

class WindResource:
    """Weibull wind speed distribution and vertical profile."""

    def __init__(self, mean_speed_ms: float, k: float = 2.0,
                 measurement_height_m: float = 10.0, roughness_length_m: float = 0.03):
        self.mean_speed = mean_speed_ms
        self.k = k  # Weibull shape parameter
        self.A = mean_speed_ms / math.gamma(1 + 1/k)  # Scale parameter
        self.z_ref = measurement_height_m
        self.z0 = roughness_length_m

    def weibull_pdf(self, v: float) -> float:
        """Weibull probability density function."""
        if v <= 0:
            return 0.0
        return (self.k / self.A) * (v / self.A) ** (self.k - 1) * \
               math.exp(-(v / self.A) ** self.k)

    def weibull_cdf(self, v: float) -> float:
        """Weibull cumulative distribution function."""
        if v <= 0:
            return 0.0
        return 1 - math.exp(-(v / self.A) ** self.k)

    def wind_at_height(self, v_ref: float, target_height_m: float) -> float:
        """Extrapolate wind speed to hub height (log law)."""
        if self.z_ref <= 0 or self.z0 <= 0:
            return v_ref
        return v_ref * math.log(target_height_m / self.z0) / math.log(self.z_ref / self.z0)

    def hours_distribution(self, v_max: float = 30.0, dv: float = 0.5) -> List[Dict]:
        """Hours per year at each wind speed bin."""
        total_hours = 8760
        bins = []
        for v in [i * dv for i in range(int(v_max / dv) + 1)]:
            prob = self.weibull_pdf(v) * dv
            hours = prob * total_hours
            bins.append({"wind_speed_ms": round(v, 1), "probability": round(prob, 5),
                        "hours_per_year": round(hours, 1)})
        return bins


# ============================================================
#  POWER CURVE MODEL
# ============================================================

class PowerCurveModel:
    """IEC 61400 compliant power curve calculation."""

    def __init__(self, turbine: TurbineSpec):
        self.t = turbine
        self.rho = 1.225  # Air density (kg/m³) at sea level

    def power_available(self, wind_speed_ms: float) -> float:
        """Available wind power (kW)."""
        return 0.5 * self.rho * self.t.swept_area_m2 * wind_speed_ms ** 3 / 1000

    def power_coefficient(self, wind_speed_ms: float) -> float:
        """Cp as function of wind speed (simplified curve)."""
        if wind_speed_ms < self.t.cut_in_ms or wind_speed_ms > self.t.cut_out_ms:
            return 0.0

        tsr = self.t.optimal_tsr * self.t.rated_wind_ms / max(0.1, wind_speed_ms)

        if wind_speed_ms <= self.t.rated_wind_ms:
            # Below rated: optimize Cp
            cp = self.t.max_cp * (1 - 0.02 * abs(tsr - self.t.optimal_tsr))
            return max(0.1, min(self.t.max_cp, cp))
        else:
            # Above rated: pitch to limit power
            cp = self.t.max_cp * (self.t.rated_wind_ms / wind_speed_ms) ** 3
            return max(0.01, cp)

    def electrical_power(self, wind_speed_ms: float) -> float:
        """Net electrical power output (kW)."""
        if wind_speed_ms < self.t.cut_in_ms or wind_speed_ms > self.t.cut_out_ms:
            return 0.0

        p_aero = self.power_available(wind_speed_ms) * self.power_coefficient(wind_speed_ms)
        p_elec = p_aero * self.t.generator_efficiency * self.t.converter_efficiency

        return min(self.t.rated_power_kw, round(p_elec, 1))

    def thrust_coefficient(self, wind_speed_ms: float) -> float:
        """Thrust coefficient for wake modeling."""
        if wind_speed_ms < self.t.cut_in_ms or wind_speed_ms > self.t.cut_out_ms:
            return 0.0

        if wind_speed_ms <= self.t.rated_wind_ms:
            return 0.85 * (1 - 0.1 * ((wind_speed_ms - 7) / 7) ** 2)
        else:
            return 0.85 * (self.t.rated_wind_ms / max(0.1, wind_speed_ms)) ** 2

    def full_curve(self, v_max: float = 30.0, dv: float = 0.5) -> List[Dict]:
        """Generate complete power curve."""
        curve = []
        for v in [i * dv for i in range(int(v_max / dv) + 1)]:
            curve.append({
                "wind_speed_ms": round(v, 1),
                "power_kw": self.electrical_power(v),
                "cp": round(self.power_coefficient(v), 4),
                "ct": round(self.thrust_coefficient(v), 4),
            })
        return curve


# ============================================================
#  WAKE MODEL (Jensen / Park)
# ============================================================

class WakeModel:
    """Jensen (Park) single-wake model for array efficiency."""

    def __init__(self, turbine: TurbineSpec, wake_decay: float = 0.04):
        self.t = turbine
        self.k_w = wake_decay  # Offshore: 0.04, Onshore: 0.075

    def wake_deficit(self, ct: float, distance_m: float) -> float:
        """Velocity deficit from single turbine wake."""
        r0 = self.t.rotor_diameter_m / 2
        rw = r0 + self.k_w * distance_m  # Wake radius
        deficit = (1 - math.sqrt(1 - ct)) * (r0 / rw) ** 2
        return min(0.5, deficit)

    def array_efficiency(self, num_turbines: int,
                         spacing_diameters: float = 7.0) -> float:
        """Approximate array efficiency for regular grid layout."""
        spacing_m = spacing_diameters * self.t.rotor_diameter_m
        rows = int(math.sqrt(num_turbines))

        total_efficiency = 0
        for row in range(rows):
            if row == 0:
                total_efficiency += 1.0  # First row = freestream
            else:
                # Assume Ct ≈ 0.75 for average conditions
                deficit = self.wake_deficit(0.75, spacing_m * row)
                v_ratio = 1 - deficit
                total_efficiency += v_ratio ** 3  # Power scales as v³

        return round(total_efficiency / rows, 4) if rows > 0 else 1.0


# ============================================================
#  ELECTROLYZER COUPLING
# ============================================================

@dataclass
class ElectrolyzerSpec:
    """PEM Electrolyzer for green H₂ production."""
    name: str = "PRIM-ELZ-100"
    rated_power_mw: float = 100.0
    efficiency_lhv: float = 0.65       # kWh_H2 / kWh_elec (LHV basis)
    h2_output_kg_mwh: float = 18.0     # kg H₂ per MWh electrical input
    water_consumption_l_kg: float = 10.0  # Liters water per kg H₂
    min_load_pct: float = 10.0
    ramp_rate_pct_s: float = 20.0
    capex_per_kw: float = 500.0        # $/kW


class H2Production:
    """Wind-to-hydrogen coupling model."""

    def __init__(self, elz: ElectrolyzerSpec = None):
        self.elz = elz or ElectrolyzerSpec()

    def h2_from_power(self, power_mw: float) -> dict:
        """H₂ production from available electrical power."""
        elz_power = min(power_mw, self.elz.rated_power_mw)
        if elz_power < self.elz.rated_power_mw * self.elz.min_load_pct / 100:
            return {"h2_kg_h": 0, "power_used_mw": 0, "curtailed_mw": power_mw}

        h2_rate = elz_power * self.elz.h2_output_kg_mwh  # kg/h
        water = h2_rate * self.elz.water_consumption_l_kg

        return {
            "h2_kg_h": round(h2_rate, 1),
            "power_used_mw": round(elz_power, 1),
            "curtailed_mw": round(max(0, power_mw - elz_power), 1),
            "water_l_h": round(water, 0),
            "efficiency_pct": round(self.elz.efficiency_lhv * 100, 1),
        }


# ============================================================
#  WIND FARM SIMULATOR
# ============================================================

class WindFarmSimulator:
    """Complete wind farm + H₂ simulation."""

    def __init__(self, turbine: TurbineSpec = None, num_turbines: int = 67,
                 wind_resource: WindResource = None, electrolyzer: ElectrolyzerSpec = None):
        self.turbine = turbine or TurbineSpec()
        self.num_turbines = num_turbines
        self.wind = wind_resource or WindResource(mean_speed_ms=9.5, k=2.1)
        self.power_model = PowerCurveModel(self.turbine)
        self.wake = WakeModel(self.turbine)
        self.h2 = H2Production(electrolyzer)

    def annual_energy_production(self) -> dict:
        """Calculate AEP with wake losses and availability."""
        wind_bins = self.wind.hours_distribution()
        array_eff = self.wake.array_efficiency(self.num_turbines)
        availability = 0.95  # 95% time-based availability

        gross_aep_mwh = 0
        net_aep_mwh = 0

        for bin in wind_bins:
            v_hub = self.wind.wind_at_height(bin["wind_speed_ms"], self.turbine.hub_height_m)
            p_single = self.power_model.electrical_power(v_hub) / 1000  # MW
            p_farm = p_single * self.num_turbines
            hours = bin["hours_per_year"]

            gross_energy = p_farm * hours
            net_energy = gross_energy * array_eff * availability

            gross_aep_mwh += gross_energy
            net_aep_mwh += net_energy

        farm_capacity = self.turbine.rated_power_kw * self.num_turbines / 1000
        capacity_factor = net_aep_mwh / (farm_capacity * 8760) if farm_capacity > 0 else 0

        # H₂ production (use average power for simplification)
        avg_power_mw = net_aep_mwh / 8760
        h2_annual = self.h2.h2_from_power(avg_power_mw)

        return {
            "farm_capacity_mw": round(farm_capacity, 0),
            "num_turbines": self.num_turbines,
            "gross_aep_gwh": round(gross_aep_mwh / 1000, 1),
            "net_aep_gwh": round(net_aep_mwh / 1000, 1),
            "wake_loss_pct": round((1 - array_eff) * 100, 1),
            "availability_pct": availability * 100,
            "capacity_factor_pct": round(capacity_factor * 100, 1),
            "equivalent_full_load_hours": round(capacity_factor * 8760, 0),
            "avg_power_mw": round(avg_power_mw, 1),
            "h2_annual_tonnes": round(h2_annual["h2_kg_h"] * 8760 / 1000, 0),
            "h2_daily_kg": round(h2_annual["h2_kg_h"] * 24, 0),
        }

    def financial_model(self, ppa_price_mwh: float = 55.0,
                        h2_price_kg: float = 4.0,
                        rec_price_mwh: float = 5.0,
                        capex_per_mw: float = 2800000) -> dict:
        """Lifetime financial projection."""
        aep = self.annual_energy_production()
        farm_mw = aep["farm_capacity_mw"]

        capex = farm_mw * capex_per_mw / 1e6  # $M
        opex_annual = capex * 0.025  # 2.5% of CapEx per year

        years = 25
        total_revenue = 0
        total_degraded_energy_mwh = 0
        for yr in range(1, years + 1):
            degradation = (1 - 0.005) ** yr
            yr_energy_mwh = aep["net_aep_gwh"] * 1000 * degradation
            total_degraded_energy_mwh += yr_energy_mwh
            energy_rev = yr_energy_mwh * ppa_price_mwh / 1e6
            h2_rev = aep["h2_annual_tonnes"] * 1000 * h2_price_kg * degradation / 1e6
            rec_rev = yr_energy_mwh * rec_price_mwh / 1e6
            total_revenue += energy_rev + h2_rev + rec_rev

        total_opex = opex_annual * years
        # LCOE uses total degraded energy over lifetime
        lcoe = (capex * 1e6 + total_opex * 1e6) / max(1, total_degraded_energy_mwh)

        return {
            "capex_M": round(capex, 0),
            "annual_opex_M": round(opex_annual, 1),
            "total_revenue_25yr_M": round(total_revenue, 0),
            "lcoe_usd_mwh": round(lcoe, 1),
            "payback_years": round(capex / max(0.1, total_revenue / years - opex_annual), 1),
            "irr_approx_pct": round((total_revenue / years - opex_annual) / capex * 100, 1),
        }


def main():
    sim = WindFarmSimulator()

    print(f"\n{'='*65}")
    print(f"  PRIM Wind — Wind Farm + H₂ Simulator")
    print(f"  PRIMEnergeia S.A.S. | PRIM Wind Division")
    print(f"{'='*65}")
    print(f"  Turbine:  {sim.turbine.name} ({sim.turbine.rated_power_kw/1000:.0f} MW)")
    print(f"  Rotor:    {sim.turbine.rotor_diameter_m} m")
    print(f"  Hub:      {sim.turbine.hub_height_m} m")
    print(f"  Farm:     {sim.num_turbines} turbines")
    print(f"  Wind:     {sim.wind.mean_speed} m/s mean (Weibull k={sim.wind.k})")
    print(f"{'='*65}\n")

    # Power curve
    print(f"  POWER CURVE")
    print(f"  {'Wind(m/s)':>10} {'Power(MW)':>10} {'Cp':>6} {'Ct':>6}")
    print(f"  {'─'*36}")
    for point in sim.power_model.full_curve()[::4]:  # Every 2 m/s
        print(f"  {point['wind_speed_ms']:>10.1f} {point['power_kw']/1000:>9.1f} "
              f"{point['cp']:>5.3f} {point['ct']:>5.3f}")

    # AEP
    print(f"\n  ANNUAL ENERGY PRODUCTION")
    print(f"  {'─'*45}")
    aep = sim.annual_energy_production()
    for k, v in aep.items():
        print(f"  {k:<30} {v}")

    # Financials
    print(f"\n  FINANCIAL MODEL (25yr)")
    print(f"  {'─'*45}")
    fin = sim.financial_model()
    for k, v in fin.items():
        print(f"  {k:<30} {v}")

    export = {
        "turbine": asdict(sim.turbine),
        "aep": aep,
        "financials": fin,
    }
    with open("prim_wind_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to prim_wind_results.json")


if __name__ == "__main__":
    main()
