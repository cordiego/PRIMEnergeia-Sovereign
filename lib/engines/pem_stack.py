#!/usr/bin/env python3
"""
PRIMEngines PEM-PB-50 — PEM Fuel Cell Power Bank Simulator
=============================================================
PRIMEnergeia S.A.S. | PRIMEngines Division

Physics-based PEM fuel cell stack simulation:
  - Nernst equation for open circuit voltage
  - Activation, ohmic, and mass transport losses
  - Polarization curve generation
  - Stack thermal management (coolant + air)
  - System efficiency (BoP parasitic loads)
  - Degradation model (voltage decay over hours)

Reference: Barbir, "PEM Fuel Cells: Theory and Practice" (2013)
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

# ============================================================
#  STACK SPECIFICATION
# ============================================================

@dataclass
class PEMSpec:
    """PEM-PB-50 fuel cell stack specification."""
    name: str = "PRIMEngines PEM-PB-50"
    rated_power_kw: float = 50.0
    num_cells: int = 370
    active_area_cm2: float = 300.0       # Per cell
    membrane: str = "Nafion 212 (50 µm)"
    catalyst_loading_mg_cm2: float = 0.3  # Pt loading
    operating_temp_c: float = 80.0
    operating_pressure_bar: float = 2.0   # Cathode pressure

    # Physical
    stack_weight_kg: float = 38.0
    bop_weight_kg: float = 7.0            # Balance of Plant
    total_weight_kg: float = 45.0
    volume_L: float = 32.0

    # Fuel
    fuel: str = "Green H₂ (99.999% purity)"
    h2_pressure_bar: float = 350.0        # Storage pressure
    h2_stoich: float = 1.5                # H₂ stoichiometry
    air_stoich: float = 2.5               # Air stoichiometry

    # Durability
    target_hours: int = 10000
    voltage_decay_uv_h: float = 2.5       # µV/h degradation rate (DOE 2030 target)


# ============================================================
#  ELECTROCHEMISTRY
# ============================================================

class PEMElectrochemistry:
    """
    PEM fuel cell electrochemical model.
    Computes single-cell voltage from thermodynamics + losses.
    """

    # Constants
    F = 96485.3329  # Faraday constant (C/mol)
    R = 8.31446     # Gas constant (J/mol·K)
    n = 2           # Electrons transferred per H₂ molecule

    def __init__(self, spec: PEMSpec):
        self.spec = spec
        self.T = spec.operating_temp_c + 273.15  # Kelvin

    def nernst_voltage(self, p_h2: float = None, p_o2: float = None) -> float:
        """
        Reversible (Nernst) OCV.
        E = E° + (RT/nF) ln(pH2 * pO2^0.5)
        """
        if p_h2 is None:
            p_h2 = self.spec.operating_pressure_bar
        if p_o2 is None:
            p_o2 = 0.21 * self.spec.operating_pressure_bar

        E0 = 1.229 - 0.000846 * (self.T - 298.15)  # Standard potential corrected for T
        E = E0 + (self.R * self.T / (self.n * self.F)) * math.log(max(1e-10, p_h2 * p_o2 ** 0.5))
        return round(E, 4)

    def activation_loss(self, current_density: float) -> float:
        """
        Activation overpotential (Tafel equation).
        η_act = (RT / αnF) · ln(j / j0)
        """
        alpha = 0.5      # Transfer coefficient
        j0 = 1e-4        # Exchange current density (A/cm²) — Pt catalyst

        if current_density <= 0:
            return 0.0

        eta = (self.R * self.T / (alpha * self.n * self.F)) * math.log(current_density / j0)
        return max(0, round(eta, 4))

    def ohmic_loss(self, current_density: float) -> float:
        """
        Ohmic overpotential from membrane resistance.
        η_ohm = j × R_membrane
        Membrane conductivity depends on humidity and temperature.
        """
        # Nafion conductivity model (Springer et al.)
        lambda_w = 14.0  # Water content (fully humidified)
        sigma = (0.005139 * lambda_w - 0.00326) * math.exp(
            1268 * (1/303 - 1/self.T)
        )
        # Membrane thickness 50 µm = 0.005 cm
        t_mem = 0.005
        R_mem = t_mem / max(0.001, sigma)  # Ohm·cm²

        # Contact resistance
        R_contact = 0.02  # Ohm·cm²

        return round(current_density * (R_mem + R_contact), 4)

    def mass_transport_loss(self, current_density: float,
                            j_limit: float = 2.0) -> float:
        """
        Concentration overpotential at high current densities.
        η_conc = c · ln(1 - j/j_L)
        """
        if current_density >= j_limit * 0.99:
            return 0.5  # Cap at 500 mV

        c = 0.03  # Concentration loss coefficient
        eta = -c * math.log(max(1e-10, 1 - current_density / j_limit))
        return max(0, round(eta, 4))

    def cell_voltage(self, current_density: float) -> float:
        """Net single-cell voltage at given current density (A/cm²)."""
        E_rev = self.nernst_voltage()
        eta_act = self.activation_loss(current_density)
        eta_ohm = self.ohmic_loss(current_density)
        eta_conc = self.mass_transport_loss(current_density)

        V_cell = E_rev - eta_act - eta_ohm - eta_conc
        return max(0.0, round(V_cell, 4))

    def polarization_curve(self, j_max: float = 2.0, steps: int = 100) -> List[Dict]:
        """Generate full polarization (V-I) curve."""
        results = []
        for i in range(steps + 1):
            j = j_max * i / steps
            v = self.cell_voltage(j)
            power_density = j * v  # W/cm²
            results.append({
                "current_density_A_cm2": round(j, 4),
                "cell_voltage_V": v,
                "power_density_W_cm2": round(power_density, 4),
                "stack_voltage_V": round(v * self.spec.num_cells, 1),
                "stack_current_A": round(j * self.spec.active_area_cm2, 1),
                "stack_power_kW": round(power_density * self.spec.active_area_cm2 * self.spec.num_cells / 1000, 2),
            })
        return results


# ============================================================
#  SYSTEM MODEL (Balance of Plant)
# ============================================================

class PEMSystem:
    """Full fuel cell system including Balance of Plant."""

    def __init__(self, spec: PEMSpec = None):
        self.spec = spec or PEMSpec()
        self.echem = PEMElectrochemistry(self.spec)

    def parasitic_power(self, gross_power_kw: float) -> Dict[str, float]:
        """BoP parasitic loads (kW)."""
        load_frac = gross_power_kw / self.spec.rated_power_kw

        compressor = 0.08 * gross_power_kw * (load_frac ** 0.5)  # Air compressor
        coolant_pump = 0.02 * gross_power_kw
        h2_recirculation = 0.01 * gross_power_kw
        controls = 0.15  # Fixed load

        return {
            "compressor_kw": round(compressor, 3),
            "coolant_pump_kw": round(coolant_pump, 3),
            "h2_recirc_kw": round(h2_recirculation, 3),
            "controls_kw": controls,
            "total_parasitic_kw": round(compressor + coolant_pump + h2_recirculation + controls, 3),
        }

    def system_efficiency(self, current_density: float) -> float:
        """Net system efficiency (LHV basis)."""
        v_cell = self.echem.cell_voltage(current_density)

        # Thermodynamic efficiency
        E_thermo = 1.481  # Thermoneutral voltage (V)
        eta_voltage = v_cell / E_thermo

        # Hydrogen utilization (with anode recirculation)
        # Effective utilization = 1 - (1 - 1/stoich) × (1 - recirculation_rate)
        recirculation_rate = 0.995
        eta_fuel = 1 - (1 - 1 / self.spec.h2_stoich) * (1 - recirculation_rate)

        # BoP efficiency
        gross_power = v_cell * current_density * self.spec.active_area_cm2 * self.spec.num_cells / 1000
        parasitic = self.parasitic_power(gross_power)
        eta_bop = 1 - parasitic["total_parasitic_kw"] / max(0.1, gross_power)

        eta_system = eta_voltage * eta_fuel * eta_bop
        return round(max(0, min(0.65, eta_system)), 4)

    def h2_consumption(self, net_power_kw: float, efficiency: float = None) -> float:
        """H₂ consumption (kg/h) at given net output."""
        if efficiency is None:
            # Find current density for this power (iterative)
            j = net_power_kw / (self.spec.rated_power_kw) * 1.5  # Approximate
            efficiency = self.system_efficiency(j)

        h2_lhv = 120.0  # MJ/kg
        consumption = net_power_kw * 3.6 / (max(0.1, efficiency) * h2_lhv)
        return round(consumption, 3)

    def operating_point(self, load_pct: float) -> dict:
        """Full system output at given load percentage."""
        j_rated = 1.5  # A/cm² at rated power
        j = j_rated * load_pct / 100

        v_cell = self.echem.cell_voltage(j)
        gross_power = v_cell * j * self.spec.active_area_cm2 * self.spec.num_cells / 1000
        parasitic = self.parasitic_power(gross_power)
        net_power = gross_power - parasitic["total_parasitic_kw"]
        efficiency = self.system_efficiency(j)
        h2_rate = self.h2_consumption(net_power, efficiency)

        # Thermal — waste heat = fuel energy in - electrical energy out
        # Fuel energy = net_power / efficiency, waste = fuel_energy - net_power
        heat_generated = net_power * (1 / max(0.1, efficiency) - 1) if efficiency > 0 else 0

        return {
            "load_pct": load_pct,
            "current_density_A_cm2": round(j, 3),
            "cell_voltage_V": v_cell,
            "stack_voltage_V": round(v_cell * self.spec.num_cells, 1),
            "gross_power_kW": round(gross_power, 2),
            "net_power_kW": round(net_power, 2),
            "system_efficiency_pct": round(efficiency * 100, 1),
            "h2_consumption_kg_h": h2_rate,
            "h2_per_kwh_g": round(h2_rate * 1000 / max(0.1, net_power), 1),
            "heat_generated_kW": round(heat_generated, 1),
            "parasitic": parasitic,
            "exhaust": "H₂O (liquid + vapor)",
            "co2_g_kwh": 0.0,
        }

    def degradation(self, hours: float) -> dict:
        """Stack degradation over operating hours."""
        voltage_loss_mv = self.spec.voltage_decay_uv_h * hours / 1000
        v_nominal = self.echem.cell_voltage(1.0)  # Voltage at rated current
        v_nominal_mv = v_nominal * 1000
        power_loss_pct = voltage_loss_mv / v_nominal_mv * 100

        # EOL defined as 10% power (voltage) loss at rated current
        eol_voltage_loss_mv = v_nominal_mv * 0.10
        eol_hours = eol_voltage_loss_mv / self.spec.voltage_decay_uv_h * 1000

        return {
            "operating_hours": hours,
            "voltage_loss_mV": round(voltage_loss_mv, 1),
            "power_loss_pct": round(power_loss_pct, 1),
            "remaining_life_pct": round(max(0, 100 - power_loss_pct), 1),
            "estimated_eol_hours": round(eol_hours),
            "estimated_eol_years": round(eol_hours / 8760, 1),
        }


def main():
    sys = PEMSystem()

    print(f"\n{'='*65}")
    print(f"  {sys.spec.name} — PEM Fuel Cell Simulator")
    print(f"  PRIMEnergeia S.A.S. | PRIMEngines Division")
    print(f"{'='*65}")
    print(f"  Cells:     {sys.spec.num_cells}")
    print(f"  Active:    {sys.spec.active_area_cm2} cm²/cell")
    print(f"  Membrane:  {sys.spec.membrane}")
    print(f"  Pt Load:   {sys.spec.catalyst_loading_mg_cm2} mg/cm²")
    print(f"  Fuel:      {sys.spec.fuel}")
    print(f"  Weight:    {sys.spec.total_weight_kg} kg")
    print(f"{'='*65}\n")

    print(f"  {'Load':>6} {'j(A/cm²)':>9} {'Vcell':>6} {'Vstack':>7} {'Pnet':>7} {'η(%)':>6} {'H₂(kg/h)':>9}")
    print(f"  {'─'*58}")

    for load in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        op = sys.operating_point(load)
        print(f"  {load:>5}%  {op['current_density_A_cm2']:>8.3f}  "
              f"{op['cell_voltage_V']:>5.3f}  {op['stack_voltage_V']:>6.1f}  "
              f"{op['net_power_kW']:>6.1f}  {op['system_efficiency_pct']:>5.1f}  "
              f"{op['h2_consumption_kg_h']:>8.3f}")

    # Polarization curve
    pol = sys.echem.polarization_curve()
    print(f"\n  Polarization curve: {len(pol)} points generated")
    print(f"  Peak power density: {max(p['power_density_W_cm2'] for p in pol):.3f} W/cm²")

    # Degradation
    print(f"\n  DEGRADATION PROJECTION")
    print(f"  {'─'*40}")
    for hours in [1000, 2500, 5000, 7500, 10000]:
        d = sys.degradation(hours)
        print(f"  {hours:>6}h: {d['voltage_loss_mV']:>5.1f} mV loss, "
              f"{d['remaining_life_pct']:.1f}% remaining")

    # Export
    export = {
        "spec": asdict(sys.spec),
        "rated_point": sys.operating_point(100),
        "polarization_curve": pol[:10],  # First 10 points
        "degradation_10k": sys.degradation(10000),
    }
    with open("pem_pb50_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to pem_pb50_results.json")


if __name__ == "__main__":
    main()

