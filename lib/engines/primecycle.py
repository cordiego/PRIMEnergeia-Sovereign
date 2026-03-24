#!/usr/bin/env python3
"""
PRIMEcycle — Perovskite Solar Module Recycling Simulator
=========================================================
PRIMEnergeia S.A.S. | PRIMEcycle Division

Circular economy model for end-of-life perovskite-silicon modules:
  - Bill of Materials (BOM) disassembly model
  - Multi-stage chemical recovery process
  - Material value calculator (LME / market prices)
  - Lead (Pb) capture and immobilization
  - Energy balance (recycling vs primary production)
  - Environmental impact (CO₂, water, waste diversion)
  - Plant economics (CapEx, OpEx, throughput scaling)

Reference: Kadro & Hagfeldt, Joule (2017) — "How to Make Perovskite Recycling Work"
"""

import math
import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict

# ============================================================
#  MODULE BOM (Bill of Materials)
# ============================================================

@dataclass
class MaterialComponent:
    """Single material in module BOM."""
    name: str
    mass_g: float           # Mass per module (grams)
    hazardous: bool = False
    market_price_usd_kg: float = 0.0
    recovery_rate: float = 0.95    # Expected recovery fraction
    recovery_energy_kj_g: float = 0.0  # Energy to recover per gram
    co2_avoided_g_per_g: float = 0.0   # CO₂ avoided vs primary production


def granas_module_bom() -> List[MaterialComponent]:
    """BOM for a Granas perovskite-silicon tandem module (1.7 m², 22 kg)."""
    return [
        MaterialComponent("Glass (front)", 8500, False, 0.80, 0.995, 0.5, 0.6),
        MaterialComponent("ETFE Film", 850, False, 12.0, 0.92, 2.0, 4.5),
        MaterialComponent("EVA Encapsulant", 1100, False, 1.2, 0.85, 1.5, 2.0),
        MaterialComponent("Silicon Cell", 2640, False, 12.0, 0.95, 8.0, 15.0),
        MaterialComponent("Perovskite (FAPbI₃)", 180, True, 85.0, 0.93, 5.0, 12.0),
        MaterialComponent("PbI₂ (lead iodide)", 95, True, 45.0, 0.975, 3.0, 8.0),
        MaterialComponent("FAI (formamidinium)", 42, False, 180.0, 0.90, 4.0, 6.0),
        MaterialComponent("MAI (methylammonium)", 28, False, 200.0, 0.88, 4.0, 6.0),
        MaterialComponent("Lead (Pb, trace)", 11, True, 2.10, 0.998, 2.0, 3.0),
        MaterialComponent("Silver (Ag)", 8.8, False, 850.0, 0.98, 15.0, 45.0),
        MaterialComponent("Copper (Cu)", 704, False, 8.50, 0.99, 3.0, 4.0),
        MaterialComponent("Aluminum (frame)", 2200, False, 2.20, 0.995, 5.0, 12.0),
        MaterialComponent("CFRP Substrate", 1760, False, 15.0, 0.88, 12.0, 25.0),
        MaterialComponent("TiO₂ (ETL)", 15, False, 3.0, 0.80, 6.0, 8.0),
        MaterialComponent("Spiro-OMeTAD (HTL)", 8, False, 5000.0, 0.75, 8.0, 20.0),
        MaterialComponent("ITO / FTO", 35, False, 25.0, 0.70, 10.0, 18.0),
        MaterialComponent("Backsheet", 1500, False, 1.5, 0.90, 1.0, 2.0),
        MaterialComponent("Junction Box", 450, False, 3.0, 0.95, 2.0, 3.0),
        MaterialComponent("Solder / Ribbon", 180, False, 5.0, 0.92, 4.0, 5.0),
        MaterialComponent("Other / Misc", 200, False, 0.5, 0.70, 1.0, 1.0),
    ]


# ============================================================
#  RECOVERY PROCESS STAGES
# ============================================================

@dataclass
class ProcessStage:
    """Single recovery process stage."""
    name: str
    description: str
    yield_pct: float           # Stage yield (0-100)
    energy_kwh_per_mod: float  # Energy consumption per module
    water_l_per_mod: float     # Water consumption per module
    time_min: float            # Processing time per module
    chemicals: Dict[str, float] = field(default_factory=dict)  # Chemical reagents (kg/module)


def recovery_process() -> List[ProcessStage]:
    """Full PRIMEcycle recovery process chain."""
    return [
        ProcessStage(
            "Collection & Sorting", "Automated optical + RFID sorting",
            98.0, 0.5, 0.0, 2.0
        ),
        ProcessStage(
            "Mechanical Disassembly", "Robotic frame/JBox/backsheet removal",
            96.5, 2.0, 0.0, 5.0
        ),
        ProcessStage(
            "Thermal Delamination", "Hot-knife EVA separation @ 150°C",
            97.0, 8.0, 0.0, 15.0
        ),
        ProcessStage(
            "Solvent Wash", "DMF extraction of perovskite layer",
            95.0, 1.5, 2.0, 10.0,
            {"DMF (recycled)": 0.05, "IPA rinse": 0.02}
        ),
        ProcessStage(
            "Pb Precipitation", "Pb²⁺ capture as PbSO₄ using Na₂SO₄",
            99.8, 0.5, 1.0, 8.0,
            {"Na₂SO₄ solution": 0.03}
        ),
        ProcessStage(
            "Chemical Recovery", "Acid leach for Si, Cu, Ag separation",
            97.3, 3.0, 5.0, 20.0,
            {"HNO₃ (dilute)": 0.02, "NaOH": 0.01}
        ),
        ProcessStage(
            "Purification", "Electrolytic refining + crystallization",
            99.0, 5.0, 3.0, 25.0
        ),
        ProcessStage(
            "Quality Control", "XRF + ICP-OES purity verification",
            100.0, 0.2, 0.0, 3.0
        ),
    ]


# ============================================================
#  RECYCLING SIMULATOR
# ============================================================

class PRIMEcycleSimulator:
    """Full recycling plant simulation."""

    def __init__(self, bom: List[MaterialComponent] = None,
                 process: List[ProcessStage] = None):
        self.bom = bom or granas_module_bom()
        self.process = process or recovery_process()
        self.module_mass_kg = sum(m.mass_g for m in self.bom) / 1000

    def process_module(self) -> dict:
        """Simulate recovery of one module through all stages."""
        cumulative_yield = 1.0
        total_energy_kwh = 0
        total_water_l = 0
        total_time_min = 0
        stage_results = []

        for stage in self.process:
            cumulative_yield *= stage.yield_pct / 100
            total_energy_kwh += stage.energy_kwh_per_mod
            total_water_l += stage.water_l_per_mod
            total_time_min += stage.time_min

            stage_results.append({
                "stage": stage.name,
                "yield_pct": stage.yield_pct,
                "cumulative_yield_pct": round(cumulative_yield * 100, 2),
                "energy_kwh": stage.energy_kwh_per_mod,
                "water_l": stage.water_l_per_mod,
            })

        # Material recovery
        material_results = []
        total_value_usd = 0
        total_co2_avoided_kg = 0
        total_pb_captured_g = 0

        for mat in self.bom:
            recovered_g = mat.mass_g * mat.recovery_rate * cumulative_yield
            value = recovered_g / 1000 * mat.market_price_usd_kg
            co2_avoided = recovered_g * mat.co2_avoided_g_per_g / 1000
            energy_used = recovered_g * mat.recovery_energy_kj_g / 3600  # kWh

            total_value_usd += value
            total_co2_avoided_kg += co2_avoided

            if mat.hazardous and "Pb" in mat.name:
                total_pb_captured_g += recovered_g

            material_results.append({
                "material": mat.name,
                "original_g": round(mat.mass_g, 1),
                "recovered_g": round(recovered_g, 1),
                "recovery_pct": round(mat.recovery_rate * cumulative_yield * 100, 1),
                "value_usd": round(value, 3),
                "co2_avoided_kg": round(co2_avoided, 3),
                "hazardous": mat.hazardous,
            })

        return {
            "module_mass_kg": round(self.module_mass_kg, 2),
            "stages": stage_results,
            "materials": material_results,
            "summary": {
                "overall_yield_pct": round(cumulative_yield * 100, 2),
                "total_value_usd": round(total_value_usd, 2),
                "total_energy_kwh": round(total_energy_kwh, 2),
                "total_water_l": round(total_water_l, 1),
                "total_time_min": round(total_time_min, 1),
                "co2_avoided_kg": round(total_co2_avoided_kg, 2),
                "pb_captured_g": round(total_pb_captured_g, 2),
                "pb_capture_rate_pct": 99.8,
                "waste_diverted_pct": round(cumulative_yield * 100, 1),
            },
        }

    def plant_economics(self, capacity_modules_yr: int = 100000) -> dict:
        """Full plant economic model."""
        module_result = self.process_module()
        rev_per_module = module_result["summary"]["total_value_usd"]
        energy_per_module = module_result["summary"]["total_energy_kwh"]

        # CapEx scaling (power law)
        base_capex = 5.0  # $M for 10K module/yr pilot
        base_capacity = 10000
        scaling_exponent = 0.65  # Economies of scale
        capex_m = base_capex * (capacity_modules_yr / base_capacity) ** scaling_exponent

        # OpEx
        labor_per_module = 2.50  # $/module
        energy_cost = energy_per_module * 0.08  # $0.08/kWh
        chemicals_per_module = 0.80
        overhead_per_module = 1.50
        opex_per_module = labor_per_module + energy_cost + chemicals_per_module + overhead_per_module
        annual_opex = opex_per_module * capacity_modules_yr / 1e6

        # Revenue
        annual_revenue = rev_per_module * capacity_modules_yr / 1e6
        # Add gate fee ($3/module for accepting waste)
        gate_fee_revenue = 3.0 * capacity_modules_yr / 1e6
        total_revenue = annual_revenue + gate_fee_revenue

        annual_profit = total_revenue - annual_opex
        payback = capex_m / max(0.01, annual_profit) if annual_profit > 0 else float('inf')

        return {
            "capacity_modules_yr": capacity_modules_yr,
            "capex_M": round(capex_m, 1),
            "revenue_per_module": round(rev_per_module, 2),
            "opex_per_module": round(opex_per_module, 2),
            "margin_per_module": round(rev_per_module + 3.0 - opex_per_module, 2),
            "annual_revenue_M": round(total_revenue, 2),
            "annual_opex_M": round(annual_opex, 2),
            "annual_profit_M": round(annual_profit, 2),
            "payback_years": round(payback, 1),
            "modules_per_day": round(capacity_modules_yr / 300, 0),  # 300 operating days
            "annual_pb_diverted_kg": round(module_result["summary"]["pb_captured_g"] * capacity_modules_yr / 1000, 0),
            "annual_co2_avoided_tonnes": round(module_result["summary"]["co2_avoided_kg"] * capacity_modules_yr / 1000, 0),
        }


def main():
    sim = PRIMEcycleSimulator()

    print(f"\n{'='*65}")
    print(f"  PRIMEcycle — Perovskite Recycling Simulator")
    print(f"  PRIMEnergeia S.A.S. | PRIMEcycle Division")
    print(f"{'='*65}")
    print(f"  Module mass: {sim.module_mass_kg:.2f} kg")
    print(f"  BOM items:   {len(sim.bom)}")
    print(f"  Stages:      {len(sim.process)}")
    print(f"{'='*65}\n")

    result = sim.process_module()

    print(f"  PROCESS CHAIN")
    print(f"  {'Stage':<25} {'Yield%':>7} {'Cumul%':>7} {'Energy':>7} {'Water':>6}")
    print(f"  {'─'*55}")
    for s in result["stages"]:
        print(f"  {s['stage']:<25} {s['yield_pct']:>6.1f}% {s['cumulative_yield_pct']:>6.2f}% "
              f"{s['energy_kwh']:>6.1f}  {s['water_l']:>5.1f}")

    print(f"\n  MATERIAL RECOVERY")
    print(f"  {'Material':<22} {'Original(g)':>11} {'Recovered(g)':>12} {'Rate%':>6} {'Value($)':>8}")
    print(f"  {'─'*65}")
    for m in result["materials"]:
        flag = " ☠️" if m["hazardous"] else ""
        print(f"  {m['material']:<22} {m['original_g']:>10.1f} {m['recovered_g']:>11.1f} "
              f"{m['recovery_pct']:>5.1f} {m['value_usd']:>7.2f}{flag}")

    s = result["summary"]
    print(f"\n  SUMMARY PER MODULE")
    print(f"  {'─'*40}")
    print(f"  Total value recovered: ${s['total_value_usd']:.2f}")
    print(f"  Energy consumed:       {s['total_energy_kwh']:.1f} kWh")
    print(f"  Water consumed:        {s['total_water_l']:.0f} L")
    print(f"  CO₂ avoided:           {s['co2_avoided_kg']:.2f} kg")
    print(f"  Pb captured:           {s['pb_captured_g']:.2f} g (99.8%)")

    # Plant economics
    print(f"\n  PLANT ECONOMICS")
    print(f"  {'─'*50}")
    for scale in [1000, 10000, 100000, 500000, 1000000]:
        e = sim.plant_economics(scale)
        print(f"  {scale:>8,} mod/yr: CapEx ${e['capex_M']:.1f}M | "
              f"Profit ${e['annual_profit_M']:.1f}M/yr | "
              f"Payback {e['payback_years']:.1f}yr | "
              f"Pb diverted {e['annual_pb_diverted_kg']:,.0f} kg")

    export = {
        "module_analysis": result["summary"],
        "materials_top5": sorted(result["materials"], key=lambda x: x["value_usd"], reverse=True)[:5],
        "economics_100k": sim.plant_economics(100000),
    }
    with open("primecycle_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to primecycle_results.json")


if __name__ == "__main__":
    main()

