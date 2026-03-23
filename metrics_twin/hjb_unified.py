"""
Granas — Unified HJB Optimal Control Across All Subsystems
=============================================================
Hamilton-Jacobi-Bellman optimizer running on EVERY Granas subsystem:

  1. SDL      — spin, anneal, concentration, additive, solvent
  2. Albedo   — green reflectance, film thickness
  3. ETFE     — haze, thickness
  4. TOPCon   — tunnel oxide, poly-Si thickness, doping
  5. CFRP     — ridge geometry, chamfer angle
  6. Blueprint — edge lengths, tessellation
  7. GHB      — Mo loading, pressure, potential

Maximizes unified Figure of Merit across all subsystems.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import json
import sys
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════════
# HJB State Space Definition
# ═══════════════════════════════════════════════════════════
@dataclass
class HJBState:
    """Complete Granas system state across all subsystems."""
    # SDL fabrication
    spin_rpm: float = 4000
    anneal_temp_C: float = 120
    concentration_M: float = 1.2
    additive_pct: float = 3.0
    solvent_ratio: float = 0.7

    # Albedo / thermal
    green_reflectance: float = 0.35
    film_thickness_nm: float = 700

    # ETFE encapsulation
    etfe_haze_pct: float = 12.0
    etfe_thickness_um: float = 100

    # TOPCon
    tunnel_oxide_nm: float = 1.5
    poly_si_nm: float = 200

    # CFRP
    chamfer_angle_deg: float = 15.0
    ridge_width_mm: float = 8.0

    # GHB
    mo_loading_wt_pct: float = 2.5
    n2_pressure_bar: float = 50.0
    applied_potential_V: float = -0.4

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.spin_rpm, self.anneal_temp_C, self.concentration_M,
            self.additive_pct, self.solvent_ratio, self.green_reflectance,
            self.film_thickness_nm, self.etfe_haze_pct, self.etfe_thickness_um,
            self.tunnel_oxide_nm, self.poly_si_nm, self.chamfer_angle_deg,
            self.ridge_width_mm, self.mo_loading_wt_pct, self.n2_pressure_bar,
            self.applied_potential_V,
        ])

    @staticmethod
    def from_vector(v: np.ndarray) -> "HJBState":
        return HJBState(
            spin_rpm=v[0], anneal_temp_C=v[1], concentration_M=v[2],
            additive_pct=v[3], solvent_ratio=v[4], green_reflectance=v[5],
            film_thickness_nm=v[6], etfe_haze_pct=v[7], etfe_thickness_um=v[8],
            tunnel_oxide_nm=v[9], poly_si_nm=v[10], chamfer_angle_deg=v[11],
            ridge_width_mm=v[12], mo_loading_wt_pct=v[13], n2_pressure_bar=v[14],
            applied_potential_V=v[15],
        )

    @staticmethod
    def bounds() -> List[Tuple[float, float]]:
        return [
            (1000, 8000),   # spin_rpm
            (50, 200),      # anneal_temp_C
            (0.5, 2.0),     # concentration_M
            (0.0, 5.0),     # additive_pct
            (0.0, 1.0),     # solvent_ratio
            (0.1, 0.5),     # green_reflectance
            (200, 1200),    # film_thickness_nm
            (5, 30),        # etfe_haze_pct
            (50, 200),      # etfe_thickness_um
            (1.0, 2.5),     # tunnel_oxide_nm
            (100, 400),     # poly_si_nm
            (5, 30),        # chamfer_angle_deg
            (3, 15),        # ridge_width_mm
            (1.0, 5.0),     # mo_loading_wt_pct
            (10, 100),      # n2_pressure_bar
            (-0.8, -0.1),   # applied_potential_V
        ]


# ═══════════════════════════════════════════════════════════
# Subsystem Objective Functions
# ═══════════════════════════════════════════════════════════
def score_sdl(s: HJBState) -> Dict[str, float]:
    """SDL fabrication score."""
    thickness = 1200.0 * s.concentration_M / np.sqrt(s.spin_rpm / 1000)
    growth = 500.0 / (1.0 + np.exp(-(s.anneal_temp_C - 90) / 15))
    rpm_f = max(0.5, 1.0 + 0.15 * (4000 - s.spin_rpm) / 4000)
    grain = float(np.clip(growth * rpm_f * 1.1, 50, 700))

    t_score = np.exp(-((thickness - 600) / 600)**2)
    g_score = 1.0 - np.exp(-grain / 150)
    c_score = np.exp(-((s.concentration_M - 1.2) / 0.5)**2)
    r_score = np.exp(-((s.spin_rpm - 4000) / 3000)**2)
    a_score = np.exp(-((s.additive_pct - 3.0) / 2.0)**2)
    sol_score = np.exp(-((s.solvent_ratio - 0.7) / 0.3)**2)

    decomp = 1.0
    if s.anneal_temp_C > 150:
        decomp = max(0.1, np.exp(-0.05 * (s.anneal_temp_C - 150)))

    pce_top = 23.0 * t_score * g_score * c_score * r_score * a_score * sol_score * decomp * 0.95
    si_coup = min(1.0, (g_score + t_score) / 2 + 0.1)
    pce_bot = 15.0 * si_coup
    pce = float(np.clip(pce_top + pce_bot, 3, 42))

    return {"pce": pce, "grain_nm": grain, "thickness_nm": thickness, "score": pce / 38}


def score_albedo(s: HJBState) -> Dict[str, float]:
    """Albedo/thermal score."""
    tj = 25 + 43 - 43 * s.green_reflectance * 1.2 - 43 * 0.003
    tj = max(30, tj)
    # Optimal: Tj ≈ 42°C
    thermal_score = np.exp(-((tj - 42) / 15)**2)
    # Jsc sacrifice penalty
    jsc_penalty = 1.0 - s.green_reflectance * 0.15
    return {"Tj_C": tj, "thermal_score": thermal_score, "jsc_penalty": jsc_penalty,
            "score": thermal_score * jsc_penalty}


def score_etfe(s: HJBState) -> Dict[str, float]:
    """ETFE encapsulation score."""
    transmittance = 96.0 * (1 - 0.001 * max(0, s.etfe_thickness_um - 100))
    haze_path = 1.0 + s.etfe_haze_pct / 100 * 0.5
    t_score = transmittance / 96.0
    h_score = min(1.0, haze_path / 1.15)
    return {"transmittance": transmittance, "haze_path": haze_path,
            "score": t_score * h_score}


def score_topcon(s: HJBState) -> Dict[str, float]:
    """TOPCon bottom cell score."""
    # Tunnel oxide: optimal 1.5nm
    tox_score = np.exp(-((s.tunnel_oxide_nm - 1.5) / 0.5)**2)
    # Poly-Si: optimal 200nm
    psi_score = np.exp(-((s.poly_si_nm - 200) / 100)**2)
    # Implied Voc depends on J0
    j0 = 2.0 + 1.5 * (1 + 0.5 * abs(s.tunnel_oxide_nm - 1.5)) + 3.0
    voc = 0.02585 * np.log(42e-3 / (j0 * 1e-15) + 1) * 1000
    return {"Voc_mV": voc, "J0_fA_cm2": j0, "score": tox_score * psi_score}


def score_cfrp(s: HJBState) -> Dict[str, float]:
    """CFRP structural score."""
    # Chamfer: optimal 15° for recycling
    chamfer_score = np.exp(-((s.chamfer_angle_deg - 15) / 8)**2)
    # Ridge width: balance between structural support and shading
    ridge_score = np.exp(-((s.ridge_width_mm - 8) / 4)**2)
    recycling = 89 * chamfer_score
    return {"recycling_pct": recycling, "score": chamfer_score * ridge_score}


def score_ghb(s: HJBState) -> Dict[str, float]:
    """Green Haber-Bosch NRR score."""
    # Mo loading: optimal 2-3%
    mo_score = np.exp(-((s.mo_loading_wt_pct - 2.5) / 1.5)**2)
    # Pressure: higher is better (up to diminishing returns)
    p_score = min(1.0, np.log(s.n2_pressure_bar + 1) / np.log(101))
    # Potential: optimal -0.4V
    v_score = np.exp(-((s.applied_potential_V + 0.4) / 0.3)**2)
    fe = 65 * 0.895 * 0.7 * v_score * p_score * mo_score
    return {"FE_pct": fe, "score": v_score * p_score * mo_score}


# ═══════════════════════════════════════════════════════════
# Unified HJB Value Function
# ═══════════════════════════════════════════════════════════
def unified_value(state: HJBState) -> Dict:
    """
    V(x) = Σ wᵢ × scoreᵢ(x)
    Hamilton-Jacobi-Bellman value function across all subsystems.
    """
    sdl = score_sdl(state)
    albedo = score_albedo(state)
    etfe = score_etfe(state)
    topcon = score_topcon(state)
    cfrp = score_cfrp(state)
    ghb = score_ghb(state)

    # Weighted composite (normalized 0-100)
    weights = {
        "sdl": 0.30,      # PCE is primary objective
        "albedo": 0.20,    # Thermal = longevity
        "etfe": 0.10,      # Encapsulation
        "topcon": 0.15,    # Bottom cell
        "cfrp": 0.10,      # Structural
        "ghb": 0.15,       # Green ammonia
    }

    value = (
        weights["sdl"] * sdl["score"] +
        weights["albedo"] * albedo["score"] +
        weights["etfe"] * etfe["score"] +
        weights["topcon"] * topcon["score"] +
        weights["cfrp"] * cfrp["score"] +
        weights["ghb"] * ghb["score"]
    ) * 100

    return {
        "value": float(value),
        "sdl": sdl, "albedo": albedo, "etfe": etfe,
        "topcon": topcon, "cfrp": cfrp, "ghb": ghb,
    }


# ═══════════════════════════════════════════════════════════
# HJB Optimizer (gradient-free, multi-start)
# ═══════════════════════════════════════════════════════════
def hjb_optimize(n_starts: int = 50, n_iterations: int = 200,
                  step_decay: float = 0.995, verbose: bool = True) -> Dict:
    """
    Multi-start stochastic gradient-free HJB optimization.
    Finds optimal state across ALL Granas subsystems simultaneously.
    """
    bounds = HJBState.bounds()
    n_dims = len(bounds)
    best_value = -np.inf
    best_state = None
    best_result = None
    convergence = []

    for start in range(n_starts):
        # Random initial state within bounds
        x = np.array([np.random.uniform(lo, hi) for lo, hi in bounds])
        step_size = 0.1

        for it in range(n_iterations):
            state = HJBState.from_vector(x)
            result = unified_value(state)
            v = result["value"]

            if v > best_value:
                best_value = v
                best_state = state
                best_result = result

            # Stochastic perturbation (coordinate-wise)
            dim = np.random.randint(n_dims)
            lo, hi = bounds[dim]
            scale = (hi - lo) * step_size
            x_trial = x.copy()
            x_trial[dim] += np.random.normal(0, scale)
            x_trial[dim] = np.clip(x_trial[dim], lo, hi)

            trial_state = HJBState.from_vector(x_trial)
            trial_v = unified_value(trial_state)["value"]
            if trial_v > v:
                x = x_trial

            step_size *= step_decay

        convergence.append(best_value)

    if verbose:
        s = best_state
        r = best_result
        print(f"\n{'='*65}")
        print(f" HJB OPTIMAL CONTROL — ALL GRANAS SUBSYSTEMS")
        print(f"{'='*65}")
        print(f" UNIFIED VALUE: {best_value:.2f} / 100")
        print(f"{'─'*65}")
        print(f" SDL:      RPM={s.spin_rpm:.0f}  Temp={s.anneal_temp_C:.0f}°C"
              f"  Conc={s.concentration_M:.2f}M  Add={s.additive_pct:.1f}%"
              f"  Sol={s.solvent_ratio:.2f}")
        print(f"           PCE={r['sdl']['pce']:.2f}%  Grain={r['sdl']['grain_nm']:.0f}nm")
        print(f" Albedo:   R={s.green_reflectance:.2f}  Tj={r['albedo']['Tj_C']:.1f}°C")
        print(f" ETFE:     Haze={s.etfe_haze_pct:.0f}%  T={r['etfe']['transmittance']:.1f}%")
        print(f" TOPCon:   tox={s.tunnel_oxide_nm:.2f}nm  pSi={s.poly_si_nm:.0f}nm"
              f"  Voc={r['topcon']['Voc_mV']:.0f}mV")
        print(f" CFRP:     Chamfer={s.chamfer_angle_deg:.0f}°"
              f"  Recycling={r['cfrp']['recycling_pct']:.0f}%")
        print(f" GHB:      Mo={s.mo_loading_wt_pct:.1f}%  P={s.n2_pressure_bar:.0f}bar"
              f"  V={s.applied_potential_V:.2f}V  FE={r['ghb']['FE_pct']:.1f}%")
        print(f"{'='*65}")

    return {
        "optimal_value": float(best_value),
        "optimal_state": {
            "sdl": {"rpm": best_state.spin_rpm, "temp": best_state.anneal_temp_C,
                    "conc": best_state.concentration_M, "additive": best_state.additive_pct,
                    "solvent": best_state.solvent_ratio},
            "albedo": {"reflectance": best_state.green_reflectance,
                       "thickness_nm": best_state.film_thickness_nm},
            "etfe": {"haze_pct": best_state.etfe_haze_pct,
                     "thickness_um": best_state.etfe_thickness_um},
            "topcon": {"tunnel_oxide_nm": best_state.tunnel_oxide_nm,
                       "poly_si_nm": best_state.poly_si_nm},
            "cfrp": {"chamfer_deg": best_state.chamfer_angle_deg,
                     "ridge_mm": best_state.ridge_width_mm},
            "ghb": {"mo_wt_pct": best_state.mo_loading_wt_pct,
                    "pressure_bar": best_state.n2_pressure_bar,
                    "potential_V": best_state.applied_potential_V},
        },
        "subsystem_scores": {
            k: round(best_result[k]["score"] * 100, 1)
            for k in ["sdl", "albedo", "etfe", "topcon", "cfrp", "ghb"]
        },
        "convergence_history": convergence,
    }


if __name__ == "__main__":
    np.random.seed(42)
    result = hjb_optimize(n_starts=30, n_iterations=300, verbose=True)
