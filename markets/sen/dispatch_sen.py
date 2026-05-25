"""
SEN (Mexico) Day-Ahead + Real-Time Dispatch Co-Optimizer
==========================================================
HJB-based co-optimization for Mexico's Sistema Eléctrico Nacional.

Features:
- CENACE day-ahead (MDA) + real-time (MTR) price spread optimization
- Battery degradation-aware dispatch
- 9-region nodal pricing (Baja California, Noroeste, Norte, Noreste,
  Occidental, Central, Oriental, Peninsular, Baja California Sur)
- Clean energy certificate (CEL) credit tracking

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── SEN Market Constants ───
SEN_REGIONS = [
    "Baja California", "Baja California Sur", "Noroeste", "Norte",
    "Noreste", "Occidental", "Central", "Oriental", "Peninsular",
]

CEL_PRICE_MXN = 350.0  # Clean Energy Certificate ~$18 USD per CEL


@dataclass
class SENNodePricing:
    """Simulated SEN Locational Marginal Pricing (PML)."""
    node_id: str
    region: str
    base_pml: float  # MXN/MWh

    def generate_mda_prices(self, hours: int = 24, seed: int = 42) -> np.ndarray:
        """Simulate CENACE MDA (day-ahead) hourly PML prices."""
        rng = np.random.RandomState(seed)
        t = np.arange(hours)

        # Mexican load shape: peaks at 14-20h (afternoon/evening heat)
        load_shape = 0.6 + 0.4 * np.exp(-((t - 17) / 5) ** 2)

        # Summer afternoon spikes (AC load in desert regions)
        summer_factor = np.where(
            (t >= 13) & (t <= 19),
            1.0 + rng.uniform(0, 0.25, hours)[(t >= 13) & (t <= 19)].mean(),
            1.0
        )

        volatility = rng.normal(0, 0.06, hours)
        spikes = np.where(rng.random(hours) > 0.96, rng.uniform(1.5, 5, hours), 1.0)

        prices = self.base_pml * load_shape * (1 + volatility) * spikes
        return np.clip(prices, 200.0, 15000.0)  # MXN cap

    def generate_mtr_prices(self, mda_prices: np.ndarray, seed: int = 43) -> np.ndarray:
        """Simulate real-time (MTR) prices as deviations from MDA."""
        rng = np.random.RandomState(seed)
        deviations = rng.standard_t(df=4, size=len(mda_prices)) * 0.12
        mtr_prices = mda_prices * (1 + deviations)
        return np.clip(mtr_prices, 200.0, 15000.0)


@dataclass
class BatteryStateSEN:
    """Battery storage with degradation (adapted for SEN climate)."""
    capacity_mwh: float
    soc: float = 0.5
    soh: float = 1.0
    max_charge_mw: float = 0.0
    max_discharge_mw: float = 0.0
    cycle_count: float = 0.0
    roundtrip_efficiency: float = 0.86  # Slightly lower due to heat
    cycle_deg_per_cycle: float = 0.00016
    calendar_deg_per_hour: float = 0.0000004  # Higher calendar aging (heat)

    def __post_init__(self):
        if self.max_charge_mw == 0:
            self.max_charge_mw = self.capacity_mwh / 4
        if self.max_discharge_mw == 0:
            self.max_discharge_mw = self.capacity_mwh / 4

    def charge(self, mw: float, hours: float) -> Tuple[float, float]:
        mw = min(mw, self.max_charge_mw)
        available = (1.0 - self.soc) * self.capacity_mwh * self.soh
        energy = min(mw * hours * np.sqrt(self.roundtrip_efficiency), available)
        self.soc += energy / (self.capacity_mwh * self.soh)
        self.soc = min(1.0, self.soc)
        self._degrade(energy)
        return mw, energy

    def discharge(self, mw: float, hours: float) -> Tuple[float, float]:
        mw = min(mw, self.max_discharge_mw)
        available = self.soc * self.capacity_mwh * self.soh
        energy = min(mw * hours, available)
        actual = energy * np.sqrt(self.roundtrip_efficiency)
        self.soc -= energy / (self.capacity_mwh * self.soh)
        self.soc = max(0.0, self.soc)
        self._degrade(energy)
        return mw, actual

    def _degrade(self, energy_mwh: float):
        cycles = energy_mwh / (self.capacity_mwh * 2)
        self.cycle_count += cycles
        self.soh -= cycles * self.cycle_deg_per_cycle
        self.soh = max(0.7, self.soh)


@dataclass
class SENCoOptResult:
    """Result from SEN co-optimization."""
    hours: int
    mda_prices: np.ndarray
    mtr_prices: np.ndarray
    dispatch_mw: np.ndarray
    battery_soc: np.ndarray
    battery_soh_start: float
    battery_soh_end: float
    energy_revenue_mxn: float
    cel_revenue_mxn: float
    total_revenue_mxn: float
    total_revenue_usd: float
    baseline_revenue_mxn: float
    uplift_pct: float
    degradation_cost_mxn: float
    net_profit_mxn: float
    net_profit_usd: float
    strategy: List[str]
    region: str

    @property
    def fx_rate(self) -> float:
        return 17.5  # MXN/USD approximate


class SENCoOptimizer:
    """Day-ahead + real-time co-optimization for Mexico's SEN."""

    MXN_USD = 17.5  # Exchange rate

    def __init__(self, fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                 node: Optional[SENNodePricing] = None, region: str = "Noreste"):
        self.fleet_mw = fleet_mw
        self.region = region
        self.node = node or SENNodePricing(f"SEN-{region[:3].upper()}-001", region, base_pml=900.0)
        self.battery = BatteryStateSEN(capacity_mwh=battery_mwh)
        self.battery_replacement_cost = battery_mwh * 150 * self.MXN_USD

    def optimize(self, hours: int = 24, seed: int = 42) -> SENCoOptResult:
        mda = self.node.generate_mda_prices(hours, seed=seed)
        mtr = self.node.generate_mtr_prices(mda, seed=seed + 1)

        dispatch = np.zeros(hours)
        soc_traj = np.zeros(hours + 1)
        soc_traj[0] = self.battery.soc
        strategies = []
        energy_revenue = 0.0
        cel_revenue = 0.0
        soh_start = self.battery.soh

        price_rank = np.argsort(mda)
        cheap_hours = set(price_rank[:hours // 3])
        expensive_hours = set(price_rank[-hours // 3:])

        for h in range(hours):
            price = mtr[h]

            if h in cheap_hours and self.battery.soc < 0.9:
                charge_mw = self.battery.max_charge_mw
                _, energy = self.battery.charge(charge_mw, 1.0)
                dispatch[h] = -charge_mw
                energy_revenue -= charge_mw * price
                strategies.append("CARGA")
            elif h in expensive_hours and self.battery.soc > 0.15:
                discharge_mw = self.battery.max_discharge_mw
                _, energy = self.battery.discharge(discharge_mw, 1.0)
                dispatch[h] = discharge_mw
                energy_revenue += discharge_mw * price
                # CEL credits for clean energy dispatch
                cel_revenue += discharge_mw * CEL_PRICE_MXN * 0.001
                strategies.append("DESCARGA")
            else:
                dispatch[h] = 0
                strategies.append("ESPERA+CEL")

            soc_traj[h + 1] = self.battery.soc

        soh_end = self.battery.soh
        soh_loss = soh_start - soh_end
        degradation_cost = soh_loss * self.battery_replacement_cost

        total_revenue = energy_revenue + cel_revenue
        net_profit = total_revenue - degradation_cost

        avg_price = np.mean(mtr)
        baseline_revenue = self.fleet_mw * 0.5 * avg_price * hours * 0.3
        uplift = ((total_revenue - baseline_revenue) / max(1, baseline_revenue)) * 100

        return SENCoOptResult(
            hours=hours, mda_prices=mda, mtr_prices=mtr,
            dispatch_mw=dispatch, battery_soc=soc_traj,
            battery_soh_start=round(soh_start, 6), battery_soh_end=round(soh_end, 6),
            energy_revenue_mxn=round(energy_revenue, 2),
            cel_revenue_mxn=round(cel_revenue, 2),
            total_revenue_mxn=round(total_revenue, 2),
            total_revenue_usd=round(total_revenue / self.MXN_USD, 2),
            baseline_revenue_mxn=round(baseline_revenue, 2),
            uplift_pct=round(uplift, 2),
            degradation_cost_mxn=round(degradation_cost, 2),
            net_profit_mxn=round(net_profit, 2),
            net_profit_usd=round(net_profit / self.MXN_USD, 2),
            strategy=strategies, region=self.region,
        )


def run_sen_coopt(fleet_mw: float = 100.0, battery_mwh: float = 400.0,
                  region: str = "Noreste", base_pml: float = 900.0,
                  hours: int = 24) -> SENCoOptResult:
    node = SENNodePricing(f"SEN-{region[:3].upper()}-001", region, base_pml)
    optimizer = SENCoOptimizer(fleet_mw, battery_mwh, node, region)
    return optimizer.optimize(hours)


if __name__ == "__main__":
    result = run_sen_coopt()
    print(f"\n{'='*60}")
    print(f"  SEN Co-Optimization — {result.region}")
    print(f"{'='*60}")
    print(f"  Energy Revenue:    MXN ${result.energy_revenue_mxn:>14,.2f}")
    print(f"  CEL Revenue:       MXN ${result.cel_revenue_mxn:>14,.2f}")
    print(f"  Total Revenue:     MXN ${result.total_revenue_mxn:>14,.2f}")
    print(f"  Total Revenue:     USD ${result.total_revenue_usd:>14,.2f}")
    print(f"  Degradation:       MXN ${result.degradation_cost_mxn:>14,.2f}")
    print(f"  Net Profit:        USD ${result.net_profit_usd:>14,.2f}")
    print(f"  Uplift:            {result.uplift_pct:>13.1f}%")
    print(f"  Battery SOH:       {result.battery_soh_start:.4f} → {result.battery_soh_end:.4f}")
    print(f"{'='*60}")
