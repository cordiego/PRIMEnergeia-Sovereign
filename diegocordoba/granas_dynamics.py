"""
Granas PV-HB Dynamics
=====================================================
Photovoltaic-Haber-Bosch multi-physics integration for the PRIME-Kernel.
Implements the mathematical specification for Granas Core.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple
from hjb_solver_fortified import HJBDynamics

class GranasDynamics(HJBDynamics):
    """
    Granas PV-HB integrated state-space model.
    State: [E_PV (MW), T_r (°C), P_r (bar), S_H2 (0.0-1.0)]
    Control: u_hb (MW) -> Power dispatched to Haber-Bosch reactor.
    """

    def __init__(self, 
                 kappa_pv: float = 0.3,
                 mu_pv: float = 50.0,
                 sigma_pv: float = 2.0,
                 lambda_grid: float = 1200.0, # Grid revenue per MWh
                 lambda_nh3: float = 5000.0,  # Value of green ammonia
                 c_temp: float = 10.0,
                 c_h2: float = 500.0):
        self.kappa_pv = kappa_pv
        self.mu_pv = mu_pv
        self.sigma_pv = sigma_pv
        self.lambda_grid = lambda_grid
        self.lambda_nh3 = lambda_nh3
        self.c_temp = c_temp
        self.c_h2 = c_h2
        
        # Thermochemical parameters
        self.C_th = 50.0       # Thermal capacity
        self.k_loss = 0.05     # Thermal loss coefficient
        self.T_amb = 25.0      # Ambient temp
        self.Q_rxn = 46.2      # Exothermic heat kJ/mol
        self.alpha = 0.4       # Heating fraction of u_hb
        self.beta = 2.0        # Compression efficiency factor
        self.gamma = 0.1       # Pressure drop per mol NH3
        self.k_leak = 0.01     # Pressure leak rate

    def state_dims(self) -> int: 
        return 4

    def state_bounds(self) -> List[Tuple[float, float]]:
        return [
            (0.0, 100.0),   # E_PV (MW)
            (300.0, 550.0), # T_r (°C)
            (100.0, 300.0), # P_r (bar)
            (0.1, 1.0)      # S_H2 (SoC)
        ]

    def control_bounds(self) -> Tuple[float, float]:
        # Technically u_hb bounds depend on E_PV, but we use an absolute max bound
        # and enforce E_PV constraint in the step function.
        return (0.0, 100.0) 

    def _ammonia_kinetics(self, T_r: float, P_r: float) -> float:
        """Modified Temkin-Pyzhev kinetics proxy"""
        # Simplified activation energy and pressure dependence
        T_k = T_r + 273.15
        k_0 = 1e6
        E_a = 100e3 # J/mol
        R = 8.314
        rate = k_0 * np.exp(-E_a / (R * T_k)) * (P_r ** 0.5)
        return float(np.clip(rate, 0.0, 10.0))

    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        E_PV, T_r, P_r, S_H2 = state
        
        # Enforce control constraint: u_hb cannot exceed available E_PV
        u_hb = float(np.clip(control, 0.0, E_PV))

        # 1. E_PV Dynamics (OU Process drift)
        dE_PV = self.kappa_pv * (self.mu_pv - E_PV)
        new_E_PV = np.clip(E_PV + dE_PV * dt, 0.0, 100.0)

        # 2. Reactor Temperature
        R_nh3 = self._ammonia_kinetics(T_r, P_r)
        dT_r = (self.alpha * u_hb) / self.C_th - self.k_loss * (T_r - self.T_amb) + self.Q_rxn * R_nh3
        new_T_r = np.clip(T_r + dT_r * dt, 300.0, 550.0)

        # 3. Reactor Pressure
        dP_r = self.beta * (1 - self.alpha) * u_hb - self.gamma * R_nh3 - self.k_leak * P_r
        new_P_r = np.clip(P_r + dP_r * dt, 100.0, 300.0)

        # 4. Hydrogen Buffer
        eta_h2 = 0.05 # H2 depletion factor per unit of NH3
        dS_H2 = -eta_h2 * R_nh3
        new_S_H2 = np.clip(S_H2 + dS_H2 * dt, 0.1, 1.0)

        return np.array([new_E_PV, new_T_r, new_P_r, new_S_H2])

    def diffusion(self, state: np.ndarray) -> np.ndarray:
        """Stochastic noise matrix for the HJB Itô correction."""
        # Only E_PV is stochastic in this formulation
        return np.array([self.sigma_pv, 0.0, 0.0, 0.0])

    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        E_PV, T_r, P_r, S_H2 = state
        u_hb = float(np.clip(control, 0.0, E_PV))
        
        u_grid = E_PV - u_hb
        grid_revenue = self.lambda_grid * u_grid
        
        R_nh3 = self._ammonia_kinetics(T_r, P_r)
        nh3_revenue = self.lambda_nh3 * R_nh3
        
        T_excess = max(0.0, T_r - 500.0) # Penalty if exceeding 500 C
        thermal_penalty = self.c_temp * (T_excess ** 2)
        
        H2_starvation = max(0.0, 0.2 - S_H2)
        h2_penalty = self.c_h2 * (H2_starvation ** 2)

        return float(-grid_revenue - nh3_revenue + thermal_penalty + h2_penalty)

    def terminal_cost(self, state: np.ndarray) -> float:
        _, _, _, S_H2 = state
        return float(-500.0 * S_H2) # Value remaining H2
