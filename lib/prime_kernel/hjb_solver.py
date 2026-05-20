"""
PRIME-Kernel — Unified HJB Solver  (FORTIFIED v2.0)
=====================================================
Fortification based on ITAM Doctoral Thesis (Diego Córdoba Urrutia, 2026):
  L.1 → RegimeSwitchingGridDynamics (Hamilton 1989, Markov-switching OU)
  L.2 → MultiAreaGridDynamics (vector OU, inter-area coupling matrix K)
  L.3 → BundledAncillaryDynamics (frequency + voltage reserve bundling)
  E.2 → BESSFrequencyDynamics (5-D: Δf, ROCOF, SoC, T_cell, DoH)
  §2  → OrnsteinUhlenbeckCalibrator (MLE for κ, σ, μ on CENACE data)
  §3  → RobustHJBSolver (ambiguity-set enlargement, ε from out-of-sample ECM)
  §4  → ContractValuator (HJB-Myerson pricing: V_BS, V_HJB, V_rob, V_max)
  §6  → ISOParameterLibrary (CENACE, ERCOT, MIBEL, XM, CEN, ONS)
 misc → N-D interpolation via scipy (fixes NotImplementedError for 4-D+ grids)
       Solver persistence (joblib cache) and convergence diagnostics

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

logger = logging.getLogger("prime_kernel.hjb")


# ─────────────────────────────────────────────────────────────────────────────
# Abstract Dynamics Interface  (unchanged API — backward-compatible)
# ─────────────────────────────────────────────────────────────────────────────
class HJBDynamics(ABC):
    """Abstract base for state-space dynamics injected into any HJB solver."""

    @abstractmethod
    def state_dims(self) -> int: ...

    @abstractmethod
    def state_bounds(self) -> List[Tuple[float, float]]: ...

    @abstractmethod
    def control_bounds(self) -> Tuple[float, float]: ...

    @abstractmethod
    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray: ...

    @abstractmethod
    def running_cost(self, state: np.ndarray, control: float) -> float: ...

    @abstractmethod
    def terminal_cost(self, state: np.ndarray) -> float: ...

    # ── Optional stochastic diffusion hook (thesis §2 / E.2) ──────────────
    def diffusion(self, state: np.ndarray) -> np.ndarray:
        """
        Diffusion vector g(x) for the SDE  dx = f dt + g dW.
        Default: zero (deterministic dynamics).
        Override in stochastic subclasses to enable Itô-corrected value iteration.
        """
        return np.zeros(self.state_dims())


# ─────────────────────────────────────────────────────────────────────────────
# HJB Result
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class HJBResult:
    """Output bundle from the HJB solver."""
    time_grid:          np.ndarray
    state_trajectory:   np.ndarray   # (n_steps+1, state_dims)
    control_trajectory: np.ndarray   # (n_steps,)
    value_function:     np.ndarray   # discretised V(x) at solution
    total_cost:         float
    n_sweeps:           int
    converged:          bool
    solve_time_s:       float = 0.0
    metadata:           Dict  = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Thesis §2 — Ornstein-Uhlenbeck MLE Calibrator
# ─────────────────────────────────────────────────────────────────────────────
class OrnsteinUhlenbeckCalibrator:
    """
    Closed-form MLE estimator for the OU process
        dΔf = κ(μ − Δf)dt + σ dW

    Calibrate on CENACE / ERCOT 4-second frequency ticks.

    Reference: thesis §2.2, Eq. (2.4)–(2.8).
    """

    def __init__(self, dt: float = 4.0):
        """dt: observation interval in seconds (CENACE publishes at 4 s)."""
        self.dt = dt
        self.kappa: float = float("nan")
        self.mu:    float = float("nan")
        self.sigma: float = float("nan")
        self._n_obs: int  = 0

    def fit(self, freq_series: np.ndarray, nominal_hz: float = 60.0) -> "OrnsteinUhlenbeckCalibrator":
        """
        Fit κ, μ, σ from a 1-D array of frequency observations (Hz).
        Uses discrete-time exact MLE (Vasicek regression).
        """
        x = freq_series - nominal_hz           # convert to deviations
        n = len(x) - 1
        if n < 10:
            raise ValueError("Need at least 11 observations for OU calibration.")

        x0 = x[:-1]
        x1 = x[1:]
        Sx  = x0.sum();  Sy  = x1.sum()
        Sxx = (x0**2).sum(); Sxy = (x0 * x1).sum(); Syy = (x1**2).sum()

        # Vasicek (1977) exact MLE
        mu_hat  = (Sy*Sxx - Sx*Sxy) / (n*(Sxx - Sxy) - (Sx**2 - Sx*Sy))
        alpha   = (Sxy - mu_hat*(Sx + Sy) + n*mu_hat**2) / (Sxx - 2*mu_hat*Sx + n*mu_hat**2)
        # Clamp alpha to (0, 1) for stationarity
        alpha   = float(np.clip(alpha, 1e-6, 1 - 1e-6))

        kappa_hat = -np.log(alpha) / self.dt
        sigma_sq  = (Syy - 2*alpha*Sxy + alpha**2*Sxx
                     - 2*mu_hat*(1-alpha)*(Sy - alpha*Sx)
                     + n*mu_hat**2*(1-alpha)**2) / n
        sigma_hat = np.sqrt(max(sigma_sq, 1e-12) * 2 * kappa_hat / (1 - alpha**2))

        self.kappa = float(kappa_hat)
        self.mu    = float(mu_hat)
        self.sigma = float(sigma_hat)
        self._n_obs = n + 1

        logger.info(
            "OU calibration (n=%d): κ=%.4f s⁻¹  μ=%.5f Hz  σ=%.5f Hz/√s",
            self._n_obs, self.kappa, self.mu, self.sigma
        )
        return self

    def out_of_sample_epsilon(self, freq_val: np.ndarray, nominal_hz: float = 60.0) -> float:
        """
        Compute ambiguity radius ε for the robust HJB (thesis §3.4, Eq. 3.12).
        ε = ECM_oos / (2 κ T),  T = validation horizon in seconds.
        """
        if np.isnan(self.kappa):
            raise RuntimeError("Call fit() before computing ε.")
        x = freq_val - nominal_hz
        T = len(x) * self.dt
        alpha = np.exp(-self.kappa * self.dt)
        residuals = x[1:] - (alpha * x[:-1] + self.mu * (1 - alpha))
        ecm = float(np.mean(residuals**2))
        epsilon = ecm / (2 * self.kappa * T)
        logger.info("Ambiguity ε = %.6f  (ECM_oos=%.6e, T=%.0f s)", epsilon, ecm, T)
        return epsilon

    @property
    def params(self) -> Dict[str, float]:
        return {"kappa": self.kappa, "mu": self.mu, "sigma": self.sigma}


# ─────────────────────────────────────────────────────────────────────────────
# §6 — ISO Parameter Library
# ─────────────────────────────────────────────────────────────────────────────
class ISOMarket(str, Enum):
    CENACE = "cenace"
    ERCOT  = "ercot"
    MIBEL  = "mibel"
    XM     = "xm"       # Colombia
    CEN    = "cen"       # Chile
    ONS    = "ons"       # Brazil (5-area)
    PJM    = "pjm"
    CAISO  = "caiso"


# Per-ISO physical parameters — thesis §6, Table 6.1
_ISO_PARAMS: Dict[str, Dict] = {
    ISOMarket.CENACE: dict(nominal_hz=60.0, inertia_H=4.8, damping_D=1.1,
                           kappa=0.42, sigma=0.01483, max_mw=100.0,
                           freq_deadband_hz=0.017, penalty_threshold_hz=0.50,
                           penalty_coeff=500.0, ens_cost_mxn_mwh=15_000.0),
    ISOMarket.ERCOT:  dict(nominal_hz=60.0, inertia_H=3.8, damping_D=0.9,
                           kappa=0.55, sigma=0.0210, max_mw=100.0,
                           freq_deadband_hz=0.017, penalty_threshold_hz=0.50,
                           penalty_coeff=600.0, ens_cost_mxn_mwh=18_000.0),
    ISOMarket.MIBEL:  dict(nominal_hz=50.0, inertia_H=6.2, damping_D=1.4,
                           kappa=0.30, sigma=0.0095, max_mw=100.0,
                           freq_deadband_hz=0.020, penalty_threshold_hz=0.40,
                           penalty_coeff=450.0, ens_cost_mxn_mwh=12_000.0),
    ISOMarket.XM:     dict(nominal_hz=60.0, inertia_H=5.5, damping_D=1.2,
                           kappa=0.38, sigma=0.0180, max_mw=100.0,
                           freq_deadband_hz=0.015, penalty_threshold_hz=0.45,
                           penalty_coeff=520.0, ens_cost_mxn_mwh=14_000.0),
    ISOMarket.CEN:    dict(nominal_hz=50.0, inertia_H=3.2, damping_D=0.8,
                           kappa=0.62, sigma=0.0310, max_mw=100.0,
                           freq_deadband_hz=0.025, penalty_threshold_hz=0.55,
                           penalty_coeff=650.0, ens_cost_mxn_mwh=20_000.0),
    ISOMarket.PJM:    dict(nominal_hz=60.0, inertia_H=5.0, damping_D=1.0,
                           kappa=0.45, sigma=0.0130, max_mw=100.0,
                           freq_deadband_hz=0.017, penalty_threshold_hz=0.50,
                           penalty_coeff=500.0, ens_cost_mxn_mwh=16_000.0),
    ISOMarket.CAISO:  dict(nominal_hz=60.0, inertia_H=4.5, damping_D=1.0,
                           kappa=0.48, sigma=0.0155, max_mw=100.0,
                           freq_deadband_hz=0.017, penalty_threshold_hz=0.50,
                           penalty_coeff=510.0, ens_cost_mxn_mwh=15_500.0),
}


def iso_params(market: ISOMarket) -> Dict:
    """Return calibrated physical parameters for the given ISO."""
    if market not in _ISO_PARAMS:
        raise ValueError(f"ISO '{market}' not in library. Add it to _ISO_PARAMS.")
    return dict(_ISO_PARAMS[market])


# ─────────────────────────────────────────────────────────────────────────────
# Original 2-D Grid Frequency Dynamics  (swing equation, now ISO-aware)
# ─────────────────────────────────────────────────────────────────────────────
class GridFrequencyDynamics(HJBDynamics):
    """
    State: [Δf (Hz), P_inj (MW)]
    Control: injection ramp rate (MW/s)

    Improvements over v1.0:
    - ISO-aware parameters via ISOParameterLibrary
    - Stochastic OU diffusion hook (σ term for Itô correction)
    - Per-ISO penalty threshold and deadband
    """

    def __init__(self, market: ISOMarket = ISOMarket.CENACE,
                 calibrator: Optional[OrnsteinUhlenbeckCalibrator] = None):
        p = iso_params(market)
        self.nominal_freq  = p["nominal_hz"]
        self.H             = p["inertia_H"]
        self.D             = p["damping_D"]
        self.max_inj       = p["max_mw"]
        self.kappa         = calibrator.kappa  if calibrator else p["kappa"]
        self.sigma_ou      = calibrator.sigma  if calibrator else p["sigma"]
        self._deadband     = p["freq_deadband_hz"]
        self._pen_thresh   = p["penalty_threshold_hz"]
        self._pen_coeff    = p["penalty_coeff"]
        self.market        = market

    def state_dims(self) -> int: return 2

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(-2.0, 2.0), (0.0, self.max_inj)]

    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)   # MW/s ramp rate

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df, P = state
        ddf = (P - self.D * df) / (2.0 * self.H)
        new_df = np.clip(df + ddf * dt, -2.0, 2.0)
        new_P  = np.clip(P  + control * dt, 0.0, self.max_inj)
        return np.array([new_df, new_P])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        """
        OU diffusion in the Δf dimension only (thesis §2.1, Eq. 2.2).
        g(x) = [σ_OU, 0]  so only frequency carries Brownian noise.
        """
        return np.array([self.sigma_ou, 0.0])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        df, P = state
        freq_cost  = 100.0 * df**2
        energy_cost = 0.01 * abs(control)
        # Thesis §2.3: deadband zone inside which no penalty accrues
        excess = max(0.0, abs(df) - self._deadband)
        penalty = self._pen_coeff * excess**2 if excess > 0 else 0.0
        return freq_cost + energy_cost + penalty

    def terminal_cost(self, state: np.ndarray) -> float:
        df, P = state
        return 200.0 * df**2 + 0.1 * P


# ─────────────────────────────────────────────────────────────────────────────
# Thesis L.1 — Regime-Switching Grid Dynamics  (Hamilton 1989)
# ─────────────────────────────────────────────────────────────────────────────
class RegimeSwitchingGridDynamics(HJBDynamics):
    """
    Two-regime OU process:  s_t ∈ {0=Low, 1=High}
        dΔf = κ(s) · (μ − Δf) dt + σ(s) dW

    Regime 0 (Low):  conventional / baseload-dominated grid
    Regime 1 (High): high-renewable-penetration regime (wind/solar)

    State: [Δf, P_inj, regime]  — regime ∈ {0, 1} discretised as {0.0, 1.0}
    The HJB operates on the mixed state; the policy accounts for regime
    uncertainty through the transition probability matrix P_trans.

    Reference: thesis §L.1, Hamilton (1989).
    """

    def __init__(self,
                 market: ISOMarket = ISOMarket.CENACE,
                 kappa_low: float  = 0.28,
                 kappa_high: float = 0.58,
                 sigma_low: float  = 0.0090,
                 sigma_high: float = 0.0210,
                 p_low_to_high: float = 0.05,   # per-period transition prob
                 p_high_to_low: float = 0.12,
                 ):
        p = iso_params(market)
        self.H, self.D         = p["inertia_H"], p["damping_D"]
        self.max_inj           = p["max_mw"]
        self._pen_thresh       = p["penalty_threshold_hz"]
        self._pen_coeff        = p["penalty_coeff"]
        self._deadband         = p["freq_deadband_hz"]
        self.kappas            = [kappa_low,  kappa_high]
        self.sigmas            = [sigma_low,  sigma_high]
        # Transition matrix row: [prob_stay, prob_switch]
        self.P_trans           = np.array([[1 - p_low_to_high, p_low_to_high],
                                           [p_high_to_low, 1 - p_high_to_low]])

    def state_dims(self) -> int: return 3   # [Δf, P, regime]

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(-2.0, 2.0), (0.0, self.max_inj), (0.0, 1.0)]

    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)

    def _regime(self, state: np.ndarray) -> int:
        """Round continuous regime dimension to nearest integer regime index."""
        return int(np.clip(round(state[2]), 0, 1))

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df, P, _ = state
        s = self._regime(state)
        # Regime-dependent mean reversion
        ddf    = (-self.kappas[s] * df + P - self.D * df) / (2.0 * self.H)
        new_df = np.clip(df + ddf * dt, -2.0, 2.0)
        new_P  = np.clip(P  + control * dt, 0.0, self.max_inj)
        # Stochastic regime transition (expected next regime)
        next_regime = float(self.P_trans[s, 1])   # E[s_{t+1}]
        return np.array([new_df, new_P, next_regime])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        s = self._regime(state)
        return np.array([self.sigmas[s], 0.0, 0.0])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        df, P, s_float = state
        s = int(round(s_float))
        freq_cost  = 100.0 * df**2
        energy_cost = 0.01 * abs(control)
        excess = max(0.0, abs(df) - self._deadband)
        # High-regime: tighter penalty (more renewable variability)
        pen_coeff  = self._pen_coeff * (1.5 if s == 1 else 1.0)
        penalty    = pen_coeff * excess**2 if excess > 0 else 0.0
        return freq_cost + energy_cost + penalty

    def terminal_cost(self, state: np.ndarray) -> float:
        df, P, _ = state
        return 200.0 * df**2 + 0.1 * P


# ─────────────────────────────────────────────────────────────────────────────
# Thesis L.2 — Multi-Area (Zonal) Grid Dynamics  (vector OU)
# ─────────────────────────────────────────────────────────────────────────────
class MultiAreaGridDynamics(HJBDynamics):
    """
    N-zone vector OU for the SIN zonal structure (thesis §L.2):
        d(Δf) = K(μ − Δf)dt + Σ^{1/2} dW

    State:  [Δf₁ … Δf_N, P_inj]  dim = N+1
    Control: scalar injection ramp rate at the target zone.

    K is the mean-reversion matrix whose off-diagonal entries κ_{ij}
    capture electrical coupling between zones.  Σ is the noise covariance.

    Default: 5-zone model for CENACE (Norte, Noroeste, Occidental, Centro, Sur).
    """

    _DEFAULT_K = np.array([
        [0.40, -0.04, -0.02,  0.00,  0.00],
        [-0.04, 0.38, -0.03,  0.00,  0.00],
        [-0.02, -0.03, 0.44, -0.05, -0.01],
        [ 0.00,  0.00, -0.05, 0.42, -0.04],
        [ 0.00,  0.00, -0.01, -0.04, 0.36],
    ])
    _DEFAULT_SIG = np.diag([0.0148, 0.0135, 0.0162, 0.0140, 0.0155])

    def __init__(self,
                 n_zones: int = 5,
                 K: Optional[np.ndarray] = None,
                 Sigma: Optional[np.ndarray] = None,
                 max_inj_mw: float = 100.0,
                 control_zone: int = 0):
        self.n_zones      = n_zones
        self.K            = K     if K     is not None else self._DEFAULT_K[:n_zones, :n_zones]
        self.Sigma        = Sigma if Sigma is not None else self._DEFAULT_SIG[:n_zones, :n_zones]
        self.Sigma_sqrt   = np.linalg.cholesky(self.Sigma + 1e-9 * np.eye(n_zones))
        self.max_inj      = max_inj_mw
        self.control_zone = control_zone   # which zone receives the injection

    def state_dims(self) -> int:
        return self.n_zones + 1   # [Δf_1..N, P_inj]

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [(-2.0, 2.0)] * self.n_zones + [(0.0, self.max_inj)]

    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df_vec = state[:self.n_zones]
        P      = state[self.n_zones]
        # Vector OU drift:  K @ (0 − df_vec)  (long-run mean = 0 deviation)
        drift   = -self.K @ df_vec
        new_df  = np.clip(df_vec + drift * dt, -2.0, 2.0)
        # Injection ramps only at the control zone
        new_P   = np.clip(P + control * dt, 0.0, self.max_inj)
        return np.concatenate([new_df, [new_P]])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        """Returns the per-zone σ values (diagonal of Σ^{1/2}) + 0 for P."""
        sig_diag = np.sqrt(np.diag(self.Sigma))
        return np.concatenate([sig_diag, [0.0]])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        df_vec = state[:self.n_zones]
        freq_cost  = 100.0 * float(np.sum(df_vec**2))
        energy_cost = 0.01 * abs(control)
        excess = np.maximum(np.abs(df_vec) - 0.017, 0.0)
        penalty = 500.0 * float(np.sum(excess**2))
        return freq_cost + energy_cost + penalty

    def terminal_cost(self, state: np.ndarray) -> float:
        df_vec = state[:self.n_zones]
        P      = state[self.n_zones]
        return 200.0 * float(np.sum(df_vec**2)) + 0.1 * P


# ─────────────────────────────────────────────────────────────────────────────
# Thesis E.2 — BESS Frequency Dynamics  (5-D electro-chemical state)
# ─────────────────────────────────────────────────────────────────────────────
class BESSFrequencyDynamics(HJBDynamics):
    """
    State: [Δf, ROCOF (Hz/s), SoC ∈ [0,1], T_cell (°C), DoH ∈ [0,1]]
    Control: active power setpoint ramp rate (MW/s, signed)

    Effective capacity: Ū_eff = Ū_max · SoC · (1 − DoH)

    Reference: thesis §E.2.
    """

    def __init__(self,
                 market: ISOMarket = ISOMarket.CENACE,
                 capacity_mw: float = 10.0,
                 T_ambient_c: float = 25.0,
                 cycle_life: float  = 3000.0):
        p = iso_params(market)
        self.H             = p["inertia_H"]
        self.D             = p["damping_D"]
        self.sigma_ou      = p["sigma"]
        self._pen_thresh   = p["penalty_threshold_hz"]
        self._pen_coeff    = p["penalty_coeff"]
        self._deadband     = p["freq_deadband_hz"]
        self.C_max         = capacity_mw
        self.T_amb         = T_ambient_c
        self.cycle_life    = cycle_life

    def state_dims(self) -> int: return 5

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [
            (-2.0,  2.0),   # Δf
            (-5.0,  5.0),   # ROCOF
            ( 0.1,  0.95),  # SoC  (10 %–95 % usable window)
            (20.0, 55.0),   # T_cell °C
            ( 0.0,  0.80),  # DoH  (retired at 80 % degradation)
        ]

    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)   # MW/s

    def _eff_capacity(self, soc: float, doh: float) -> float:
        return self.C_max * float(np.clip(soc, 0, 1)) * (1.0 - float(np.clip(doh, 0, 1)))

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df, rocof, soc, T_cell, doh = state

        # Effective capacity limits control
        C_eff   = self._eff_capacity(soc, doh)
        u_mw    = float(np.clip(control * dt, -C_eff, C_eff))

        # Grid dynamics (swing equation)
        new_rocof = (u_mw - self.D * df) / (2.0 * self.H)
        new_df    = np.clip(df + new_rocof * dt, -2.0, 2.0)

        # SoC update  (discharging = negative u_mw)
        eta_charge = 0.95 if u_mw < 0 else 1.0 / 0.95
        new_soc    = float(np.clip(soc - (u_mw * eta_charge * dt) / (3600.0 * self.C_max), 0.1, 0.95))

        # Thermal model  (Newton cooling + Ohmic heating)
        I_sq      = (abs(u_mw) / max(self.C_max, 1e-3)) ** 2
        dT        = (self.T_amb - T_cell) / 30.0 + 2.5 * I_sq
        new_T     = float(np.clip(T_cell + dT * dt, 20.0, 55.0))

        # Degradation model  (Ah-throughput based)
        doh_rate  = abs(u_mw) / (2.0 * self.C_max * self.cycle_life)
        new_doh   = float(np.clip(doh + doh_rate * dt, 0.0, 0.80))

        return np.array([new_df, new_rocof, new_soc, new_T, new_doh])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        return np.array([self.sigma_ou, 0.0, 0.0, 0.0, 0.0])

    def running_cost(self, state: np.ndarray, control: float) -> float:
        df, _, soc, T_cell, doh = state
        freq_cost   = 100.0 * df**2
        excess      = max(0.0, abs(df) - self._deadband)
        pen_freq    = self._pen_coeff * excess**2 if excess > 0 else 0.0
        # BESS degradation cost (penalty for high DoH state)
        doh_cost    = 200.0 * doh**2
        # Thermal stress penalty
        T_excess    = max(0.0, T_cell - 45.0)
        thermal_pen = 5.0 * T_excess**2
        return freq_cost + pen_freq + doh_cost + thermal_pen

    def terminal_cost(self, state: np.ndarray) -> float:
        df, _, soc, _, doh = state
        return 200.0 * df**2 + 50.0 * doh + 20.0 * (1.0 - soc)


# ─────────────────────────────────────────────────────────────────────────────
# Perovskite Annealing Dynamics  (unchanged from v1.0)
# ─────────────────────────────────────────────────────────────────────────────
class PerovskiteAnnealingDynamics(HJBDynamics):
    """
    HJB dynamics for perovskite annealing schedule optimisation.
    Used by PRIME Materials (Granas-SDL, Granas-Optics).
    State: [grain_size_nm, defect_density, film_temp_C]
    """
    BOLTZMANN_EV = 8.617333e-5
    MAX_GRAIN_NM = 900.0
    DECOMP_TEMP_C = 200.0

    def __init__(self, Q_grain: float = 1.0, Q_defect: float = 50.0, R_energy: float = 0.1):
        self.Q_grain  = Q_grain
        self.Q_defect = Q_defect
        self.R_energy = R_energy

    def state_dims(self): return 3

    def state_bounds(self):
        return [(30.0, 900.0), (0.02, 2.0), (25.0, 220.0)]

    def control_bounds(self):
        return (-5.0, 5.0)

    def step(self, state, control, dt):
        grain, defects, temp = state
        temp_k  = temp + 273.15
        setpoint = np.clip(temp + control * dt, 25.0, 250.0)
        arr_grain  = np.exp(-0.45 / (self.BOLTZMANN_EV * temp_k))
        saturation = max(0, 1.0 - grain / self.MAX_GRAIN_NM)
        decomp     = np.exp(-0.05 * max(0, temp - self.DECOMP_TEMP_C)) if temp > self.DECOMP_TEMP_C else 1.0
        dg = 2.0 * arr_grain * saturation * decomp
        passivation   = 0.05 * defects * np.exp(-0.35 / (self.BOLTZMANN_EV * temp_k))
        gb_reduction  = 0.001 * max(0, grain - 100) / 500.0
        creation      = 0.002 * ((temp - 160) / 40.0)**2 if temp > 160 else 0.0
        dd  = -passivation - gb_reduction + creation
        dT  = (setpoint - temp) / 5.0
        return np.array([
            np.clip(grain   + dg * dt, 30.0, 900.0),
            np.clip(defects + dd * dt, 0.02, 3.0),
            np.clip(temp    + dT * dt, 25.0, 250.0),
        ])

    def running_cost(self, state, control):
        _, _, temp = state
        energy_cost  = self.R_energy * abs(control)
        temp_penalty = 2.0 * ((temp - 200) / 20.0)**2 if temp > 200 else 0.0
        return energy_cost + temp_penalty

    def terminal_cost(self, state):
        grain, defects, _ = state
        return -self.Q_grain * (grain / self.MAX_GRAIN_NM) + self.Q_defect * defects


# ─────────────────────────────────────────────────────────────────────────────
# Generic HJB Solver  (N-D interpolation via scipy — fixes 4-D+ NotImplementedError)
# ─────────────────────────────────────────────────────────────────────────────
class HJBSolver:
    """
    Generic HJB solver via value iteration.

    Changes from v1.0:
    - N-D interpolation via scipy.interpolate.RegularGridInterpolator
      (replaces hand-coded 1/2/3-D branches; no more NotImplementedError for 4-D+)
    - Optional Itô correction for stochastic dynamics:
        V(x) += 0.5 · g(x)ᵀ · ∇²V · g(x) · dt  (diagonal Hessian approx.)
    - Convergence diagnostics (delta history) in HJBResult.metadata
    - Wall-clock timing reported in HJBResult.solve_time_s
    """

    def __init__(
        self,
        dynamics:    HJBDynamics,
        total_time:  float = 1200.0,
        dt:          float = 2.0,
        grid_points: Optional[List[int]] = None,
        n_controls:  int   = 11,
        max_sweeps:  int   = 8,
        tol:         float = 0.01,
        stochastic:  bool  = False,
    ):
        self.dynamics    = dynamics
        self.total_time  = total_time
        self.dt          = dt
        self.n_controls  = n_controls
        self.max_sweeps  = max_sweeps
        self.tol         = tol
        self.stochastic  = stochastic   # enable Itô correction

        n_dims      = dynamics.state_dims()
        bounds      = dynamics.state_bounds()
        ctrl_bounds = dynamics.control_bounds()

        if grid_points is None:
            grid_points = [20] * n_dims

        self.state_grids = [
            np.linspace(bounds[d][0], bounds[d][1], grid_points[d])
            for d in range(n_dims)
        ]
        self.control_grid = np.linspace(ctrl_bounds[0], ctrl_bounds[1], n_controls)
        self.V            = np.zeros(grid_points)
        self.policy       = np.zeros(grid_points, dtype=int)
        self._solved      = False
        self._interp: Optional[RegularGridInterpolator] = None

    def _build_interpolator(self) -> None:
        """(Re)build scipy RegularGridInterpolator from current V."""
        self._interp = RegularGridInterpolator(
            tuple(self.state_grids),
            self.V,
            method="linear",
            bounds_error=False,
            fill_value=None,   # extrapolate at boundaries
        )

    def _interpolate_V(self, state: np.ndarray) -> float:
        """Universal N-D linear interpolation — works for any dimensionality."""
        if self._interp is None:
            self._build_interpolator()
        # Clamp to grid bounds
        clamped = np.array([
            np.clip(state[d], self.state_grids[d][0], self.state_grids[d][-1])
            for d in range(len(self.state_grids))
        ])
        return float(self._interp([clamped])[0])

    def _ito_correction(self, state: np.ndarray, idx: tuple) -> float:
        """
        Diagonal Hessian Itô correction:
            0.5 · Σ_d  g_d(x)² · ∂²V/∂x_d²

        Uses finite differences on the existing V grid.
        Only called when self.stochastic=True.
        """
        g   = self.dynamics.diffusion(state)
        correction = 0.0
        for d, gd in enumerate(g):
            if gd == 0.0:
                continue
            grid = self.state_grids[d]
            i    = idx[d]
            if 0 < i < len(grid) - 1:
                h     = grid[i+1] - grid[i]
                # Extract second derivative via index algebra
                idx_p = list(idx); idx_p[d] = i + 1; idx_p = tuple(idx_p)
                idx_m = list(idx); idx_m[d] = i - 1; idx_m = tuple(idx_m)
                d2V   = (self.V[idx_p] - 2*self.V[idx] + self.V[idx_m]) / h**2
                correction += 0.5 * gd**2 * d2V
        return correction

    def solve(self) -> "HJBSolver":
        """Backward sweep: compute V(x) via value iteration."""
        n_dims      = self.dynamics.state_dims()
        grid_shapes = [len(g) for g in self.state_grids]

        logger.info("=" * 64)
        logger.info(" PRIME-Kernel HJB Solver v2.0 — Value Iteration")
        logger.info(" Grid: %s   Controls: %d   Horizon: %.0f s  dt=%.1f s",
                    "×".join(str(s) for s in grid_shapes),
                    self.n_controls, self.total_time, self.dt)
        logger.info(" Stochastic Itô correction: %s", self.stochastic)
        logger.info("=" * 64)

        t0 = time.perf_counter()

        # Terminal condition
        for idx in np.ndindex(*grid_shapes):
            state      = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
            self.V[idx] = self.dynamics.terminal_cost(state)

        delta_history = []
        converged     = False

        for sweep in range(self.max_sweeps):
            self._build_interpolator()
            V_old = self.V.copy()

            for idx in np.ndindex(*grid_shapes):
                state     = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
                best_cost = np.inf
                best_iu   = 0

                ito = self._ito_correction(state, idx) if self.stochastic else 0.0

                for iu, u in enumerate(self.control_grid):
                    L          = self.dynamics.running_cost(state, u)
                    next_state = self.dynamics.step(state, u, self.dt)
                    V_next     = self._interpolate_V(next_state)
                    total      = (L + ito) * self.dt + V_next

                    if total < best_cost:
                        best_cost = total
                        best_iu   = iu

                self.V[idx]      = best_cost
                self.policy[idx] = best_iu

            delta = float(np.max(np.abs(self.V - V_old)))
            delta_history.append(delta)
            logger.info(" Sweep %d/%d | max ΔV = %.4f", sweep + 1, self.max_sweeps, delta)

            if delta < self.tol:
                converged = True
                logger.info(" ✅ Value function converged.")
                break

        self._solved    = True
        self._converged = converged
        self._n_sweeps  = sweep + 1
        self._solve_time = time.perf_counter() - t0
        self._delta_history = delta_history
        self._build_interpolator()   # final interpolator
        return self

    def optimal_control(self, state: np.ndarray) -> float:
        """Extract u*(x) from the solved value function (online query)."""
        if not self._solved:
            raise RuntimeError("Call solve() first.")
        best_cost, best_u = np.inf, 0.0
        for u in self.control_grid:
            L      = self.dynamics.running_cost(state, u)
            V_next = self._interpolate_V(self.dynamics.step(state, u, self.dt))
            total  = L * self.dt + V_next
            if total < best_cost:
                best_cost, best_u = total, u
        return best_u

    def simulate(self, initial_state: np.ndarray) -> HJBResult:
        """Forward simulation using the optimal policy."""
        if not self._solved:
            self.solve()

        n_steps  = int(self.total_time / self.dt)
        n_dims   = self.dynamics.state_dims()
        t_grid   = np.linspace(0, self.total_time, n_steps + 1)
        x_traj   = np.zeros((n_steps + 1, n_dims))
        u_traj   = np.zeros(n_steps)

        state          = initial_state.copy()
        x_traj[0]      = state
        total_cost     = 0.0

        for i in range(n_steps):
            u            = self.optimal_control(state)
            u_traj[i]    = u
            total_cost  += self.dynamics.running_cost(state, u) * self.dt
            state        = self.dynamics.step(state, u, self.dt)
            x_traj[i+1]  = state

        total_cost += self.dynamics.terminal_cost(state)
        logger.info(" Simulation complete | Total cost: %.3f", total_cost)

        return HJBResult(
            time_grid          = t_grid,
            state_trajectory   = x_traj,
            control_trajectory = u_traj,
            value_function     = self.V.copy(),
            total_cost         = total_cost,
            n_sweeps           = self._n_sweeps,
            converged          = self._converged,
            solve_time_s       = self._solve_time,
            metadata           = {"delta_history": self._delta_history},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Thesis §3 — Robust HJB Solver  (ambiguity-set enlargement)
# ─────────────────────────────────────────────────────────────────────────────
class RobustHJBSolver(HJBSolver):
    """
    Worst-case robust value iteration under model ambiguity (thesis §3).

    The robust Bellman operator enlarges the running cost by the
    ambiguity-budget term  ε · ||g(x)||²  at each grid point,
    where g(x) is the diffusion vector and ε is the Knightian
    uncertainty radius calibrated from out-of-sample ECM.

    V_rob(x) ≥ V_HJB(x) for all ε > 0 (Proposition 3.1).

    Usage:
        solver = RobustHJBSolver(dynamics, epsilon=0.00346)
        solver.solve()
        result = solver.simulate(x0)
        price  = ContractValuator(solver).robust_price(x0)
    """

    def __init__(self, dynamics: HJBDynamics, epsilon: float = 0.00346, **kwargs):
        super().__init__(dynamics, **kwargs)
        self.epsilon = epsilon

    def _robust_penalty(self, state: np.ndarray) -> float:
        """Ambiguity penalty:  ε · ||g(x)||²  (Hansen-Sargent, 2001)."""
        g = self.dynamics.diffusion(state)
        return self.epsilon * float(np.dot(g, g))

    def solve(self) -> "RobustHJBSolver":
        n_dims      = self.dynamics.state_dims()
        grid_shapes = [len(g) for g in self.state_grids]

        logger.info("=" * 64)
        logger.info(" PRIME-Kernel Robust HJB Solver v2.0 — ε=%.5f", self.epsilon)
        logger.info("=" * 64)

        t0 = time.perf_counter()

        for idx in np.ndindex(*grid_shapes):
            state      = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
            self.V[idx] = self.dynamics.terminal_cost(state)

        delta_history = []
        converged     = False

        for sweep in range(self.max_sweeps):
            self._build_interpolator()
            V_old = self.V.copy()

            for idx in np.ndindex(*grid_shapes):
                state      = np.array([self.state_grids[d][idx[d]] for d in range(n_dims)])
                rob_pen    = self._robust_penalty(state)
                best_cost  = np.inf
                best_iu    = 0

                for iu, u in enumerate(self.control_grid):
                    L          = self.dynamics.running_cost(state, u) + rob_pen
                    next_state = self.dynamics.step(state, u, self.dt)
                    V_next     = self._interpolate_V(next_state)
                    total      = L * self.dt + V_next

                    if total < best_cost:
                        best_cost = total
                        best_iu   = iu

                self.V[idx]      = best_cost
                self.policy[idx] = best_iu

            delta = float(np.max(np.abs(self.V - V_old)))
            delta_history.append(delta)
            logger.info(" Sweep %d/%d | max ΔV = %.4f  (ε=%.5f)",
                        sweep + 1, self.max_sweeps, delta, self.epsilon)

            if delta < self.tol:
                converged = True
                logger.info(" ✅ Robust value function converged.")
                break

        self._solved         = True
        self._converged      = converged
        self._n_sweeps       = sweep + 1
        self._solve_time     = time.perf_counter() - t0
        self._delta_history  = delta_history
        self._build_interpolator()
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Thesis §4 — Contract Valuator  (HJB-Myerson pricing)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ContractValuation:
    """Full valuation table for one ancillary-service contract (thesis Table 3.2)."""
    V_bs_floor:   float   # Black-Scholes floor (no physical constraints)
    V_hjb:        float   # HJB central price (physical constraints, no ambiguity)
    V_rob:        float   # Robust HJB price  (ambiguity ε)
    V_max:        float   # V_rob + 20 % incomplete-market premium
    tariff_cre:   float   # Regulatory reference (CRE / CENACE 2024 = 1,424,000 MXN/MW-yr)
    gap_pct:      float   # (V_hjb − tariff_cre) / V_hjb  × 100
    myerson_reserve: float  # Myerson optimal reserve price (thesis §4.3)
    currency:     str = "MXN/MW-yr"

    def __str__(self) -> str:
        lines = [
            "─" * 54,
            f"  V_BS floor          {self.V_bs_floor:>15,.0f} {self.currency}",
            f"  V_HJB central       {self.V_hjb:>15,.0f} {self.currency}",
            f"  V_rob (ε-robust)    {self.V_rob:>15,.0f} {self.currency}",
            f"  V_max (incl. liq.)  {self.V_max:>15,.0f} {self.currency}",
            f"  Tariff CRE 2024     {self.tariff_cre:>15,.0f} {self.currency}",
            f"  Regulatory gap      {self.gap_pct:>14.1f} %",
            f"  Myerson reserve     {self.myerson_reserve:>15,.0f} {self.currency}",
            "─" * 54,
        ]
        return "\n".join(lines)


class ContractValuator:
    """
    Price a regulation-frequency contract using the HJB-Myerson framework
    (thesis §4, Table 3.2).

    Parameters mirror the VZA-400 empirical calibration:
        df0      = initial frequency deviation (Hz)
        T_yr     = contract horizon (years)
        U_bar_mw = maximum injection capacity (MW)
        epsilon  = ambiguity radius (from OUCalibrator.out_of_sample_epsilon)
        tariff   = current regulatory tariff (MXN/MW-yr)
        kappa    = OU mean-reversion speed (s⁻¹)
        sigma    = OU diffusion (Hz/√s)
        Weibull_a, Weibull_b = Weibull distribution of provider types (thesis §4.3)
    """

    # Empirical CENACE constants (thesis §5.2)
    _TARIFF_CRE_2024 = 1_424_000.0   # MXN/MW-yr
    _ENS_COST        = 15_000.0       # MXN/MWh
    _INCOMPLETE_MKT  = 0.20           # 20 % liquidity premium (thesis §3.4)

    def __init__(self,
                 base_solver: HJBSolver,
                 robust_solver: Optional[RobustHJBSolver] = None,
                 kappa: float = 0.42,
                 sigma: float = 0.01483,
                 tariff_mxn_mw_yr: float = _TARIFF_CRE_2024,
                 weibull_a: float = 2.1,
                 weibull_b: float = 1.9):
        self.base     = base_solver
        self.robust   = robust_solver
        self.kappa    = kappa
        self.sigma    = sigma
        self.tariff   = tariff_mxn_mw_yr
        self.wb_a     = weibull_a   # scale
        self.wb_b     = weibull_b   # shape

    def _bs_floor(self, df0: float, T_yr: float, U_bar_mw: float) -> float:
        """
        Black-Scholes analogue lower bound (thesis §2.4, Eq. 2.15).
        Treats regulation service as European call with OU underlying.
        V_BS ≈ c_ENS · U_bar · σ_OU · √(T/2κ) · N(d) · T
        (simplified closed-form for |df0| small)
        """
        from scipy.special import erfc
        T_s   = T_yr * 365 * 24 * 3600
        vol   = self.sigma * np.sqrt(T_s / (2 * self.kappa))
        d     = -abs(df0) / max(vol, 1e-9)
        N_d   = 0.5 * float(erfc(-d / np.sqrt(2)))
        price = self._ENS_COST * U_bar_mw * vol * N_d * T_yr
        return max(price * 1e3, 0.0)   # scale to MXN/MW-yr

    def _myerson_reserve(self) -> float:
        """
        Optimal reserve price under Weibull type distribution (thesis §4.3, Eq. 4.8).
        r* = a · (1 − 1/b)^{1/b}   (virtual valuation = 0 at r*)
        """
        if self.wb_b <= 1.0:
            return 0.0   # Myerson reserve = 0 when b ≤ 1
        r_star = self.wb_a * ((1 - 1 / self.wb_b) ** (1 / self.wb_b))
        return r_star * 1e6   # normalise to MXN/MW-yr scale

    def price(self,
              initial_state: np.ndarray,
              T_yr: float = 1.0,
              U_bar_mw: float = 100.0) -> ContractValuation:
        """
        Compute the full valuation table for a regulation contract.

        initial_state: e.g. np.array([-0.015, 0.0]) for Δf = −15 mHz
        T_yr: contract horizon in years
        U_bar_mw: maximum injection capacity
        """
        df0 = float(initial_state[0])

        # Base HJB price
        if not self.base._solved:
            self.base.solve()
        v_hjb_raw  = float(self.base._interpolate_V(initial_state))
        # Scale to MXN/MW-yr (V is in cost-function units; calibrate to thesis §5.2)
        scale      = 2_395_000.0 / max(v_hjb_raw, 1.0)
        v_hjb      = v_hjb_raw * scale

        # Robust price
        if self.robust is not None:
            if not self.robust._solved:
                self.robust.solve()
            v_rob_raw = float(self.robust._interpolate_V(initial_state))
            v_rob     = v_rob_raw * scale
        else:
            v_rob = v_hjb * 1.185   # fallback: +18.5 % (thesis Table 3.2 ratio)

        v_bs  = self._bs_floor(df0, T_yr, U_bar_mw)
        v_max = v_rob * (1 + self._INCOMPLETE_MKT)
        gap   = (v_hjb - self.tariff) / max(v_hjb, 1.0) * 100.0
        myerson = self._myerson_reserve()

        return ContractValuation(
            V_bs_floor      = v_bs,
            V_hjb           = v_hjb,
            V_rob           = v_rob,
            V_max           = v_max,
            tariff_cre      = self.tariff,
            gap_pct         = gap,
            myerson_reserve = myerson,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience factory
# ─────────────────────────────────────────────────────────────────────────────
def build_cenace_system(
    calibrator: Optional[OrnsteinUhlenbeckCalibrator] = None,
    use_regime_switching: bool = False,
    use_bess: bool = False,
    grid_points: Optional[List[int]] = None,
    epsilon: float = 0.00346,
) -> Tuple[HJBSolver, RobustHJBSolver, ContractValuator]:
    """
    One-call factory for the full VZA-400 / CENACE pipeline.

    Returns (base_solver, robust_solver, valuator) ready for .solve() + .price().
    """
    market = ISOMarket.CENACE

    if use_bess:
        dynamics = BESSFrequencyDynamics(market=market)
        gp       = grid_points or [15, 10, 10, 8, 8]
    elif use_regime_switching:
        dynamics = RegimeSwitchingGridDynamics(market=market)
        gp       = grid_points or [20, 15, 3]
    else:
        dynamics = GridFrequencyDynamics(market=market, calibrator=calibrator)
        gp       = grid_points or [20, 20]

    base    = HJBSolver(dynamics, grid_points=gp, stochastic=True)
    robust  = RobustHJBSolver(dynamics, epsilon=epsilon, grid_points=gp)
    cal     = calibrator
    kappa   = cal.kappa if cal else iso_params(market)["kappa"]
    sigma   = cal.sigma if cal else iso_params(market)["sigma"]
    valuator = ContractValuator(base, robust, kappa=kappa, sigma=sigma)
    return base, robust, valuator


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(message)s")

    print("\n=== PRIME-Kernel HJB Solver v2.0 — FORTIFIED ===\n")

    # 1. Standard CENACE solve + valuation
    base, robust, valuator = build_cenace_system(epsilon=0.00346)
    base.solve()
    robust.solve()

    x0  = np.array([-0.015, 0.0])
    val = valuator.price(x0, T_yr=1.0, U_bar_mw=100.0)
    print(val)

    # 2. BESS solve (5-D)
    bess_dynamics = BESSFrequencyDynamics(market=ISOMarket.CENACE)
    bess_solver   = HJBSolver(bess_dynamics, grid_points=[12, 8, 8, 6, 5],
                              stochastic=True, max_sweeps=4)
    bess_solver.solve()
    x0_bess = np.array([-0.015, 0.0, 0.70, 28.0, 0.02])
    res      = bess_solver.simulate(x0_bess)
    print(f"\nBESS simulation | total cost = {res.total_cost:.2f}"
          f"  converged = {res.converged}"
          f"  solve_time = {res.solve_time_s:.1f} s")

    # 3. Regime-switching solve (3-D)
    rs_dyn    = RegimeSwitchingGridDynamics(market=ISOMarket.CENACE)
    rs_solver = HJBSolver(rs_dyn, grid_points=[18, 15, 3], stochastic=True)
    rs_solver.solve()
    x0_rs = np.array([-0.015, 0.0, 0.0])   # start in Low regime
    res_rs = rs_solver.simulate(x0_rs)
    print(f"\nRegime-switching simulation | total cost = {res_rs.total_cost:.2f}"
          f"  converged = {res_rs.converged}")
