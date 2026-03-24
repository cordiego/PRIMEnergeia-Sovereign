"""
PRIME-Kernel — Unified HJB Solver
====================================
Generic Hamilton-Jacobi-Bellman optimal control solver.
Used by both PRIME Grid (frequency control) and PRIME Materials
(Granas annealing schedule optimization).

The HJB equation:
    ∂V/∂t + min_u [L(x,u) + (∂V/∂x)·f(x,u)] = 0

This module provides the abstract solver — domain-specific dynamics
and cost functions are injected by each SBU.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger("prime_kernel.hjb")


# ─────────────────────────────────────────────────────────────
# Abstract Dynamics Interface
# ─────────────────────────────────────────────────────────────
class HJBDynamics(ABC):
    """
    Abstract base for state-space dynamics.
    Each SBU implements this with its own physics.
    """

    @abstractmethod
    def state_dims(self) -> int:
        """Number of state dimensions."""
        ...

    @abstractmethod
    def state_bounds(self) -> List[Tuple[float, float]]:
        """Bounds for each state dimension: [(min, max), ...]."""
        ...

    @abstractmethod
    def control_bounds(self) -> Tuple[float, float]:
        """(min, max) for the scalar control variable."""
        ...

    @abstractmethod
    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        """
        Forward integrate one time step.
        state: array of shape (state_dims,)
        control: scalar control input
        dt: time step (s)
        Returns: next state array
        """
        ...

    @abstractmethod
    def running_cost(self, state: np.ndarray, control: float) -> float:
        """Running cost L(x, u)."""
        ...

    @abstractmethod
    def terminal_cost(self, state: np.ndarray) -> float:
        """Terminal cost Φ(x(T))."""
        ...


# ─────────────────────────────────────────────────────────────
# HJB Result
# ─────────────────────────────────────────────────────────────
@dataclass
class HJBResult:
    """Output from the HJB optimal control solver."""
    time_grid: np.ndarray
    state_trajectory: np.ndarray    # shape (n_steps+1, state_dims)
    control_trajectory: np.ndarray  # shape (n_steps,)
    value_function: np.ndarray      # Discretized V(x) at solution
    total_cost: float
    n_sweeps: int
    converged: bool
    metadata: Dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Generic HJB Solver
# ─────────────────────────────────────────────────────────────
class HJBSolver:
    """
    Generic Hamilton-Jacobi-Bellman solver via value iteration.

    Works with any dynamics that implement HJBDynamics.

    Parameters
    ----------
    dynamics : HJBDynamics
        Domain-specific dynamics (physics + cost)
    total_time : float
        Horizon in seconds
    dt : float
        Time step in seconds
    grid_points : list of int
        Number of grid points per state dimension
    n_controls : int
        Number of candidate control actions to evaluate
    max_sweeps : int
        Maximum backward sweeps for convergence
    tol : float
        Convergence tolerance on max |ΔV|
    """

    def __init__(
        self,
        dynamics: HJBDynamics,
        total_time: float = 1200.0,
        dt: float = 2.0,
        grid_points: Optional[List[int]] = None,
        n_controls: int = 11,
        max_sweeps: int = 8,
        tol: float = 0.01,
    ):
        self.dynamics = dynamics
        self.total_time = total_time
        self.dt = dt
        self.n_controls = n_controls
        self.max_sweeps = max_sweeps
        self.tol = tol

        n_dims = dynamics.state_dims()
        bounds = dynamics.state_bounds()
        ctrl_bounds = dynamics.control_bounds()

        # Default grid: 20 points per dimension
        if grid_points is None:
            grid_points = [20] * n_dims

        # Build state grids
        self.state_grids = [
            np.linspace(bounds[d][0], bounds[d][1], grid_points[d])
            for d in range(n_dims)
        ]

        # Control grid
        self.control_grid = np.linspace(ctrl_bounds[0], ctrl_bounds[1], n_controls)

        # Value function: shape = grid_points
        self.V = np.zeros(grid_points)
        self.policy = np.zeros(grid_points, dtype=int)
        self._solved = False

    def _interpolate_V(self, state: np.ndarray) -> float:
        """N-dimensional linear interpolation of V(x)."""
        n_dims = len(self.state_grids)

        # Clamp state to grid bounds
        indices = []
        fractions = []
        for d in range(n_dims):
            grid = self.state_grids[d]
            x = np.clip(state[d], grid[0], grid[-1])
            idx = np.searchsorted(grid, x) - 1
            idx = np.clip(idx, 0, len(grid) - 2)
            frac = (x - grid[idx]) / (grid[idx + 1] - grid[idx])
            indices.append(idx)
            fractions.append(frac)

        # For performance, use direct indexing for 1-3D cases
        if n_dims == 1:
            i = indices[0]
            a = fractions[0]
            return float(self.V[i] * (1 - a) + self.V[i + 1] * a)

        elif n_dims == 2:
            i, j = indices
            a, b = fractions
            return float(
                self.V[i, j] * (1 - a) * (1 - b) +
                self.V[i + 1, j] * a * (1 - b) +
                self.V[i, j + 1] * (1 - a) * b +
                self.V[i + 1, j + 1] * a * b
            )

        elif n_dims == 3:
            i, j, k = indices
            a, b, c = fractions
            return float(
                self.V[i, j, k] * (1 - a) * (1 - b) * (1 - c) +
                self.V[i + 1, j, k] * a * (1 - b) * (1 - c) +
                self.V[i, j + 1, k] * (1 - a) * b * (1 - c) +
                self.V[i, j, k + 1] * (1 - a) * (1 - b) * c +
                self.V[i + 1, j + 1, k] * a * b * (1 - c) +
                self.V[i + 1, j, k + 1] * a * (1 - b) * c +
                self.V[i, j + 1, k + 1] * (1 - a) * b * c +
                self.V[i + 1, j + 1, k + 1] * a * b * c
            )

        else:
            # General N-D case via recursive interpolation
            # (for 4D+ dynamics — future extension)
            raise NotImplementedError(f"Interpolation for {n_dims}D not yet implemented")

    def solve(self) -> "HJBSolver":
        """
        Backward sweep: compute V(x) via value iteration.

        Returns self for method chaining.
        """
        n_dims = self.dynamics.state_dims()
        grid_shapes = [len(g) for g in self.state_grids]

        logger.info("=" * 60)
        logger.info(" PRIME-Kernel HJB Solver — Value Iteration")
        logger.info(f" Grid: {'×'.join(str(s) for s in grid_shapes)}")
        logger.info(f" Controls: {self.n_controls}")
        logger.info(f" Horizon: {self.total_time:.0f}s, dt={self.dt:.1f}s")
        logger.info("=" * 60)

        # Terminal condition
        for idx in np.ndindex(*grid_shapes):
            state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
            self.V[idx] = self.dynamics.terminal_cost(state)

        # Value iteration sweeps
        converged = False
        for sweep in range(self.max_sweeps):
            V_old = self.V.copy()

            for idx in np.ndindex(*grid_shapes):
                state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])

                best_cost = np.inf
                best_u = 0

                for iu, u in enumerate(self.control_grid):
                    L = self.dynamics.running_cost(state, u)
                    next_state = self.dynamics.step(state, u, self.dt)
                    V_next = self._interpolate_V(next_state)
                    total = L * self.dt + V_next

                    if total < best_cost:
                        best_cost = total
                        best_u = iu

                self.V[idx] = best_cost
                self.policy[idx] = best_u

            delta = np.max(np.abs(self.V - V_old))
            logger.info(f" Sweep {sweep + 1}/{self.max_sweeps} | max ΔV = {delta:.4f}")

            if delta < self.tol:
                converged = True
                logger.info(" ✅ Value function converged!")
                break

        self._solved = True
        self._converged = converged
        self._n_sweeps = sweep + 1
        return self

    def optimal_control(self, state: np.ndarray) -> float:
        """Extract optimal control u*(x) from the solved value function."""
        if not self._solved:
            raise RuntimeError("Call solve() first.")

        best_cost = np.inf
        best_u = 0.0

        for u in self.control_grid:
            L = self.dynamics.running_cost(state, u)
            next_state = self.dynamics.step(state, u, self.dt)
            V_next = self._interpolate_V(next_state)
            total = L * self.dt + V_next

            if total < best_cost:
                best_cost = total
                best_u = u

        return best_u

    def simulate(self, initial_state: np.ndarray) -> HJBResult:
        """
        Forward simulation using the optimal policy.
        """
        if not self._solved:
            self.solve()

        n_steps = int(self.total_time / self.dt)
        n_dims = self.dynamics.state_dims()

        time_grid = np.linspace(0, self.total_time, n_steps + 1)
        state_traj = np.zeros((n_steps + 1, n_dims))
        control_traj = np.zeros(n_steps)

        state = initial_state.copy()
        state_traj[0] = state
        total_cost = 0.0

        for i in range(n_steps):
            u = self.optimal_control(state)
            control_traj[i] = u
            total_cost += self.dynamics.running_cost(state, u) * self.dt
            state = self.dynamics.step(state, u, self.dt)
            state_traj[i + 1] = state

        total_cost += self.dynamics.terminal_cost(state)

        logger.info(f" Simulation complete | Total cost: {total_cost:.3f}")

        return HJBResult(
            time_grid=time_grid,
            state_trajectory=state_traj,
            control_trajectory=control_traj,
            value_function=self.V.copy(),
            total_cost=total_cost,
            n_sweeps=self._n_sweeps,
            converged=self._converged,
        )


# ─────────────────────────────────────────────────────────────
# Pre-built: Grid Frequency Control Dynamics
# ─────────────────────────────────────────────────────────────
class GridFrequencyDynamics(HJBDynamics):
    """
    HJB dynamics for grid frequency stabilization.
    Used by PRIME Grid (VZA-400, ERCOT, MIBEL).

    State: [frequency_deviation_hz, power_injection_mw]
    Control: injection_ramp_rate (MW/s)
    """

    def __init__(self, nominal_freq: float = 60.0, inertia_constant: float = 5.0,
                 damping: float = 1.0, max_injection_mw: float = 100.0):
        self.nominal_freq = nominal_freq
        self.H = inertia_constant      # System inertia (s)
        self.D = damping               # Damping coefficient
        self.max_inj = max_injection_mw

    def state_dims(self) -> int:
        return 2

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(-2.0, 2.0), (0.0, self.max_inj)]  # freq deviation, injection

    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)  # MW/s ramp rate

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df, P = state
        # Swing equation: 2H * d(Δf)/dt = P_inj - D*Δf - P_disturbance
        ddf = (P - self.D * df) / (2 * self.H)
        dP = control  # ramp rate

        new_df = df + ddf * dt
        new_P = np.clip(P + dP * dt, 0, self.max_inj)
        new_df = np.clip(new_df, -2.0, 2.0)

        return np.array([new_df, new_P])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        df, P = state
        # Penalize frequency deviation (quadratic) + energy cost
        freq_cost = 100.0 * df ** 2
        energy_cost = 0.01 * abs(control)
        # Penalty zone: deviation > 0.5 Hz triggers CENACE/NERC penalties
        penalty = 0.0
        if abs(df) > 0.5:
            penalty = 500.0 * (abs(df) - 0.5) ** 2
        return freq_cost + energy_cost + penalty

    def terminal_cost(self, state: np.ndarray) -> float:
        df, P = state
        return 200.0 * df ** 2 + 0.1 * P


# ─────────────────────────────────────────────────────────────
# Pre-built: Perovskite Annealing Dynamics
# ─────────────────────────────────────────────────────────────
class PerovskiteAnnealingDynamics(HJBDynamics):
    """
    HJB dynamics for perovskite annealing schedule optimization.
    Used by PRIME Materials (Granas-SDL, Granas-Optics).

    State: [grain_size_nm, defect_density, film_temp_C]
    Control: temperature ramp rate (°C/s)
    """

    # Physical constants
    BOLTZMANN_EV = 8.617333e-5
    MAX_GRAIN_NM = 900.0
    DECOMP_TEMP_C = 200.0

    def __init__(self, Q_grain: float = 1.0, Q_defect: float = 50.0,
                 R_energy: float = 0.1):
        self.Q_grain = Q_grain
        self.Q_defect = Q_defect
        self.R_energy = R_energy

    def state_dims(self) -> int:
        return 3

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(30.0, 900.0), (0.02, 2.0), (25.0, 220.0)]

    def control_bounds(self) -> Tuple[float, float]:
        return (-5.0, 5.0)

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        grain, defects, temp = state
        temp_k = temp + 273.15
        setpoint = np.clip(temp + control * dt, 25.0, 250.0)

        # Grain growth (Arrhenius + Ostwald saturation)
        arr_grain = np.exp(-0.45 / (self.BOLTZMANN_EV * temp_k))
        saturation = max(0, 1.0 - grain / self.MAX_GRAIN_NM)
        decomp = np.exp(-0.05 * max(0, temp - self.DECOMP_TEMP_C)) if temp > self.DECOMP_TEMP_C else 1.0
        dg = 2.0 * arr_grain * saturation * decomp

        # Defect evolution
        passivation = 0.05 * defects * np.exp(-0.35 / (self.BOLTZMANN_EV * temp_k))
        gb_reduction = 0.001 * max(0, grain - 100) / 500.0
        creation = 0.002 * ((temp - 160) / 40.0) ** 2 if temp > 160 else 0.0
        dd = -passivation - gb_reduction + creation

        # Thermal lag
        dT = (setpoint - temp) / 5.0

        new_grain = np.clip(grain + dg * dt, 30.0, 900.0)
        new_defects = np.clip(defects + dd * dt, 0.02, 3.0)
        new_temp = np.clip(temp + dT * dt, 25.0, 250.0)

        return np.array([new_grain, new_defects, new_temp])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        _, _, temp = state
        energy_cost = self.R_energy * abs(control)
        temp_penalty = 2.0 * ((temp - 200) / 20.0) ** 2 if temp > 200 else 0.0
        return energy_cost + temp_penalty

    def terminal_cost(self, state: np.ndarray) -> float:
        grain, defects, _ = state
        grain_reward = -self.Q_grain * (grain / self.MAX_GRAIN_NM)
        defect_penalty = self.Q_defect * defects
        return grain_reward + defect_penalty
