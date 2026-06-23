"""
PRIME-Kernel — Entropy Production Engine  (Esposito-Seifert)
=============================================================
Implements stochastic thermodynamics for diffusion processes.

The entropy production rate Σ̇(x,u) for a controlled SDE
    dx = [f(x) + g(x)·u] dt + σ dW
is given by (Seifert 2005, Esposito 2012):

    Σ̇ = (1/T) · ||f_total - f_rev||²_{D⁻¹}

where f_rev = D · ∇ln(p_ss) is the reversible part of the drift,
D = σσᵀ/2 is the diffusion tensor, and T is the effective temperature.

For an OU process with parameters (κ, μ, σ), the effective temperature
is T_eff = σ² / (2κ), making p_ss exactly Boltzmann-distributed.

This module is the thermodynamic foundation for the negentropic HJB solver.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict

import numpy as np

logger = logging.getLogger("prime_kernel.entropy")


# ─────────────────────────────────────────────────────────────────────────────
# Core Data Structures
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class EntropyDecomposition:
    """Decomposition of entropy production at a single state-control pair."""
    sigma_dot_total: float           # Total Σ̇(x, u) — always ≥ 0
    irreversible_drift: np.ndarray   # f_irrev = f_total - f_rev
    reversible_drift: np.ndarray     # f_rev = D · ∇ln(p_ss)
    total_drift: np.ndarray          # f(x) + g(x)·u
    control_cost: float              # ½ uᵀ R u
    negentropic_cost: float          # Σ̇ + ½ uᵀ R u (the HJB running cost)


@dataclass
class EntropyTrajectory:
    """Entropy production tracked along a simulation trajectory."""
    times: np.ndarray                          # (n_steps,)
    sigma_dot: np.ndarray                      # (n_steps,) — Σ̇ per step
    cumulative_entropy: np.ndarray             # (n_steps,) — ∫Σ̇ dt
    control_costs: np.ndarray                  # (n_steps,) — ½uᵀRu per step
    negentropic_costs: np.ndarray              # (n_steps,) — total running cost
    irreversible_norms: np.ndarray             # (n_steps,) — ||f_irrev||
    landauer_bound: float = 0.0                # Theoretical minimum entropy


# ─────────────────────────────────────────────────────────────────────────────
# Entropy Production Rate Engine
# ─────────────────────────────────────────────────────────────────────────────
class EntropyProductionRate:
    """
    Esposito-Seifert entropy production rate for controlled diffusion processes.

    For a controlled SDE:
        dx = [f(x) + g(x)·u] dt + σ dW

    The entropy production rate is:
        Σ̇(x,u) = (1/T) · ||f(x) + g(x)u - D·∇ln(p_ss)||²_{D⁻¹}

    where:
        D = ½ σσᵀ                   (diffusion tensor)
        T = σ²/(2κ)                 (effective temperature for OU)
        f_rev = D · ∇ln(p_ss)       (reversible drift component)

    The Second Law guarantees Σ̇ ≥ 0 always.

    Parameters
    ----------
    effective_temperature : float
        T_eff = σ²/(2κ) for OU processes. Sets the energy scale.
    diffusion_vector : np.ndarray
        The diagonal diffusion coefficients σ_i (from dynamics.diffusion()).
        We construct D = diag(σ_i²/2) from these.
    """

    def __init__(
        self,
        effective_temperature: float,
        diffusion_vector: np.ndarray,
        regularization: float = 1e-12,
    ):
        if effective_temperature <= 0:
            raise ValueError(f"Temperature must be positive, got {effective_temperature}")

        self.T = effective_temperature
        self.sigma_vec = np.asarray(diffusion_vector, dtype=np.float64)
        self.n_dims = len(self.sigma_vec)
        self.reg = regularization

        # D = diag(σᵢ²/2) — the diffusion tensor
        sigma_sq = self.sigma_vec ** 2
        self.D_diag = sigma_sq / 2.0 + self.reg  # regularized diagonal
        self.D = np.diag(self.D_diag)

        # D⁻¹ for the weighted norm
        self.D_inv_diag = 1.0 / self.D_diag
        self.D_inv = np.diag(self.D_inv_diag)

        logger.debug(
            "EntropyEngine initialized: T_eff=%.6f, dims=%d, D_diag=%s",
            self.T, self.n_dims, self.D_diag,
        )

    @classmethod
    def from_ou_params(
        cls,
        kappa: float,
        sigma: float,
        n_dims: int,
        sigma_vector: Optional[np.ndarray] = None,
    ) -> "EntropyProductionRate":
        """
        Construct from Ornstein-Uhlenbeck parameters.

        T_eff = σ² / (2κ)  — the stationary variance of the OU process,
        which makes p_ss exactly a Boltzmann distribution with that temperature.

        Parameters
        ----------
        kappa : float
            Mean-reversion speed (s⁻¹).
        sigma : float
            Diffusion intensity (Hz/√s for frequency dynamics).
        n_dims : int
            State-space dimensionality.
        sigma_vector : optional np.ndarray
            Full diffusion vector. If None, uses [sigma, 0, 0, ...].
        """
        T_eff = (sigma ** 2) / (2.0 * kappa)
        if sigma_vector is None:
            sigma_vector = np.zeros(n_dims)
            sigma_vector[0] = sigma
        return cls(effective_temperature=T_eff, diffusion_vector=sigma_vector)

    # ── Reversible / Irreversible Drift Decomposition ─────────────────────

    def reversible_drift_ou(
        self,
        state: np.ndarray,
        mu: np.ndarray,
        kappa_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Reversible drift for OU-type processes.

        For multivariate OU: dX = K(μ - X)dt + σ dW
        The stationary distribution is p_ss ~ N(μ, Σ_∞)
        where Σ_∞ solves the Lyapunov equation: K·Σ_∞ + Σ_∞·Kᵀ = σσᵀ

        ∇ln(p_ss) = -Σ_∞⁻¹ · (x - μ)
        f_rev = D · ∇ln(p_ss) = -D · Σ_∞⁻¹ · (x - μ)

        For diagonal systems: Σ_∞,ii = σᵢ²/(2κᵢ), so
        ∇ln(p_ss)_i = -2κᵢ/σᵢ² · (xᵢ - μᵢ) = -(1/T_i)·(xᵢ-μᵢ)

        Parameters
        ----------
        state : np.ndarray
            Current state x.
        mu : np.ndarray
            Long-run mean of the OU process.
        kappa_matrix : np.ndarray
            Mean-reversion matrix K (can be diagonal array or full matrix).
        """
        deviation = state - mu

        # Handle diagonal vs full K
        if kappa_matrix.ndim == 1:
            # Diagonal: Σ_∞,ii = σᵢ²/(2κᵢ)
            kappa_diag = kappa_matrix
            sigma_inf_inv_diag = np.where(
                self.sigma_vec > 0,
                2.0 * kappa_diag / (self.sigma_vec ** 2 + self.reg),
                0.0,
            )
            grad_log_pss = -sigma_inf_inv_diag * deviation
        else:
            # Full matrix: solve Lyapunov for Σ_∞
            # K·Σ + Σ·Kᵀ = σσᵀ  →  use scipy if needed
            # For now, use diagonal approximation
            kappa_diag = np.diag(kappa_matrix)
            sigma_inf_inv_diag = np.where(
                self.sigma_vec > 0,
                2.0 * kappa_diag / (self.sigma_vec ** 2 + self.reg),
                0.0,
            )
            grad_log_pss = -sigma_inf_inv_diag * deviation

        # f_rev = D · ∇ln(p_ss)
        f_rev = self.D_diag * grad_log_pss
        return f_rev

    def irreversible_drift(
        self,
        total_drift: np.ndarray,
        reversible_drift: np.ndarray,
    ) -> np.ndarray:
        """
        f_irrev = f_total - f_rev

        The irreversible component of the drift is what generates entropy.
        At thermodynamic equilibrium, f_irrev = 0 and Σ̇ = 0.
        """
        return total_drift - reversible_drift

    # ── Entropy Production Rate ───────────────────────────────────────────

    def sigma_dot(
        self,
        total_drift: np.ndarray,
        reversible_drift: np.ndarray,
    ) -> float:
        """
        Compute the entropy production rate:
            Σ̇ = (1/T) · ||f_irrev||²_{D⁻¹}
              = (1/T) · f_irrevᵀ · D⁻¹ · f_irrev

        This is ALWAYS ≥ 0 (Second Law of Thermodynamics).

        Parameters
        ----------
        total_drift : np.ndarray
            f(x) + g(x)·u — the full drift including control.
        reversible_drift : np.ndarray
            D · ∇ln(p_ss) — the reversible (equilibrium) drift.

        Returns
        -------
        float
            Σ̇ ≥ 0
        """
        f_irrev = self.irreversible_drift(total_drift, reversible_drift)
        # Weighted norm: ||v||²_{D⁻¹} = vᵀ D⁻¹ v
        weighted_norm_sq = float(f_irrev @ self.D_inv @ f_irrev)
        sigma_dot_val = weighted_norm_sq / self.T
        return max(0.0, sigma_dot_val)  # enforce 2nd Law numerically

    def sigma_dot_from_state(
        self,
        state: np.ndarray,
        control: float,
        drift_func,
        diffusion_func,
        mu: np.ndarray,
        kappa_matrix: np.ndarray,
    ) -> float:
        """
        Convenience: compute Σ̇ directly from state and control.

        Parameters
        ----------
        state : current state x
        control : control action u (scalar)
        drift_func : callable(state, control, dt) → next_state
            (we extract the drift from finite differences)
        diffusion_func : callable(state) → σ vector
        mu : long-run mean
        kappa_matrix : mean-reversion matrix
        """
        # Compute total drift via small-dt Euler approximation
        dt_small = 1e-4
        next_state = drift_func(state, control, dt_small)
        total_drift = (next_state - state) / dt_small

        # Compute reversible drift
        f_rev = self.reversible_drift_ou(state, mu, kappa_matrix)

        return self.sigma_dot(total_drift, f_rev)

    # ── Full Decomposition ────────────────────────────────────────────────

    def decompose(
        self,
        state: np.ndarray,
        control: float,
        total_drift: np.ndarray,
        mu: np.ndarray,
        kappa_matrix: np.ndarray,
        control_penalty_R: float = 0.1,
    ) -> EntropyDecomposition:
        """
        Full entropy decomposition at a single (x, u) pair.

        Returns the Σ̇ breakdown plus the negentropic running cost
        L_neg(x,u) = Σ̇(x,u) + ½·R·u²

        Parameters
        ----------
        state : current state
        control : control action (scalar)
        total_drift : f(x) + g(x)·u (pre-computed)
        mu : OU long-run mean
        kappa_matrix : mean-reversion matrix
        control_penalty_R : weight on control effort
        """
        f_rev = self.reversible_drift_ou(state, mu, kappa_matrix)
        f_irrev = self.irreversible_drift(total_drift, f_rev)
        s_dot = self.sigma_dot(total_drift, f_rev)
        ctrl_cost = 0.5 * control_penalty_R * control ** 2
        neg_cost = s_dot + ctrl_cost

        return EntropyDecomposition(
            sigma_dot_total=s_dot,
            irreversible_drift=f_irrev,
            reversible_drift=f_rev,
            total_drift=total_drift,
            control_cost=ctrl_cost,
            negentropic_cost=neg_cost,
        )

    # ── Negentropic Running Cost (drop-in for HJB) ───────────────────────

    def negentropic_running_cost(
        self,
        state: np.ndarray,
        control: float,
        total_drift: np.ndarray,
        mu: np.ndarray,
        kappa_matrix: np.ndarray,
        control_penalty_R: float = 0.1,
    ) -> float:
        """
        The negentropic running cost for the HJB:
            L_neg(x,u) = Σ̇(x,u) + ½ R u²

        This replaces the heuristic quadratic cost in the standard solver.
        The 2nd Law IS the integrando.

        Parameters
        ----------
        state, control, total_drift, mu, kappa_matrix :
            Same as decompose().
        control_penalty_R :
            Scalar weight on control effort (the "Maxwell demon budget").
        """
        f_rev = self.reversible_drift_ou(state, mu, kappa_matrix)
        s_dot = self.sigma_dot(total_drift, f_rev)
        return s_dot + 0.5 * control_penalty_R * control ** 2

    # ── Landauer Bound ────────────────────────────────────────────────────

    def landauer_bound(
        self,
        initial_state: np.ndarray,
        target_state: np.ndarray,
        mu: np.ndarray,
        kappa_matrix: np.ndarray,
    ) -> float:
        """
        Compute the Landauer-like dissipation bound: the minimum entropy
        that MUST be produced to drive the system from initial_state to
        target_state (synchronization).

        Uses the Mahalanobis distance as a proxy for the KL divergence
        between the initial condition (delta distribution at x_init) and
        the stationary distribution p_ss:

            Σ_min = ½ · (x_init - x_target)ᵀ · Σ_∞⁻¹ · (x_init - x_target)

        This is proportional to the minimum work required to perform the
        state transformation, and is always ≥ 0 with equality iff
        x_init = x_target.
        """
        # For diagonal OU: Σ_∞,ii = σᵢ²/(2κᵢ)
        if kappa_matrix.ndim == 1:
            kappa_diag = kappa_matrix
        else:
            kappa_diag = np.diag(kappa_matrix)

        sigma_inf_inv_diag = np.where(
            self.sigma_vec > 0,
            2.0 * kappa_diag / (self.sigma_vec ** 2 + self.reg),
            0.0,
        )

        displacement = initial_state - target_state

        # Mahalanobis distance: ½ dᵀ Σ_∞⁻¹ d
        bound = 0.5 * float(sigma_inf_inv_diag @ (displacement ** 2))
        return max(0.0, bound)


# ─────────────────────────────────────────────────────────────────────────────
# Utility: Build entropy engine from ISO parameters
# ─────────────────────────────────────────────────────────────────────────────
def build_entropy_engine_cenace(
    kappa: float = 0.42,
    sigma: float = 0.01483,
    n_dims: int = 2,
    sigma_vector: Optional[np.ndarray] = None,
) -> EntropyProductionRate:
    """
    Factory for building an entropy engine with CENACE calibration defaults.

    T_eff = σ² / (2κ) = 0.01483² / (2 × 0.42) ≈ 2.617e-4

    This is the "thermal energy scale" of the Mexican grid's frequency noise.
    """
    engine = EntropyProductionRate.from_ou_params(
        kappa=kappa, sigma=sigma, n_dims=n_dims, sigma_vector=sigma_vector,
    )
    logger.info(
        "CENACE entropy engine: T_eff=%.6e, κ=%.4f, σ=%.5f",
        engine.T, kappa, sigma,
    )
    return engine
