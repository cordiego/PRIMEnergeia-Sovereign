"""
PRIMEnergeia — Modbus TCP Adapter
====================================
Adapter for legacy PLCs, RTUs, and generator controllers via
Modbus TCP (IEEE standard, 30+ year protocol).

Every generator controller speaks Modbus. This adapter reads
holding registers for measurements and writes registers for
optimal dispatch setpoints.

Dependencies:
    pip install pymodbus

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import struct
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.adapters.modbus")

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    ModbusTcpClient = None


# ============================================================
#  Register Map — Configurable per plant
# ============================================================

@classmethod
def _default_register_map():
    """Standard Modbus register layout (override per plant)."""
    return {
        "read": {
            # signal_name: (register_address, count, data_type, scale_factor)
            "frequency_hz":        (1, 2, "float32", 1.0),
            "voltage_a_kv":        (3, 2, "float32", 1.0),
            "voltage_b_kv":        (5, 2, "float32", 1.0),
            "voltage_c_kv":        (7, 2, "float32", 1.0),
            "active_power_mw":     (9, 2, "float32", 1.0),
            "reactive_power_mvar": (11, 2, "float32", 1.0),
            "power_factor":        (13, 2, "float32", 1.0),
        },
        "write": {
            # signal_name: (register_address, data_type, scale_factor)
            "mw_setpoint":   (100, "uint16", 10.0),   # MW × 10
            "mvar_setpoint": (101, "uint16", 10.0),    # MVAR × 10
            "mode":          (102, "uint16", 1.0),     # 0=HOLD, 1=CHARGE, 2=DISCHARGE
        },
    }


class ModbusTCPAdapter(PlantAdapter):
    """Modbus TCP adapter for legacy PLCs and generator controllers.

    Usage:
        adapter = ModbusTCPAdapter(
            host="192.168.1.100",
            port=502,
            market="SEN",
            node_id="05-VZA-400",
        )

        with adapter:
            state = adapter.read_state()
            setpoint = hjb.solve(state)
            adapter.write_setpoint(setpoint)

    Register Map Configuration:
        Pass a custom register_map dict to override the default layout.
        Each read register: (address, count, type, scale)
        Each write register: (address, type, scale)
    """

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 502,
        unit_id: int = 1,
        market: str = "ERCOT",
        node_id: str = "",
        f_nom: float = 60.0,
        register_map: Optional[Dict] = None,
        read_only: bool = False,
        timeout_seconds: float = 3.0,
    ):
        super().__init__(name=f"modbus:{host}:{port}", read_only=read_only)

        if not MODBUS_AVAILABLE:
            raise ImportError(
                "pymodbus not found. Install with:\n"
                "  pip install pymodbus"
            )

        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.market = market
        self.node_id = node_id
        self.f_nom = f_nom
        self.timeout = timeout_seconds

        # Register map
        self.register_map = register_map or {
            "read": {
                "frequency_hz":        (1, 2, "float32", 1.0),
                "voltage_a_kv":        (3, 2, "float32", 1.0),
                "voltage_b_kv":        (5, 2, "float32", 1.0),
                "voltage_c_kv":        (7, 2, "float32", 1.0),
                "active_power_mw":     (9, 2, "float32", 1.0),
                "reactive_power_mvar": (11, 2, "float32", 1.0),
                "power_factor":        (13, 2, "float32", 1.0),
            },
            "write": {
                "mw_setpoint":   (100, "uint16", 10.0),
                "mvar_setpoint": (101, "uint16", 10.0),
                "mode":          (102, "uint16", 1.0),
            },
        }

        self._client: Optional[ModbusTcpClient] = None

    # --- Register Decoding Helpers ---

    @staticmethod
    def _decode_float32(registers: list) -> float:
        """Decode two 16-bit Modbus registers into IEEE 754 float32."""
        if len(registers) < 2:
            return 0.0
        raw_bytes = struct.pack(">HH", registers[0], registers[1])
        return struct.unpack(">f", raw_bytes)[0]

    @staticmethod
    def _decode_uint16(registers: list) -> int:
        """Decode a single 16-bit register."""
        return int(registers[0]) if registers else 0

    @staticmethod
    def _encode_uint16(value: float, scale: float) -> int:
        """Encode a float value into a scaled uint16 for writing."""
        return int(round(value * scale))

    # --- Lifecycle ---

    def connect(self) -> None:
        """Connect to Modbus TCP device."""
        self._client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.timeout,
        )

        if not self._client.connect():
            raise ConnectionError(
                f"Modbus TCP connection failed to {self.host}:{self.port}\n"
                f"Verify the RTU/PLC is powered on and the IP is correct."
            )

        self._connected = True
        logger.info(
            f"[{self.name}] Connected to {self.host}:{self.port} "
            f"(unit_id={self.unit_id})"
        )

    def close(self) -> None:
        """Disconnect from Modbus TCP device."""
        if self._client:
            self._client.close()
        self._connected = False
        logger.info(f"[{self.name}] Disconnected from {self.host}:{self.port}")

    # --- Read/Write Implementation ---

    def _read_register(self, address: int, count: int, data_type: str, scale: float) -> float:
        """Read and decode a single measurement from Modbus registers."""
        try:
            result = self._client.read_holding_registers(
                address=address,
                count=count,
                slave=self.unit_id,
            )
            if result.isError():
                logger.warning(f"[{self.name}] Register {address} read error: {result}")
                return 0.0

            if data_type == "float32":
                raw = self._decode_float32(result.registers)
            elif data_type == "uint16":
                raw = self._decode_uint16(result.registers)
            elif data_type == "int16":
                raw = result.registers[0]
                if raw > 32767:
                    raw -= 65536
            else:
                raw = result.registers[0]

            return raw / scale

        except Exception as e:
            logger.warning(f"[{self.name}] Register {address} exception: {e}")
            return 0.0

    def _read_state_impl(self) -> GridState:
        """Read all measurement registers from the Modbus device."""
        values = {}
        for signal_name, (addr, count, dtype, scale) in self.register_map["read"].items():
            values[signal_name] = self._read_register(addr, count, dtype, scale)

        return GridState(
            frequency_hz=round(values.get("frequency_hz", self.f_nom), 4),
            voltage_a_kv=round(values.get("voltage_a_kv", 0.0), 2),
            voltage_b_kv=round(values.get("voltage_b_kv", 0.0), 2),
            voltage_c_kv=round(values.get("voltage_c_kv", 0.0), 2),
            active_power_mw=round(values.get("active_power_mw", 0.0), 2),
            reactive_power_mvar=round(values.get("reactive_power_mvar", 0.0), 2),
            power_factor=round(values.get("power_factor", 1.0), 4),
            node_id=self.node_id,
            market=self.market,
            timestamp=datetime.now(),
            quality="GOOD",
        )

    def _write_setpoint_impl(self, setpoint: ControlSetpoint) -> bool:
        """Write optimal setpoints to Modbus registers."""
        success = True
        write_map = self.register_map.get("write", {})

        # Write MW setpoint
        if "mw_setpoint" in write_map:
            addr, dtype, scale = write_map["mw_setpoint"]
            value = self._encode_uint16(setpoint.active_power_mw, scale)
            try:
                result = self._client.write_register(
                    address=addr, value=value, slave=self.unit_id
                )
                if result.isError():
                    logger.error(f"[{self.name}] MW write error at reg {addr}")
                    success = False
            except Exception as e:
                logger.error(f"[{self.name}] MW write exception: {e}")
                success = False

        # Write MVAR setpoint
        if "mvar_setpoint" in write_map:
            addr, dtype, scale = write_map["mvar_setpoint"]
            value = self._encode_uint16(setpoint.reactive_power_mvar, scale)
            try:
                result = self._client.write_register(
                    address=addr, value=value, slave=self.unit_id
                )
                if result.isError():
                    success = False
            except Exception as e:
                logger.error(f"[{self.name}] MVAR write exception: {e}")
                success = False

        # Write mode
        if "mode" in write_map:
            addr, dtype, scale = write_map["mode"]
            try:
                result = self._client.write_register(
                    address=addr, value=int(setpoint.mode), slave=self.unit_id
                )
                if result.isError():
                    success = False
            except Exception as e:
                logger.error(f"[{self.name}] Mode write exception: {e}")
                success = False

        if success:
            logger.debug(
                f"[{self.name}] Registers written: "
                f"MW={setpoint.active_power_mw:.1f}, "
                f"MVAR={setpoint.reactive_power_mvar:.1f}, "
                f"mode={setpoint.mode}"
            )

        return success

    def scan_registers(
        self, start: int = 0, count: int = 50
    ) -> Dict[int, int]:
        """Scan a range of holding registers for site assessment.

        Returns a dict of {register_address: raw_value} for all
        registers that return valid data.
        """
        if not self._client:
            raise RuntimeError("Not connected")

        found = {}
        for addr in range(start, start + count):
            try:
                result = self._client.read_holding_registers(
                    address=addr, count=1, slave=self.unit_id
                )
                if not result.isError():
                    found[addr] = result.registers[0]
            except Exception:
                pass

        logger.info(
            f"[{self.name}] Register scan {start}–{start+count}: "
            f"{len(found)} active registers found"
        )
        return found
