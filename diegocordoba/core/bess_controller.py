"""
PRIMEnergeia — BESS Controller
=================================
Battery Energy Storage System controller with safety constraints,
operating modes, and revenue tracking. Translates HJB/DRL optimal
control into safe charge/discharge commands.

Usage:
    from core.bess_controller import BESSController
    bess = BESSController(capacity_mwh=400, max_power_mw=100)
    setpoint = bess.dispatch(grid_state, control_signal)

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import IntEnum
from datetime import datetime

logger = logging.getLogger("prime.bess")


# ─────────────────────────────────────────────────────────────
# Operating Modes
# ─────────────────────────────────────────────────────────────

class BESSMode(IntEnum):
    IDLE = 0
    FREQUENCY_RESPONSE = 1
    PRICE_ARBITRAGE = 2
    PEAK_SHAVING = 3
    VOLTAGE_SUPPORT = 4
    EMERGENCY = 5
    MAINTENANCE = 6


MODE_LABELS = {
    BESSMode.IDLE: "IDLE",
    BESSMode.FREQUENCY_RESPONSE: "FREQ_RESPONSE",
    BESSMode.PRICE_ARBITRAGE: "ARBITRAGE",
    BESSMode.PEAK_SHAVING: "PEAK_SHAVE",
    BESSMode.VOLTAGE_SUPPORT: "VOLT_SUPPORT",
    BESSMode.EMERGENCY: "EMERGENCY",
    BESSMode.MAINTENANCE: "MAINTENANCE",
}


# ─────────────────────────────────────────────────────────────
# Safety Limits
# ─────────────────────────────────────────────────────────────

@dataclass
class SafetyLimits:
    """Battery safety constraints — IEEE 2800 / NERC PRC-024."""
    soc_min_pct: float = 10.0         # Min SoC (protect cell chemistry)
    soc_max_pct: float = 90.0         # Max SoC (thermal safety)
    soc_emergency_min: float = 5.0    # Absolute minimum (shutdown)
    soc_emergency_max: float = 95.0   # Absolute maximum
    max_c_rate_charge: float = 1.0    # Max charge C-rate
    max_c_rate_discharge: float = 1.0 # Max discharge C-rate
    ramp_rate_mw_s: float = 50.0      # Max power ramp (MW/s)
    max_temperature_c: float = 45.0   # Cell temperature limit
    min_temperature_c: float = 5.0    # Low temp cutoff
    max_cycles_day: int = 4           # Daily cycle limit (degradation)
    anti_island_delay_ms: float = 160 # IEEE 1547 anti-islanding
    ride_through_hz_low: float = 57.0 # Under-frequency ride-through
    ride_through_hz_high: float = 61.8 # Over-frequency ride-through


# ─────────────────────────────────────────────────────────────
# Battery Model
# ─────────────────────────────────────────────────────────────

@dataclass
class BatteryState:
    """Real-time battery state."""
    soc_pct: float = 50.0
    soc_mwh: float = 200.0
    power_mw: float = 0.0
    temperature_c: float = 25.0
    voltage_v: float = 800.0
    current_a: float = 0.0
    cycle_count: float = 0.0
    daily_cycles: float = 0.0
    health_pct: float = 100.0
    mode: BESSMode = BESSMode.IDLE
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "soc_pct": round(self.soc_pct, 2),
            "power_mw": round(self.power_mw, 2),
            "temperature_c": round(self.temperature_c, 1),
            "health_pct": round(self.health_pct, 2),
            "mode": MODE_LABELS.get(self.mode, "UNKNOWN"),
            "cycle_count": round(self.cycle_count, 1),
        }


class BatteryModel:
    """Physics-based battery model with degradation."""

    def __init__(self, capacity_mwh: float = 400.0, max_power_mw: float = 100.0,
                 efficiency_charge: float = 0.94, efficiency_discharge: float = 0.94,
                 nominal_voltage_v: float = 800.0):
        self.capacity_mwh = capacity_mwh
        self.max_power_mw = max_power_mw
        self.eff_charge = efficiency_charge
        self.eff_discharge = efficiency_discharge
        self.nominal_v = nominal_voltage_v

        # State
        self.state = BatteryState(
            soc_pct=50.0,
            soc_mwh=capacity_mwh * 0.5,
            health_pct=100.0,
        )

        # Degradation tracking
        self._throughput_mwh = 0.0
        self._last_power_sign = 0

    def step(self, power_mw: float, dt_s: float) -> BatteryState:
        """Advance battery state by dt_s seconds at the given power level.

        power_mw > 0: discharge (inject to grid)
        power_mw < 0: charge (absorb from grid)
        """
        energy_mwh = power_mw * dt_s / 3600.0

        if power_mw >= 0:
            # Discharging
            actual_energy = energy_mwh / self.eff_discharge
        else:
            # Charging
            actual_energy = energy_mwh * self.eff_charge

        self.state.soc_mwh -= actual_energy
        self.state.soc_mwh = np.clip(self.state.soc_mwh, 0, self.capacity_mwh)
        self.state.soc_pct = 100.0 * self.state.soc_mwh / self.capacity_mwh
        self.state.power_mw = power_mw

        # Temperature model (simplified thermal)
        ambient = 25.0
        heat = 0.002 * power_mw ** 2  # I²R losses
        cooling = 0.05 * (self.state.temperature_c - ambient)
        self.state.temperature_c += (heat - cooling) * dt_s
        self.state.temperature_c = np.clip(self.state.temperature_c, -10, 60)

        # Voltage model (simplified OCV + IR drop)
        ocv = self.nominal_v * (0.85 + 0.3 * self.state.soc_pct / 100)
        ir_drop = 0.01 * abs(power_mw) * 1e6 / (self.nominal_v * 1000)
        self.state.voltage_v = ocv - ir_drop * np.sign(power_mw)

        # Cycle counting (rainflow simplified)
        self._throughput_mwh += abs(energy_mwh)
        current_sign = np.sign(power_mw)
        if current_sign != self._last_power_sign and current_sign != 0:
            self.state.daily_cycles += 0.5
        self._last_power_sign = current_sign
        self.state.cycle_count = self._throughput_mwh / (2 * self.capacity_mwh)

        # Degradation (calendar + cycling)
        cycle_deg = 0.00002 * abs(energy_mwh)  # ~0.02% per full cycle
        temp_factor = 1.0 + 0.05 * max(0, self.state.temperature_c - 35)
        self.state.health_pct -= cycle_deg * temp_factor
        self.state.health_pct = max(self.state.health_pct, 0)

        self.state.timestamp = datetime.now()
        return self.state


# ─────────────────────────────────────────────────────────────
# Revenue Tracker
# ─────────────────────────────────────────────────────────────

@dataclass
class RevenueRecord:
    timestamp: float = 0.0
    source: str = ""
    amount_usd: float = 0.0
    energy_mwh: float = 0.0
    price_usd_mwh: float = 0.0


class RevenueTracker:
    """Track BESS revenue from multiple streams."""

    def __init__(self):
        self.records: List[RevenueRecord] = []
        self.total_revenue_usd = 0.0
        self.total_penalties_usd = 0.0
        self.freq_response_usd = 0.0
        self.arbitrage_usd = 0.0
        self.peak_shaving_usd = 0.0
        self.penalty_avoidance_usd = 0.0

    def record_revenue(self, source: str, amount: float, energy: float = 0,
                       price: float = 0, timestamp: float = 0):
        self.records.append(RevenueRecord(
            timestamp=timestamp, source=source,
            amount_usd=amount, energy_mwh=energy, price_usd_mwh=price,
        ))
        self.total_revenue_usd += amount
        if source == "freq_response":
            self.freq_response_usd += amount
        elif source == "arbitrage":
            self.arbitrage_usd += amount
        elif source == "peak_shaving":
            self.peak_shaving_usd += amount
        elif source == "penalty_avoidance":
            self.penalty_avoidance_usd += amount

    def record_penalty(self, amount: float, timestamp: float = 0):
        self.total_penalties_usd += amount
        self.records.append(RevenueRecord(
            timestamp=timestamp, source="penalty", amount_usd=-amount,
        ))

    @property
    def net_revenue(self) -> float:
        return self.total_revenue_usd - self.total_penalties_usd

    def summary(self) -> Dict:
        return {
            "total_revenue_usd": round(self.total_revenue_usd, 2),
            "total_penalties_usd": round(self.total_penalties_usd, 2),
            "net_revenue_usd": round(self.net_revenue, 2),
            "freq_response_usd": round(self.freq_response_usd, 2),
            "arbitrage_usd": round(self.arbitrage_usd, 2),
            "peak_shaving_usd": round(self.peak_shaving_usd, 2),
            "penalty_avoidance_usd": round(self.penalty_avoidance_usd, 2),
            "n_records": len(self.records),
        }


# ─────────────────────────────────────────────────────────────
# BESS Controller — Main Class
# ─────────────────────────────────────────────────────────────

class BESSController:
    """Production-grade BESS controller with safety constraints.

    Translates HJB/DRL optimal control signals into safe
    battery charge/discharge commands.

    Parameters
    ----------
    capacity_mwh : float
        Total battery energy capacity
    max_power_mw : float
        Maximum charge/discharge power
    market : str
        Market for regulatory parameters
    """

    def __init__(self, capacity_mwh: float = 400.0, max_power_mw: float = 100.0,
                 market: str = "ERCOT", safety: Optional[SafetyLimits] = None):
        self.battery = BatteryModel(
            capacity_mwh=capacity_mwh,
            max_power_mw=max_power_mw,
        )
        self.safety = safety or SafetyLimits()
        self.revenue = RevenueTracker()
        self.market = market
        self.max_power = max_power_mw

        # Mode management
        self.mode = BESSMode.IDLE
        self.prev_mode = BESSMode.IDLE

        # State for mode selection
        self._charge_price = None
        self._arbitrage_threshold = 20.0  # $/MWh spread to trigger arbitrage

        logger.info(
            f"BESS Controller initialized: {capacity_mwh} MWh / "
            f"{max_power_mw} MW | Market: {market}"
        )

    def dispatch(self, freq_deviation_hz: float, lmp_price: float,
                 control_signal_mw: float, dt_s: float = 0.01,
                 time_s: float = 0.0) -> Tuple[float, BatteryState]:
        """Main dispatch function: control signal → safe power command.

        Parameters
        ----------
        freq_deviation_hz : float
            Current frequency deviation from nominal
        lmp_price : float
            Current locational marginal price ($/MWh)
        control_signal_mw : float
            Desired power from HJB/DRL controller
        dt_s : float
            Time step in seconds
        time_s : float
            Current simulation time

        Returns
        -------
        (actual_power_mw, battery_state)
        """
        # 1. Select operating mode
        self.mode = self._select_mode(freq_deviation_hz, lmp_price)

        # 2. Apply mode-specific logic
        desired_power = self._mode_dispatch(
            freq_deviation_hz, lmp_price, control_signal_mw
        )

        # 3. Apply safety constraints
        safe_power = self._apply_safety(desired_power, dt_s)

        # 4. Execute on battery model
        state = self.battery.step(safe_power, dt_s)
        state.mode = self.mode

        # 5. Track revenue
        self._track_revenue(
            safe_power, freq_deviation_hz, lmp_price, dt_s, time_s
        )

        return safe_power, state

    def _select_mode(self, freq_dev: float, price: float) -> BESSMode:
        """Determine operating mode from grid conditions."""
        soc = self.battery.state.soc_pct
        temp = self.battery.state.temperature_c

        # Emergency conditions
        if temp > self.safety.max_temperature_c:
            return BESSMode.EMERGENCY
        if soc < self.safety.soc_emergency_min or soc > self.safety.soc_emergency_max:
            return BESSMode.EMERGENCY

        # Frequency response has priority
        if abs(freq_dev) > 0.02:
            return BESSMode.FREQUENCY_RESPONSE

        # Price arbitrage opportunity
        if self._charge_price is not None:
            spread = price - self._charge_price
            if spread > self._arbitrage_threshold and soc > 20:
                return BESSMode.PRICE_ARBITRAGE
        if price < 20 and soc < 80:
            self._charge_price = price
            return BESSMode.PRICE_ARBITRAGE

        # Peak shaving (high price periods)
        if price > 200 and soc > 20:
            return BESSMode.PEAK_SHAVING

        return BESSMode.IDLE

    def _mode_dispatch(self, freq_dev: float, price: float,
                       control_signal: float) -> float:
        """Compute desired power based on operating mode."""

        if self.mode == BESSMode.FREQUENCY_RESPONSE:
            # Follow HJB/DRL control signal for frequency response
            return control_signal

        elif self.mode == BESSMode.PRICE_ARBITRAGE:
            if price < 20:
                # Charge at low prices
                return -self.max_power * 0.5
            elif self._charge_price and price - self._charge_price > self._arbitrage_threshold:
                # Discharge at high prices
                self._charge_price = None
                return self.max_power * 0.8
            return 0.0

        elif self.mode == BESSMode.PEAK_SHAVING:
            # Discharge proportional to price excess
            excess = (price - 200) / 300
            return self.max_power * min(excess, 0.8)

        elif self.mode == BESSMode.VOLTAGE_SUPPORT:
            return control_signal * 0.3

        elif self.mode == BESSMode.EMERGENCY:
            # Ramp to zero
            return 0.0

        return 0.0  # IDLE

    def _apply_safety(self, desired_mw: float, dt_s: float) -> float:
        """Apply all safety constraints to desired power command."""
        power = desired_mw
        soc = self.battery.state.soc_pct
        current_power = self.battery.state.power_mw

        # 1. C-rate limits
        max_discharge = self.battery.capacity_mwh * self.safety.max_c_rate_discharge
        max_charge = self.battery.capacity_mwh * self.safety.max_c_rate_charge
        power = np.clip(power, -max_charge, max_discharge)

        # 2. Absolute power limit
        power = np.clip(power, -self.max_power, self.max_power)

        # 3. Ramp rate limit
        max_ramp = self.safety.ramp_rate_mw_s * dt_s
        power = current_power + np.clip(power - current_power, -max_ramp, max_ramp)

        # 4. SoC limits — prevent over-charge/over-discharge
        if power > 0 and soc <= self.safety.soc_min_pct:
            power = 0.0  # Cannot discharge below min SoC
        if power < 0 and soc >= self.safety.soc_max_pct:
            power = 0.0  # Cannot charge above max SoC

        # 5. SoC soft limits — reduce power near boundaries
        if power > 0 and soc < self.safety.soc_min_pct + 10:
            factor = (soc - self.safety.soc_min_pct) / 10.0
            power *= max(factor, 0)
        if power < 0 and soc > self.safety.soc_max_pct - 10:
            factor = (self.safety.soc_max_pct - soc) / 10.0
            power *= max(factor, 0)

        # 6. Temperature protection
        if self.battery.state.temperature_c > self.safety.max_temperature_c - 5:
            factor = (self.safety.max_temperature_c - self.battery.state.temperature_c) / 5.0
            power *= max(factor, 0)

        # 7. Daily cycle limit
        if self.battery.state.daily_cycles >= self.safety.max_cycles_day:
            power *= 0.1

        return power

    def _track_revenue(self, power_mw: float, freq_dev: float,
                       price: float, dt_s: float, time_s: float):
        """Calculate and record revenue from dispatch."""
        energy_mwh = abs(power_mw) * dt_s / 3600

        if self.mode == BESSMode.FREQUENCY_RESPONSE:
            # FCAS / frequency response payment
            payment = 25.0 * abs(power_mw) * dt_s / 3600  # $/MW-hr rate
            self.revenue.record_revenue(
                "freq_response", payment, energy_mwh, price, time_s
            )

        elif self.mode == BESSMode.PRICE_ARBITRAGE:
            if power_mw > 0:  # Discharging (selling)
                payment = energy_mwh * price
                self.revenue.record_revenue(
                    "arbitrage", payment, energy_mwh, price, time_s
                )
            else:  # Charging (buying)
                cost = energy_mwh * price
                self.revenue.record_revenue(
                    "arbitrage", -cost, energy_mwh, price, time_s
                )

        elif self.mode == BESSMode.PEAK_SHAVING:
            payment = energy_mwh * price * 0.5  # Value from avoided peak demand
            self.revenue.record_revenue(
                "peak_shaving", payment, energy_mwh, price, time_s
            )

    def get_state(self) -> Dict:
        """Get full controller state for telemetry."""
        return {
            "battery": self.battery.state.to_dict(),
            "mode": MODE_LABELS.get(self.mode, "UNKNOWN"),
            "revenue": self.revenue.summary(),
            "market": self.market,
        }

    def reset_daily(self):
        """Reset daily counters (call at midnight)."""
        self.battery.state.daily_cycles = 0.0


# ─────────────────────────────────────────────────────────────
# Demo / Self-Test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(message)s")

    print("[⚡] PRIMEnergeia BESS Controller — 24hr Simulation\n")

    bess = BESSController(capacity_mwh=400, max_power_mw=100, market="ERCOT")
    dt = 0.1
    duration = 86400  # 24 hours
    n_steps = int(duration / dt)

    rng = np.random.RandomState(42)

    for step in range(n_steps):
        t = step * dt
        hour = (t / 3600) % 24

        # Simulate price (high during afternoon)
        price = 40 + 60 * np.sin(np.pi * (hour - 6) / 12) ** 2
        price += rng.normal(0, 5)
        price = max(price, 5)
        if rng.random() < 0.001:
            price += rng.uniform(200, 2000)

        # Simulate frequency deviation
        freq_dev = rng.normal(0, 0.02)
        if rng.random() < 0.002:
            freq_dev += rng.choice([-1, 1]) * rng.uniform(0.1, 0.5)

        # HJB control signal (simplified for demo)
        control = -50.0 * freq_dev

        power, state = bess.dispatch(freq_dev, price, control, dt, t)

        # Print hourly summary
        if step % int(3600 / dt) == 0 and step > 0:
            h = int(hour)
            rev = bess.revenue.summary()
            print(
                f"  Hour {h:2d} | SoC: {state.soc_pct:5.1f}% | "
                f"Power: {state.power_mw:+7.1f} MW | "
                f"Mode: {MODE_LABELS[state.mode]:14s} | "
                f"Net Rev: ${rev['net_revenue_usd']:>10,.2f} | "
                f"Health: {state.health_pct:.2f}%"
            )

    print(f"\n{'=' * 70}")
    print(f" 24hr Summary")
    print(f"{'=' * 70}")
    rev = bess.revenue.summary()
    for k, v in rev.items():
        print(f"  {k:30s}: {v}")
    print(f"  {'battery_health':30s}: {bess.battery.state.health_pct:.2f}%")
    print(f"  {'total_cycles':30s}: {bess.battery.state.cycle_count:.1f}")
