"""
PRIMEnergeia — CSV Adapter
===========================
Wraps the existing data_loader.py for offline batch analysis.
Reads historical market data from CSV files and replays it
as a sequence of GridState snapshots.

Best for: Proof-of-concept, pilot week 1, historical backtesting.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.adapters.csv")

# Resolve data_loader from project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class CSVAdapter(PlantAdapter):
    """Offline adapter that replays CSV market data as GridState snapshots.

    Usage:
        adapter = CSVAdapter("data/ercot_real.csv", market="ercot")
        adapter.connect()

        while adapter.has_next():
            state = adapter.read_state()
            setpoint = hjb.solve(state)
            adapter.write_setpoint(setpoint)  # Logged, not written to hardware

        results = adapter.get_results()
    """

    def __init__(
        self,
        filepath: str,
        market: str = "ercot",
        node_id: str = "",
        f_nom: float = 60.0,
        v_nom: float = 345.0,
        capacity_mw: float = 100.0,
    ):
        super().__init__(name=f"csv:{os.path.basename(filepath)}", read_only=True)
        self.filepath = filepath
        self.market = market
        self.node_id = node_id
        self.f_nom = f_nom
        self.v_nom = v_nom
        self.capacity_mw = capacity_mw

        self._dataset = None
        self._cursor = 0
        self._results = []

    def connect(self) -> None:
        """Load CSV via data_loader and prepare for replay."""
        try:
            from data.data_loader import load_dataset
            self._dataset = load_dataset(
                filepath=self.filepath,
                market=self.market,
                node_id=self.node_id or None,
            )
            self._cursor = 0
            self._connected = True
            logger.info(
                f"[{self.name}] Loaded {self._dataset.hours} intervals "
                f"from {self.filepath} (market={self.market})"
            )
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to load CSV: {e}") from e

    def close(self) -> None:
        self._connected = False
        logger.info(f"[{self.name}] Closed. {len(self._results)} results logged.")

    def has_next(self) -> bool:
        """Check if there are more intervals to replay."""
        if self._dataset is None:
            return False
        return self._cursor < self._dataset.hours

    @property
    def progress(self) -> float:
        """Replay progress as 0.0–1.0."""
        if self._dataset is None or self._dataset.hours == 0:
            return 0.0
        return self._cursor / self._dataset.hours

    def _read_state_impl(self) -> GridState:
        """Return the next interval as a GridState snapshot."""
        if not self.has_next():
            raise StopIteration("No more intervals in CSV dataset")

        ds = self._dataset
        i = self._cursor
        self._cursor += 1

        # Extract price (always available)
        da_price = float(ds.da_prices[i]) if i < len(ds.da_prices) else 0.0

        # Extract power (if SEN nodo format with actual/theoretical)
        active_power = 0.0
        if ds.actual_mw is not None and i < len(ds.actual_mw):
            active_power = float(ds.actual_mw[i])

        # Synthesize realistic frequency from price (high price → stressed grid → lower f)
        price_stress = np.clip((da_price - 50) / 500, -0.02, 0.02)
        freq = self.f_nom + np.random.normal(0, 0.008) - price_stress

        # Synthesize voltage from load
        load_fraction = active_power / max(self.capacity_mw, 1)
        voltage = self.v_nom * (1.0 - load_fraction * 0.01 + np.random.normal(0, 0.001))

        # Timestamp
        if ds.timestamps and i < len(ds.timestamps):
            try:
                ts = ds.timestamps[i]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                ts = datetime.now() + timedelta(minutes=15 * i)
        else:
            ts = datetime.now() + timedelta(minutes=15 * i)

        return GridState(
            frequency_hz=round(freq, 4),
            voltage_a_kv=round(voltage, 2),
            active_power_mw=round(active_power, 2),
            lmp_price=round(da_price, 2),
            node_id=self.node_id,
            market=self.market.upper(),
            timestamp=ts,
            quality="GOOD",
        )

    def _write_setpoint_impl(self, setpoint: ControlSetpoint) -> bool:
        """Log the setpoint for backtesting analysis (no hardware write)."""
        self._results.append({
            "interval": self._cursor - 1,
            "optimal_mw": setpoint.active_power_mw,
            "mode": setpoint.mode_label,
            "actual_mw": self._last_state.active_power_mw if self._last_state else 0,
            "lmp": self._last_state.lmp_price if self._last_state else 0,
            "solver_ms": setpoint.solver_time_ms,
        })
        return True

    def get_results(self) -> list:
        """Return all logged setpoints for post-analysis."""
        return self._results

    def compute_savings(self, interval_hours: float = 0.25) -> dict:
        """Calculate total capital rescued from the backtest."""
        total_rescued = 0.0
        for r in self._results:
            delta_mw = r["optimal_mw"] - r["actual_mw"]
            if delta_mw > 0:
                total_rescued += delta_mw * r["lmp"] * interval_hours

        return {
            "total_rescued_usd": round(total_rescued, 2),
            "intervals": len(self._results),
            "avg_rescue_per_interval": round(
                total_rescued / max(len(self._results), 1), 2
            ),
        }
