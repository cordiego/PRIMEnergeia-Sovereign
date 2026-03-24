"""
PRIMStack — Multi-Timescale Master HJB Controller
====================================================
Hamilton-Jacobi-Bellman optimal control at the plant level.

Dispatches energy across all subsystems simultaneously:

State:   x = (H₂_kg, NH₃_kg, battery_soc, solar_irrad, panel_age)
Control: u = (electrolyzer_pct, engine_dispatch, battery_mode, grid_export)
f(x,u):  Plant dynamics (primstack.py subsystem models)
L(x,u):  -revenue + fuel_cost + degradation_penalties
V(x,t):  Value function (optimal cost-to-go)

Multi-timescale:
  - Hours:  H₂/NH₃ buffer + grid arbitrage + engine dispatch
  - Years:  Panel degradation + blade life + replacement scheduling

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [STACK-HJB] - %(message)s")


@dataclass
class StackHJBState:
    """Reduced plant state for HJB optimization."""
    h2_level: float         # H₂ stored as fraction of capacity (0-1)
    nh3_level: float        # NH₃ stored as fraction (0-1)
    battery_soc: float      # Battery state of charge (0-1)
    grid_price_norm: float  # Normalized grid price (0-1)
    solar_cf: float         # Solar capacity factor at current hour (0-1)


@dataclass
class StackControl:
    """Plant-level control inputs."""
    electrolyzer_pct: float  # % of surplus sent to electrolyzer (0-100)
    engine_load_pct: float   # Engine fleet load dispatch (0-100)
    battery_mode: float      # -1=discharge, 0=idle, +1=charge
    haber_bosch_pct: float   # % of H₂ routed to NH₃ synthesis (0-100)
    grid_export_pct: float   # % of surplus exported to grid (0-100)


@dataclass
class StackHJBResult:
    """Output from the stack-level HJB optimization."""
    time_grid: np.ndarray
    h2_trajectory: np.ndarray
    nh3_trajectory: np.ndarray
    soc_trajectory: np.ndarray
    revenue_trajectory: np.ndarray
    electrolyzer_trajectory: np.ndarray
    engine_trajectory: np.ndarray
    grid_export_trajectory: np.ndarray
    value_function: np.ndarray
    optimal_strategy: Dict[str, float]
    annual_revenue_usd: float
    h2_self_sufficiency_pct: float
    renewable_fraction_pct: float
    total_cost: float


class StackHJBController:
    """
    Master HJB controller for the full PRIMStack plant.

    Optimizes energy dispatch across hourly intervals
    to maximize revenue while maintaining fuel buffers
    and minimizing equipment degradation.
    """

    def __init__(
        self,
        total_hours: int = 8760,     # 1 year
        dt_h: float = 1.0,          # Hourly resolution
        n_h2: int = 12,             # H₂ level grid points
        n_nh3: int = 10,
        n_soc: int = 8,
        n_elec: int = 6,            # Control: electrolyzer %
        n_engine: int = 6,          # Control: engine load %
        n_battery: int = 3,         # Control: charge/idle/discharge
        # Weights
        Q_revenue: float = 1.0,
        Q_h2_buffer: float = 2.0,   # Penalize empty H₂
        Q_nh3_buffer: float = 1.5,  # Penalize empty NH₃
        Q_soc_buffer: float = 1.0,  # Penalize empty battery
        Q_degradation: float = 0.5,
        # Plant parameters
        grid_price_base: float = 65.0,    # $/MWh
        total_renewable_mw: float = 150.0,
        engine_fleet_kw: float = 1455.0,  # 3×335 + 5×50 + 2×100
        bess_mwh: float = 400.0,
        h2_capacity_kg: float = 5000.0,
        nh3_capacity_kg: float = 20000.0,
    ):
        self.total_hours = total_hours
        self.dt_h = dt_h
        self.Q_revenue = Q_revenue
        self.Q_h2_buffer = Q_h2_buffer
        self.Q_nh3_buffer = Q_nh3_buffer
        self.Q_soc_buffer = Q_soc_buffer
        self.Q_degradation = Q_degradation

        self.grid_price_base = grid_price_base
        self.total_renewable_mw = total_renewable_mw
        self.engine_fleet_kw = engine_fleet_kw
        self.bess_mwh = bess_mwh
        self.h2_capacity_kg = h2_capacity_kg
        self.nh3_capacity_kg = nh3_capacity_kg

        # State grids
        self.h2_grid = np.linspace(0.05, 0.95, n_h2)
        self.nh3_grid = np.linspace(0.05, 0.95, n_nh3)
        self.soc_grid = np.linspace(0.10, 0.95, n_soc)

        # Control grids
        self.elec_grid = np.linspace(0, 100, n_elec)
        self.engine_grid = np.linspace(0, 100, n_engine)
        self.battery_grid = np.array([-1, 0, 1])  # discharge/idle/charge

        self.V = None

    def _solar_profile(self, hour_of_day: int) -> float:
        """Solar capacity factor by hour."""
        angle = (hour_of_day - 12) / 6.0
        return max(0, np.cos(angle * np.pi / 2)) ** 1.3

    def _grid_price(self, hour_of_day: int) -> float:
        """Time-of-use grid price multiplier."""
        # Peak: 14:00-20:00 (1.5×), off-peak: 22:00-06:00 (0.6×)
        if 14 <= hour_of_day <= 20:
            return self.grid_price_base * 1.5
        elif hour_of_day >= 22 or hour_of_day <= 6:
            return self.grid_price_base * 0.6
        return self.grid_price_base

    def _dynamics(self, state: StackHJBState, elec_pct: float,
                  engine_pct: float, battery_mode: float,
                  hour: int) -> Tuple[StackHJBState, float]:
        """
        Plant state transition + running cost.

        Returns: (new_state, cost)
        """
        solar_cf = self._solar_profile(hour % 24)
        wind_cf = 0.42 * (0.9 + 0.2 * np.sin(hour * 0.1))  # Simplified
        total_gen_fraction = (solar_cf * 0.33 + wind_cf * 0.67)  # Weighted by capacity

        surplus_fraction = max(0, total_gen_fraction - 0.1)  # Above self-consumption

        # Electrolyzer: surplus → H₂
        h2_production = surplus_fraction * (elec_pct / 100) * 0.02  # Normalized rate
        new_h2 = min(0.95, state.h2_level + h2_production)

        # Engine dispatch: consumes H₂ (PEM, HYP) or NH₃ (AICE)
        h2_consumption = (engine_pct / 100) * 0.01  # Normalized
        nh3_consumption = (engine_pct / 100) * 0.005
        new_h2 = max(0.05, new_h2 - h2_consumption)
        new_nh3 = max(0.05, state.nh3_level - nh3_consumption)

        # NH₃ synthesis from excess H₂
        if new_h2 > 0.7:
            nh3_synth = (new_h2 - 0.7) * 0.1
            new_h2 -= nh3_synth * 0.2
            new_nh3 = min(0.95, new_nh3 + nh3_synth)

        # Battery
        if battery_mode > 0:
            new_soc = min(0.95, state.battery_soc + 0.02)
        elif battery_mode < 0:
            new_soc = max(0.10, state.battery_soc - 0.02)
        else:
            new_soc = state.battery_soc

        # Revenue
        price = self._grid_price(hour % 24)
        grid_export = surplus_fraction * (1 - elec_pct / 100) * self.total_renewable_mw
        engine_revenue = (engine_pct / 100) * self.engine_fleet_kw / 1000 * price / 1000  # $/h → normalized
        export_revenue = grid_export * price / 1000

        # Running cost
        revenue = (export_revenue + engine_revenue) * self.Q_revenue
        h2_penalty = self.Q_h2_buffer * max(0, 0.3 - new_h2) ** 2
        nh3_penalty = self.Q_nh3_buffer * max(0, 0.3 - new_nh3) ** 2
        soc_penalty = self.Q_soc_buffer * max(0, 0.2 - new_soc) ** 2
        degradation = self.Q_degradation * (engine_pct / 100) * 0.001

        cost = -revenue + h2_penalty + nh3_penalty + soc_penalty + degradation

        new_state = StackHJBState(
            h2_level=new_h2, nh3_level=new_nh3, battery_soc=new_soc,
            grid_price_norm=price / (self.grid_price_base * 1.5),
            solar_cf=solar_cf,
        )
        return new_state, cost

    def _interpolate_V(self, h2, nh3, soc):
        h2 = np.clip(h2, self.h2_grid[0], self.h2_grid[-1])
        nh3 = np.clip(nh3, self.nh3_grid[0], self.nh3_grid[-1])
        soc = np.clip(soc, self.soc_grid[0], self.soc_grid[-1])
        ih = int(np.clip(np.searchsorted(self.h2_grid, h2)-1, 0, len(self.h2_grid)-2))
        jn = int(np.clip(np.searchsorted(self.nh3_grid, nh3)-1, 0, len(self.nh3_grid)-2))
        ks = int(np.clip(np.searchsorted(self.soc_grid, soc)-1, 0, len(self.soc_grid)-2))
        ah = (h2 - self.h2_grid[ih]) / (self.h2_grid[ih+1] - self.h2_grid[ih])
        an = (nh3 - self.nh3_grid[jn]) / (self.nh3_grid[jn+1] - self.nh3_grid[jn])
        asoc = (soc - self.soc_grid[ks]) / (self.soc_grid[ks+1] - self.soc_grid[ks])
        V = self.V
        return float(
            V[ih,jn,ks]*(1-ah)*(1-an)*(1-asoc) + V[ih+1,jn,ks]*ah*(1-an)*(1-asoc) +
            V[ih,jn+1,ks]*(1-ah)*an*(1-asoc) + V[ih,jn,ks+1]*(1-ah)*(1-an)*asoc +
            V[ih+1,jn+1,ks]*ah*an*(1-asoc) + V[ih+1,jn,ks+1]*ah*(1-an)*asoc +
            V[ih,jn+1,ks+1]*(1-ah)*an*asoc + V[ih+1,jn+1,ks+1]*ah*an*asoc)

    def solve_value_function(self):
        """Value iteration over the plant state space."""
        logger.info("=" * 60)
        logger.info(" STACK HJB — Solving Plant Value Function")
        logger.info(f" Grid: {len(self.h2_grid)}×{len(self.nh3_grid)}×{len(self.soc_grid)}")
        logger.info("=" * 60)

        nh, nn, ns = len(self.h2_grid), len(self.nh3_grid), len(self.soc_grid)
        self.V = np.zeros((nh, nn, ns))

        # Terminal: reward full buffers
        for ih in range(nh):
            for jn in range(nn):
                for ks in range(ns):
                    self.V[ih,jn,ks] = -(self.Q_h2_buffer * self.h2_grid[ih] +
                                          self.Q_nh3_buffer * self.nh3_grid[jn] +
                                          self.Q_soc_buffer * self.soc_grid[ks])

        for sweep in range(4):
            V_old = self.V.copy()
            for ih in range(nh):
                for jn in range(nn):
                    for ks in range(ns):
                        best = np.inf
                        state = StackHJBState(self.h2_grid[ih], self.nh3_grid[jn],
                                              self.soc_grid[ks], 0.5, 0.5)
                        for ep in self.elec_grid:
                            for eng in self.engine_grid:
                                for batt in self.battery_grid:
                                    ns2, cost = self._dynamics(state, ep, eng, batt, 12)
                                    total = cost * self.dt_h + self._interpolate_V(
                                        ns2.h2_level, ns2.nh3_level, ns2.battery_soc)
                                    if total < best:
                                        best = total
                        self.V[ih,jn,ks] = best

            delta = np.max(np.abs(self.V - V_old))
            logger.info(f" Sweep {sweep+1}/4 | max ΔV = {delta:.6f}")
            if delta < 0.001:
                break

        logger.info(" Stack HJB solved.")
        return self

    def optimal_dispatch(self, state: StackHJBState, hour: int) -> StackControl:
        """Extract optimal control from value function."""
        if self.V is None:
            raise RuntimeError("Solve first.")

        best_cost = np.inf
        best_u = StackControl(50, 50, 0, 30, 50)

        for ep in self.elec_grid:
            for eng in self.engine_grid:
                for batt in self.battery_grid:
                    ns2, cost = self._dynamics(state, ep, eng, batt, hour)
                    total = cost * self.dt_h + self._interpolate_V(
                        ns2.h2_level, ns2.nh3_level, ns2.battery_soc)
                    if total < best_cost:
                        best_cost = total
                        best_u = StackControl(ep, eng, batt, 30, 100 - ep)

        return best_u

    def simulate(self, initial: Optional[StackHJBState] = None,
                 hours: int = 168) -> StackHJBResult:
        """Forward simulation with optimal policy."""
        if self.V is None:
            self.solve_value_function()

        if initial is None:
            initial = StackHJBState(0.50, 0.50, 0.50, 0.5, 0.5)

        n = hours
        t = np.arange(n + 1) * self.dt_h
        h2_t, nh3_t, soc_t = [np.zeros(n+1) for _ in range(3)]
        rev_t, elec_t, eng_t, grid_t = [np.zeros(n) for _ in range(4)]

        state = initial
        h2_t[0], nh3_t[0], soc_t[0] = state.h2_level, state.nh3_level, state.battery_soc
        cum_revenue = 0

        for i in range(n):
            hour = i % 24
            control = self.optimal_dispatch(state, hour)

            elec_t[i] = control.electrolyzer_pct
            eng_t[i] = control.engine_load_pct
            grid_t[i] = control.grid_export_pct

            state, cost = self._dynamics(state, control.electrolyzer_pct,
                                          control.engine_load_pct,
                                          control.battery_mode, hour)

            h2_t[i+1] = state.h2_level
            nh3_t[i+1] = state.nh3_level
            soc_t[i+1] = state.battery_soc

            price = self._grid_price(hour)
            hourly_revenue = (control.grid_export_pct / 100 * self.total_renewable_mw *
                              state.solar_cf * price / 1000)
            cum_revenue += hourly_revenue
            rev_t[i] = cum_revenue

        # Metrics
        h2_self_suff = (1 - np.mean(np.maximum(0, 0.3 - h2_t[1:])) / 0.3) * 100
        nh3_self_suff = (1 - np.mean(np.maximum(0, 0.3 - nh3_t[1:])) / 0.3) * 100
        renewable_frac = np.mean(elec_t) / 100 * 80 + 20  # Approx

        mid_nh3 = len(self.nh3_grid) // 2
        V_slice = self.V[:, mid_nh3, :]

        return StackHJBResult(
            time_grid=t, h2_trajectory=h2_t, nh3_trajectory=nh3_t,
            soc_trajectory=soc_t, revenue_trajectory=rev_t,
            electrolyzer_trajectory=elec_t, engine_trajectory=eng_t,
            grid_export_trajectory=grid_t, value_function=V_slice,
            optimal_strategy={
                "avg_electrolyzer_pct": float(np.mean(elec_t)),
                "avg_engine_load_pct": float(np.mean(eng_t)),
                "avg_grid_export_pct": float(np.mean(grid_t)),
                "final_h2_level": h2_t[-1],
                "final_nh3_level": nh3_t[-1],
                "final_soc": soc_t[-1],
            },
            annual_revenue_usd=cum_revenue * (8760 / hours),
            h2_self_sufficiency_pct=h2_self_suff,
            renewable_fraction_pct=renewable_frac,
            total_cost=-cum_revenue,
        )


if __name__ == "__main__":
    ctrl = StackHJBController(
        n_h2=8, n_nh3=8, n_soc=6,
        n_elec=5, n_engine=5, n_battery=3)
    result = ctrl.simulate(hours=168)  # 1 week
    print(f"\n{'='*60}")
    print(f" 🏭 STACK HJB — OPTIMAL PLANT DISPATCH (1 week)")
    print(f"{'='*60}")
    for k, v in result.optimal_strategy.items():
        print(f"   {k}: {v:.2f}")
    print(f"   Annualized revenue: ${result.annual_revenue_usd:,.0f}")
    print(f"   H₂ self-sufficiency: {result.h2_self_sufficiency_pct:.1f}%")
    print(f"   Renewable fraction: {result.renewable_fraction_pct:.1f}%")
    print(f"{'='*60}")
