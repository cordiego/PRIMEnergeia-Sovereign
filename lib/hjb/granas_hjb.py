"""
PRIMEnergeia — Granas HJB Controller
======================================
Hamilton-Jacobi-Bellman dynamic programming for optimal annealing
schedule control during perovskite solar cell fabrication.

Solves the HJB equation over the crystallization state space:

    ∂V/∂t + min_u [L(x,u) + (∂V/∂x)·f(x,u)] = 0

State:   x = (grain_size_nm, defect_density, film_temp_C)
Control: u = temperature ramp rate (°C/s)
f(x,u):  Arrhenius grain growth + defect evolution + thermal lag
L(x,u):  Running cost (energy penalty + quality penalty)
V(x,t):  Value function (optimal cost-to-go)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [Granas HJB] - %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Physical Constants
# ─────────────────────────────────────────────────────────────
BOLTZMANN_EV = 8.617333e-5   # eV/K
ROOM_TEMP_K = 300.0          # 27 °C
ACTIVATION_GRAIN = 0.45      # Grain growth activation energy (eV)
ACTIVATION_DEFECT = 0.35     # Defect annealing activation energy (eV)


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class AnnealingState:
    """State of the perovskite film during annealing."""
    grain_size_nm: float    # Average grain diameter (nm)
    defect_density: float   # Relative defect density (a.u.)
    film_temp_C: float      # Current film temperature (°C)


@dataclass
class HJBResult:
    """Output from the HJB optimal control solver."""
    time_grid: np.ndarray              # Time steps (s)
    grain_trajectory: np.ndarray       # Grain size over time (nm)
    defect_trajectory: np.ndarray      # Defect density over time
    temp_trajectory: np.ndarray        # Film temperature over time (°C)
    control_trajectory: np.ndarray     # Optimal ramp rate over time (°C/s)
    value_function: np.ndarray         # V(grain, defect) at final temp
    optimal_schedule: List[Tuple[float, float]]  # (time_s, temp_C) pairs
    terminal_grain_nm: float
    terminal_defects: float
    pce_boost_pct: float               # Estimated PCE improvement vs. static
    total_cost: float                  # Total accumulated cost


# ─────────────────────────────────────────────────────────────
# Crystallization Dynamics
# ─────────────────────────────────────────────────────────────
class CrystallizationDynamics:
    """
    State-space model of perovskite film evolution during annealing.

    Three coupled dynamics:
      1. Grain growth (Arrhenius, Ostwald ripening)
      2. Defect passivation/creation
      3. Thermal lag (first-order)
    """

    # Pre-exponential factors (calibrated to MAPbI3 literature)
    GRAIN_RATE_PREFACTOR = 2.0       # nm/s base growth rate
    DEFECT_ANNEAL_PREFACTOR = 0.05   # Defect passivation rate
    DEFECT_CREATION_PREFACTOR = 0.002  # High-temp defect creation rate
    THERMAL_TAU = 5.0                # Thermal time constant (s)

    # Physical limits
    MAX_GRAIN_NM = 900.0
    MIN_GRAIN_NM = 30.0
    MAX_DEFECTS = 3.0
    MIN_DEFECTS = 0.02
    DECOMP_TEMP_C = 200.0           # MAPbI3 decomposition onset

    @staticmethod
    def grain_growth_rate(grain_nm: float, temp_C: float) -> float:
        """
        Arrhenius grain growth rate (nm/s).
        Ostwald ripening: larger grains grow slower (saturating).
        Higher temperature → faster growth until decomposition.
        """
        temp_K = temp_C + 273.15
        # Arrhenius factor
        arrhenius = np.exp(-ACTIVATION_GRAIN / (BOLTZMANN_EV * temp_K))
        # Saturation: growth slows as grains approach maximum
        saturation = (1.0 - grain_nm / CrystallizationDynamics.MAX_GRAIN_NM)
        saturation = max(saturation, 0.0)
        # Decomposition penalty above 200°C
        decomp = 1.0
        if temp_C > CrystallizationDynamics.DECOMP_TEMP_C:
            excess = temp_C - CrystallizationDynamics.DECOMP_TEMP_C
            decomp = np.exp(-0.05 * excess)

        rate = CrystallizationDynamics.GRAIN_RATE_PREFACTOR * arrhenius * saturation * decomp
        return float(rate)

    @staticmethod
    def defect_evolution_rate(defects: float, temp_C: float,
                              grain_nm: float) -> float:
        """
        Net defect rate = passivation (negative) + creation (positive).
        Moderate temp → passivation dominates.
        Very high temp → Pb⁰ defects form (creation dominates).
        Larger grains → fewer grain-boundary defects.
        """
        temp_K = temp_C + 273.15

        # Passivation: Arrhenius, proportional to current defect density
        passivation = (CrystallizationDynamics.DEFECT_ANNEAL_PREFACTOR
                       * defects
                       * np.exp(-ACTIVATION_DEFECT / (BOLTZMANN_EV * temp_K)))

        # Grain-boundary reduction: larger grains = less surface defects
        gb_reduction = 0.001 * max(0, grain_nm - 100) / 500.0

        # Defect creation at high temperatures (Pb⁰ formation)
        creation = 0.0
        if temp_C > 160:
            excess = (temp_C - 160) / 40.0
            creation = CrystallizationDynamics.DEFECT_CREATION_PREFACTOR * excess ** 2

        # Net rate (negative = improving)
        rate = -passivation - gb_reduction + creation
        return float(rate)

    @staticmethod
    def thermal_dynamics(film_temp_C: float, setpoint_C: float) -> float:
        """
        First-order thermal lag: dT/dt = (T_set - T_film) / τ
        Models the lag between heater setpoint and actual film temperature.
        """
        return (setpoint_C - film_temp_C) / CrystallizationDynamics.THERMAL_TAU

    @classmethod
    def step(cls, state: AnnealingState, control_ramp: float,
             dt: float) -> AnnealingState:
        """
        Forward integrate one time step.

        Parameters
        ----------
        state : AnnealingState
            Current (grain, defects, temp)
        control_ramp : float
            Temperature ramp rate (°C/s). The setpoint is current + ramp*dt.
        dt : float
            Time step (s)

        Returns
        -------
        AnnealingState : next state
        """
        setpoint = state.film_temp_C + control_ramp * dt

        # Clamp setpoint to physical limits
        setpoint = np.clip(setpoint, 25.0, 250.0)

        # Compute rates
        dg = cls.grain_growth_rate(state.grain_size_nm, state.film_temp_C)
        dd = cls.defect_evolution_rate(state.defect_density, state.film_temp_C,
                                       state.grain_size_nm)
        dT = cls.thermal_dynamics(state.film_temp_C, setpoint)

        # Euler integration
        new_grain = state.grain_size_nm + dg * dt
        new_defects = state.defect_density + dd * dt
        new_temp = state.film_temp_C + dT * dt

        # Clamp to physical bounds
        new_grain = float(np.clip(new_grain, cls.MIN_GRAIN_NM, cls.MAX_GRAIN_NM))
        new_defects = float(np.clip(new_defects, cls.MIN_DEFECTS, cls.MAX_DEFECTS))
        new_temp = float(np.clip(new_temp, 25.0, 250.0))

        return AnnealingState(
            grain_size_nm=new_grain,
            defect_density=new_defects,
            film_temp_C=new_temp,
        )


# ─────────────────────────────────────────────────────────────
# HJB Controller
# ─────────────────────────────────────────────────────────────
class GranasHJBController:
    """
    Hamilton-Jacobi-Bellman optimal control solver for perovskite
    annealing schedule optimization.

    Uses value iteration (backward dynamic programming) on a
    discretized state-time grid:

        V(x, t) = min_u [L(x,u)·dt + V(x', t+dt)]

    where x' = f(x, u, dt) is the next state.

    Parameters
    ----------
    total_time_s : float
        Total annealing duration (seconds). Default 1200s (20 min).
    dt : float
        Time step (seconds). Default 2.0s.
    n_grain : int
        Grid points for grain size dimension.
    n_defect : int
        Grid points for defect density dimension.
    n_temp : int
        Grid points for temperature dimension.
    n_control : int
        Number of candidate control actions (ramp rates).
    Q_grain : float
        Terminal cost weight for grain size (negative = reward large grains).
    Q_defect : float
        Terminal cost weight for defect density.
    R_energy : float
        Running cost weight for energy consumption (|ramp|).
    """

    def __init__(
        self,
        total_time_s: float = 1200.0,
        dt: float = 2.0,
        n_grain: int = 30,
        n_defect: int = 25,
        n_temp: int = 20,
        n_control: int = 11,
        Q_grain: float = 1.0,
        Q_defect: float = 50.0,
        R_energy: float = 0.1,
    ):
        self.total_time_s = total_time_s
        self.dt = dt
        self.n_grain = n_grain
        self.n_defect = n_defect
        self.n_temp = n_temp
        self.n_control = n_control
        self.Q_grain = Q_grain
        self.Q_defect = Q_defect
        self.R_energy = R_energy

        self.dynamics = CrystallizationDynamics()

        # State grids
        self.grain_grid = np.linspace(30, 900, n_grain)
        self.defect_grid = np.linspace(0.02, 2.0, n_defect)
        self.temp_grid = np.linspace(25, 220, n_temp)

        # Control grid: ramp rates from -5 °C/s (cooling) to +5 °C/s (heating)
        self.control_grid = np.linspace(-5.0, 5.0, n_control)

        # Time grid
        self.n_time = int(total_time_s / dt) + 1
        self.time_grid = np.linspace(0, total_time_s, self.n_time)

        # Value function: V[grain, defect, temp]
        self.V = None
        self.policy = None  # Optimal control index at each state

    def _terminal_cost(self, grain_nm: float, defect: float) -> float:
        """
        Terminal cost: penalize small grains and high defects.
        Reward large grains → negative cost contribution.
        """
        # Grain reward: larger is better (normalized 0-1)
        grain_normalized = grain_nm / CrystallizationDynamics.MAX_GRAIN_NM
        grain_cost = -self.Q_grain * grain_normalized

        # Defect penalty: lower is better
        defect_cost = self.Q_defect * defect

        return grain_cost + defect_cost

    def _running_cost(self, ramp_rate: float, temp_C: float) -> float:
        """
        Running cost: energy consumption + over-temperature penalty.
        """
        # Energy cost: proportional to |ramp rate|
        energy_cost = self.R_energy * abs(ramp_rate)

        # Over-temperature penalty (above 200°C → decomposition)
        temp_penalty = 0.0
        if temp_C > 200:
            temp_penalty = 2.0 * ((temp_C - 200) / 20.0) ** 2

        return energy_cost + temp_penalty

    def _interpolate_V(self, grain: float, defect: float,
                       temp: float) -> float:
        """Trilinear interpolation of V on the state grid."""
        # Clamp to grid bounds
        grain = np.clip(grain, self.grain_grid[0], self.grain_grid[-1])
        defect = np.clip(defect, self.defect_grid[0], self.defect_grid[-1])
        temp = np.clip(temp, self.temp_grid[0], self.temp_grid[-1])

        # Find indices
        ig = np.searchsorted(self.grain_grid, grain) - 1
        ig = np.clip(ig, 0, self.n_grain - 2)
        jd = np.searchsorted(self.defect_grid, defect) - 1
        jd = np.clip(jd, 0, self.n_defect - 2)
        kt = np.searchsorted(self.temp_grid, temp) - 1
        kt = np.clip(kt, 0, self.n_temp - 2)

        # Fractional positions
        ag = (grain - self.grain_grid[ig]) / (self.grain_grid[ig+1] - self.grain_grid[ig])
        ad = (defect - self.defect_grid[jd]) / (self.defect_grid[jd+1] - self.defect_grid[jd])
        at = (temp - self.temp_grid[kt]) / (self.temp_grid[kt+1] - self.temp_grid[kt])

        # Trilinear interpolation
        V = self.V
        val = (
            V[ig, jd, kt] * (1-ag)*(1-ad)*(1-at) +
            V[ig+1, jd, kt] * ag*(1-ad)*(1-at) +
            V[ig, jd+1, kt] * (1-ag)*ad*(1-at) +
            V[ig, jd, kt+1] * (1-ag)*(1-ad)*at +
            V[ig+1, jd+1, kt] * ag*ad*(1-at) +
            V[ig+1, jd, kt+1] * ag*(1-ad)*at +
            V[ig, jd+1, kt+1] * (1-ag)*ad*at +
            V[ig+1, jd+1, kt+1] * ag*ad*at
        )
        return float(val)

    def solve_value_function(self) -> "GranasHJBController":
        """
        Backward sweep: compute V(x,t) for all states and times.
        Uses dynamic programming:
            V(x, T) = terminal_cost(x)
            V(x, t) = min_u [L(x,u)*dt + V(f(x,u), t+dt)]

        Returns self for chaining.
        """
        logger.info("=" * 60)
        logger.info(" GRANAS HJB — Solving Value Function")
        logger.info(f" Grid: {self.n_grain}×{self.n_defect}×{self.n_temp}")
        logger.info(f" Controls: {self.n_control} ramp rates")
        logger.info(f" Time steps: {self.n_time} ({self.total_time_s:.0f}s)")
        logger.info("=" * 60)

        # Initialize V at terminal time
        self.V = np.zeros((self.n_grain, self.n_defect, self.n_temp))
        self.policy = np.zeros((self.n_grain, self.n_defect, self.n_temp),
                               dtype=int)

        # Terminal condition
        for ig in range(self.n_grain):
            for jd in range(self.n_defect):
                self.V[ig, jd, :] = self._terminal_cost(
                    self.grain_grid[ig], self.defect_grid[jd]
                )

        # Backward sweep (value iteration in state space)
        # We iterate multiple sweeps to converge the value function
        n_sweeps = 5
        for sweep in range(n_sweeps):
            V_old = self.V.copy()

            for ig in range(self.n_grain):
                for jd in range(self.n_defect):
                    for kt in range(self.n_temp):
                        state = AnnealingState(
                            grain_size_nm=self.grain_grid[ig],
                            defect_density=self.defect_grid[jd],
                            film_temp_C=self.temp_grid[kt],
                        )

                        best_cost = np.inf
                        best_u = 0

                        for iu, ramp in enumerate(self.control_grid):
                            # Running cost
                            L = self._running_cost(ramp, state.film_temp_C)

                            # Next state
                            next_state = self.dynamics.step(
                                state, ramp, self.dt
                            )

                            # Future cost (interpolated)
                            V_next = self._interpolate_V(
                                next_state.grain_size_nm,
                                next_state.defect_density,
                                next_state.film_temp_C,
                            )

                            total = L * self.dt + V_next
                            if total < best_cost:
                                best_cost = total
                                best_u = iu

                        self.V[ig, jd, kt] = best_cost
                        self.policy[ig, jd, kt] = best_u

            # Check convergence
            delta = np.max(np.abs(self.V - V_old))
            logger.info(f" Sweep {sweep+1}/{n_sweeps} | max ΔV = {delta:.4f}")
            if delta < 0.01:
                logger.info(" Value function converged!")
                break

        logger.info(" HJB value function solved.")
        return self

    def optimal_policy(self, state: AnnealingState) -> float:
        """
        Extract optimal control u*(x) from the value function.

        Parameters
        ----------
        state : AnnealingState
            Current state

        Returns
        -------
        float : optimal ramp rate (°C/s)
        """
        if self.V is None:
            raise RuntimeError("Value function not solved. Call solve_value_function() first.")

        # Find best control by evaluating all candidates
        best_cost = np.inf
        best_ramp = 0.0

        for ramp in self.control_grid:
            L = self._running_cost(ramp, state.film_temp_C)
            next_state = self.dynamics.step(state, ramp, self.dt)
            V_next = self._interpolate_V(
                next_state.grain_size_nm,
                next_state.defect_density,
                next_state.film_temp_C,
            )
            total = L * self.dt + V_next
            if total < best_cost:
                best_cost = total
                best_ramp = ramp

        return best_ramp

    def simulate_trajectory(
        self,
        initial_state: Optional[AnnealingState] = None,
    ) -> HJBResult:
        """
        Forward simulation using the optimal policy.

        Parameters
        ----------
        initial_state : AnnealingState, optional
            Starting state. Default: room temp, small grains, high defects.

        Returns
        -------
        HJBResult : complete trajectory and metrics
        """
        if self.V is None:
            self.solve_value_function()

        if initial_state is None:
            initial_state = AnnealingState(
                grain_size_nm=50.0,
                defect_density=1.5,
                film_temp_C=25.0,
            )

        n_steps = int(self.total_time_s / self.dt)
        time_grid = np.linspace(0, self.total_time_s, n_steps + 1)
        grain_traj = np.zeros(n_steps + 1)
        defect_traj = np.zeros(n_steps + 1)
        temp_traj = np.zeros(n_steps + 1)
        control_traj = np.zeros(n_steps)

        state = initial_state
        grain_traj[0] = state.grain_size_nm
        defect_traj[0] = state.defect_density
        temp_traj[0] = state.film_temp_C

        total_cost = 0.0

        for i in range(n_steps):
            # Get optimal control
            ramp = self.optimal_policy(state)
            control_traj[i] = ramp

            # Running cost
            total_cost += self._running_cost(ramp, state.film_temp_C) * self.dt

            # Step dynamics
            state = self.dynamics.step(state, ramp, self.dt)
            grain_traj[i + 1] = state.grain_size_nm
            defect_traj[i + 1] = state.defect_density
            temp_traj[i + 1] = state.film_temp_C

        # Terminal cost
        total_cost += self._terminal_cost(state.grain_size_nm, state.defect_density)

        # Build optimal schedule (time, temp) pairs — sampled every 30s
        schedule = []
        for i in range(0, len(time_grid), max(1, int(30.0 / self.dt))):
            schedule.append((float(time_grid[i]), float(temp_traj[i])))
        if schedule[-1][0] < self.total_time_s:
            schedule.append((float(time_grid[-1]), float(temp_traj[-1])))

        # Estimate PCE boost: compare terminal grain/defects vs. static anneal
        # Static baseline: hold at 140°C for entire duration
        baseline_state = AnnealingState(50.0, 1.5, 25.0)
        for _ in range(n_steps):
            baseline_state = self.dynamics.step(baseline_state, 0.5, self.dt)

        # Simple PCE proxy: larger grains + lower defects = better
        opt_score = np.log1p(state.grain_size_nm / 100) * np.exp(-0.5 * state.defect_density)
        base_score = np.log1p(baseline_state.grain_size_nm / 100) * np.exp(-0.5 * baseline_state.defect_density)
        pce_boost = max(0.0, (opt_score / base_score - 1.0) * 25.8)  # Scaled by practical cap

        logger.info("-" * 60)
        logger.info(f" HJB Trajectory Complete")
        logger.info(f" Terminal grain:   {state.grain_size_nm:.1f} nm")
        logger.info(f" Terminal defects: {state.defect_density:.4f}")
        logger.info(f" PCE boost:        +{pce_boost:.2f}%")
        logger.info(f" Total cost:       {total_cost:.3f}")
        logger.info("-" * 60)

        # Value function slice for visualization (at optimal temp)
        opt_temp_idx = np.argmin(np.abs(self.temp_grid - np.mean(temp_traj)))
        V_slice = self.V[:, :, opt_temp_idx]

        return HJBResult(
            time_grid=time_grid,
            grain_trajectory=grain_traj,
            defect_trajectory=defect_traj,
            temp_trajectory=temp_traj,
            control_trajectory=control_traj,
            value_function=V_slice,
            optimal_schedule=schedule,
            terminal_grain_nm=state.grain_size_nm,
            terminal_defects=state.defect_density,
            pce_boost_pct=pce_boost,
            total_cost=total_cost,
        )

    def get_optimal_schedule(
        self,
        initial_state: Optional[AnnealingState] = None,
    ) -> List[Tuple[float, float]]:
        """
        Convenience method: return just the (time, temperature) schedule.
        """
        result = self.simulate_trajectory(initial_state)
        return result.optimal_schedule


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    controller = GranasHJBController(
        total_time_s=1200.0,
        dt=2.0,
        n_grain=25,
        n_defect=20,
        n_temp=15,
        n_control=9,
    )

    result = controller.simulate_trajectory()

    print(f"\n{'='*55}")
    print(f" 🧠 HJB OPTIMAL ANNEALING SCHEDULE")
    print(f"{'─'*55}")
    print(f" Duration:         {controller.total_time_s:.0f}s ({controller.total_time_s/60:.0f} min)")
    print(f" Terminal Grain:   {result.terminal_grain_nm:.1f} nm")
    print(f" Terminal Defects: {result.terminal_defects:.4f}")
    print(f" PCE Boost:        +{result.pce_boost_pct:.2f}%")
    print(f" Total Cost:       {result.total_cost:.3f}")
    print(f"{'─'*55}")
    print(f" OPTIMAL SCHEDULE (time → temperature):")
    for t, T in result.optimal_schedule[:15]:
        print(f"   t={t:7.1f}s ({t/60:5.1f} min) → {T:.1f} °C")
    if len(result.optimal_schedule) > 15:
        print(f"   ... ({len(result.optimal_schedule)} total points)")
    print(f"{'='*55}")
