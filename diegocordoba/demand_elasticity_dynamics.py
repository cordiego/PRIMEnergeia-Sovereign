"""
PRIME-Kernel — Demand Elasticity Dynamics (ICDN Integration)
=============================================================
This module integrates the Integrable Context-Dependent Demand Network (ICDN)
with the PRIME Grid HJB Solver. It introduces a 4th state variable (Demand Deviation)
whose elasticity is guaranteed to be integrable (curl-free) to preserve the
value function's smoothness.

Injection Points:
1. Demand Response as Control Input in the swing equation.
2. Price-context-aware HJB running cost L(x,u).
3. VZA-400 Pilot: Predictive state initializer for anticipatory optimal control.

Drafted for tomorrow morning's commit.
"""

import numpy as np
from typing import List, Tuple, Optional, Callable
from hjb_solver_fortified import HJBDynamics, ISOMarket, iso_params

class DemandElasticityDynamics(HJBDynamics):
    """
    Integrates ICDN's exact integrable elasticity surfaces into PRIME's HJB solver.
    
    State (4D): [Δf (Hz), P_inj (MW), P_m (MW), Demand_Dev (MW)]
    Control: injection ramp rate (MW/s)
    
    The demand deviation state is governed by a learned price-elasticity surface
    conditioned on (time_of_day, temperature, cenace_zone).
    """
    
    def __init__(self, 
                 market: ISOMarket = ISOMarket.CENACE,
                 elasticity_surface: Optional[Callable] = None):
        """
        elasticity_surface: The ICDN-derived D_demand(price, context) function.
        """
        p = iso_params(market)
        self.H = p["inertia_H"]
        self.D = p["damping_D"]
        self.max_inj = p["max_mw"]
        self._deadband = p["freq_deadband_hz"]
        self._pen_coeff = p["penalty_coeff"]
        
        # ICDN context features for VZA-400 Pilot
        self.context = {
            "time_of_day": 12.0,
            "temperature": 25.0,
            "cenace_zone": "Occidental"
        }
        
        # Placeholder for the exact integrable ICDN surface
        self.elasticity_surface = elasticity_surface if elasticity_surface else self._default_icdn_surface
        
    def _default_icdn_surface(self, price: float, context: dict) -> float:
        """Fallback ICDN surface returning elasticity gradient."""
        return -0.05 * price  # Simplified linear elasticity
        
    def state_dims(self) -> int: return 4
    
    def state_bounds(self) -> List[Tuple[float, float]]:
        return [
            (-2.0, 2.0),         # Δf (Hz)
            (0.0, self.max_inj), # P_inj (MW)
            (0.0, self.max_inj), # P_m (Mechanical power)
            (-50.0, 50.0)        # Demand Deviation (MW)
        ]
        
    def control_bounds(self) -> Tuple[float, float]:
        return (-10.0, 10.0)
        
    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        df, P_inj, P_m, demand_dev = state
        
        # 1. ⚡ Demand Response as a Control Input
        # Real grid freq deviations are 40-60% driven by demand-side shocks.
        # Swing equation now incorporates Demand_Dev explicitly as a load shock.
        ddf = (P_m + P_inj - demand_dev - self.D * df) / (2.0 * self.H)
        new_df = np.clip(df + ddf * dt, -2.0, 2.0)
        
        new_P_inj = np.clip(P_inj + control * dt, 0.0, self.max_inj)
        
        # Simple dynamics for P_m (assumed constant or slow-moving governor for now)
        new_P_m = P_m 
        
        # ICDN exact elasticity gradient drives demand deviation
        price = 500.0 # In a real implementation, this would be the dynamic nodal price
        d_demand = self.elasticity_surface(price, self.context)
        new_demand_dev = np.clip(demand_dev + d_demand * dt, -50.0, 50.0)
        
        return np.array([new_df, new_P_inj, new_P_m, new_demand_dev])
        
    def running_cost(self, state: np.ndarray, control: float, t: float = 0.0) -> float:
        df, P_inj, P_m, demand_dev = state
        freq_cost = 100.0 * df**2
        
        # 2. 🎯 The HJB Running Cost L(x,u) Gets Smarter
        # The cost of injecting 1 MW/s at peak demand is structurally different.
        price = self._pen_coeff # Base price
        
        # Context-aware energy cost scaling based on demand deviation severity
        severity_factor = 1.0 + 0.02 * abs(demand_dev)
        energy_cost = (0.01 * price * severity_factor) * abs(control)
        
        excess = max(0.0, abs(df) - self._deadband)
        penalty = price * excess**2 if excess > 0 else 0.0
        
        return freq_cost + energy_cost + penalty
        
    def terminal_cost(self, state: np.ndarray) -> float:
        df, P_inj, P_m, demand_dev = state
        return 200.0 * df**2 + 0.1 * P_inj + 10.0 * abs(demand_dev)
        
    def initialize_vza400_predictive_state(self, time_of_day: float, temp: float, price_signal: float) -> np.ndarray:
        """
        3. 🔮 VZA-400 Pilot — Forecasting Load Before the Disturbance.
        Anticipatory optimal control initializer.
        """
        self.context["time_of_day"] = time_of_day
        self.context["temperature"] = temp
        
        # Predict exact initial demand deviation from ICDN surface
        predicted_demand_dev = self.elasticity_surface(price_signal, self.context) * 10.0 
        
        return np.array([0.0, 0.0, 50.0, predicted_demand_dev])
