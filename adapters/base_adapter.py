"""
PRIMEnergeia — Base Adapter (Abstract Interface)
===================================================
Defines the universal contract that all protocol adapters implement.
Any adapter — CSV, API, OPC UA, Modbus, IEC 61850 — exposes the
same read_state() / write_setpoint() interface so the HJB solver
never knows (or cares) what protocol is underneath.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger("prime.adapters")


# ============================================================
#  Data Classes — Standard Grid State & Control Setpoint
# ============================================================

@dataclass
class GridState:
    """Snapshot of plant electrical measurements at a single instant.

    This is the universal input to the HJB solver — regardless of whether
    the data came from a CSV file, an OPC UA server, or a PMU stream.
    """
    # --- Core measurements (always populated) ---
    frequency_hz: float = 60.0
    voltage_a_kv: float = 0.0
    active_power_mw: float = 0.0

    # --- Optional measurements ---
    voltage_b_kv: float = 0.0
    voltage_c_kv: float = 0.0
    reactive_power_mvar: float = 0.0
    power_factor: float = 1.0
    rocof_hz_s: float = 0.0       # Rate of Change of Frequency
    thd_pct: float = 0.0          # Total Harmonic Distortion

    # --- Market context ---
    lmp_price: float = 0.0        # Locational Marginal Price ($/MWh)
    node_id: str = ""             # ISO node identifier
    market: str = ""              # Market name (ERCOT, SEN, MIBEL, etc.)

    # --- Metadata ---
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""              # Adapter name that produced this state
    quality: str = "GOOD"         # GOOD / UNCERTAIN / BAD / SIMULATED

    def is_nominal(self, f_nom: float = 60.0, tolerance_hz: float = 0.05) -> bool:
        """Check if frequency is within nominal tolerance."""
        return abs(self.frequency_hz - f_nom) < tolerance_hz

    def to_dict(self) -> dict:
        """Serialize to dictionary for logging/JSON."""
        return {
            "f": self.frequency_hz,
            "v_a": self.voltage_a_kv,
            "p_mw": self.active_power_mw,
            "q_mvar": self.reactive_power_mvar,
            "pf": self.power_factor,
            "rocof": self.rocof_hz_s,
            "thd": self.thd_pct,
            "lmp": self.lmp_price,
            "node": self.node_id,
            "market": self.market,
            "ts": self.timestamp.isoformat(),
            "source": self.source,
            "quality": self.quality,
        }


@dataclass
class ControlSetpoint:
    """Optimal command to send back to the plant.

    Computed by the HJB solver. The adapter is responsible for
    translating this into the plant's native protocol (Modbus
    registers, OPC UA tags, IEC 61850 control objects, etc.)
    """
    active_power_mw: float = 0.0     # Optimal MW dispatch
    reactive_power_mvar: float = 0.0  # Optimal MVAR dispatch
    mode: int = 0                     # 0=HOLD, 1=CHARGE, 2=DISCHARGE
    mode_label: str = "HOLD"          # Human-readable mode

    # --- Optional sub-signals ---
    frequency_droop_pct: float = 5.0  # Governor droop setting
    voltage_setpoint_kv: float = 0.0  # AVR voltage setpoint
    inertia_injection_pu: float = 0.0 # Synthetic inertia from HJB

    # --- Metadata ---
    timestamp: datetime = field(default_factory=datetime.now)
    solver_time_ms: float = 0.0       # How long HJB took to compute
    confidence: float = 1.0           # 0.0–1.0 solver confidence

    MODE_LABELS = {0: "HOLD", 1: "CHARGE", 2: "DISCHARGE"}

    def __post_init__(self):
        if self.mode in self.MODE_LABELS:
            self.mode_label = self.MODE_LABELS[self.mode]


# ============================================================
#  Abstract Base — All Adapters Must Implement This
# ============================================================

class PlantAdapter(ABC):
    """Abstract interface for power plant data connectivity.

    Every adapter — regardless of protocol — provides exactly
    two operations:

        1. read_state()      → GridState    (read from plant)
        2. write_setpoint()  → bool         (write to plant)

    Plus lifecycle management:

        3. connect()         → None         (open connection)
        4. close()           → None         (clean shutdown)
        5. is_connected      → bool         (health check)

    The HJB solver calls these methods in a tight loop:

        while True:
            state = adapter.read_state()
            setpoint = hjb.solve(state)
            adapter.write_setpoint(setpoint)
    """

    def __init__(self, name: str = "base", read_only: bool = False):
        self.name = name
        self.read_only = read_only
        self._connected = False
        self._read_count = 0
        self._write_count = 0
        self._error_count = 0
        self._last_state: Optional[GridState] = None
        self._last_setpoint: Optional[ControlSetpoint] = None
        logger.info(f"[{self.name}] Adapter initialized (read_only={read_only})")

    # --- Abstract methods to implement ---

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to plant data source."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Clean shutdown of connection."""
        ...

    @abstractmethod
    def _read_state_impl(self) -> GridState:
        """Protocol-specific state read (override this)."""
        ...

    @abstractmethod
    def _write_setpoint_impl(self, setpoint: ControlSetpoint) -> bool:
        """Protocol-specific setpoint write (override this)."""
        ...

    # --- Public interface (with telemetry wrapping) ---

    def read_state(self) -> GridState:
        """Read current plant state. Wraps _read_state_impl with telemetry."""
        try:
            state = self._read_state_impl()
            state.source = self.name
            self._last_state = state
            self._read_count += 1
            return state
        except Exception as e:
            self._error_count += 1
            logger.error(f"[{self.name}] Read failed: {e}")
            # Return last known good state if available
            if self._last_state:
                self._last_state.quality = "BAD"
                return self._last_state
            raise

    def write_setpoint(self, setpoint: ControlSetpoint) -> bool:
        """Write optimal setpoint to plant. Wraps _write_setpoint_impl with safety."""
        if self.read_only:
            logger.debug(f"[{self.name}] Read-only mode — setpoint logged but not written")
            self._last_setpoint = setpoint
            return True

        try:
            success = self._write_setpoint_impl(setpoint)
            if success:
                self._last_setpoint = setpoint
                self._write_count += 1
            return success
        except Exception as e:
            self._error_count += 1
            logger.error(f"[{self.name}] Write failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> Dict:
        """Adapter telemetry for monitoring dashboards."""
        return {
            "adapter": self.name,
            "connected": self._connected,
            "read_only": self.read_only,
            "reads": self._read_count,
            "writes": self._write_count,
            "errors": self._error_count,
            "last_state": self._last_state.to_dict() if self._last_state else None,
        }

    # --- Context manager support ---

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __repr__(self):
        status = "CONNECTED" if self._connected else "DISCONNECTED"
        return f"<{self.__class__.__name__} '{self.name}' [{status}] reads={self._read_count} writes={self._write_count}>"
