#!/usr/bin/env python3
"""
PRIMEnergeia Battery — Grid-Scale Energy Storage Simulator
============================================================
PRIMEnergeia S.A.S. | Battery Division

Battery energy storage system (BESS) model:
  - Cell-level electrochemistry (equivalent circuit)
  - Multi-chemistry support (LFP, NMC, SSB, VRFB)
  - Calendar + cycle aging (semi-empirical)
  - Dispatch optimizer (peak shaving, arbitrage, freq. reg.)
  - Revenue stack calculator (energy, capacity, ancillary)
  - Thermal management (HVAC, liquid cooling)

Reference: Jossen, "Fundamentals of Battery Dynamics" (2006)
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

# ============================================================
#  CELL CHEMISTRY MODELS
# ============================================================

@dataclass
class CellChemistry:
    """Battery cell chemistry parameters."""
    name: str = "LFP"
    nominal_voltage_v: float = 3.2
    capacity_ah: float = 280.0
    energy_density_wh_kg: float = 160.0
    energy_density_wh_l: float = 350.0
    cycle_life_80pct: int = 6000
    calendar_life_yr: int = 20
    charge_rate_c: float = 1.0
    discharge_rate_c: float = 2.0
    round_trip_eff: float = 0.945
    min_soc: float = 0.05
    max_soc: float = 0.95
    temp_range_c: Tuple[float, float] = (-20.0, 55.0)
    self_discharge_pct_month: float = 2.0
    cost_per_kwh: float = 110.0

    # Equivalent circuit model
    r_internal_mohm: float = 0.8      # Internal resistance (mΩ)
    r_ct_mohm: float = 0.3            # Charge transfer resistance
    tau_rc_s: float = 30.0             # RC time constant


CHEMISTRIES = {
    "LFP": CellChemistry(
        name="LFP", nominal_voltage_v=3.2, capacity_ah=280, energy_density_wh_kg=160,
        cycle_life_80pct=6000, round_trip_eff=0.945, cost_per_kwh=110, r_internal_mohm=0.8
    ),
    "NMC811": CellChemistry(
        name="NMC811", nominal_voltage_v=3.7, capacity_ah=100, energy_density_wh_kg=250,
        cycle_life_80pct=2000, round_trip_eff=0.935, cost_per_kwh=130, r_internal_mohm=1.2
    ),
    "SSB": CellChemistry(
        name="Solid-State (SSB)", nominal_voltage_v=3.8, capacity_ah=80, energy_density_wh_kg=400,
        cycle_life_80pct=10000, round_trip_eff=0.96, cost_per_kwh=200, r_internal_mohm=0.5,
        self_discharge_pct_month=0.5
    ),
    "VRFB": CellChemistry(
        name="Vanadium Redox Flow", nominal_voltage_v=1.4, capacity_ah=1000, energy_density_wh_kg=25,
        cycle_life_80pct=20000, round_trip_eff=0.78, cost_per_kwh=350, r_internal_mohm=0.3,
        self_discharge_pct_month=0.1, charge_rate_c=0.25, discharge_rate_c=0.25
    ),
}


# ============================================================
#  SYSTEM SPECIFICATION
# ============================================================

@dataclass
class BESSSpec:
    """Battery Energy Storage System specification."""
    name: str = "PRIMEnergeia BESS-400"
    chemistry: str = "LFP"
    energy_mwh: float = 400.0
    power_mw: float = 100.0
    duration_h: float = 4.0
    modules_series: int = 15         # Cells in series per module
    modules_parallel: int = 10       # Modules in parallel per string
    strings: int = 834               # Total strings

    # BOS
    inverter_efficiency: float = 0.985
    transformer_efficiency: float = 0.995
    hvac_power_pct: float = 0.02     # % of rated power for cooling

    # Financial
    capex_per_kwh: float = 180.0     # Installed $/kWh
    opex_per_kwh_yr: float = 5.0     # Annual O&M
    warranty_yr: int = 25


# ============================================================
#  DEGRADATION MODEL
# ============================================================

class DegradationModel:
    """
    Semi-empirical battery degradation combining:
    - Calendar aging (SEI growth, sqrt(t) law)
    - Cycle aging (Ah-throughput model)
    - Temperature acceleration (Arrhenius)
    """

    def __init__(self, cell: CellChemistry):
        self.cell = cell

    def calendar_aging(self, years: float, avg_temp_c: float = 25.0,
                       avg_soc: float = 0.5) -> float:
        """Capacity loss from calendar aging (fraction)."""
        # Arrhenius temperature factor
        Ea = 24500  # Activation energy (J/mol)
        R = 8.314
        T_ref = 298.15
        T = avg_temp_c + 273.15
        k_T = math.exp(-Ea / R * (1/T - 1/T_ref))

        # SOC stress factor (higher SOC = faster aging)
        k_soc = 1 + 1.5 * (avg_soc - 0.5) ** 2

        # Base rate from cycle life target
        base_rate = 0.20 / (self.cell.calendar_life_yr ** 0.5)

        loss = base_rate * k_T * k_soc * math.sqrt(years)
        return min(0.40, loss)  # Cap at 40% loss

    def cycle_aging(self, equivalent_full_cycles: int, dod: float = 0.80,
                    avg_temp_c: float = 25.0) -> float:
        """Capacity loss from cycling (fraction)."""
        # Cycles to 80% SOH
        N80 = self.cell.cycle_life_80pct

        # DOD stress (deeper cycles = more damage)
        k_dod = (dod / 0.80) ** 1.5

        # Temperature factor
        k_T = 1.0 + 0.05 * max(0, avg_temp_c - 25)

        loss = 0.20 * (equivalent_full_cycles / N80) * k_dod * k_T
        return min(0.40, loss)

    def total_degradation(self, years: float, cycles_per_year: float = 365,
                          dod: float = 0.80, avg_temp_c: float = 25.0) -> dict:
        """Combined calendar + cycle degradation."""
        total_cycles = int(years * cycles_per_year)
        cal = self.calendar_aging(years, avg_temp_c)
        cyc = self.cycle_aging(total_cycles, dod, avg_temp_c)

        # Combined (not simply additive — use sqrt of sum of squares)
        combined = math.sqrt(cal**2 + cyc**2)
        combined = min(0.40, combined)

        return {
            "years": years,
            "equivalent_cycles": total_cycles,
            "calendar_loss_pct": round(cal * 100, 2),
            "cycle_loss_pct": round(cyc * 100, 2),
            "total_loss_pct": round(combined * 100, 2),
            "soh_pct": round((1 - combined) * 100, 2),
            "remaining_capacity_pct": round((1 - combined) * 100, 2),
        }


# ============================================================
#  DISPATCH OPTIMIZER
# ============================================================

class DispatchOptimizer:
    """Simple rule-based dispatch for BESS revenue optimization."""

    def __init__(self, spec: BESSSpec, cell: CellChemistry):
        self.spec = spec
        self.cell = cell

    def daily_arbitrage(self, prices_24h: List[float], soc_init: float = 0.5) -> dict:
        """
        Simple peak-shaving arbitrage over 24 hours.
        Charge during cheapest 4 hours, discharge during most expensive 4 hours.
        """
        if len(prices_24h) != 24:
            raise ValueError("Need 24 hourly prices")

        indexed = [(p, i) for i, p in enumerate(prices_24h)]
        sorted_prices = sorted(indexed)

        # Cheapest 4 hours = charge, most expensive 4 hours = discharge
        charge_hours = {h for _, h in sorted_prices[:int(self.spec.duration_h)]}
        discharge_hours = {h for _, h in sorted_prices[-int(self.spec.duration_h):]}

        soc = soc_init
        schedule = []
        charge_cost = 0
        discharge_revenue = 0

        for hour in range(24):
            price = prices_24h[hour]
            action = "idle"
            power_mw = 0
            energy_mwh = 0

            if hour in charge_hours and soc < self.cell.max_soc:
                action = "charge"
                energy_available = (self.cell.max_soc - soc) * self.spec.energy_mwh
                energy_mwh = min(self.spec.power_mw, energy_available)
                soc += energy_mwh / self.spec.energy_mwh
                power_mw = -energy_mwh  # Negative = charging
                charge_cost += energy_mwh * price

            elif hour in discharge_hours and soc > self.cell.min_soc:
                action = "discharge"
                energy_available = (soc - self.cell.min_soc) * self.spec.energy_mwh
                energy_mwh = min(self.spec.power_mw, energy_available)
                soc -= energy_mwh / self.spec.energy_mwh
                power_mw = energy_mwh * self.cell.round_trip_eff
                discharge_revenue += power_mw * price

            schedule.append({
                "hour": hour,
                "price_usd_mwh": price,
                "action": action,
                "power_mw": round(power_mw, 1),
                "soc_pct": round(soc * 100, 1),
            })

        net_revenue = discharge_revenue - charge_cost

        return {
            "schedule": schedule,
            "charge_cost_usd": round(charge_cost, 0),
            "discharge_revenue_usd": round(discharge_revenue, 0),
            "net_revenue_usd": round(net_revenue, 0),
            "cycles_used": 1.0,
        }


# ============================================================
#  REVENUE MODEL
# ============================================================

class RevenueModel:
    """Multi-stream BESS revenue calculator."""

    def __init__(self, spec: BESSSpec, cell: CellChemistry, degradation: DegradationModel):
        self.spec = spec
        self.cell = cell
        self.degradation = degradation

    def annual_revenue(self, year: int, energy_price_spread: float = 40.0,
                       capacity_price_kw_yr: float = 50.0,
                       ancillary_price_mw_h: float = 15.0) -> dict:
        """Annual revenue from all streams."""
        # Degradation at this year
        deg = self.degradation.total_degradation(year)
        soh = deg["soh_pct"] / 100

        # Energy arbitrage (spread × energy × days × RTE × SOH)
        arbitrage = (energy_price_spread * self.spec.energy_mwh *
                     365 * self.cell.round_trip_eff * soh / 1e6)

        # Capacity payments ($/kW-yr × power MW × 1000 × SOH)
        capacity = capacity_price_kw_yr * self.spec.power_mw * 1000 * soh / 1e6

        # Ancillary services (freq reg: $/MW-h × power × hours/day × days)
        ancillary_hours = 8  # Available 8h/day for frequency regulation
        ancillary = (ancillary_price_mw_h * self.spec.power_mw *
                     ancillary_hours * 365 * soh / 1e6)

        total = arbitrage + capacity + ancillary

        # O&M cost
        opex = self.spec.opex_per_kwh_yr * self.spec.energy_mwh * 1000 / 1e6

        return {
            "year": year,
            "soh_pct": deg["soh_pct"],
            "arbitrage_M": round(arbitrage, 2),
            "capacity_M": round(capacity, 2),
            "ancillary_M": round(ancillary, 2),
            "gross_revenue_M": round(total, 2),
            "opex_M": round(opex, 2),
            "net_revenue_M": round(total - opex, 2),
        }

    def lifetime_economics(self, years: int = 25) -> dict:
        """Full lifetime economic projection."""
        capex = self.spec.capex_per_kwh * self.spec.energy_mwh * 1000 / 1e6
        yearly = []
        cum_net = 0

        for yr in range(1, years + 1):
            rev = self.annual_revenue(yr)
            cum_net += rev["net_revenue_M"]
            rev["cumulative_net_M"] = round(cum_net, 2)
            yearly.append(rev)

        # Payback period
        payback = None
        for yr_data in yearly:
            if yr_data["cumulative_net_M"] >= capex:
                payback = yr_data["year"]
                break

        total_revenue = sum(y["gross_revenue_M"] for y in yearly)
        total_net = sum(y["net_revenue_M"] for y in yearly)

        return {
            "capex_M": round(capex, 1),
            "lifetime_gross_revenue_M": round(total_revenue, 1),
            "lifetime_net_revenue_M": round(total_net, 1),
            "roi_pct": round((total_net - capex) / capex * 100, 1),
            "payback_years": payback,
            "yearly_detail": yearly,
        }


# ============================================================
#  CLI
# ============================================================

def main():
    spec = BESSSpec()
    cell = CHEMISTRIES[spec.chemistry]
    deg = DegradationModel(cell)
    rev = RevenueModel(spec, cell, deg)

    print(f"\n{'='*65}")
    print(f"  {spec.name} — Grid-Scale Battery Simulator")
    print(f"  PRIMEnergeia S.A.S. | Battery Division")
    print(f"{'='*65}")
    print(f"  Chemistry:  {cell.name}")
    print(f"  Energy:     {spec.energy_mwh} MWh")
    print(f"  Power:      {spec.power_mw} MW")
    print(f"  Duration:   {spec.duration_h} hours")
    print(f"  RTE:        {cell.round_trip_eff * 100:.1f}%")
    print(f"  Cycle Life: {cell.cycle_life_80pct:,} (to 80% SOH)")
    print(f"{'='*65}\n")

    # Degradation projection
    print(f"  DEGRADATION PROJECTION ({cell.name})")
    print(f"  {'Year':>5} {'Cycles':>7} {'Cal%':>6} {'Cyc%':>6} {'Total%':>7} {'SOH%':>6}")
    print(f"  {'─'*43}")
    for yr in [1, 2, 5, 10, 15, 20, 25]:
        d = deg.total_degradation(yr)
        print(f"  {yr:>5} {d['equivalent_cycles']:>7,} {d['calendar_loss_pct']:>5.1f} "
              f"{d['cycle_loss_pct']:>5.1f}  {d['total_loss_pct']:>5.1f}  {d['soh_pct']:>5.1f}")

    # Revenue
    print(f"\n  LIFETIME ECONOMICS (25yr)")
    print(f"  {'─'*55}")
    econ = rev.lifetime_economics(25)
    print(f"  CapEx:             ${econ['capex_M']:.1f}M")
    print(f"  Lifetime Revenue:  ${econ['lifetime_gross_revenue_M']:.1f}M")
    print(f"  Lifetime Net:      ${econ['lifetime_net_revenue_M']:.1f}M")
    print(f"  ROI:               {econ['roi_pct']:.1f}%")
    print(f"  Payback:           {econ['payback_years']} years")

    # Daily dispatch
    print(f"\n  DAILY ARBITRAGE (sample prices)")
    prices = [25, 22, 20, 18, 19, 22, 35, 55, 75, 65, 50, 45,
              42, 40, 45, 55, 80, 95, 85, 70, 55, 40, 30, 25]
    dispatch = DispatchOptimizer(spec, cell)
    result = dispatch.daily_arbitrage(prices)
    print(f"  Charge cost:    ${result['charge_cost_usd']:,.0f}")
    print(f"  Discharge rev:  ${result['discharge_revenue_usd']:,.0f}")
    print(f"  Net revenue:    ${result['net_revenue_usd']:,.0f}")

    export = {
        "spec": asdict(spec),
        "chemistry": asdict(cell),
        "economics": {k: v for k, v in econ.items() if k != "yearly_detail"},
        "degradation_25yr": deg.total_degradation(25),
    }
    with open("bess_400_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to bess_400_results.json")


if __name__ == "__main__":
    main()

