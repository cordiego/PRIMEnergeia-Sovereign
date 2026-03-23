"""
PRIMEnergeia — Granas SDL HJB Controller
==========================================
Hamilton-Jacobi-Bellman optimal control for perovskite fabrication
experiment campaign optimization (Self-Driving Lab).

DISTINCT from Optics HJB: this optimizes the FABRICATION PROCESS,
not the optical panel design.

State:   x = (spin_rpm, anneal_temp_C, concentration_M)
Control: u = (Δrpm, Δtemp, Δconc)
f(x,u):  Perovskite crystallization + film quality response
L(x,u):  Running cost (resource penalty + deviation from target)
V(x,t):  Value function (optimal cost-to-go)
Target:  Maximize PCE (power conversion efficiency)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - [SDL-HJB] - %(message)s")

# NumPy 2.0 compat
_trapz = getattr(np, 'trapezoid', None) or getattr(np, 'trapz', None)


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class FabricationState:
    """State of the fabrication recipe during optimization."""
    spin_rpm: float           # Spin coating speed (rpm)
    anneal_temp_C: float      # Annealing temperature (°C)
    concentration_M: float    # Precursor concentration (mol/L)


@dataclass
class SDLHJBResult:
    """Output from the SDL HJB fabrication optimizer."""
    iteration_grid: np.ndarray
    rpm_trajectory: np.ndarray
    temp_trajectory: np.ndarray
    conc_trajectory: np.ndarray
    pce_trajectory: np.ndarray
    grain_trajectory: np.ndarray
    control_trajectory: np.ndarray     # (n_iter, 3)
    value_function: np.ndarray         # V(rpm, temp) slice
    optimal_recipe: Dict[str, float]
    pce_improvement_pct: float
    total_cost: float


# ─────────────────────────────────────────────────────────────
# Perovskite Fabrication Response Model
# ─────────────────────────────────────────────────────────────
class FabricationModel:
    """
    Physics-informed surrogate model for perovskite fabrication.

    Maps (spin_rpm, anneal_temp, concentration) → PCE + grain_size.

    Based on empirical relationships:
      - Spin speed → film thickness (∝ 1/√rpm)
      - Anneal temp → grain growth (Arrhenius) + decomposition
      - Concentration → crystal quality + coverage
    """

    # Optimal windows (MAPbI3 literature)
    RPM_OPT = 4000.0
    TEMP_OPT = 100.0           # °C — optimal annealing
    CONC_OPT = 1.2             # M
    DECOMP_ONSET = 150.0       # °C

    @staticmethod
    def film_thickness_nm(spin_rpm: float, concentration_M: float) -> float:
        """Empirical: thickness ∝ conc / √rpm."""
        return float(1200.0 * concentration_M / np.sqrt(spin_rpm / 1000))

    @staticmethod
    def grain_size_nm(anneal_temp_C: float, spin_rpm: float) -> float:
        """Arrhenius grain growth with decomposition cutoff."""
        temp_K = anneal_temp_C + 273.15
        Ea = 0.45  # eV
        kB = 8.617e-5  # eV/K
        growth = 200 * np.exp(-Ea / (kB * temp_K))
        # Slower spin → thicker film → more time for grain growth
        rpm_factor = 1.0 + 0.3 * (4000 - spin_rpm) / 4000
        # Decomposition above onset
        decomp = 1.0
        if anneal_temp_C > FabricationModel.DECOMP_ONSET:
            decomp = np.exp(-0.03 * (anneal_temp_C - FabricationModel.DECOMP_ONSET))
        grain = growth * max(rpm_factor, 0.3) * decomp
        return float(np.clip(grain, 30, 900))

    @staticmethod
    def predict_pce(spin_rpm: float, anneal_temp_C: float,
                    concentration_M: float) -> float:
        """
        Predict PCE from fabrication parameters.

        PCE model combines:
          - Film quality (grain size, coverage)
          - Thickness optimization (too thin → low absorption, too thick → recombination)
          - Compositional quality (concentration affects stoichiometry)
        """
        # Film thickness
        thickness = FabricationModel.film_thickness_nm(spin_rpm, concentration_M)

        # Grain size
        grain = FabricationModel.grain_size_nm(anneal_temp_C, spin_rpm)

        # Thickness penalty (optimal ~400-600nm)
        thickness_score = np.exp(-((thickness - 500) / 300)**2)

        # Grain quality (bigger = better, up to ~500nm)
        grain_score = 1.0 - np.exp(-grain / 200)

        # Concentration quality (optimal ~1.0-1.4 M)
        conc_score = np.exp(-((concentration_M - 1.2) / 0.4)**2)

        # Spin uniformity (moderate rpm = best uniformity)
        rpm_score = np.exp(-((spin_rpm - 4000) / 2000)**2)

        # Anneal quality (decomposition penalty)
        anneal_score = 1.0
        if anneal_temp_C > FabricationModel.DECOMP_ONSET:
            anneal_score = max(0.1, np.exp(-0.05 * (anneal_temp_C - FabricationModel.DECOMP_ONSET)))
        # Too low temp → poor crystallinity
        if anneal_temp_C < 60:
            anneal_score *= 0.5

        # Combined PCE (max ~22% for MAPbI3)
        base_pce = 22.0
        pce = base_pce * thickness_score * grain_score * conc_score * rpm_score * anneal_score

        # Add noise floor
        pce = max(2.0, pce + np.random.normal(0, 0.1))
        return float(np.clip(pce, 0, 25))


# ─────────────────────────────────────────────────────────────
# SDL HJB Controller
# ─────────────────────────────────────────────────────────────
class SDLHJBController:
    """
    HJB optimal control for perovskite fabrication recipe optimization.

    State: (spin_rpm, anneal_temp_C, concentration_M)
    Control: (Δrpm, Δtemp, Δconc)

    V(x, k) = min_u [L(x,u) + V(x', k+1)]
    """

    def __init__(
        self,
        n_iterations: int = 25,
        n_rpm: int = 15,
        n_temp: int = 15,
        n_conc: int = 10,
        n_control: int = 5,
        Q_pce: float = 5.0,
        R_control: float = 0.3,
    ):
        self.n_iterations = n_iterations
        self.n_rpm = n_rpm
        self.n_temp = n_temp
        self.n_conc = n_conc
        self.n_control = n_control
        self.Q_pce = Q_pce
        self.R_control = R_control

        # State grids
        self.rpm_grid = np.linspace(1000, 8000, n_rpm)
        self.temp_grid = np.linspace(50, 200, n_temp)
        self.conc_grid = np.linspace(0.5, 2.0, n_conc)

        # Control grids
        self.drpm_grid = np.linspace(-500, 500, n_control)
        self.dtemp_grid = np.linspace(-15, 15, n_control)
        self.dconc_grid = np.linspace(-0.1, 0.1, n_control)

        self.V = None
        self.model = FabricationModel()

    def _terminal_cost(self, rpm: float, temp: float, conc: float) -> float:
        """Reward high PCE."""
        pce = self.model.predict_pce(rpm, temp, conc)
        return -self.Q_pce * pce

    def _running_cost(self, drpm: float, dtemp: float, dconc: float) -> float:
        """Penalize large recipe changes (equipment stability)."""
        return self.R_control * (
            abs(drpm) / 500 + abs(dtemp) / 15 + abs(dconc) / 0.1
        )

    def _interpolate_V(self, rpm: float, temp: float, conc: float) -> float:
        """Trilinear interpolation of V."""
        rpm = np.clip(rpm, self.rpm_grid[0], self.rpm_grid[-1])
        temp = np.clip(temp, self.temp_grid[0], self.temp_grid[-1])
        conc = np.clip(conc, self.conc_grid[0], self.conc_grid[-1])

        ir = int(np.clip(np.searchsorted(self.rpm_grid, rpm) - 1, 0, self.n_rpm - 2))
        jt = int(np.clip(np.searchsorted(self.temp_grid, temp) - 1, 0, self.n_temp - 2))
        kc = int(np.clip(np.searchsorted(self.conc_grid, conc) - 1, 0, self.n_conc - 2))

        ar = (rpm - self.rpm_grid[ir]) / (self.rpm_grid[ir+1] - self.rpm_grid[ir])
        at = (temp - self.temp_grid[jt]) / (self.temp_grid[jt+1] - self.temp_grid[jt])
        ac = (conc - self.conc_grid[kc]) / (self.conc_grid[kc+1] - self.conc_grid[kc])

        V = self.V
        return float(
            V[ir, jt, kc] * (1-ar)*(1-at)*(1-ac) +
            V[ir+1, jt, kc] * ar*(1-at)*(1-ac) +
            V[ir, jt+1, kc] * (1-ar)*at*(1-ac) +
            V[ir, jt, kc+1] * (1-ar)*(1-at)*ac +
            V[ir+1, jt+1, kc] * ar*at*(1-ac) +
            V[ir+1, jt, kc+1] * ar*(1-at)*ac +
            V[ir, jt+1, kc+1] * (1-ar)*at*ac +
            V[ir+1, jt+1, kc+1] * ar*at*ac
        )

    def solve_value_function(self) -> "SDLHJBController":
        """Value iteration on fabrication state space."""
        logger.info("=" * 60)
        logger.info(" SDL-HJB — Solving Fabrication Value Function")
        logger.info(f" Grid: {self.n_rpm}×{self.n_temp}×{self.n_conc}")
        logger.info("=" * 60)

        self.V = np.zeros((self.n_rpm, self.n_temp, self.n_conc))

        # Terminal cost
        for ir in range(self.n_rpm):
            for jt in range(self.n_temp):
                for kc in range(self.n_conc):
                    self.V[ir, jt, kc] = self._terminal_cost(
                        self.rpm_grid[ir], self.temp_grid[jt], self.conc_grid[kc])

        # Value iteration
        for sweep in range(3):
            V_old = self.V.copy()
            for ir in range(self.n_rpm):
                for jt in range(self.n_temp):
                    for kc in range(self.n_conc):
                        r, t, c = self.rpm_grid[ir], self.temp_grid[jt], self.conc_grid[kc]
                        best = np.inf
                        for drpm in self.drpm_grid:
                            for dtemp in self.dtemp_grid:
                                for dconc in self.dconc_grid:
                                    r2 = np.clip(r + drpm, 1000, 8000)
                                    t2 = np.clip(t + dtemp, 50, 200)
                                    c2 = np.clip(c + dconc, 0.5, 2.0)
                                    L = self._running_cost(drpm, dtemp, dconc)
                                    total = L + self._interpolate_V(r2, t2, c2)
                                    if total < best:
                                        best = total
                        self.V[ir, jt, kc] = best

            delta = np.max(np.abs(self.V - V_old))
            logger.info(f" Sweep {sweep+1}/3 | max ΔV = {delta:.4f}")
            if delta < 0.01:
                break

        logger.info(" SDL-HJB value function solved.")
        return self

    def optimal_control(self, state: FabricationState) -> Tuple[float, float, float]:
        """Extract optimal control."""
        if self.V is None:
            raise RuntimeError("Solve first.")
        best_cost, best_u = np.inf, (0.0, 0.0, 0.0)
        for drpm in self.drpm_grid:
            for dtemp in self.dtemp_grid:
                for dconc in self.dconc_grid:
                    r2 = np.clip(state.spin_rpm + drpm, 1000, 8000)
                    t2 = np.clip(state.anneal_temp_C + dtemp, 50, 200)
                    c2 = np.clip(state.concentration_M + dconc, 0.5, 2.0)
                    L = self._running_cost(drpm, dtemp, dconc)
                    total = L + self._interpolate_V(r2, t2, c2)
                    if total < best_cost:
                        best_cost = total
                        best_u = (drpm, dtemp, dconc)
        return best_u

    def optimize(self, initial: Optional[FabricationState] = None) -> SDLHJBResult:
        """Forward simulation using optimal policy."""
        if self.V is None:
            self.solve_value_function()

        if initial is None:
            initial = FabricationState(3000.0, 80.0, 0.8)

        iters = np.arange(self.n_iterations + 1)
        rpm_t = np.zeros(self.n_iterations + 1)
        temp_t = np.zeros(self.n_iterations + 1)
        conc_t = np.zeros(self.n_iterations + 1)
        pce_t = np.zeros(self.n_iterations + 1)
        grain_t = np.zeros(self.n_iterations + 1)
        ctrl_t = np.zeros((self.n_iterations, 3))

        state = initial
        rpm_t[0], temp_t[0], conc_t[0] = state.spin_rpm, state.anneal_temp_C, state.concentration_M
        pce_t[0] = self.model.predict_pce(state.spin_rpm, state.anneal_temp_C, state.concentration_M)
        grain_t[0] = self.model.grain_size_nm(state.anneal_temp_C, state.spin_rpm)
        initial_pce = pce_t[0]
        total_cost = 0.0

        for i in range(self.n_iterations):
            dr, dt, dc = self.optimal_control(state)
            ctrl_t[i] = [dr, dt, dc]
            total_cost += self._running_cost(dr, dt, dc)

            state = FabricationState(
                spin_rpm=float(np.clip(state.spin_rpm + dr, 1000, 8000)),
                anneal_temp_C=float(np.clip(state.anneal_temp_C + dt, 50, 200)),
                concentration_M=float(np.clip(state.concentration_M + dc, 0.5, 2.0)),
            )
            rpm_t[i+1] = state.spin_rpm
            temp_t[i+1] = state.anneal_temp_C
            conc_t[i+1] = state.concentration_M
            pce_t[i+1] = self.model.predict_pce(state.spin_rpm, state.anneal_temp_C, state.concentration_M)
            grain_t[i+1] = self.model.grain_size_nm(state.anneal_temp_C, state.spin_rpm)

        final_pce = pce_t[-1]
        improvement = (final_pce - initial_pce) / max(initial_pce, 1) * 100

        mid_c = self.n_conc // 2
        V_slice = self.V[:, :, mid_c]

        logger.info("-" * 60)
        logger.info(f" SDL-HJB Complete")
        logger.info(f" RPM:  {initial.spin_rpm:.0f} → {state.spin_rpm:.0f}")
        logger.info(f" Temp: {initial.anneal_temp_C:.0f} → {state.anneal_temp_C:.0f} °C")
        logger.info(f" Conc: {initial.concentration_M:.2f} → {state.concentration_M:.2f} M")
        logger.info(f" PCE:  {initial_pce:.2f} → {final_pce:.2f}% (+{improvement:.1f}%)")
        logger.info("-" * 60)

        return SDLHJBResult(
            iteration_grid=iters,
            rpm_trajectory=rpm_t,
            temp_trajectory=temp_t,
            conc_trajectory=conc_t,
            pce_trajectory=pce_t,
            grain_trajectory=grain_t,
            control_trajectory=ctrl_t,
            value_function=V_slice,
            optimal_recipe={
                "spin_rpm": state.spin_rpm,
                "anneal_temp_C": state.anneal_temp_C,
                "concentration_M": state.concentration_M,
                "pce_pct": final_pce,
                "grain_nm": grain_t[-1],
                "thickness_nm": self.model.film_thickness_nm(state.spin_rpm, state.concentration_M),
            },
            pce_improvement_pct=improvement,
            total_cost=total_cost,
        )


if __name__ == "__main__":
    ctrl = SDLHJBController(n_iterations=15, n_rpm=12, n_temp=12, n_conc=8, n_control=5)
    res = ctrl.optimize()
    print(f"\n{'='*55}")
    print(f" 🧬 SDL-HJB OPTIMAL RECIPE")
    for k, v in res.optimal_recipe.items():
        print(f"   {k}: {v:.2f}")
    print(f"   PCE improvement: +{res.pce_improvement_pct:.1f}%")
    print(f"{'='*55}")
