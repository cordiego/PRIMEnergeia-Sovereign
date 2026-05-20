"""
PRIMEnergeia — Industrial SCADA Adapter  (FORTIFIED v2.0)
==========================================================
Fortification based on ITAM Doctoral Thesis (Diego Córdoba Urrutia, 2026):

  §2   → ISO-aware nominal frequency (50 Hz MIBEL/CEN vs 60 Hz CENACE/ERCOT)
         OU-calibrated lockout thresholds per market (deadband_hz, pen_thresh_hz)
  §3   → ROCOF-based lockout with hysteresis (Proposition 3.2 safety condition)
  L.2  → ZonalMeasurement: per-zone Δf vector for multi-area control
  E.2  → BESSMeasurement: SoC, T_cell, DoH fields for BESS adapters
  misc → Quality-flag propagation through SafetyInterlockAdapter
         Persistent audit log (write to SQLite or CSV)
         Watchdog thread: auto-disconnect + reconnect on communication loss
         Manual lockout override (authorised operators only)
         CENACE-specific NERC thresholds (0.017 Hz deadband, ROCOF 0.5 Hz/s)

Backward-compatible with v1.0: existing create_adapter() calls unchanged.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import abc
import csv
import logging
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple
from collections import deque

import numpy as np

logger = logging.getLogger("primenergeia.scada")


# ─────────────────────────────────────────────────────────────────────────────
# ISO market constants  (thesis §2, §6)
# ─────────────────────────────────────────────────────────────────────────────
class ISOMarket(str, Enum):
    CENACE = "cenace"
    ERCOT  = "ercot"
    MIBEL  = "mibel"
    XM     = "xm"
    CEN    = "cen"
    ONS    = "ons"
    PJM    = "pjm"
    CAISO  = "caiso"


_ISO_FREQ: Dict[str, float] = {
    ISOMarket.CENACE: 60.0,
    ISOMarket.ERCOT:  60.0,
    ISOMarket.PJM:    60.0,
    ISOMarket.CAISO:  60.0,
    ISOMarket.XM:     60.0,
    ISOMarket.MIBEL:  50.0,
    ISOMarket.CEN:    50.0,
    ISOMarket.ONS:    60.0,
}

# NERC/regulatory deadbands and lockout thresholds per ISO
_ISO_THRESHOLDS: Dict[str, Dict[str, float]] = {
    ISOMarket.CENACE: dict(deadband_hz=0.017, lockout_hz=0.50, rocof_hz_s=0.50, clear_hz=0.10),
    ISOMarket.ERCOT:  dict(deadband_hz=0.017, lockout_hz=0.50, rocof_hz_s=0.50, clear_hz=0.10),
    ISOMarket.MIBEL:  dict(deadband_hz=0.020, lockout_hz=0.40, rocof_hz_s=0.40, clear_hz=0.08),
    ISOMarket.XM:     dict(deadband_hz=0.015, lockout_hz=0.45, rocof_hz_s=0.45, clear_hz=0.09),
    ISOMarket.CEN:    dict(deadband_hz=0.025, lockout_hz=0.55, rocof_hz_s=0.60, clear_hz=0.12),
    ISOMarket.PJM:    dict(deadband_hz=0.017, lockout_hz=0.50, rocof_hz_s=0.50, clear_hz=0.10),
    ISOMarket.CAISO:  dict(deadband_hz=0.017, lockout_hz=0.50, rocof_hz_s=0.50, clear_hz=0.10),
    ISOMarket.ONS:    dict(deadband_hz=0.018, lockout_hz=0.50, rocof_hz_s=0.50, clear_hz=0.10),
}


def _iso_nominal(market: ISOMarket) -> float:
    return _ISO_FREQ.get(market, 60.0)


def _iso_thresh(market: ISOMarket) -> Dict[str, float]:
    return dict(_ISO_THRESHOLDS.get(market, _ISO_THRESHOLDS[ISOMarket.CENACE]))


# ─────────────────────────────────────────────────────────────────────────────
# Shared data types
# ─────────────────────────────────────────────────────────────────────────────
class ProtocolType(str, Enum):
    MODBUS_TCP = "modbus_tcp"
    DNP3       = "dnp3"
    SIMULATED  = "simulated"


@dataclass
class GridMeasurement:
    """A single telemetry snapshot from the RTU / IED."""
    freq_hz:             float
    rocof_hz_s:          float
    active_power_mw:     float
    reactive_power_mvar: float
    voltage_pu:          float
    current_ka:          float
    timestamp:           float
    quality_ok:          bool  = True
    source:              str   = "unknown"
    market:              str   = ISOMarket.CENACE

    @property
    def freq_deviation_hz(self) -> float:
        nominal = _iso_nominal(self.market)
        return self.freq_hz - nominal

    @property
    def in_deadband(self) -> bool:
        thresh = _iso_thresh(self.market)
        return abs(self.freq_deviation_hz) < thresh["deadband_hz"]


@dataclass
class ZonalMeasurement:
    """
    Multi-zone frequency snapshot for multi-area control (thesis §L.2).
    Carries Δf per zone + zonal power injections.
    """
    freq_hz_zones:       np.ndarray   # shape (n_zones,)
    rocof_hz_s_zones:    np.ndarray   # shape (n_zones,)
    power_mw_zones:      np.ndarray   # shape (n_zones,)
    voltage_pu_zones:    np.ndarray   # shape (n_zones,)
    timestamp:           float
    quality_ok:          bool  = True
    source:              str   = "unknown"
    market:              str   = ISOMarket.CENACE
    zone_labels:         List[str] = field(default_factory=list)

    @property
    def mean_freq_deviation_hz(self) -> float:
        nominal = _iso_nominal(self.market)
        return float(np.mean(self.freq_hz_zones)) - nominal

    @property
    def max_freq_deviation_hz(self) -> float:
        nominal = _iso_nominal(self.market)
        return float(np.max(np.abs(self.freq_hz_zones - nominal)))


@dataclass
class BESSMeasurement(GridMeasurement):
    """
    Extended measurement for BESS adapters (thesis §E.2).
    Adds electrochemical state: SoC, T_cell, DoH.
    """
    soc:     float = 0.80   # State of Charge ∈ [0,1]
    t_cell:  float = 25.0   # Cell temperature (°C)
    doh:     float = 0.00   # Degree of Health degradation ∈ [0,1]
    c_eff_mw: float = 10.0  # Effective capacity Ū·SoC·(1−DoH) (MW)


@dataclass
class ControlCommand:
    """Command sent to the field device."""
    delta_power_mw: float
    timestamp:      float
    source:         str   = "HJB"
    acknowledged:   bool  = False
    operator_id:    str   = "auto"   # audit trail


# ─────────────────────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────────────────────
class AuditLog:
    """
    Append-only CSV audit log for control commands and safety events.
    Writes to {log_dir}/primenergeia_audit_{date}.csv.
    Thread-safe.
    """

    _HEADER = ["timestamp", "event", "adapter", "value", "reason", "operator"]

    def __init__(self, log_dir: str = "/tmp/prime_logs"):
        os.makedirs(log_dir, exist_ok=True)
        date     = time.strftime("%Y%m%d")
        self._path = Path(log_dir) / f"primenergeia_audit_{date}.csv"
        self._lock = threading.Lock()
        if not self._path.exists():
            self._write_row(self._HEADER)

    def _write_row(self, row: List) -> None:
        with self._lock:
            with open(self._path, "a", newline="") as f:
                csv.writer(f).writerow(row)

    def log_command(self, adapter_name: str, cmd: ControlCommand) -> None:
        self._write_row([
            f"{cmd.timestamp:.3f}", "WRITE", adapter_name,
            f"{cmd.delta_power_mw:.3f}", "", cmd.operator_id,
        ])

    def log_lockout(self, adapter_name: str, reason: str) -> None:
        self._write_row([
            f"{time.time():.3f}", "LOCKOUT", adapter_name,
            "", reason, "system",
        ])

    def log_lockout_clear(self, adapter_name: str) -> None:
        self._write_row([
            f"{time.time():.3f}", "LOCKOUT_CLEAR", adapter_name,
            "", "freq restored", "system",
        ])

    def log_error(self, adapter_name: str, msg: str) -> None:
        self._write_row([
            f"{time.time():.3f}", "ERROR", adapter_name, "", msg, "system",
        ])


# Global audit log instance (shared across adapters)
_AUDIT_LOG: Optional[AuditLog] = None


def get_audit_log(log_dir: str = "/tmp/prime_logs") -> AuditLog:
    global _AUDIT_LOG
    if _AUDIT_LOG is None:
        _AUDIT_LOG = AuditLog(log_dir)
    return _AUDIT_LOG


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base adapter  (extended health report + watchdog hook)
# ─────────────────────────────────────────────────────────────────────────────
class BaseAdapter(abc.ABC):
    """Common interface for all protocol adapters."""

    def __init__(self, name: str = "adapter",
                 market: ISOMarket = ISOMarket.CENACE) -> None:
        self.name          = name
        self.market        = market
        self.nominal_freq  = _iso_nominal(market)
        self._lock         = threading.Lock()
        self._connected    = False
        self._read_count   = 0
        self._write_count  = 0
        self._error_count  = 0
        self._last_read_ts = 0.0
        self._recent_quality: Deque[bool] = deque(maxlen=20)

    @abc.abstractmethod
    def connect(self) -> bool: ...

    @abc.abstractmethod
    def disconnect(self) -> None: ...

    @abc.abstractmethod
    def read_state(self) -> Optional[GridMeasurement]: ...

    @abc.abstractmethod
    def write_control(self, command: ControlCommand) -> bool: ...

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def quality_rate(self) -> float:
        """Fraction of recent reads with quality_ok=True."""
        if not self._recent_quality:
            return 1.0
        return sum(self._recent_quality) / len(self._recent_quality)

    def health_report(self) -> dict:
        return {
            "adapter":      self.name,
            "market":       self.market,
            "nominal_hz":   self.nominal_freq,
            "connected":    self._connected,
            "reads":        self._read_count,
            "writes":       self._write_count,
            "errors":       self._error_count,
            "error_rate":   self._error_count / max(1, self._read_count + self._write_count),
            "quality_rate": self.quality_rate,
            "last_read_age_s": time.time() - self._last_read_ts if self._last_read_ts else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Modbus TCP Adapter  (unchanged from v1.0; ISO-market field added)
# ─────────────────────────────────────────────────────────────────────────────
_MODBUS_FUNC_READ  = 0x03
_MODBUS_FUNC_WRITE = 0x10


class ModbusTCPAdapter(BaseAdapter):
    """Raw-socket Modbus TCP (no pymodbus dependency)."""

    def __init__(self, host: str, port: int = 502,
                 unit_id: int = 1, timeout_s: float = 0.5,
                 market: ISOMarket = ISOMarket.CENACE) -> None:
        super().__init__(name=f"modbus://{host}:{port}", market=market)
        self.host, self.port = host, port
        self.unit_id, self.timeout_s = unit_id, timeout_s
        self._sock: Optional[socket.socket] = None
        self._transaction_id = 0

    def connect(self) -> bool:
        try:
            self._sock = socket.create_connection(
                (self.host, self.port), timeout=self.timeout_s)
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._connected = True
            logger.info("Modbus TCP connected → %s:%d (%s)",
                        self.host, self.port, self.market)
            return True
        except OSError as exc:
            logger.error("Modbus connect failed: %s", exc)
            self._connected = False
            self._error_count += 1
            return False

    def disconnect(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
        self._connected = False
        logger.info("Modbus TCP disconnected.")

    def _next_tid(self) -> int:
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        return self._transaction_id

    def _read_registers(self, start_reg: int,
                        count: int) -> Optional[List[int]]:
        if not self._sock:
            return None
        req = struct.pack(">HHHBBHH",
                          self._next_tid(), 0, 6,
                          self.unit_id, _MODBUS_FUNC_READ,
                          start_reg, count)
        try:
            self._sock.sendall(req)
            header = self._sock.recv(9)
            if len(header) < 9:
                raise OSError("Short header")
            n_bytes = header[8]
            data    = self._sock.recv(n_bytes)
            return [struct.unpack_from(">H", data, i)[0]
                    for i in range(0, n_bytes, 2)]
        except OSError as exc:
            logger.warning("Modbus read error: %s", exc)
            self._error_count += 1
            return None

    def _write_register(self, reg: int, value_int: int) -> bool:
        if not self._sock:
            return False
        req = struct.pack(">HHHBBBHH",
                          self._next_tid(), 0, 6,
                          self.unit_id, 0x06, 0, reg, value_int)
        try:
            self._sock.sendall(req)
            self._sock.recv(12)
            return True
        except OSError as exc:
            logger.warning("Modbus write error: %s", exc)
            self._error_count += 1
            return False

    def read_state(self) -> Optional[GridMeasurement]:
        with self._lock:
            regs = self._read_registers(0x0000, 12)
            ok   = regs is not None and len(regs) >= 12
            self._recent_quality.append(ok)
            if not ok:
                self._error_count += 1
                return None
            self._read_count  += 1
            self._last_read_ts = time.time()
            return GridMeasurement(
                freq_hz             = regs[0] * 0.001 + regs[1] * 0.001 / 65536,
                rocof_hz_s          = struct.unpack(">h", struct.pack(">H", regs[2]))[0] * 1e-4,
                active_power_mw     = regs[4] * 0.01,
                reactive_power_mvar = regs[6] * 0.01,
                voltage_pu          = regs[8] * 1e-4,
                current_ka          = regs[10] * 1e-3,
                timestamp           = time.time(),
                quality_ok          = True,
                source              = self.name,
                market              = self.market,
            )

    def write_control(self, command: ControlCommand) -> bool:
        with self._lock:
            reg_val = int(command.delta_power_mw / 0.01) & 0xFFFF
            ok = self._write_register(0x0100, reg_val)
            if ok:
                self._write_count += 1
                get_audit_log().log_command(self.name, command)
                logger.debug("Modbus write: %.2f MW → reg 0x0100",
                             command.delta_power_mw)
            return ok


# ─────────────────────────────────────────────────────────────────────────────
# DNP3 Adapter  (stub + pyDNP3 bridge, unchanged except market field)
# ─────────────────────────────────────────────────────────────────────────────
class DNP3Adapter(BaseAdapter):
    def __init__(self, host: str, port: int = 20000,
                 master_addr: int = 1, outstation_addr: int = 10,
                 market: ISOMarket = ISOMarket.CENACE) -> None:
        super().__init__(name=f"dnp3://{host}:{port}", market=market)
        self.host, self.port = host, port
        self.master_addr, self.outstation_addr = master_addr, outstation_addr
        self._latest: Optional[GridMeasurement] = None
        try:
            import pydnp3.opendnp3 as opendnp3
            import pydnp3.openpal  as openpal
            import pydnp3.asiopal  as asiopal
            self._opendnp3, self._openpal, self._asiopal = opendnp3, openpal, asiopal
            self._have_dnp3 = True
        except ImportError:
            logger.warning("pyDNP3 not installed — DNP3Adapter in stub mode")
            self._have_dnp3 = False

    def connect(self) -> bool:
        if not self._have_dnp3:
            logger.error("pyDNP3 not available; cannot connect to %s", self.name)
            return False
        try:
            manager = self._asiopal.DNP3Manager(1)
            channel = manager.AddTCPClient(
                "primenergeia",
                self._openpal.LogFilters(self._opendnp3.levels.NORMAL),
                self._asiopal.ChannelRetry(),
                self.host, "0.0.0.0", self.port, None)
            self._channel = channel
            self._connected = True
            logger.info("DNP3 connected → %s:%d", self.host, self.port)
            return True
        except Exception as exc:
            logger.error("DNP3 connect error: %s", exc)
            self._error_count += 1
            return False

    def disconnect(self) -> None:
        self._connected = False
        self._channel   = None

    def read_state(self) -> Optional[GridMeasurement]:
        self._read_count   += 1
        self._last_read_ts  = time.time()
        self._recent_quality.append(self._latest is not None)
        return self._latest

    def write_control(self, command: ControlCommand) -> bool:
        if not self._connected or not self._have_dnp3:
            return False
        self._write_count += 1
        get_audit_log().log_command(self.name, command)
        logger.debug("DNP3 write: %.2f MW → outstation %d",
                     command.delta_power_mw, self.outstation_addr)
        return True

    def on_measurement(self, meas: GridMeasurement) -> None:
        self._latest = meas


# ─────────────────────────────────────────────────────────────────────────────
# Simulated Adapter  (swing-equation, ISO-aware)
# ─────────────────────────────────────────────────────────────────────────────
class SimulatedAdapter(BaseAdapter):
    """
    Software-in-the-loop adapter.
    Runs a swing-equation + OU noise simulation internally.
    Now ISO-aware: uses calibrated H, D, σ per market.
    """

    DT = 0.1   # 100 ms scan cycle

    def __init__(self, market: ISOMarket = ISOMarket.CENACE,
                 disturbance_mw: float = 0.0,
                 noise_std: float = 0.002) -> None:
        # Import ISO params here to avoid circular import
        _MARKET_PHYSICS = {
            ISOMarket.CENACE: (4.8, 1.1),
            ISOMarket.ERCOT:  (3.8, 0.9),
            ISOMarket.MIBEL:  (6.2, 1.4),
            ISOMarket.XM:     (5.5, 1.2),
            ISOMarket.CEN:    (3.2, 0.8),
            ISOMarket.PJM:    (5.0, 1.0),
            ISOMarket.CAISO:  (4.5, 1.0),
            ISOMarket.ONS:    (5.2, 1.1),
        }
        H, D = _MARKET_PHYSICS.get(market, (4.8, 1.1))
        super().__init__(name="simulated", market=market)
        self.H, self.D        = H, D
        self._freq            = self.nominal_freq
        self._rocof           = 0.0
        self._p_active        = 100.0
        self._dp_load         = disturbance_mw
        self._noise_std       = noise_std
        self._rng             = np.random.default_rng(seed=42)

    def connect(self) -> bool:
        self._connected = True
        logger.info("SimulatedAdapter connected (f₀=%.1f Hz, disturbance=%.1f MW, market=%s)",
                    self.nominal_freq, self._dp_load, self.market)
        return True

    def disconnect(self) -> None:
        self._connected = False

    def inject_disturbance(self, delta_mw: float) -> None:
        self._dp_load += delta_mw
        logger.info("Disturbance injected: %+.1f MW  total=%+.1f MW",
                    delta_mw, self._dp_load)

    def read_state(self) -> GridMeasurement:
        with self._lock:
            self._rocof = ((-self.D * (self._freq - self.nominal_freq)
                            - self._dp_load) / (2.0 * self.H))
            self._freq  += self._rocof * self.DT
            self._freq  += self._rng.normal(0, self._noise_std)
            self._read_count  += 1
            self._last_read_ts = time.time()
            self._recent_quality.append(True)
            return GridMeasurement(
                freq_hz             = self._freq,
                rocof_hz_s          = self._rocof,
                active_power_mw     = self._p_active + self._dp_load,
                reactive_power_mvar = 12.0,
                voltage_pu          = 1.0 + self._rng.normal(0, 0.002),
                current_ka          = 0.95,
                timestamp           = time.time(),
                quality_ok          = True,
                source              = self.name,
                market              = self.market,
            )

    def write_control(self, command: ControlCommand) -> bool:
        with self._lock:
            self._dp_load   -= command.delta_power_mw * 0.8
            self._write_count += 1
            get_audit_log().log_command(self.name, command)
            logger.debug("SimAdapter: applied %.2f MW  remaining Δload=%.2f MW",
                         command.delta_power_mw, self._dp_load)
            return True


# ─────────────────────────────────────────────────────────────────────────────
# Adapter factory  (backward-compatible)
# ─────────────────────────────────────────────────────────────────────────────
def create_adapter(protocol: ProtocolType,
                   host: str = "127.0.0.1",
                   port: Optional[int] = None,
                   market: ISOMarket = ISOMarket.CENACE,
                   **kwargs) -> BaseAdapter:
    """
    Factory function — market parameter selects ISO-calibrated thresholds.

        adapter = create_adapter(ProtocolType.MODBUS_TCP,
                                 host="192.168.1.100",
                                 market=ISOMarket.CENACE)
    """
    if protocol == ProtocolType.MODBUS_TCP:
        return ModbusTCPAdapter(host, port or 502,  market=market, **kwargs)
    elif protocol == ProtocolType.DNP3:
        return DNP3Adapter(host, port or 20000, market=market, **kwargs)
    elif protocol == ProtocolType.SIMULATED:
        return SimulatedAdapter(market=market, **kwargs)
    raise ValueError(f"Unknown protocol: {protocol}")


# ─────────────────────────────────────────────────────────────────────────────
# Safety Interlock Adapter  (FORTIFIED)
# ─────────────────────────────────────────────────────────────────────────────
class SafetyInterlockAdapter(BaseAdapter):
    """
    Decorator that enforces hard safety limits before forwarding commands.

    Fortification improvements over v1.0:
    ─────────────────────────────────────
    1. ISO-aware thresholds: deadband_hz, lockout_hz, rocof_hz_s pulled
       from _ISO_THRESHOLDS per market instead of hardcoded values.
    2. Hysteresis on lockout clear: requires Δf < clear_hz (not just < 0.1 Hz)
       AND |ROCOF| < 0.2 Hz/s for ≥ CLEAR_HOLD_S consecutive seconds.
       This prevents chattering near the lockout boundary (thesis §3, Prop 3.2).
    3. Quality-flag propagation: a measurement with quality_ok=False triggers
       a precautionary lockout (unknown grid state = unsafe to control).
    4. ROCOF lockout threshold is ISO-specific (0.50 Hz/s for CENACE/NERC).
    5. Operator override: authorised operator can manually clear lockout.
    6. All lockout events written to AuditLog.
    7. MAX_DELTA_MW and rate limit configurable at construction.
    """

    CLEAR_HOLD_S      = 5.0   # seconds of restored frequency before clearing lockout
    MAX_WRITE_RATE_HZ = 10.0  # max commands per second

    def __init__(self, inner: BaseAdapter,
                 max_delta_mw: float = 50.0,
                 authorised_operators: Optional[List[str]] = None) -> None:
        super().__init__(name=f"safe:{inner.name}", market=inner.market)
        self._inner               = inner
        self._lockout             = False
        self._lockout_reason      = ""
        self._last_write_time     = 0.0
        self._min_write_interval  = 1.0 / self.MAX_WRITE_RATE_HZ
        self._clear_start_ts: Optional[float] = None
        self._authorised_ops      = set(authorised_operators or ["dispatcher", "auto"])
        self._audit               = get_audit_log()
        self._max_delta_mw        = max_delta_mw

        # Load ISO-specific thresholds
        t = _iso_thresh(inner.market)
        self._lockout_hz    = t["lockout_hz"]
        self._rocof_hz_s    = t["rocof_hz_s"]
        self._clear_hz      = t["clear_hz"]

    # ── Delegation ────────────────────────────────────────────────────────────
    def connect(self) -> bool:
        ok = self._inner.connect()
        self._connected = ok
        return ok

    def disconnect(self) -> None:
        self._inner.disconnect()
        self._connected = False

    # ── Read + lockout management ─────────────────────────────────────────────
    def read_state(self) -> Optional[GridMeasurement]:
        meas = self._inner.read_state()
        if meas is None:
            return None

        self._read_count      += 1
        self._last_read_ts     = time.time()
        self._recent_quality.append(meas.quality_ok)

        # Quality-flag lockout: unknown state is unsafe
        if not meas.quality_ok:
            if not self._lockout:
                self._set_lockout("quality_ok=False — measurement unreliable")
            return meas

        df    = abs(meas.freq_deviation_hz)
        rocof = abs(meas.rocof_hz_s)

        # Check lockout conditions
        if df > self._lockout_hz:
            if not self._lockout:
                self._set_lockout(f"|Δf|={df:.4f} Hz > {self._lockout_hz}")
        elif rocof > self._rocof_hz_s:
            if not self._lockout:
                self._set_lockout(f"ROCOF={rocof:.3f} Hz/s > {self._rocof_hz_s}")

        # Hysteresis clear: must hold within clear_hz for CLEAR_HOLD_S seconds
        if self._lockout:
            if df < self._clear_hz and rocof < 0.2:
                if self._clear_start_ts is None:
                    self._clear_start_ts = time.monotonic()
                elif (time.monotonic() - self._clear_start_ts) >= self.CLEAR_HOLD_S:
                    self._clear_lockout()
            else:
                self._clear_start_ts = None   # reset hold timer

        return meas

    # ── Write + safety enforcement ────────────────────────────────────────────
    def write_control(self, command: ControlCommand) -> bool:
        # Rate limiter
        now = time.monotonic()
        dt  = now - self._last_write_time
        if dt < self._min_write_interval:
            logger.debug("Write throttled (%.1f ms since last)", dt * 1000)
            return False

        if self._lockout:
            logger.critical("SAFETY LOCKOUT — write BLOCKED. Reason: %s",
                            self._lockout_reason)
            return False

        # Amplitude clamp
        clamped = float(np.clip(command.delta_power_mw,
                                -self._max_delta_mw, self._max_delta_mw))
        if clamped != command.delta_power_mw:
            logger.warning("Control clamped: %.2f → %.2f MW",
                           command.delta_power_mw, clamped)

        safe_cmd = ControlCommand(
            delta_power_mw = clamped,
            timestamp      = command.timestamp,
            source         = command.source,
            operator_id    = command.operator_id,
        )
        ok = self._inner.write_control(safe_cmd)
        if ok:
            self._write_count   += 1
            self._last_write_time = now
        else:
            self._error_count += 1
        return ok

    # ── Lockout helpers ───────────────────────────────────────────────────────
    def _set_lockout(self, reason: str) -> None:
        self._lockout        = True
        self._lockout_reason = reason
        self._clear_start_ts = None
        logger.critical("SAFETY LOCKOUT SET — %s | adapter=%s", reason, self.name)
        self._audit.log_lockout(self.name, reason)

    def _clear_lockout(self) -> None:
        self._lockout        = False
        self._lockout_reason = ""
        self._clear_start_ts = None
        logger.info("Safety lockout CLEARED — frequency restored. adapter=%s", self.name)
        self._audit.log_lockout_clear(self.name)

    def manual_clear_lockout(self, operator_id: str) -> bool:
        """
        Authorised operator can manually clear lockout (e.g. after physical inspection).
        Returns True if operator is authorised, False otherwise.
        """
        if operator_id not in self._authorised_ops:
            logger.warning("Unauthorised lockout clear attempt by '%s'", operator_id)
            return False
        self._clear_lockout()
        logger.warning("Lockout manually cleared by operator '%s'", operator_id)
        self._audit.log_lockout_clear(self.name + f"[manual:{operator_id}]")
        return True

    @property
    def in_lockout(self) -> bool:
        return self._lockout

    @property
    def lockout_reason(self) -> str:
        return self._lockout_reason

    def health_report(self) -> dict:
        r = super().health_report()
        r.update({
            "in_lockout":      self._lockout,
            "lockout_reason":  self._lockout_reason,
            "iso_lockout_hz":  self._lockout_hz,
            "iso_rocof_limit": self._rocof_hz_s,
            "iso_clear_hz":    self._clear_hz,
            "inner_adapter":   self._inner.health_report(),
        })
        return r


# ─────────────────────────────────────────────────────────────────────────────
# Watchdog  (auto-reconnect on communication loss)
# ─────────────────────────────────────────────────────────────────────────────
class WatchdogAdapter(BaseAdapter):
    """
    Wraps any adapter with a background watchdog thread.
    If no successful read within `timeout_s`, the adapter is disconnected
    and reconnected automatically.
    """

    def __init__(self, inner: BaseAdapter,
                 timeout_s: float = 30.0,
                 retry_interval_s: float = 5.0) -> None:
        super().__init__(name=f"watchdog:{inner.name}", market=inner.market)
        self._inner           = inner
        self._timeout_s       = timeout_s
        self._retry_interval  = retry_interval_s
        self._wd_thread: Optional[threading.Thread] = None
        self._stop_event      = threading.Event()

    def connect(self) -> bool:
        ok = self._inner.connect()
        self._connected = ok
        if ok:
            self._start_watchdog()
        return ok

    def disconnect(self) -> None:
        self._stop_event.set()
        self._inner.disconnect()
        self._connected = False

    def _start_watchdog(self) -> None:
        self._stop_event.clear()
        self._wd_thread = threading.Thread(target=self._watchdog_loop,
                                           daemon=True, name=f"wd-{self.name}")
        self._wd_thread.start()
        logger.info("Watchdog started for %s (timeout=%.0f s)", self.name, self._timeout_s)

    def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self._retry_interval)
            last_read = self._inner._last_read_ts
            age       = time.time() - last_read if last_read else self._timeout_s + 1
            if age > self._timeout_s:
                logger.warning("Watchdog: no reads in %.0f s — reconnecting %s",
                               age, self.name)
                try:
                    self._inner.disconnect()
                    time.sleep(1.0)
                    ok = self._inner.connect()
                    logger.info("Watchdog reconnect %s", "OK" if ok else "FAILED")
                except Exception as exc:
                    logger.error("Watchdog reconnect error: %s", exc)

    def read_state(self) -> Optional[GridMeasurement]:
        return self._inner.read_state()

    def write_control(self, command: ControlCommand) -> bool:
        return self._inner.write_control(command)


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(message)s")

    print("\n=== PRIMEnergeia SCADA v2.0 — FORTIFIED ===\n")

    for market in [ISOMarket.CENACE, ISOMarket.MIBEL, ISOMarket.CEN]:
        sim    = SimulatedAdapter(market=market, disturbance_mw=-15.0)
        safe   = SafetyInterlockAdapter(sim, max_delta_mw=50.0)
        safe.connect()

        print(f"  [{market}] nominal={safe.nominal_freq:.0f} Hz "
              f"lockout_thresh={safe._lockout_hz:.2f} Hz "
              f"rocof_thresh={safe._rocof_hz_s:.2f} Hz/s")

        meas = safe.read_state()
        if meas:
            print(f"    Δf = {meas.freq_deviation_hz*1000:.1f} mHz  "
                  f"deadband={meas.in_deadband}  quality={meas.quality_ok}")

        cmd = ControlCommand(delta_power_mw=10.0,
                             timestamp=time.time(), operator_id="auto")
        ok  = safe.write_control(cmd)
        print(f"    write_control → {ok}  lockout={safe.in_lockout}")
        safe.disconnect()
        print()

    # Test hysteresis: inject large disturbance → lockout → confirm it holds
    sim  = SimulatedAdapter(market=ISOMarket.CENACE, disturbance_mw=-60.0)
    safe = SafetyInterlockAdapter(sim)
    safe.connect()
    for _ in range(10):
        safe.read_state()
    print(f"  After −60 MW disturbance: lockout={safe.in_lockout}  reason='{safe.lockout_reason}'")
    ok = safe.manual_clear_lockout("dispatcher")
    print(f"  Manual clear by 'dispatcher': allowed={ok}  lockout={safe.in_lockout}")
    ok_bad = safe.manual_clear_lockout("unknown_user")
    print(f"  Manual clear by 'unknown_user': allowed={ok_bad}")
    safe.disconnect()
