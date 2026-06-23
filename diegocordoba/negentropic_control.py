"""
PRIME-Kernel — Closed-Form Negentropic Optimal Control
=======================================================
The "Maxwell Demon with a Budget" — u*(x).

For a negentropic HJB where the running cost is:
    L(x,u) = Σ̇(x,u) + ½ uᵀ R u

and Σ̇ is quadratic in u (Esposito-Seifert form), the optimal control
has a closed-form solution:

    u*(x) = -R⁻¹ · g(x)ᵀ · [∇V(x) + (1/T)·D⁻¹·f_irrev(x)]

Two components:
    1. ∇V(x) — ANTICIPATORY: pushes toward the negentropic potential well
       (the synchronized state at 60 Hz is the minimum of V)
    2. (1/T)·D⁻¹·f_irrev — THERMODYNAMIC: compensates local entropy production
       (this term does NOT exist in standard LQR — it's the signature of the 2nd Law)

Together: Granas ANTICIPATES future desynchronization cost AND
COMPENSATES current entropy production. A Maxwell demon with infinite
horizon and finite budget R.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from entropy_production import EntropyProductionRate

logger = logging.getLogger("prime_kernel.negentropic_control")


# ─────────────────────────────────────────────────────────────────────────────
# Control Decomposition
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ControlDecomposition:
    """Decomposes u* into its anticipatory and thermodynamic components."""
    u_star: float                    # Total optimal control
    u_anticipatory: float            # -R⁻¹ gᵀ ∇V component
    u_thermodynamic: float           # -R⁻¹ gᵀ (1/T D⁻¹ f_irrev) component
    anticipatory_ratio: float        # |u_antic| / (|u_antic| + |u_thermo|)
    thermodynamic_ratio: float       # |u_thermo| / (|u_antic| + |u_thermo|)
    maxwell_demon_budget: float      # ½ R u*² — what the demon "spends"


# ─────────────────────────────────────────────────────────────────────────────
# Negentropic Optimal Control
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicOptimalControl:
    """
    Closed-form optimal control for the negentropic HJB.

    u*(x) = -R⁻¹ · g(x)ᵀ · [∇V(x) + (1/T)·D⁻¹·f_irrev(x)]

    This is exact when Σ̇ is quadratic in u and there are no control constraints.
    When control is bounded, the formula gives the unconstrained optimum which
    is then projected onto [u_min, u_max].

    Parameters
    ----------
    entropy_engine : EntropyProductionRate
        The thermodynamic engine (provides T, D, D⁻¹).
    control_penalty_R : float
        Scalar weight on control effort. Larger R = cheaper to be lazy = weaker demon.
    control_bounds : tuple(float, float)
        Physical limits [u_min, u_max] for the control.
    diffusion_coupling : np.ndarray
        g(x) — how control enters the dynamics. For scalar control and
        additive injection: g = [0, 1/(2H)] (enters the swing equation).
    """

    def __init__(
        self,
        entropy_engine: EntropyProductionRate,
        control_penalty_R: float = 0.1,
        control_bounds: Tuple[float, float] = (-10.0, 10.0),
        diffusion_coupling: Optional[np.ndarray] = None,
    ):
        self.engine = entropy_engine
        self.R = control_penalty_R
        self.R_inv = 1.0 / max(self.R, 1e-12)
        self.u_min, self.u_max = control_bounds
        self.n_dims = entropy_engine.n_dims

        # Default g(x): scalar control entering only 2nd state dimension
        # (swing equation: dΔf/dt = ... + u/(2H))
        if diffusion_coupling is None:
            self.g = np.zeros(self.n_dims)
            if self.n_dims >= 2:
                self.g[1] = 1.0  # Control enters ROCOF/P_inj dimension
            else:
                self.g[0] = 1.0
        else:
            self.g = np.asarray(diffusion_coupling, dtype=np.float64)

    def compute_u_star(
        self,
        state: np.ndarray,
        V_grad: np.ndarray,
        f_irreversible: np.ndarray,
        clip: bool = True,
    ) -> float:
        """
        The jewel: closed-form negentropic feedback.

        u*(x) = -R⁻¹ · gᵀ · [∇V(x) + (1/T)·D⁻¹·f_irrev(x)]

        Parameters
        ----------
        state : np.ndarray
            Current state x (used for state-dependent g if needed).
        V_grad : np.ndarray
            ∇V(x) — gradient of the value function (from finite differences).
        f_irreversible : np.ndarray
            f_irrev(x) = f_total(x,u=0) - f_rev(x) at zero control.
        clip : bool
            If True, project onto [u_min, u_max].

        Returns
        -------
        float
            Optimal control u*.
        """
        # Thermodynamic term: (1/T) · D⁻¹ · f_irrev
        thermo_term = (1.0 / self.engine.T) * (self.engine.D_inv @ f_irreversible)

        # Combined gradient
        combined = V_grad + thermo_term

        # u* = -R⁻¹ · gᵀ · combined
        u_star = -self.R_inv * float(self.g @ combined)

        if clip:
            u_star = float(np.clip(u_star, self.u_min, self.u_max))

        return u_star

    def decompose_control(
        self,
        state: np.ndarray,
        V_grad: np.ndarray,
        f_irreversible: np.ndarray,
    ) -> ControlDecomposition:
        """
        Decompose u* into anticipatory vs thermodynamic components.

        This decomposition reveals HOW Granas stabilizes the grid:
        - Anticipatory: "I push toward 60 Hz because future cost is high"
        - Thermodynamic: "I compensate the entropy being produced right now"

        Parameters
        ----------
        state, V_grad, f_irreversible : same as compute_u_star()
        """
        # Anticipatory component: -R⁻¹ gᵀ ∇V
        u_antic = -self.R_inv * float(self.g @ V_grad)

        # Thermodynamic component: -R⁻¹ gᵀ (1/T D⁻¹ f_irrev)
        thermo_term = (1.0 / self.engine.T) * (self.engine.D_inv @ f_irreversible)
        u_thermo = -self.R_inv * float(self.g @ thermo_term)

        # Total
        u_total = u_antic + u_thermo
        u_clipped = float(np.clip(u_total, self.u_min, self.u_max))

        # Ratios
        abs_sum = abs(u_antic) + abs(u_thermo)
        if abs_sum > 1e-12:
            antic_ratio = abs(u_antic) / abs_sum
            thermo_ratio = abs(u_thermo) / abs_sum
        else:
            antic_ratio = 0.5
            thermo_ratio = 0.5

        demon_budget = 0.5 * self.R * u_clipped ** 2

        return ControlDecomposition(
            u_star=u_clipped,
            u_anticipatory=u_antic,
            u_thermodynamic=u_thermo,
            anticipatory_ratio=antic_ratio,
            thermodynamic_ratio=thermo_ratio,
            maxwell_demon_budget=demon_budget,
        )

    def estimate_V_gradient(
        self,
        state: np.ndarray,
        V_interpolator,
        h: float = 0.01,
    ) -> np.ndarray:
        """
        Estimate ∇V(x) via central finite differences.

        Parameters
        ----------
        state : np.ndarray
            Current state.
        V_interpolator : callable
            V(x) → float (e.g., solver._interpolate_V).
        h : float
            Finite difference step size.

        Returns
        -------
        np.ndarray
            Approximate gradient ∇V(x).
        """
        grad = np.zeros(self.n_dims)
        for d in range(self.n_dims):
            state_plus = state.copy()
            state_minus = state.copy()
            state_plus[d] += h
            state_minus[d] -= h
            grad[d] = (V_interpolator(state_plus) - V_interpolator(state_minus)) / (2.0 * h)
        return grad


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────
def build_negentropic_control_cenace(
    entropy_engine: EntropyProductionRate,
    inertia_H: float = 4.8,
    control_penalty_R: float = 0.1,
    control_bounds: Tuple[float, float] = (-10.0, 10.0),
) -> NegentropicOptimalControl:
    """
    Factory for CENACE-calibrated negentropic controller.

    The diffusion coupling g(x) for the swing equation is:
        g = [0, 1/(2H)]  — control enters as dΔf/dt = ... + u/(2H)
    """
    n_dims = entropy_engine.n_dims
    g = np.zeros(n_dims)
    if n_dims >= 2:
        g[1] = 1.0 / (2.0 * inertia_H)
    else:
        g[0] = 1.0 / (2.0 * inertia_H)

    controller = NegentropicOptimalControl(
        entropy_engine=entropy_engine,
        control_penalty_R=control_penalty_R,
        control_bounds=control_bounds,
        diffusion_coupling=g,
    )
    logger.info(
        "CENACE negentropic controller: R=%.4f, H=%.1f, bounds=%s",
        control_penalty_R, inertia_H, control_bounds,
    )
    return controller
