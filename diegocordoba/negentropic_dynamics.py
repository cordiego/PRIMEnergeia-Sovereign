"""
PRIME-Kernel — Negentropic Dynamics
====================================
HJBDynamics subclasses where the running cost IS the entropy production rate.

These classes inherit from the existing dynamics (GridFrequencyDynamics,
BESSFrequencyDynamics, etc.) and ONLY override running_cost() to use
the Esposito-Seifert entropy production Σ̇(x,u) + ½Ru².

V(x) solved with these dynamics is a negentropic potential — it measures
how much thermodynamic order must be drained from state x to reach the
synchronized attractor (60 Hz, ROCOF=0).

The step(), diffusion(), state_bounds(), and terminal_cost() methods
are INHERITED unchanged → 100% backward compatible.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional

import numpy as np

from hjb_solver_fortified import (
    HJBDynamics,
    GridFrequencyDynamics,
    RegimeSwitchingGridDynamics,
    BESSFrequencyDynamics,
    MultiAreaGridDynamics,
    BidimensionalSovereignDynamics,
    ISOMarket,
    iso_params,
    OrnsteinUhlenbeckCalibrator,
)
from entropy_production import EntropyProductionRate

logger = logging.getLogger("prime_kernel.negentropic_dynamics")


# ─────────────────────────────────────────────────────────────────────────────
# Base mixin for negentropic running cost injection
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicCostMixin:
    """
    Mixin that overrides running_cost() with entropy-based cost.

    Subclasses must set:
        self._entropy_engine : EntropyProductionRate
        self._control_R : float
        self._ou_mu : np.ndarray
        self._ou_kappa : np.ndarray or matrix
    """

    def _compute_total_drift(self, state: np.ndarray, control: float) -> np.ndarray:
        """
        Extract the total drift f(x) + g(x)u by Euler approximation.
        Uses a small dt to get the instantaneous drift vector.
        """
        dt_probe = 1e-4
        next_state = self.step(state, control, dt_probe)
        return (next_state - state) / dt_probe

    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        """
        Negentropic running cost: Σ̇(x,u) + ½Ru²

        This replaces the heuristic quadratic cost. The entropy production
        rate IS the integrando — the 2nd Law is the cost function.
        """
        # Compute total drift at this (state, control)
        total_drift = self._compute_total_drift(state, control)

        # Compute reversible drift from OU steady state
        f_rev = self._entropy_engine.reversible_drift_ou(
            state, self._ou_mu, self._ou_kappa,
        )

        # Σ̇ = (1/T) ||f_total - f_rev||²_{D⁻¹}
        sigma_dot = self._entropy_engine.sigma_dot(total_drift, f_rev)

        # Control penalty (Maxwell demon budget)
        control_cost = 0.5 * self._control_R * control ** 2

        return sigma_dot + control_cost


# ─────────────────────────────────────────────────────────────────────────────
# 2-D: Negentropic Grid Frequency Dynamics
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicGridDynamics(NegentropicCostMixin, GridFrequencyDynamics):
    """
    Grid dynamics where running_cost = Σ̇(x,u) + ½Ru².

    State: [Δf (Hz), P_inj (MW)]
    Control: injection ramp rate (MW/s)

    V(x) becomes the negentropic potential:
    - V(Δf=0, P=optimal) = minimum (the 60 Hz synchronization well)
    - V(Δf=±2, ...) = maximum (far from synchronization, high entropy)

    The entropy production rate captures the PHYSICAL cost of being
    out of synchronization, not an ad-hoc engineering penalty.
    """

    def __init__(
        self,
        market: ISOMarket = ISOMarket.CENACE,
        calibrator: Optional[OrnsteinUhlenbeckCalibrator] = None,
        control_penalty_R: float = 0.1,
    ):
        # Initialize parent grid dynamics (step, diffusion, bounds)
        GridFrequencyDynamics.__init__(self, market=market, calibrator=calibrator)

        # OU parameters for entropy engine
        self._control_R = control_penalty_R

        # Build entropy engine: T_eff = σ²/(2κ)
        sigma_vec = self.diffusion(np.zeros(2))  # [σ_OU, 0]
        self._entropy_engine = EntropyProductionRate.from_ou_params(
            kappa=self.kappa,
            sigma=self.sigma_ou,
            n_dims=2,
            sigma_vector=sigma_vec,
        )

        # OU equilibrium: μ = [0, 0] (nominal frequency, zero injection)
        self._ou_mu = np.array([0.0, 0.0])
        # Mean-reversion matrix (diagonal approximation)
        self._ou_kappa = np.array([self.kappa, 0.1])  # P_inj has slow mean reversion

        logger.info(
            "NegentropicGridDynamics: T_eff=%.6e, R=%.4f, κ=%.4f",
            self._entropy_engine.T, self._control_R, self.kappa,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3-D: Negentropic Regime-Switching Dynamics
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicRegimeDynamics(NegentropicCostMixin, RegimeSwitchingGridDynamics):
    """
    Regime-switching grid dynamics with entropy-based cost.

    State: [Δf (Hz), P_inj (MW), regime ∈ {0,1}]
    Control: injection ramp rate (MW/s)

    The entropy engine adapts to the current regime:
    regime 0 (low renewable): lower σ → lower T → less entropy at equilibrium
    regime 1 (high renewable): higher σ → higher T → more entropy to manage
    """

    def __init__(
        self,
        market: ISOMarket = ISOMarket.CENACE,
        control_penalty_R: float = 0.1,
        **kwargs,
    ):
        RegimeSwitchingGridDynamics.__init__(self, market=market, **kwargs)
        self._control_R = control_penalty_R

        # Build entropy engine for regime 0 (default — updated dynamically)
        sigma_vec = np.array([self.sigmas[0], 0.0, 0.0])
        self._entropy_engine = EntropyProductionRate.from_ou_params(
            kappa=self.kappas[0],
            sigma=self.sigmas[0],
            n_dims=3,
            sigma_vector=sigma_vec,
        )

        self._ou_mu = np.array([0.0, 0.0, 0.0])
        self._ou_kappa = np.array([self.kappas[0], 0.1, 0.0])

        # Pre-build engines for both regimes
        self._engines_by_regime = {}
        for regime in [0, 1]:
            sv = np.array([self.sigmas[regime], 0.0, 0.0])
            self._engines_by_regime[regime] = EntropyProductionRate.from_ou_params(
                kappa=self.kappas[regime],
                sigma=self.sigmas[regime],
                n_dims=3,
                sigma_vector=sv,
            )

    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        """Regime-aware entropy cost: switch engine based on current regime."""
        regime = self._regime(state)

        # Update entropy engine for current regime
        self._entropy_engine = self._engines_by_regime[regime]
        self._ou_kappa = np.array([self.kappas[regime], 0.1, 0.0])

        # Delegate to mixin
        return NegentropicCostMixin.running_cost(self, state, control, t)


# ─────────────────────────────────────────────────────────────────────────────
# 5-D: Negentropic BESS Dynamics
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicBESSDynamics(NegentropicCostMixin, BESSFrequencyDynamics):
    """
    BESS dynamics with entropy-based running cost.

    State: [Δf, ROCOF, SoC, T_cell, DoH]
    Control: power setpoint ramp (MW/s)

    The entropy production captures the thermodynamic cost of:
    - Frequency deviation (electromagnetic disorder)
    - Thermal stress (cell heating → irreversible degradation)
    - SoC displacement from optimal (chemical potential imbalance)
    """

    def __init__(
        self,
        market: ISOMarket = ISOMarket.CENACE,
        control_penalty_R: float = 0.1,
        **kwargs,
    ):
        BESSFrequencyDynamics.__init__(self, market=market, **kwargs)
        self._control_R = control_penalty_R

        # 5-D diffusion vector: only frequency carries noise
        sigma_vec = self.diffusion(np.zeros(5))  # [σ_OU, 0, 0, 0, 0]
        self._entropy_engine = EntropyProductionRate.from_ou_params(
            kappa=0.42,  # CENACE default
            sigma=self.sigma_ou,
            n_dims=5,
            sigma_vector=sigma_vec,
        )

        # OU equilibrium for 5-D BESS
        self._ou_mu = np.array([0.0, 0.0, 0.5, 25.0, 0.0])
        # Mean-reversion rates for each state dimension
        self._ou_kappa = np.array([
            0.42,   # Δf: OU reversion (from CENACE calibration)
            0.5,    # ROCOF: fast reversion
            0.01,   # SoC: slow reversion to 50%
            0.033,  # T_cell: thermal time constant ~30s
            0.001,  # DoH: very slow degradation
        ])


# ─────────────────────────────────────────────────────────────────────────────
# N-Zone: Negentropic Multi-Area Dynamics
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicMultiAreaDynamics(NegentropicCostMixin, MultiAreaGridDynamics):
    """
    Multi-area grid with entropy-based cost.

    State: [Δf₁ ... Δf_N, P_inj]
    Control: injection ramp at target zone

    The entropy production here captures inter-area coupling effects:
    when one zone desynchronizes, it produces entropy that propagates
    through the coupling matrix K.
    """

    def __init__(
        self,
        n_zones: int = 5,
        control_penalty_R: float = 0.1,
        **kwargs,
    ):
        MultiAreaGridDynamics.__init__(self, n_zones=n_zones, **kwargs)
        self._control_R = control_penalty_R

        n_dims = n_zones + 1
        sigma_vec = self.diffusion(np.zeros(n_dims))
        self._entropy_engine = EntropyProductionRate.from_ou_params(
            kappa=0.40,  # average zone kappa
            sigma=0.015,  # average zone sigma
            n_dims=n_dims,
            sigma_vector=sigma_vec,
        )

        self._ou_mu = np.zeros(n_dims)
        kappa_diag = np.append(np.diag(self.K), [0.1])
        self._ou_kappa = kappa_diag


# ─────────────────────────────────────────────────────────────────────────────
# Kuramoto Oscillator Dynamics (NEW — not inheriting)
# ─────────────────────────────────────────────────────────────────────────────
class NegentropicKuramotoDynamics(HJBDynamics):
    """
    Kuramoto oscillator model for grid synchronization with negentropic cost.

    The Kuramoto model is the natural setting for the Esposito connection
    (his paper uses Kuramoto explicitly for the entropy-synchronization link).

    State: [θ₁, θ₂, ..., θ_N] — phase angles of N oscillators
    Control: u (scalar) — power injection that affects all oscillators uniformly

    Dynamics:
        dθᵢ = [ωᵢ + (K/N)·Σⱼ sin(θⱼ - θᵢ) + u/N] dt + σ dWᵢ

    The entropy production rate in Kuramoto is:
        Σ̇ = (1/T) · Σᵢ ||ωᵢ + K/N Σⱼ sin(θⱼ-θᵢ) + u/N - f_rev,i||² / Dᵢ

    The synchronized state (all θᵢ equal, mod 2π) is the minimum of V(θ).

    Parameters
    ----------
    n_oscillators : int
        Number of Kuramoto oscillators (grid nodes).
    natural_frequencies : np.ndarray
        ωᵢ — natural frequencies. Default: drawn from Cauchy distribution
        centered at 60 Hz with spread γ (Lorentzian).
    coupling_K : float
        Coupling strength. K > K_c ≈ 2γ for synchronization.
    sigma_noise : float
        Individual oscillator noise intensity.
    """

    def __init__(
        self,
        n_oscillators: int = 5,
        natural_frequencies: Optional[np.ndarray] = None,
        coupling_K: float = 2.0,
        sigma_noise: float = 0.1,
        control_penalty_R: float = 0.1,
        nominal_freq: float = 60.0,
    ):
        self.N = n_oscillators
        self.K = coupling_K
        self.sigma = sigma_noise
        self._control_R = control_penalty_R
        self.nominal_freq = nominal_freq

        # Natural frequencies: small deviations from nominal
        if natural_frequencies is not None:
            self.omega = natural_frequencies
        else:
            rng = np.random.default_rng(42)
            self.omega = rng.normal(0.0, 0.05, size=n_oscillators)  # deviations from nominal

        # Entropy engine
        sigma_vec = np.full(n_oscillators, sigma_noise)
        # Effective kappa for Kuramoto: related to coupling K
        kappa_eff = coupling_K / n_oscillators
        self._entropy_engine = EntropyProductionRate.from_ou_params(
            kappa=kappa_eff,
            sigma=sigma_noise,
            n_dims=n_oscillators,
            sigma_vector=sigma_vec,
        )

        # Equilibrium: all phases equal (synchronized state)
        self._ou_mu = np.zeros(n_oscillators)
        self._ou_kappa = np.full(n_oscillators, kappa_eff)

        logger.info(
            "KuramotoDynamics: N=%d, K=%.2f, σ=%.3f, T_eff=%.6e",
            self.N, self.K, self.sigma, self._entropy_engine.T,
        )

    def state_dims(self) -> int:
        return self.N

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(-np.pi, np.pi)] * self.N

    def control_bounds(self) -> Tuple[float, float]:
        return (-5.0, 5.0)

    def _kuramoto_drift(self, phases: np.ndarray, control: float) -> np.ndarray:
        """
        Kuramoto drift:
            dθᵢ/dt = ωᵢ + (K/N)·Σⱼ sin(θⱼ - θᵢ) + u/N
        """
        drift = self.omega.copy()
        for i in range(self.N):
            coupling = 0.0
            for j in range(self.N):
                coupling += np.sin(phases[j] - phases[i])
            drift[i] += (self.K / self.N) * coupling + control / self.N
        return drift

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        drift = self._kuramoto_drift(state, control)
        new_state = state + drift * dt
        # Wrap to [-π, π]
        new_state = np.mod(new_state + np.pi, 2 * np.pi) - np.pi
        return new_state

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        return np.full(self.N, self.sigma)

    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        """Negentropic cost: Σ̇ + ½Ru²"""
        total_drift = self._kuramoto_drift(state, control)
        f_rev = self._entropy_engine.reversible_drift_ou(
            state, self._ou_mu, self._ou_kappa,
        )
        sigma_dot = self._entropy_engine.sigma_dot(total_drift, f_rev)
        control_cost = 0.5 * self._control_R * control ** 2
        return sigma_dot + control_cost

    def terminal_cost(self, state: np.ndarray) -> float:
        """
        Terminal cost based on Kuramoto order parameter.
        r = |1/N Σ exp(iθⱼ)| — 1 = perfect sync, 0 = incoherent.
        """
        z = np.mean(np.exp(1j * state))
        r = abs(z)
        return 100.0 * (1.0 - r) ** 2  # Penalize desynchronization

    def order_parameter(self, state: np.ndarray) -> float:
        """Kuramoto order parameter r ∈ [0,1]. r=1 is full synchronization."""
        return float(abs(np.mean(np.exp(1j * state))))


# ─────────────────────────────────────────────────────────────────────────────
# Factory functions
# ─────────────────────────────────────────────────────────────────────────────
def build_negentropic_cenace(
    dynamics_type: str = "grid",
    control_penalty_R: float = 0.1,
    calibrator: Optional[OrnsteinUhlenbeckCalibrator] = None,
    market: ISOMarket = ISOMarket.CENACE,
) -> HJBDynamics:
    """
    Factory for negentropic dynamics with CENACE defaults.

    Parameters
    ----------
    dynamics_type : str
        One of: "grid", "regime", "bess", "multiarea", "kuramoto"
    control_penalty_R : float
        Maxwell demon budget.
    """
    if dynamics_type == "grid":
        return NegentropicGridDynamics(
            market=market, calibrator=calibrator,
            control_penalty_R=control_penalty_R,
        )
    elif dynamics_type == "regime":
        return NegentropicRegimeDynamics(
            market=market, control_penalty_R=control_penalty_R,
        )
    elif dynamics_type == "bess":
        return NegentropicBESSDynamics(
            market=market, control_penalty_R=control_penalty_R,
        )
    elif dynamics_type == "multiarea":
        return NegentropicMultiAreaDynamics(
            control_penalty_R=control_penalty_R,
        )
    elif dynamics_type == "kuramoto":
        return NegentropicKuramotoDynamics(
            control_penalty_R=control_penalty_R,
        )
    else:
        raise ValueError(f"Unknown dynamics type: {dynamics_type}")
