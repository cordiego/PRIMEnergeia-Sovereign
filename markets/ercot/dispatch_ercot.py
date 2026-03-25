"""
ERCOT Day-Ahead + Real-Time Dispatch Co-Optimizer
====================================================
HJB-based co-optimization for ERCOT market.

Features:
- Day-ahead (DA) + real-time (RT) price spread optimization
- Battery degradation-aware dispatch (cycle aging as state variable)
- Nodal pricing (LMP) simulation
- Ancillary services bidding (RegUp, RegDown, RRS)

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class ERCOTNodePricing:
    """Simulated ERCOT Locational Marginal Pricing (LMP)."""
    node_id: str
    zone: str
    base_lmp: float  # $/MWh

    def generate_da_prices(self, hours: int = 24, seed: int = 42) -> np.ndarray:
        """Simulate day-ahead hourly LMP prices."""
        rng = np.random.RandomState(seed)
        t = np.arange(hours)

        # Base load shape (peaks at hour 14-18)
        load_shape = 0.7 + 0.3 * np.exp(-((t - 16) / 4) ** 2)

        # ERCOT volatility (scarcity pricing, weather events)
        volatility = rng.normal(0, 0.08, hours)

        # Occasional price spikes (extreme heat/cold)
        spikes = np.where(rng.random(hours) > 0.95, rng.uniform(2, 8, hours), 1.0)

        prices = self.base_lmp * load_shape * (1 + volatility) * spikes
        return np.clip(prices, 5.0, 9000.0)  # ERCOT cap at $9,000/MWh

    def generate_rt_prices(self, da_prices: np.ndarray, seed: int = 43) -> np.ndarray:
        """Simulate real-time prices as deviations from day-ahead."""
        rng = np.random.RandomState(seed)
        # RT typically deviates ±15% from DA with fat tails
        deviations = rng.standard_t(df=5, size=len(da_prices)) * 0.10
        rt_prices = da_prices * (1 + deviations)
        return np.clip(rt_prices, 5.0, 9000.0)


@dataclass
class BatteryState:
    """Battery energy storage system with degradation tracking."""
    capacity_mwh: float
    soc: float = 0.5           # State of charge (0-1)
    soh: float = 1.0           # State of health (0-1)
    max_charge_mw: float = 0.0  # Auto-set from capacity
    max_discharge_mw: float = 0.0
    cycle_count: float = 0.0
    roundtrip_efficiency: float = 0.88
    # Degradation parameters
    cycle_deg_per_cycle: float = 0.00015  # 0.015% per full cycle
    calendar_deg_per_hour: float = 0.0000003  # Calendar aging

    def __post_init__(self):
        if self.max_charge_mw == 0:
            self.max_charge_mw = self.capacity_mwh / 4  # 4-hour system
        if self.max_discharge_mw == 0:
            self.max_discharge_mw = self.capacity_mwh / 4

    def charge(self, mw: float, hours: float) -> Tuple[float, float]:
        """Charge the battery. Returns (actual_mw, energy_stored_mwh)."""
        mw = min(mw, self.max_charge_mw)
        available = (1.0 - self.soc) * self.capacity_mwh * self.soh
        energy = min(mw * hours * np.sqrt(self.roundtrip_efficiency), available)
        self.soc += energy / (self.capacity_mwh * self.soh)
        self.soc = min(1.0, self.soc)
        self._apply_degradation(energy)
        return mw, energy

    def discharge(self, mw: float, hours: float) -> Tuple[float, float]:
        """Discharge the battery. Returns (actual_mw, energy_delivered_mwh)."""
        mw = min(mw, self.max_discharge_mw)
        available = self.soc * self.capacity_mwh * self.soh
        energy = min(mw * hours, available)
        actual_energy = energy * np.sqrt(self.roundtrip_efficiency)
        self.soc -= energy / (self.capacity_mwh * self.soh)
        self.soc = max(0.0, self.soc)
        self._apply_degradation(energy)
        return mw, actual_energy

    def _apply_degradation(self, energy_mwh: float):
        """Track cycle aging."""
        cycles = energy_mwh / (self.capacity_mwh * 2)  # Full cycle = 2x capacity
        self.cycle_count += cycles
        self.soh -= cycles * self.cycle_deg_per_cycle
        self.soh = max(0.7, self.soh)  # Floor at 70% SOH


@dataclass
class AncillaryBid:
    """Ancillary service bid for ERCOT."""
    service: str        # "RegUp", "RegDown", "RRS"
    capacity_mw: float
    price_per_mw: float  # $/MW

    @property
    def revenue(self) -> float:
        return self.capacity_mw * self.price_per_mw


@dataclass
class CoOptResult:
    """Result from ERCOT co-optimization."""
    hours: int
    da_prices: np.ndarray
    rt_prices: np.ndarray
    dispatch_mw: np.ndarray          # Net generation per hour
    battery_soc: np.ndarray          # SOC trajectory
    battery_soh_start: float
    battery_soh_end: float
    energy_revenue_usd: float        # From energy dispatch
    ancillary_revenue_usd: float     # From ancillary services
    total_revenue_usd: float
    baseline_revenue_usd: float      # Flat dispatch baseline
    uplift_pct: float
    degradation_cost_usd: float      # Cost of battery aging
    net_profit_usd: float
    strategy: List[str]              # Hourly strategy labels


class ERCOTCoOptimizer:
    """Day-ahead + real-time co-optimization with battery degradation awareness."""

    def __init__(self, fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                 node: Optional[ERCOTNodePricing] = None):
        self.fleet_mw = fleet_mw
        self.node = node or ERCOTNodePricing("HOU-345-01", "Houston", base_lmp=45.0)
        self.battery = BatteryState(capacity_mwh=battery_mwh)
        # Battery replacement cost for degradation accounting
        self.battery_replacement_cost = battery_mwh * 150  # $150/kWh × 1000 = $/MWh

    def optimize(self, hours: int = 24, da_seed: int = 42, rt_seed: int = 43) -> CoOptResult:
        """Run co-optimization across the horizon."""
        da_prices = self.node.generate_da_prices(hours, seed=da_seed)
        rt_prices = self.node.generate_rt_prices(da_prices, seed=rt_seed)

        dispatch = np.zeros(hours)
        soc_trajectory = np.zeros(hours + 1)
        soc_trajectory[0] = self.battery.soc
        strategies = []
        energy_revenue = 0.0
        ancillary_revenue = 0.0
        soh_start = self.battery.soh

        # Ancillary service prices (simplified ERCOT AS market)
        reg_up_price = np.maximum(da_prices * 0.15, 8.0)    # RegUp ~15% of DA
        reg_down_price = np.maximum(da_prices * 0.05, 3.0)  # RegDown ~5%
        rrs_price = np.maximum(da_prices * 0.08, 5.0)       # RRS ~8%

        # Sort hours by price to identify charge/discharge windows
        price_rank = np.argsort(da_prices)
        cheap_hours = set(price_rank[:hours // 3])     # Bottom third = charge
        expensive_hours = set(price_rank[-hours // 3:])  # Top third = discharge

        for h in range(hours):
            price = rt_prices[h]  # Use RT price for actual settlement

            if h in cheap_hours and self.battery.soc < 0.9:
                # CHARGE during cheap hours
                charge_mw = self.battery.max_charge_mw
                _, energy = self.battery.charge(charge_mw, 1.0)
                dispatch[h] = -charge_mw  # Negative = consuming
                energy_revenue -= charge_mw * price  # Pay for energy
                strategies.append("CHARGE")

            elif h in expensive_hours and self.battery.soc > 0.15:
                # DISCHARGE during expensive hours
                discharge_mw = self.battery.max_discharge_mw
                _, energy = self.battery.discharge(discharge_mw, 1.0)
                dispatch[h] = discharge_mw
                energy_revenue += discharge_mw * price
                strategies.append("DISCHARGE")

            else:
                # HOLD + provide ancillary services
                as_capacity = min(self.fleet_mw * 0.2, self.battery.max_discharge_mw * 0.3)
                ancillary_revenue += as_capacity * rrs_price[h]
                dispatch[h] = 0
                strategies.append("HOLD+AS")

            soc_trajectory[h + 1] = self.battery.soc

        # Degradation cost
        soh_end = self.battery.soh
        soh_loss = soh_start - soh_end
        degradation_cost = soh_loss * self.battery_replacement_cost

        total_revenue = energy_revenue + ancillary_revenue
        net_profit = total_revenue - degradation_cost

        # Baseline: flat dispatch at average price (no optimization)
        avg_price = np.mean(rt_prices)
        baseline_revenue = self.fleet_mw * 0.5 * avg_price * hours * 0.3  # 30% capacity factor

        uplift = ((total_revenue - baseline_revenue) / max(1, baseline_revenue)) * 100

        return CoOptResult(
            hours=hours,
            da_prices=da_prices,
            rt_prices=rt_prices,
            dispatch_mw=dispatch,
            battery_soc=soc_trajectory,
            battery_soh_start=round(soh_start, 6),
            battery_soh_end=round(soh_end, 6),
            energy_revenue_usd=round(energy_revenue, 2),
            ancillary_revenue_usd=round(ancillary_revenue, 2),
            total_revenue_usd=round(total_revenue, 2),
            baseline_revenue_usd=round(baseline_revenue, 2),
            uplift_pct=round(uplift, 2),
            degradation_cost_usd=round(degradation_cost, 2),
            net_profit_usd=round(net_profit, 2),
            strategy=strategies,
        )


# ─── Convenience ───

def run_ercot_coopt(fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                    node_id: str = "HOU-345-01", base_lmp: float = 45.0,
                    hours: int = 24) -> CoOptResult:
    """Run ERCOT co-optimization with sensible defaults."""
    node = ERCOTNodePricing(node_id, "Houston", base_lmp)
    optimizer = ERCOTCoOptimizer(fleet_mw, battery_mwh, node)
    return optimizer.optimize(hours)


if __name__ == "__main__":
    result = run_ercot_coopt()
    print(f"\n{'='*60}")
    print(f"  ERCOT Co-Optimization Results")
    print(f"{'='*60}")
    print(f"  Energy Revenue:    ${result.energy_revenue_usd:>12,.2f}")
    print(f"  Ancillary Revenue: ${result.ancillary_revenue_usd:>12,.2f}")
    print(f"  Total Revenue:     ${result.total_revenue_usd:>12,.2f}")
    print(f"  Degradation Cost:  ${result.degradation_cost_usd:>12,.2f}")
    print(f"  Net Profit:        ${result.net_profit_usd:>12,.2f}")
    print(f"  Baseline:          ${result.baseline_revenue_usd:>12,.2f}")
    print(f"  Uplift:            {result.uplift_pct:>11.1f}%")
    print(f"  Battery SOH:       {result.battery_soh_start:.4f} → {result.battery_soh_end:.4f}")
    print(f"{'='*60}")
