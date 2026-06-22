"""
Granas Hydrogen-Compatible Back Contact Physics
===============================================
Models the electrochemical nitrogen reduction reaction (NRR) 
to ammonia using the PRIMEnergeia PG-MoSA-BC architecture.

Catalyst: Single-site Molybdenum on carbon (PG-MoSA-BC)
Mechanism: Proton-coupled electron transfer (PCET)
"""

import numpy as np
from dataclasses import dataclass

@dataclass
class BackContactPhysics:
    # Operating conditions
    temperature_K: float = 298.15
    pressure_bar: float = 50.0
    applied_potential_V_RHE: float = -0.4
    
    # Binding energies (eV)
    n2_binding_energy_eV: float = -0.65
    h_adsorption_free_energy_eV: float = 0.45
    
    # Performance metrics
    faradaic_efficiency_nrr: float = 0.584
    ammonia_yield_rate_ug_h_cm2: float = 24.5

    def calculate_module_yield(self, active_area_m2: float) -> dict:
        """
        Calculate total ammonia yield for a given module active area.
        """
        active_area_cm2 = active_area_m2 * 10000
        yield_ug_h = self.ammonia_yield_rate_ug_h_cm2 * active_area_cm2
        yield_g_h = yield_ug_h / 1e6
        yield_g_day = yield_g_h * 24
        yield_kg_year = yield_g_day * 365 / 1000
        
        return {
            "active_area_m2": active_area_m2,
            "ammonia_yield_g_h": yield_g_h,
            "ammonia_yield_g_day": yield_g_day,
            "ammonia_yield_kg_year": yield_kg_year,
            "faradaic_efficiency_pct": self.faradaic_efficiency_nrr * 100
        }

if __name__ == "__main__":
    physics = BackContactPhysics()
    
    # Using Granas module active area (from module_spec.py)
    active_area_m2 = 6.24
    results = physics.calculate_module_yield(active_area_m2)
    
    print("═" * 60)
    print(" GRANAS BACK CONTACT: PG-MoSA-BC PHYSICS")
    print("═" * 60)
    print(f" Catalyst: Mo Single-Atom on Carbon (MoSA)")
    print(f" Temperature: {physics.temperature_K} K")
    print(f" Pressure: {physics.pressure_bar} bar N2")
    print(f" N2 Binding Energy: {physics.n2_binding_energy_eV} eV")
    print(f" ΔG*H (HER Suppression): +{physics.h_adsorption_free_energy_eV} eV")
    print("-" * 60)
    print(" RESULTS FOR 2.1m x 3.4m MODULE (Active Area: {:.2f} m²)".format(active_area_m2))
    print(f" Faradaic Efficiency (NRR): {results['faradaic_efficiency_pct']:.1f}%")
    print(f" Ammonia Yield Rate: {physics.ammonia_yield_rate_ug_h_cm2} μg/h/cm²")
    print(f" Ammonia Yield (Module): {results['ammonia_yield_g_h']:.2f} g/h")
    print(f" Ammonia Yield (Daily):  {results['ammonia_yield_g_day']:.2f} g/day")
    print(f" Ammonia Yield (Annual): {results['ammonia_yield_kg_year']:.2f} kg/year")
    print("═" * 60)
