"""
PRIME-Kernel — Negentropic HJB Solver
=======================================
Hamilton-Jacobi-Bellman solver where V(x) is the negentropic potential.

The stationary HJB equation:
    ρV(x) = min_u { Σ̇(x,u) + ½uᵀRu + ∇V·(f+gu) + ½tr(σσᵀ∇²V) }

Key innovations vs base HJBSolver:
1. Running cost = entropy_rate(x,u) — derived from physics, not heuristic
2. Can use closed-form u*(x) (bypasses grid search over controls)
3. Tracks entropy decomposition (reversible vs irreversible) per trajectory step
4. V(x) has physical meaning: negentropic potential (minimum at synchronization)
5. Landauer bound verification: checks if total Σ ≥ Σ_Landauer

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from hjb_solver_fortified import (
    HJBDynamics,
    HJBSolver,
    RobustHJBSolver,
    HJBResult,
    ISOMarket,
    iso_params,
    OrnsteinUhlenbeckCalibrator,
    ContractValuator,
)
from entropy_production import (
    EntropyProductionRate,
    EntropyDecomposition,
    EntropyTrajectory,
    build_entropy_engine_cenace,
)
from negentropic_control import (
    NegentropicOptimalControl,
    ControlDecomposition,
    build_negentropic_control_cenace,
)
from negentropic_dynamics import (
    NegentropicGridDynamics,
    NegentropicBESSDynamics,
    NegentropicRegimeDynamics,
    NegentropicKuramotoDynamics,
    build_negentropic_cenace,
)

logger = logging.getLogger("prime_kernel.negentropic_solver")


# ─────────────────────────────────────────────────────────────────────────────
# Extended Result with Entropy Tracking
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class NegentropicHJBResult(HJBResult):
    """HJB result extended with entropy production tracking."""
    entropy_trajectory: Optional[EntropyTrajectory] = None
    control_decompositions: Optional[List[ControlDecomposition]] = None
    landauer_bound: float = 0.0
    total_entropy_produced: float = 0.0
    landauer_efficiency: float = 0.0   # Σ_Landauer / Σ_total ∈ [0,1]
    negentropic_well_depth: float = 0.0   # V(x_sync) — depth of the potential well


# ─────────────────────────────────────────────────────────────────────────────
# Negentropic HJB Solver
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicHJBSolver(HJBSolver):
    """
    HJB solver where V(x) is the negentropic potential.

    This solver can operate in two modes:
    1. GRID SEARCH (default): Same as base solver but with entropy-based running cost.
       Use when dynamics are complex and u* formula may not apply cleanly.
    2. CLOSED-FORM: Uses u*(x) = -R⁻¹ gᵀ [∇V + (1/T)D⁻¹f_irrev] to bypass
       control grid search. Faster but requires quadratic structure in u.

    The solver automatically uses negentropic dynamics (NegentropicCostMixin).
    """

    def __init__(
        self,
        dynamics: HJBDynamics,
        entropy_engine: Optional[EntropyProductionRate] = None,
        controller: Optional[NegentropicOptimalControl] = None,
        use_closed_form_control: bool = False,
        discount_rate: float = 0.0,
        **kwargs,
    ):
        """
        Parameters
        ----------
        dynamics : HJBDynamics
            Should be a NegentropicCostMixin subclass for entropy-based cost.
        entropy_engine : EntropyProductionRate
            If None, builds one from dynamics attributes.
        controller : NegentropicOptimalControl
            For closed-form u*. If None and use_closed_form=True, builds one.
        use_closed_form_control : bool
            If True, uses u* formula instead of grid search over controls.
        discount_rate : float
            ρ in the stationary HJB: ρV = min{...}. Default 0 (infinite horizon, no discount).
        """
        super().__init__(dynamics, stochastic=True, **kwargs)
        self.discount_rate = discount_rate
        self.use_closed_form = use_closed_form_control

        # Build or use provided entropy engine
        if entropy_engine is not None:
            self.entropy_engine = entropy_engine
        elif hasattr(dynamics, '_entropy_engine'):
            self.entropy_engine = dynamics._entropy_engine
        else:
            # Fallback: build from CENACE defaults
            self.entropy_engine = build_entropy_engine_cenace()

        # Build or use provided controller
        if controller is not None:
            self.controller = controller
        elif use_closed_form_control:
            self.controller = build_negentropic_control_cenace(self.entropy_engine)
        else:
            self.controller = None

        # Entropy tracking during simulation
        self._entropy_history: List[float] = []
        self._control_decomps: List[ControlDecomposition] = []

    def solve(self) -> "NegentropicHJBSolver":
        """
        Solve the negentropic HJB via value iteration.

        When use_closed_form=True, the inner loop replaces the control grid
        search with the analytical u* formula, which is O(1) per grid point
        instead of O(n_controls).
        """
        n_dims = self.dynamics.state_dims()
        grid_shapes = [len(g) for g in self.state_grids]

        logger.info("=" * 64)
        logger.info(" PRIME-Kernel Negentropic HJB Solver")
        logger.info(" Grid: %s   Controls: %d   Mode: %s",
                     "×".join(str(s) for s in grid_shapes),
                     self.n_controls,
                     "CLOSED-FORM u*" if self.use_closed_form else "GRID SEARCH")
        logger.info(" T_eff: %.6e   ρ: %.4f", self.entropy_engine.T, self.discount_rate)
        logger.info("=" * 64)

        t0 = time.perf_counter()

        # Terminal condition
        for idx in np.ndindex(*grid_shapes):
            state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
            self.V[idx] = self.dynamics.terminal_cost(state)

        delta_history = []
        converged = False

        for sweep in range(self.max_sweeps):
            self._build_interpolator()
            V_old = self.V.copy()

            for idx in np.ndindex(*grid_shapes):
                state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])

                # Itô correction (stochastic term)
                ito = self._ito_correction(state, idx)

                if self.use_closed_form and self.controller is not None:
                    # ── CLOSED-FORM MODE ──
                    # Estimate ∇V via finite differences
                    V_grad = self.controller.estimate_V_gradient(
                        state, self._interpolate_V
                    )

                    # Get f_irrev at u=0
                    dt_small = 1e-4
                    next_0 = self.dynamics.step(state, 0.0, dt_small)
                    drift_0 = (next_0 - state) / dt_small
                    f_rev = self.entropy_engine.reversible_drift_ou(
                        state,
                        getattr(self.dynamics, '_ou_mu', np.zeros(n_dims)),
                        getattr(self.dynamics, '_ou_kappa', np.ones(n_dims) * 0.42),
                    )
                    f_irrev = drift_0 - f_rev

                    # Compute u*
                    u_star = self.controller.compute_u_star(state, V_grad, f_irrev)

                    # Evaluate cost at u*
                    L = self.dynamics.running_cost(state, u_star, t=0.0)
                    next_state = self.dynamics.step(state, u_star, self.dt)
                    V_next = self._interpolate_V(next_state)

                    # Discount
                    if self.discount_rate > 0:
                        discount = 1.0 / (1.0 + self.discount_rate * self.dt)
                    else:
                        discount = 1.0

                    best_cost = (L + ito) * self.dt + discount * V_next

                else:
                    # ── GRID SEARCH MODE ──
                    best_cost = np.inf
                    best_iu = 0

                    for iu, u in enumerate(self.control_grid):
                        L = self.dynamics.running_cost(state, u, t=0.0)
                        next_state = self.dynamics.step(state, u, self.dt)
                        V_next = self._interpolate_V(next_state)

                        if self.discount_rate > 0:
                            discount = 1.0 / (1.0 + self.discount_rate * self.dt)
                        else:
                            discount = 1.0

                        total = (L + ito) * self.dt + discount * V_next

                        if total < best_cost:
                            best_cost = total
                            best_iu = iu

                    self.policy[idx] = best_iu

                self.V[idx] = best_cost

            delta = float(np.max(np.abs(self.V - V_old)))
            delta_history.append(delta)
            logger.info(" Sweep %d/%d | max ΔV = %.6f", sweep + 1, self.max_sweeps, delta)

            if delta < self.tol:
                converged = True
                logger.info(" ✅ Negentropic value function converged.")
                break

        self._solved = True
        self._converged = converged
        self._n_sweeps = sweep + 1
        self._solve_time = time.perf_counter() - t0
        self._delta_history = delta_history
        self._build_interpolator()

        # Report negentropic well depth
        sync_state = np.zeros(n_dims)
        well_depth = self._interpolate_V(sync_state)
        logger.info(" Negentropic well depth V(x_sync) = %.4f", well_depth)

        return self

    def simulate_with_entropy(
        self,
        initial_state: np.ndarray,
    ) -> NegentropicHJBResult:
        """
        Forward simulation with full entropy production tracking.

        Returns the standard HJB trajectory PLUS:
        - Entropy production rate Σ̇(t) at each step
        - Cumulative entropy ∫Σ̇ dt
        - Control decomposition (anticipatory vs thermodynamic)
        - Landauer bound and efficiency
        """
        if not self._solved:
            self.solve()

        n_steps = int(self.total_time / self.dt)
        n_dims = self.dynamics.state_dims()
        t_grid = np.linspace(0, self.total_time, n_steps + 1)
        x_traj = np.zeros((n_steps + 1, n_dims))
        u_traj = np.zeros(n_steps)

        # Entropy tracking arrays
        sigma_dots = np.zeros(n_steps)
        cumulative_entropy = np.zeros(n_steps)
        control_costs = np.zeros(n_steps)
        negentropic_costs = np.zeros(n_steps)
        irrev_norms = np.zeros(n_steps)
        control_decomps = []

        state = initial_state.copy()
        x_traj[0] = state
        total_cost = 0.0
        total_entropy = 0.0

        for i in range(n_steps):
            t = t_grid[i]
            u = self.optimal_control(state, t)
            u_traj[i] = u

            # Compute entropy decomposition
            dt_small = 1e-4
            next_probe = self.dynamics.step(state, u, dt_small)
            total_drift = (next_probe - state) / dt_small

            ou_mu = getattr(self.dynamics, '_ou_mu', np.zeros(n_dims))
            ou_kappa = getattr(self.dynamics, '_ou_kappa', np.ones(n_dims) * 0.42)

            decomp = self.entropy_engine.decompose(
                state, u, total_drift, ou_mu, ou_kappa,
                control_penalty_R=getattr(self.dynamics, '_control_R', 0.1),
            )

            sigma_dots[i] = decomp.sigma_dot_total
            control_costs[i] = decomp.control_cost
            negentropic_costs[i] = decomp.negentropic_cost
            irrev_norms[i] = float(np.linalg.norm(decomp.irreversible_drift))

            total_entropy += decomp.sigma_dot_total * self.dt
            cumulative_entropy[i] = total_entropy

            # Control decomposition (if controller available)
            if self.controller is not None:
                V_grad = self.controller.estimate_V_gradient(
                    state, self._interpolate_V,
                )
                f_irrev = decomp.irreversible_drift
                ctrl_decomp = self.controller.decompose_control(state, V_grad, f_irrev)
                control_decomps.append(ctrl_decomp)

            # Advance state
            total_cost += self.dynamics.running_cost(state, u, t) * self.dt
            state = self.dynamics.step(state, u, self.dt)
            x_traj[i + 1] = state

        total_cost += self.dynamics.terminal_cost(state)

        # Landauer bound
        target_state = np.zeros(n_dims)  # synchronization
        landauer = self.entropy_engine.landauer_bound(
            initial_state, target_state, ou_mu, ou_kappa,
        )
        landauer_eff = landauer / max(total_entropy, 1e-12)

        # Well depth
        well_depth = self._interpolate_V(target_state)

        entropy_traj = EntropyTrajectory(
            times=t_grid[:-1],
            sigma_dot=sigma_dots,
            cumulative_entropy=cumulative_entropy,
            control_costs=control_costs,
            negentropic_costs=negentropic_costs,
            irreversible_norms=irrev_norms,
            landauer_bound=landauer,
        )

        logger.info(" Simulation complete:")
        logger.info("   Total cost: %.4f", total_cost)
        logger.info("   Total entropy produced: %.6f", total_entropy)
        logger.info("   Landauer bound: %.6f", landauer)
        logger.info("   Landauer efficiency: %.2f%%", landauer_eff * 100)

        return NegentropicHJBResult(
            time_grid=t_grid,
            state_trajectory=x_traj,
            control_trajectory=u_traj,
            value_function=self.V.copy(),
            total_cost=total_cost,
            n_sweeps=self._n_sweeps,
            converged=self._converged,
            solve_time_s=self._solve_time,
            metadata={"delta_history": self._delta_history},
            entropy_trajectory=entropy_traj,
            control_decompositions=control_decomps if control_decomps else None,
            landauer_bound=landauer,
            total_entropy_produced=total_entropy,
            landauer_efficiency=landauer_eff,
            negentropic_well_depth=well_depth,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Robust Negentropic Solver (ambiguity + entropy)
# ─────────────────────────────────────────────────────────────────────────────
class RobustNegentropicHJBSolver(NegentropicHJBSolver):
    """
    Robust negentropic solver: minimax HJB with entropy cost under ambiguity.

    Combines the Knightian uncertainty (thesis §3) with the thermodynamic
    entropy cost: the adversary inflates the entropy production rate,
    the controller minimizes it.

    V_rob_neg(x) ≥ V_neg(x) for all ε > 0.
    """

    def __init__(self, dynamics: HJBDynamics, epsilon: float = 0.00346, **kwargs):
        super().__init__(dynamics, **kwargs)
        self.epsilon = epsilon

    def _robust_entropy_penalty(self, state: np.ndarray) -> float:
        """
        Robust penalty: ε · ||g(x)||² (Hansen-Sargent)
        added to the entropy production rate.
        """
        g = self.dynamics.diffusion(state)
        return self.epsilon * float(np.dot(g, g))

    def solve(self) -> "RobustNegentropicHJBSolver":
        """Override solve to add robust penalty to running cost."""
        n_dims = self.dynamics.state_dims()
        grid_shapes = [len(g) for g in self.state_grids]

        logger.info("=" * 64)
        logger.info(" PRIME-Kernel Robust Negentropic HJB Solver — ε=%.5f", self.epsilon)
        logger.info("=" * 64)

        t0 = time.perf_counter()

        for idx in np.ndindex(*grid_shapes):
            state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
            self.V[idx] = self.dynamics.terminal_cost(state)

        delta_history = []
        converged = False

        for sweep in range(self.max_sweeps):
            self._build_interpolator()
            V_old = self.V.copy()

            for idx in np.ndindex(*grid_shapes):
                state = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
                rob_pen = self._robust_entropy_penalty(state)
                ito = self._ito_correction(state, idx)
                best_cost = np.inf
                best_iu = 0

                for iu, u in enumerate(self.control_grid):
                    L = self.dynamics.running_cost(state, u, t=0.0) + rob_pen
                    next_state = self.dynamics.step(state, u, self.dt)
                    V_next = self._interpolate_V(next_state)
                    total = (L + ito) * self.dt + V_next

                    if total < best_cost:
                        best_cost = total
                        best_iu = iu

                self.V[idx] = best_cost
                self.policy[idx] = best_iu

            delta = float(np.max(np.abs(self.V - V_old)))
            delta_history.append(delta)
            logger.info(" Sweep %d/%d | max ΔV = %.6f (ε=%.5f)",
                         sweep + 1, self.max_sweeps, delta, self.epsilon)

            if delta < self.tol:
                converged = True
                logger.info(" ✅ Robust negentropic value function converged.")
                break

        self._solved = True
        self._converged = converged
        self._n_sweeps = sweep + 1
        self._solve_time = time.perf_counter() - t0
        self._delta_history = delta_history
        self._build_interpolator()
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Factory: One-Call Pipeline
# ─────────────────────────────────────────────────────────────────────────────
def build_negentropic_cenace_system(
    dynamics_type: str = "grid",
    control_penalty_R: float = 0.1,
    epsilon: float = 0.00346,
    use_closed_form: bool = False,
    grid_points: Optional[List[int]] = None,
    calibrator: Optional[OrnsteinUhlenbeckCalibrator] = None,
) -> Tuple[NegentropicHJBSolver, RobustNegentropicHJBSolver]:
    """
    One-call factory for the full negentropic CENACE pipeline.

    Returns (neg_solver, robust_neg_solver) ready for .solve() + .simulate_with_entropy().

    Parameters
    ----------
    dynamics_type : str
        One of: "grid", "regime", "bess", "kuramoto"
    control_penalty_R : float
        The Maxwell demon budget.
    epsilon : float
        Knightian ambiguity radius.
    """
    dynamics = build_negentropic_cenace(
        dynamics_type=dynamics_type,
        control_penalty_R=control_penalty_R,
        calibrator=calibrator,
    )

    # Default grid points per dynamics type
    if grid_points is None:
        grid_map = {
            "grid": [20, 20],
            "regime": [20, 15, 3],
            "bess": [12, 8, 8, 6, 5],
            "kuramoto": [10] * dynamics.state_dims(),
            "multiarea": [8] * dynamics.state_dims(),
        }
        gp = grid_map.get(dynamics_type, [20] * dynamics.state_dims())
    else:
        gp = grid_points

    neg_solver = NegentropicHJBSolver(
        dynamics,
        use_closed_form_control=use_closed_form,
        grid_points=gp,
    )

    robust_solver = RobustNegentropicHJBSolver(
        dynamics,
        epsilon=epsilon,
        grid_points=gp,
    )

    return neg_solver, robust_solver


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
    )

    print("\n=== PRIME-Kernel Negentropic HJB Solver ===\n")

    # 1. Build negentropic CENACE system
    neg_solver, robust_solver = build_negentropic_cenace_system(
        dynamics_type="grid",
        control_penalty_R=0.1,
    )

    # 2. Solve
    neg_solver.solve()

    # 3. Simulate with entropy tracking
    x0 = np.array([-0.015, 0.0])
    result = neg_solver.simulate_with_entropy(x0)

    print(f"\n  Total cost: {result.total_cost:.4f}")
    print(f"  Total Σ produced: {result.total_entropy_produced:.6f}")
    print(f"  Landauer bound: {result.landauer_bound:.6f}")
    print(f"  Landauer efficiency: {result.landauer_efficiency:.2%}")
    print(f"  Well depth V(sync): {result.negentropic_well_depth:.4f}")
    print(f"  Max Σ̇ rate: {result.entropy_trajectory.sigma_dot.max():.6f}")

    # 4. Robust solve
    print("\n--- Robust Negentropic ---")
    robust_solver.solve()
    x0 = np.array([-0.015, 0.0])
    res_rob = robust_solver.simulate_with_entropy(x0)
    print(f"  Robust total cost: {res_rob.total_cost:.4f}")
    print(f"  Robust Σ produced: {res_rob.total_entropy_produced:.6f}")
