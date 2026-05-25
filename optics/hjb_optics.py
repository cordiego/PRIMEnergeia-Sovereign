"""
PRIMEnergeia — Granas HJB-Optics Controller
=============================================
Hamilton-Jacobi-Bellman optimal control for photonic panel design.

Solves the HJB equation over the optical design state space:

    ∂V/∂t + min_u [L(x,u) + (∂V/∂x)·f(x,u)] = 0

State:   x = (granule_radius_nm, packing_density, film_thickness_nm)
Control: u = (Δradius, Δdensity, Δthickness)
f(x,u):  Mie scattering + TMM absorption response
L(x,u):  Running cost (fabrication penalty + deviation from target)
V(x,t):  Value function (optimal cost-to-go)

Target: Maximize Jsc (short-circuit current) subject to:
  - Fabrication constraints (5nm≤Δr≤5nm per step)
  - Material budget (density ≤ 0.74 FCC limit)
  - Yablonovitch 4n² light-trapping target

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - [HJB-Optics] - %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Physical Constants
# ─────────────────────────────────────────────────────────────
Q_ELECTRON = 1.602e-19    # C
H_PLANCK = 6.626e-34      # J·s
C_LIGHT = 2.998e8         # m/s
NM = 1e-9                 # nm → m

# NumPy 2.0 compat
_trapz = getattr(np, 'trapezoid', None) or getattr(np, 'trapz', None)


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class OpticalDesignState:
    """State of the panel design during optimization."""
    radius_nm: float          # Granule radius (nm)
    packing_density: float    # Volume fraction (0-0.74)
    thickness_nm: float       # Active layer thickness (nm)


@dataclass
class HJBOpticsResult:
    """Output from the HJB optics optimization."""
    iteration_grid: np.ndarray           # Iteration steps
    radius_trajectory: np.ndarray        # Granule radius over iterations
    density_trajectory: np.ndarray       # Packing density over iterations
    thickness_trajectory: np.ndarray     # Thickness over iterations
    jsc_trajectory: np.ndarray           # Jsc at each step
    absorption_trajectory: np.ndarray    # Weighted absorption at each step
    control_trajectory: np.ndarray       # Applied controls (n_iter×3)
    value_function: np.ndarray           # V(radius, density) slice
    optimal_design: Dict[str, float]     # Final optimal parameters
    jsc_improvement_pct: float           # Improvement vs. initial
    total_cost: float


# ─────────────────────────────────────────────────────────────
# Fast Optical Response Model
# ─────────────────────────────────────────────────────────────
class FastOpticsModel:
    """
    Lightweight optical model for HJB inner loop.
    Uses parametric Mie + TMM approximation:

    A(λ) ≈ 1 - exp[-2κ · d · enhancement(r, f)]

    where enhancement comes from Mie scattering.
    Full engine is too slow for value iteration — this runs in μs.
    """

    # MAPbI3 reference optical constants
    BANDGAP_NM = 800.0
    N_AVG = 2.5
    KAPPA_PEAK = 0.8

    @staticmethod
    def mie_enhancement(radius_nm: float, wavelength_nm: float,
                        density: float) -> float:
        """Path length enhancement from Mie scattering."""
        x = 2 * np.pi * radius_nm / wavelength_nm  # Size parameter
        # Mie resonance peak near x ≈ 2-4
        q_sca = 2.0 * (1 - np.exp(-x)) * np.sin(x / 2)**2
        # Multiple scattering enhancement proportional to density
        enhancement = 1.0 + q_sca * density * 8.0
        return float(enhancement)

    @staticmethod
    def absorptance_spectrum(radius_nm: float, density: float,
                             thickness_nm: float,
                             wavelengths_nm: np.ndarray) -> np.ndarray:
        """Fast A(λ) calculation via Beer-Lambert with Mie enhancement."""
        # Extinction coefficient profile (MAPbI3-like)
        kappa = np.where(
            wavelengths_nm < FastOpticsModel.BANDGAP_NM,
            FastOpticsModel.KAPPA_PEAK * np.exp(
                -(wavelengths_nm - 400)**2 / 30000) + 0.15,
            0.005
        )

        absorptance = np.zeros_like(wavelengths_nm)
        for i, wl in enumerate(wavelengths_nm):
            enh = FastOpticsModel.mie_enhancement(radius_nm, wl, density)
            # Effective optical path = thickness × enhancement
            alpha = 4 * np.pi * kappa[i] / (wl * NM)  # absorption coefficient
            eff_path = thickness_nm * NM * enh
            absorptance[i] = 1.0 - np.exp(-alpha * eff_path)

        return np.clip(absorptance, 0, 1)

    @staticmethod
    def calculate_jsc(radius_nm: float, density: float,
                      thickness_nm: float) -> float:
        """Fast Jsc calculation."""
        wl = np.linspace(300, 1200, 46)
        absorptance = FastOpticsModel.absorptance_spectrum(
            radius_nm, density, thickness_nm, wl
        )

        # AM1.5G photon flux (parametric)
        wl_m = wl * NM
        bb = (2 * H_PLANCK * C_LIGHT**2 / wl_m**5) / \
             (np.exp(H_PLANCK * C_LIGHT / (wl_m * 1.381e-23 * 5778)) - 1)
        E = 1.4 * bb / np.max(bb)
        flux = E * wl_m / (H_PLANCK * C_LIGHT)

        jsc_A_m2 = Q_ELECTRON * _trapz(absorptance * flux, wl)
        return float(jsc_A_m2 / 10.0)  # mA/cm²

    @staticmethod
    def weighted_absorption(radius_nm: float, density: float,
                            thickness_nm: float) -> float:
        """AM1.5G-weighted absorption (%)."""
        wl = np.linspace(300, 1200, 46)
        absorptance = FastOpticsModel.absorptance_spectrum(
            radius_nm, density, thickness_nm, wl
        )
        wl_m = wl * NM
        bb = (2 * H_PLANCK * C_LIGHT**2 / wl_m**5) / \
             (np.exp(H_PLANCK * C_LIGHT / (wl_m * 1.381e-23 * 5778)) - 1)
        irr = 1.4 * bb / np.max(bb)
        return float(_trapz(absorptance * irr, wl) / _trapz(irr, wl) * 100)


# ─────────────────────────────────────────────────────────────
# HJB-Optics Controller
# ─────────────────────────────────────────────────────────────
class HJBOpticsController:
    """
    Hamilton-Jacobi-Bellman optimal control for photonic panel design.

    State space: (radius_nm, packing_density, thickness_nm)
    Control: (Δradius, Δdensity, Δthickness)

    Uses value iteration on a 3D grid:
        V(x, k) = min_u [L(x,u) + V(x', k+1)]

    where x' = x + u (design parameter adjustment).

    The cost L(x,u) penalizes:
      - Low Jsc (we want to maximize it)
      - Large control jumps (fabrication smoothness)
      - Density above FCC limit 0.74
    """

    def __init__(
        self,
        n_iterations: int = 30,
        n_radius: int = 20,
        n_density: int = 15,
        n_thickness: int = 12,
        n_control: int = 7,
        Q_jsc: float = 10.0,
        Q_absorption: float = 1.0,
        R_control: float = 0.5,
    ):
        self.n_iterations = n_iterations
        self.n_radius = n_radius
        self.n_density = n_density
        self.n_thickness = n_thickness
        self.n_control = n_control
        self.Q_jsc = Q_jsc
        self.Q_absorption = Q_absorption
        self.R_control = R_control

        # State grids
        self.radius_grid = np.linspace(80, 600, n_radius)
        self.density_grid = np.linspace(0.1, 0.72, n_density)
        self.thickness_grid = np.linspace(200, 2000, n_thickness)

        # Control grids (Δ per iteration)
        self.dr_grid = np.linspace(-30, 30, n_control)      # nm
        self.df_grid = np.linspace(-0.05, 0.05, n_control)   # density fraction
        self.dd_grid = np.linspace(-100, 100, n_control)     # nm thickness

        # Value function V[radius, density, thickness]
        self.V = None
        self.policy = None

        self.optics = FastOpticsModel()

    def _terminal_cost(self, radius: float, density: float,
                       thickness: float) -> float:
        """Terminal cost: reward high Jsc and absorption."""
        jsc = self.optics.calculate_jsc(radius, density, thickness)
        # Negative cost = reward for high Jsc
        cost = -self.Q_jsc * jsc

        # Bonus for high absorption
        abs_pct = self.optics.weighted_absorption(radius, density, thickness)
        cost -= self.Q_absorption * abs_pct / 100.0

        return cost

    def _running_cost(self, dr: float, df: float, dd: float,
                      density: float) -> float:
        """Running cost: penalize large jumps and constraint violations."""
        # Control effort (fabrication smoothness)
        effort = self.R_control * (abs(dr)/30 + abs(df)/0.05 + abs(dd)/100)

        # Density constraint: penalize above FCC limit
        density_penalty = 0.0
        if density > 0.72:
            density_penalty = 20.0 * (density - 0.72)**2

        return effort + density_penalty

    def _interpolate_V(self, r: float, d: float, t: float) -> float:
        """Trilinear interpolation of V on the state grid."""
        r = np.clip(r, self.radius_grid[0], self.radius_grid[-1])
        d = np.clip(d, self.density_grid[0], self.density_grid[-1])
        t = np.clip(t, self.thickness_grid[0], self.thickness_grid[-1])

        ir = int(np.clip(np.searchsorted(self.radius_grid, r) - 1,
                         0, self.n_radius - 2))
        jd = int(np.clip(np.searchsorted(self.density_grid, d) - 1,
                         0, self.n_density - 2))
        kt = int(np.clip(np.searchsorted(self.thickness_grid, t) - 1,
                         0, self.n_thickness - 2))

        ar = (r - self.radius_grid[ir]) / (self.radius_grid[ir+1] - self.radius_grid[ir])
        ad = (d - self.density_grid[jd]) / (self.density_grid[jd+1] - self.density_grid[jd])
        at = (t - self.thickness_grid[kt]) / (self.thickness_grid[kt+1] - self.thickness_grid[kt])

        V = self.V
        return float(
            V[ir, jd, kt] * (1-ar)*(1-ad)*(1-at) +
            V[ir+1, jd, kt] * ar*(1-ad)*(1-at) +
            V[ir, jd+1, kt] * (1-ar)*ad*(1-at) +
            V[ir, jd, kt+1] * (1-ar)*(1-ad)*at +
            V[ir+1, jd+1, kt] * ar*ad*(1-at) +
            V[ir+1, jd, kt+1] * ar*(1-ad)*at +
            V[ir, jd+1, kt+1] * (1-ar)*ad*at +
            V[ir+1, jd+1, kt+1] * ar*ad*at
        )

    def solve_value_function(self) -> "HJBOpticsController":
        """
        Backward sweep to compute V(x).
        Uses value iteration:
            V(x) = min_u [L(x,u) + V(x + u)]
        """
        logger.info("=" * 60)
        logger.info(" HJB-OPTICS — Solving Value Function")
        logger.info(f" Grid: {self.n_radius}×{self.n_density}×{self.n_thickness}")
        logger.info(f" Controls: {self.n_control}³ = {self.n_control**3}")
        logger.info("=" * 60)

        # Initialize with terminal cost
        self.V = np.zeros((self.n_radius, self.n_density, self.n_thickness))
        self.policy = np.zeros((self.n_radius, self.n_density, self.n_thickness, 3))

        for ir in range(self.n_radius):
            for jd in range(self.n_density):
                for kt in range(self.n_thickness):
                    self.V[ir, jd, kt] = self._terminal_cost(
                        self.radius_grid[ir],
                        self.density_grid[jd],
                        self.thickness_grid[kt],
                    )

        # Value iteration sweeps
        n_sweeps = 4
        for sweep in range(n_sweeps):
            V_old = self.V.copy()

            for ir in range(self.n_radius):
                for jd in range(self.n_density):
                    for kt in range(self.n_thickness):
                        r = self.radius_grid[ir]
                        d = self.density_grid[jd]
                        t = self.thickness_grid[kt]

                        best_cost = np.inf
                        best_u = (0, 0, 0)

                        # Sample control space (not full grid — too slow)
                        for dr in self.dr_grid[::2]:
                            for df in self.df_grid[::2]:
                                for dd in self.dd_grid[::2]:
                                    # Next state
                                    r2 = np.clip(r + dr, 80, 600)
                                    d2 = np.clip(d + df, 0.1, 0.72)
                                    t2 = np.clip(t + dd, 200, 2000)

                                    L = self._running_cost(dr, df, dd, d2)
                                    V_next = self._interpolate_V(r2, d2, t2)
                                    total = L + V_next

                                    if total < best_cost:
                                        best_cost = total
                                        best_u = (dr, df, dd)

                        self.V[ir, jd, kt] = best_cost
                        self.policy[ir, jd, kt] = best_u

            delta = np.max(np.abs(self.V - V_old))
            logger.info(f" Sweep {sweep+1}/{n_sweeps} | max ΔV = {delta:.4f}")
            if delta < 0.01:
                logger.info(" Value function converged!")
                break

        logger.info(" HJB-Optics value function solved.")
        return self

    def optimal_control(self, state: OpticalDesignState) -> Tuple[float, float, float]:
        """Extract optimal control u*(x) from value function."""
        if self.V is None:
            raise RuntimeError("Solve value function first.")

        best_cost = np.inf
        best_u = (0.0, 0.0, 0.0)

        for dr in self.dr_grid:
            for df in self.df_grid:
                for dd in self.dd_grid:
                    r2 = np.clip(state.radius_nm + dr, 80, 600)
                    d2 = np.clip(state.packing_density + df, 0.1, 0.72)
                    t2 = np.clip(state.thickness_nm + dd, 200, 2000)

                    L = self._running_cost(dr, df, dd, d2)
                    V_next = self._interpolate_V(r2, d2, t2)
                    total = L + V_next

                    if total < best_cost:
                        best_cost = total
                        best_u = (dr, df, dd)

        return best_u

    def optimize(self, initial_state: Optional[OpticalDesignState] = None,
                 ) -> HJBOpticsResult:
        """
        Forward simulation using optimal policy.
        """
        if self.V is None:
            self.solve_value_function()

        if initial_state is None:
            initial_state = OpticalDesignState(
                radius_nm=150.0,
                packing_density=0.3,
                thickness_nm=500.0,
            )

        iters = np.arange(self.n_iterations + 1)
        r_traj = np.zeros(self.n_iterations + 1)
        d_traj = np.zeros(self.n_iterations + 1)
        t_traj = np.zeros(self.n_iterations + 1)
        jsc_traj = np.zeros(self.n_iterations + 1)
        abs_traj = np.zeros(self.n_iterations + 1)
        ctrl_traj = np.zeros((self.n_iterations, 3))

        state = initial_state
        r_traj[0] = state.radius_nm
        d_traj[0] = state.packing_density
        t_traj[0] = state.thickness_nm
        jsc_traj[0] = self.optics.calculate_jsc(
            state.radius_nm, state.packing_density, state.thickness_nm)
        abs_traj[0] = self.optics.weighted_absorption(
            state.radius_nm, state.packing_density, state.thickness_nm)

        total_cost = 0.0
        initial_jsc = jsc_traj[0]

        for i in range(self.n_iterations):
            dr, df, dd = self.optimal_control(state)
            ctrl_traj[i] = [dr, df, dd]

            total_cost += self._running_cost(dr, df, dd, state.packing_density)

            state = OpticalDesignState(
                radius_nm=float(np.clip(state.radius_nm + dr, 80, 600)),
                packing_density=float(np.clip(state.packing_density + df, 0.1, 0.72)),
                thickness_nm=float(np.clip(state.thickness_nm + dd, 200, 2000)),
            )

            r_traj[i+1] = state.radius_nm
            d_traj[i+1] = state.packing_density
            t_traj[i+1] = state.thickness_nm
            jsc_traj[i+1] = self.optics.calculate_jsc(
                state.radius_nm, state.packing_density, state.thickness_nm)
            abs_traj[i+1] = self.optics.weighted_absorption(
                state.radius_nm, state.packing_density, state.thickness_nm)

        # Terminal cost
        total_cost += self._terminal_cost(
            state.radius_nm, state.packing_density, state.thickness_nm)

        final_jsc = jsc_traj[-1]
        improvement = (final_jsc - initial_jsc) / initial_jsc * 100

        # Value function slice for visualization
        mid_t = self.n_thickness // 2
        V_slice = self.V[:, :, mid_t]

        logger.info("-" * 60)
        logger.info(f" HJB-Optics Optimization Complete")
        logger.info(f" Radius:   {initial_state.radius_nm:.0f} → {state.radius_nm:.0f} nm")
        logger.info(f" Density:  {initial_state.packing_density:.3f} → {state.packing_density:.3f}")
        logger.info(f" Thickness: {initial_state.thickness_nm:.0f} → {state.thickness_nm:.0f} nm")
        logger.info(f" Jsc:      {initial_jsc:.2f} → {final_jsc:.2f} mA/cm² (+{improvement:.1f}%)")
        logger.info(f" Absorption: {abs_traj[0]:.1f}% → {abs_traj[-1]:.1f}%")
        logger.info("-" * 60)

        return HJBOpticsResult(
            iteration_grid=iters,
            radius_trajectory=r_traj,
            density_trajectory=d_traj,
            thickness_trajectory=t_traj,
            jsc_trajectory=jsc_traj,
            absorption_trajectory=abs_traj,
            control_trajectory=ctrl_traj,
            value_function=V_slice,
            optimal_design={
                "radius_nm": state.radius_nm,
                "packing_density": state.packing_density,
                "thickness_nm": state.thickness_nm,
                "jsc_mA_cm2": final_jsc,
                "absorption_pct": abs_traj[-1],
            },
            jsc_improvement_pct=improvement,
            total_cost=total_cost,
        )


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctrl = HJBOpticsController(
        n_iterations=20,
        n_radius=15,
        n_density=12,
        n_thickness=10,
        n_control=5,
    )
    result = ctrl.optimize()

    print(f"\n{'='*55}")
    print(f" 🔬 HJB-OPTICS OPTIMAL DESIGN")
    print(f"{'─'*55}")
    for k, v in result.optimal_design.items():
        print(f"   {k}: {v:.2f}")
    print(f"   Jsc improvement: +{result.jsc_improvement_pct:.1f}%")
    print(f"{'='*55}")
