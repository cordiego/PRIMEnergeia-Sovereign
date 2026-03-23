"""
Granas Metrics — Holistic Performance Engine
=============================================
Unified metrics twin of all Granas sub-products:
  - Granas Optics  → Jsc, absorption, EQE, Mie scattering
  - Granas SDL     → PCE, grain size, fabrication recipe
  - Granas SIBO    → Bayesian optimization convergence, GP surrogate

Computes cross-product holistic metrics:
  - Device-level PCE (fabrication × optics)
  - Fab-Optics correlation matrix
  - Pareto front (Jsc vs PCE vs cost)
  - Figure-of-merit composites

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - [METRICS] - %(message)s")

_trapz = getattr(np, 'trapezoid', None) or getattr(np, 'trapz', None)


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════
@dataclass
class OpticsMetrics:
    """Snapshot of Granas Optics performance."""
    radius_nm: float
    packing_density: float
    thickness_nm: float
    jsc_mA_cm2: float
    weighted_absorption_pct: float
    eqe_avg_pct: float
    size_parameter: float         # x = 2πr/λ at 500nm
    yablonovitch_ratio: float     # jsc / yablonovitch_limit

    @staticmethod
    def from_params(radius: float, density: float, thickness: float) -> "OpticsMetrics":
        """Generate optics metrics from design parameters."""
        wl = np.linspace(300, 1200, 91)

        # Fast Mie+TMM approximation (same as hjb_optics.py)
        x = 2 * np.pi * radius / wl
        q_ext = 2.0 - (4.0 / x) * np.sin(x) + (4.0 / x**2) * (1 - np.cos(x))
        q_ext = np.clip(q_ext, 0, 4)

        path_enhance = 1.0 + density * q_ext
        n_imag = 0.5 * np.exp(-((wl - 400) / 200)**2)  # perovskite-like k
        alpha = 4 * np.pi * n_imag / wl * 1e7
        absorptance = 1 - np.exp(-alpha * thickness * 1e-7 * path_enhance)
        absorptance = np.clip(absorptance, 0, 1)

        # Jsc calculation with correct units
        # AM1.5G approximation: ~1.5 W/m²/nm peak at 500nm
        am15_W_m2_nm = 1.5 * np.exp(-((wl - 500) / 300)**2)
        # Photon flux: Φ = E_λ × λ / (h×c) [photons/m²/s/nm]
        # h×c = 1240 eV·nm, q = 1.602e-19 C
        photon_flux = am15_W_m2_nm * wl / (1240 * 1.602e-19)  # photons/m²/s/nm
        # Jsc = q × ∫ EQE(λ) × Φ(λ) dλ  [A/m²] → convert to mA/cm²
        integrand = absorptance * photon_flux * 1.602e-19  # A/m²/nm
        jsc_A_m2 = float(_trapz(integrand, wl))             # A/m²
        jsc = jsc_A_m2 / 10.0  # A/m² → mA/cm²  (1 A/m² = 0.1 mA/cm²)
        jsc = float(np.clip(jsc, 0.5, 40))

        eqe_avg = float(np.mean(absorptance[(wl >= 400) & (wl <= 750)])) * 100
        x_500 = 2 * np.pi * radius / 500
        yab_limit = 69.0

        return OpticsMetrics(
            radius_nm=radius, packing_density=density,
            thickness_nm=thickness, jsc_mA_cm2=jsc,
            weighted_absorption_pct=float(np.mean(absorptance)) * 100,
            eqe_avg_pct=eqe_avg, size_parameter=x_500,
            yablonovitch_ratio=jsc / yab_limit,
        )


@dataclass
class SDLMetrics:
    """Snapshot of Granas SDL fabrication performance."""
    spin_rpm: float
    anneal_temp_C: float
    concentration_M: float
    pce_pct: float
    grain_nm: float
    thickness_nm: float
    film_quality: float          # 0-1 composite
    recipe_cost: float           # normalized fab cost

    @staticmethod
    def from_recipe(rpm: float, temp: float, conc: float) -> "SDLMetrics":
        """Generate SDL metrics from fabrication recipe."""
        # Film thickness
        thickness = 1200.0 * conc / np.sqrt(rpm / 1000)

        # Grain size (sigmoid model)
        growth = 500.0 / (1.0 + np.exp(-(temp - 90) / 15))
        growth = max(growth, 50.0)
        rpm_factor = max(0.5, 1.0 + 0.15 * (4000 - rpm) / 4000)
        decomp = 1.0
        if temp > 150:
            decomp = max(0.3, 1.0 - 0.02 * (temp - 150))
        grain = float(np.clip(growth * rpm_factor * decomp, 50, 700))

        # PCE
        t_score = np.exp(-((thickness - 550) / 500)**2)
        g_score = 1.0 - np.exp(-grain / 150)
        c_score = np.exp(-((conc - 1.2) / 0.5)**2)
        r_score = np.exp(-((rpm - 4000) / 3000)**2)
        a_score = 1.0
        if temp > 150:
            a_score = max(0.1, np.exp(-0.05 * (temp - 150)))
        if temp < 60:
            a_score *= 0.5
        pce = float(np.clip(max(2.0, 22.0 * t_score * g_score * c_score * r_score * a_score), 0, 25))

        film_quality = float(g_score * t_score * a_score)
        recipe_cost = (rpm / 8000 * 0.3 + temp / 200 * 0.4 + conc / 2.0 * 0.3)

        return SDLMetrics(
            spin_rpm=rpm, anneal_temp_C=temp, concentration_M=conc,
            pce_pct=pce, grain_nm=grain, thickness_nm=thickness,
            film_quality=film_quality, recipe_cost=recipe_cost,
        )


@dataclass
class SIBOMetrics:
    """Snapshot of Granas SIBO (Bayesian Optimizer) performance."""
    iteration: int
    best_pce: float
    gp_uncertainty: float
    exploration_ratio: float
    params_explored: int

    @staticmethod
    def generate_campaign(n_iterations: int = 25) -> List["SIBOMetrics"]:
        """Simulate a Bayesian optimization campaign."""
        metrics = []
        best = 5.0
        for i in range(n_iterations):
            # PCE improves with log convergence
            improvement = 15 * (1 - np.exp(-0.15 * i)) + np.random.normal(0, 0.3)
            candidate = 5.0 + improvement
            best = max(best, candidate)
            uncertainty = 3.0 * np.exp(-0.08 * i) + 0.2
            explore = max(0.1, 0.8 * np.exp(-0.1 * i))
            metrics.append(SIBOMetrics(
                iteration=i, best_pce=best,
                gp_uncertainty=uncertainty,
                exploration_ratio=explore,
                params_explored=(i + 1) * 6,
            ))
        return metrics


# ═══════════════════════════════════════════════════════════
# Holistic Performance
# ═══════════════════════════════════════════════════════════
@dataclass
class HolisticGranas:
    """Cross-product holistic metrics."""

    # Sub-product metrics
    optics: OpticsMetrics
    sdl: SDLMetrics
    sibo: List[SIBOMetrics]

    # Holistic composites
    device_pce: float = 0.0            # optics × fabrication
    figure_of_merit: float = 0.0       # weighted composite
    cost_efficiency: float = 0.0       # PCE / cost
    technology_readiness: float = 0.0  # 1-9 TRL estimate

    def compute(self) -> "HolisticGranas":
        """Calculate cross-product holistic metrics."""
        # Device-level PCE = SDL PCE × optics enhancement
        optics_boost = 1.0 + 0.2 * (self.optics.jsc_mA_cm2 / 20 - 1)
        self.device_pce = self.sdl.pce_pct * max(0.8, optics_boost)

        # Figure of Merit = weighted composite
        pce_norm = self.sdl.pce_pct / 22.0
        jsc_norm = self.optics.jsc_mA_cm2 / 25.0
        grain_norm = self.sdl.grain_nm / 500.0
        abs_norm = self.optics.weighted_absorption_pct / 100.0
        self.figure_of_merit = (
            0.35 * pce_norm +
            0.25 * jsc_norm +
            0.20 * grain_norm +
            0.20 * abs_norm
        ) * 100

        # Cost efficiency
        self.cost_efficiency = self.sdl.pce_pct / max(self.sdl.recipe_cost, 0.1)

        # TRL estimate
        if self.sdl.pce_pct > 18:
            self.technology_readiness = 6
        elif self.sdl.pce_pct > 14:
            self.technology_readiness = 5
        elif self.sdl.pce_pct > 10:
            self.technology_readiness = 4
        else:
            self.technology_readiness = 3

        return self

    @staticmethod
    def generate_sweep(
        rpm_range=(2000, 6000, 5),
        temp_range=(60, 150, 8),
        radius_range=(100, 500, 5),
    ):
        """Generate a sweep for Pareto analysis."""
        rpms = np.linspace(*rpm_range)
        temps = np.linspace(*temp_range[:2], int(temp_range[2]))
        radii = np.linspace(*radius_range)

        results = []
        for rpm in rpms:
            for temp in temps:
                for radius in radii:
                    sdl = SDLMetrics.from_recipe(rpm, temp, 1.2)
                    optics = OpticsMetrics.from_params(radius, 0.5, sdl.thickness_nm)
                    h = HolisticGranas(
                        optics=optics, sdl=sdl,
                        sibo=[]
                    ).compute()
                    results.append({
                        "rpm": rpm, "temp": temp, "radius": radius,
                        "pce": sdl.pce_pct, "jsc": optics.jsc_mA_cm2,
                        "grain_nm": sdl.grain_nm, "device_pce": h.device_pce,
                        "fom": h.figure_of_merit, "cost_eff": h.cost_efficiency,
                        "trl": h.technology_readiness,
                    })
        return results


if __name__ == "__main__":
    optics = OpticsMetrics.from_params(300, 0.5, 500)
    sdl = SDLMetrics.from_recipe(4000, 120, 1.2)
    sibo = SIBOMetrics.generate_campaign(20)

    h = HolisticGranas(optics=optics, sdl=sdl, sibo=sibo).compute()

    print(f"\n{'='*55}")
    print(f" GRANAS HOLISTIC METRICS")
    print(f"{'='*55}")
    print(f" Optics:  Jsc={optics.jsc_mA_cm2:.2f} mA/cm²  Abs={optics.weighted_absorption_pct:.1f}%")
    print(f" SDL:     PCE={sdl.pce_pct:.2f}%  Grain={sdl.grain_nm:.0f}nm")
    print(f" SIBO:    Best={sibo[-1].best_pce:.2f}%  after {len(sibo)} iterations")
    print(f" ─────────────────────────────────────")
    print(f" Device PCE:  {h.device_pce:.2f}%")
    print(f" Figure of Merit: {h.figure_of_merit:.1f}/100")
    print(f" Cost Efficiency: {h.cost_efficiency:.1f}")
    print(f" TRL: {h.technology_readiness}")
    print(f"{'='*55}")
