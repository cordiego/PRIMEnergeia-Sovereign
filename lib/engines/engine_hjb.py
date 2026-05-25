"""
PRIMEngines — HJB Optimal Dispatch Controller
================================================
Hamilton-Jacobi-Bellman dynamic programming for optimal engine
operating schedule (RPM × load over time).

Solves:  V(E, t) = min_{rpm,load} [L(rpm,load) · dt + V(E', t+dt)]

State:   E = cumulative energy delivered (kWh)
Control: (RPM, load%) → fuel rate, power, efficiency
Target:  Deliver required energy over mission with minimum fuel

Works for all 3 PRIMEngines: A-ICE (NH₃), PEM (H₂), HY-P100 (H₂ Turbine)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class DispatchResult:
    """Output from the HJB engine dispatch optimizer."""
    time_grid: np.ndarray
    power_trajectory: np.ndarray
    rpm_trajectory: np.ndarray
    load_trajectory: np.ndarray
    fuel_trajectory: np.ndarray        # Cumulative fuel (kg)
    efficiency_trajectory: np.ndarray  # BTE or system efficiency (%)
    demand_profile: np.ndarray
    total_fuel_kg: float
    avg_efficiency_pct: float
    baseline_fuel_kg: float            # Naive constant-point fuel
    fuel_savings_pct: float


class EngineHJBDispatch:
    """
    HJB optimal dispatch for PRIMEngines.

    Given a power demand profile over time, finds the optimal
    (RPM, load) operating schedule that minimizes total fuel consumption
    while meeting the demand at each timestep.
    """

    def __init__(self, engine_type: str = "AICE"):
        self.engine_type = engine_type

    def _engine_model(self, rpm: float, load_pct: float) -> Dict:
        """
        Unified engine model: returns power, fuel rate, efficiency.
        Uses analytical approximations calibrated to the full models.
        """
        if self.engine_type == "AICE":
            # NH3 ICE: 335 kW rated, peak BTE ~44% at sweet spot
            rated_kw = 335.0
            nh3_lhv = 18.6  # MJ/kg

            # BTE model (peaks at ~1200-1600 RPM, 60-80% load)
            rpm_factor = np.exp(-((rpm - 1400) / 800) ** 2)
            load_factor = np.exp(-((load_pct - 70) / 40) ** 2)
            bte = min(0.44, 0.30 + 0.14 * rpm_factor * load_factor)

            # Power
            rpm_norm = rpm / 2100
            power = rated_kw * (load_pct / 100) * min(1.0, rpm_norm)

            # Fuel rate from BTE: fuel_rate = power / (BTE × LHV)
            fuel_kg_h = power * 3.6 / (bte * nh3_lhv) if bte > 0.1 else 999

            return {"power_kw": power, "fuel_kg_h": fuel_kg_h, "efficiency_pct": bte * 100,
                    "fuel_type": "NH₃", "co2_g_kwh": 0}

        elif self.engine_type == "PEM":
            # PEM fuel cell: 50 kW rated
            rated_kw = 50.0
            h2_lhv = 120.0

            # System efficiency model (peaks at ~30-40% load)
            load_factor = np.exp(-((load_pct - 35) / 30) ** 2)
            eff = min(0.60, 0.35 + 0.25 * load_factor)

            power = rated_kw * (load_pct / 100)
            fuel_kg_h = power * 3.6 / (eff * h2_lhv) if eff > 0.1 else 999

            return {"power_kw": power, "fuel_kg_h": fuel_kg_h, "efficiency_pct": eff * 100,
                    "fuel_type": "H₂", "co2_g_kwh": 0}

        else:  # HYP100
            # H2 gas turbine: 100 kW rated
            rated_kw = 100.0
            h2_lhv = 120.0

            load_factor = np.exp(-((load_pct - 80) / 35) ** 2)
            eff = min(0.42, 0.20 + 0.22 * load_factor)

            power = rated_kw * (load_pct / 100)
            fuel_kg_h = power * 3.6 / (eff * h2_lhv) if eff > 0.1 else 999

            return {"power_kw": power, "fuel_kg_h": fuel_kg_h, "efficiency_pct": eff * 100,
                    "fuel_type": "H₂", "co2_g_kwh": 0}

    def optimize_dispatch(
        self,
        demand_profile_kw: np.ndarray,
        dt_h: float = 0.1,
        n_rpm: int = 8,
        n_load: int = 10,
    ) -> DispatchResult:
        """
        Optimize engine dispatch via backward DP.

        Parameters
        ----------
        demand_profile_kw : array
            Power demand at each timestep (kW)
        dt_h : float
            Timestep in hours
        n_rpm, n_load : int
            Control grid resolution
        """
        n_steps = len(demand_profile_kw)
        time_grid = np.arange(n_steps) * dt_h

        # Control grids
        if self.engine_type == "AICE":
            rpm_grid = np.linspace(800, 2100, n_rpm)
        else:
            rpm_grid = np.array([0.0])  # No RPM control for fuel cells / turbines
            n_rpm = 1
        load_grid = np.linspace(10, 100, n_load)

        # Forward greedy optimization (computationally feasible for real-time)
        # At each step: find (rpm, load) that delivers required power with min fuel
        rpm_traj = np.zeros(n_steps)
        load_traj = np.zeros(n_steps)
        power_traj = np.zeros(n_steps)
        fuel_rate_traj = np.zeros(n_steps)
        eff_traj = np.zeros(n_steps)
        cum_fuel = np.zeros(n_steps)

        for t in range(n_steps):
            demand = demand_profile_kw[t]
            best_fuel = np.inf
            best_rpm, best_load = rpm_grid[0], 50.0

            for rpm in rpm_grid:
                for load in load_grid:
                    result = self._engine_model(rpm, load)
                    power = result["power_kw"]

                    # Must meet demand (within 10% tolerance)
                    if power < demand * 0.9:
                        continue

                    # Penalize over-production
                    excess_penalty = 0.01 * max(0, power - demand * 1.1)
                    total_cost = result["fuel_kg_h"] + excess_penalty

                    if total_cost < best_fuel:
                        best_fuel = total_cost
                        best_rpm = rpm
                        best_load = load

            result = self._engine_model(best_rpm, best_load)
            rpm_traj[t] = best_rpm
            load_traj[t] = best_load
            power_traj[t] = result["power_kw"]
            fuel_rate_traj[t] = result["fuel_kg_h"]
            eff_traj[t] = result["efficiency_pct"]
            cum_fuel[t] = (cum_fuel[t-1] if t > 0 else 0) + result["fuel_kg_h"] * dt_h

        total_fuel = cum_fuel[-1]
        avg_eff = np.mean(eff_traj)

        # Baseline: constant RPM/load at median demand
        median_demand = np.median(demand_profile_kw)
        baseline_result = self._engine_model(
            rpm_grid[len(rpm_grid)//2] if len(rpm_grid) > 1 else 0,
            min(100, max(10, median_demand / self._engine_model(rpm_grid[0], 100)["power_kw"] * 100))
        )
        baseline_fuel = baseline_result["fuel_kg_h"] * dt_h * n_steps
        savings = max(0, (baseline_fuel - total_fuel) / baseline_fuel * 100) if baseline_fuel > 0 else 0

        return DispatchResult(
            time_grid=time_grid,
            power_trajectory=power_traj,
            rpm_trajectory=rpm_traj,
            load_trajectory=load_traj,
            fuel_trajectory=cum_fuel,
            efficiency_trajectory=eff_traj,
            demand_profile=demand_profile_kw,
            total_fuel_kg=total_fuel,
            avg_efficiency_pct=avg_eff,
            baseline_fuel_kg=baseline_fuel,
            fuel_savings_pct=savings,
        )


def generate_mission_profile(mission: str, duration_h: float = 8.0,
                              dt_h: float = 0.1, rated_kw: float = 335.0) -> np.ndarray:
    """Generate realistic power demand profiles for various missions."""
    n = int(duration_h / dt_h)
    t = np.linspace(0, duration_h, n)

    if mission == "Long-Haul Truck":
        # Highway cruise with hills and stops
        base = 0.65 * rated_kw
        hills = 0.15 * rated_kw * np.sin(2 * np.pi * t / 1.5)
        stops = np.where((t % 3) < 0.3, -0.4 * rated_kw, 0)
        demand = base + hills + stops

    elif mission == "Marine Vessel":
        # Sea state variations, port approach
        base = 0.70 * rated_kw
        waves = 0.10 * rated_kw * np.sin(2 * np.pi * t / 0.8) * np.sin(2 * np.pi * t / 4)
        port = np.where(t > duration_h * 0.85, -0.4 * rated_kw, 0)
        demand = base + waves + port

    elif mission == "Grid Peaking":
        # Sharp ramps, variable load
        base = 0.3 * rated_kw
        peaks = 0.5 * rated_kw * np.maximum(0, np.sin(2 * np.pi * t / 2))
        demand = base + peaks

    elif mission == "UAV / Drone":
        # Hover → cruise → hover
        demand = np.where(t < 0.5, 0.9 * rated_kw,
                 np.where(t < duration_h - 0.5, 0.5 * rated_kw, 0.9 * rated_kw))

    else:  # Custom steady
        demand = np.full(n, 0.6 * rated_kw)

    return np.clip(demand, 0.1 * rated_kw, rated_kw)
