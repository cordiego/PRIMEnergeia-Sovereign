"""
PRIMEnergeia — IEC 61850 Adapter
===================================
Production-grade adapter for IEC 61850 (substation automation standard).
Supports MMS (Manufacturing Message Specification) for configuration reads
and GOOSE (Generic Object Oriented Substation Event) for sub-millisecond
event-driven control — the protocol needed for synthetic inertia injection.

IEC 61850 is the gold standard for modern digital substations.
All protection relays, breaker controllers, and IEDs from
ABB, Siemens, GE, SEL, and Schneider support this protocol.

Dependencies:
    pip install iec61850  # Python bindings for libiec61850
    # Alternatively: use the C library directly via ctypes

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Callable, List
from dataclasses import dataclass

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.adapters.iec61850")

try:
    import iec61850
    IEC61850_AVAILABLE = True
except ImportError:
    IEC61850_AVAILABLE = False
    iec61850 = None


# ============================================================
#  IEC 61850 Data Model — Logical Node Paths
# ============================================================

@dataclass
class IEC61850TagMap:
    """IEC 61850 logical node references for a protection relay / IED.

    Standard path format: LogicalDevice/LogicalNode.DataObject.DataAttribute

    Example for a typical generator protection relay:
        frequency:     GenProtection/MMXU1.Hz.mag.f
        active_power:  GenMeter/MMXU1.TotW.mag.f
        voltage:       GenMeter/MMXU1.PhV.phsA.cVal.mag.f
    """

    # Measurement nodes (MMXU = Measurement)
    frequency_path:   str = "GenProtection/MMXU1.Hz.mag.f"
    voltage_a_path:   str = "GenMeter/MMXU1.PhV.phsA.cVal.mag.f"
    voltage_b_path:   str = "GenMeter/MMXU1.PhV.phsB.cVal.mag.f"
    voltage_c_path:   str = "GenMeter/MMXU1.PhV.phsC.cVal.mag.f"
    active_power_path: str = "GenMeter/MMXU1.TotW.mag.f"
    reactive_power_path: str = "GenMeter/MMXU1.TotVAr.mag.f"
    power_factor_path: str = "GenMeter/MMXU1.TotPF.mag.f"

    # Control nodes (CSWI = Switchgear Control, GGIO = Generic I/O)
    mw_setpoint_path:  str = "GenController/GGIO1.AnOut1.setMag.f"
    mvar_setpoint_path: str = "GenController/GGIO1.AnOut2.setMag.f"
    mode_setpoint_path: str = "GenController/GGIO1.IntOut1.stVal"

    # GOOSE subscription
    goose_control_block: str = "GenProtection/LLN0$GO$gcbAnalogValues"
    goose_app_id: int = 0x0001


# Functional constraints for IEC 61850 reads/writes
FC_MX = 0   # Measurement (live values)
FC_SP = 5   # Setpoint (control values)
FC_ST = 3   # Status


class IEC61850Adapter(PlantAdapter):
    """IEC 61850 / GOOSE adapter for sub-millisecond grid control.

    This is the production-grade adapter for synthetic inertia injection
    where PRIMEnergeia's < 0.5ms latency claim matters.

    Usage:
        adapter = IEC61850Adapter(
            ied_host="192.168.1.100",
            ied_port=102,
            tag_map=IEC61850TagMap(
                frequency_path="Relay/MMXU1.Hz.mag.f",
                active_power_path="Meter/MMXU1.TotW.mag.f",
            ),
            market="SEN",
            node_id="05-VZA-400",
        )

        with adapter:
            # Event-driven mode (GOOSE)
            adapter.subscribe_goose(on_frequency_event)

            # Or polling mode (MMS)
            state = adapter.read_state()
            setpoint = hjb.solve(state)
            adapter.write_setpoint(setpoint)
    """

    def __init__(
        self,
        ied_host: str = "192.168.1.100",
        ied_port: int = 102,
        tag_map: Optional[IEC61850TagMap] = None,
        market: str = "SEN",
        node_id: str = "",
        f_nom: float = 60.0,
        read_only: bool = False,
    ):
        super().__init__(name=f"iec61850:{node_id or ied_host}", read_only=read_only)

        if not IEC61850_AVAILABLE:
            raise ImportError(
                "IEC 61850 library not found. Install with:\n"
                "  pip install iec61850\n"
                "  # Or build libiec61850 from source: "
                "https://github.com/mz-automation/libiec61850"
            )

        self.ied_host = ied_host
        self.ied_port = ied_port
        self.tags = tag_map or IEC61850TagMap()
        self.market = market
        self.node_id = node_id
        self.f_nom = f_nom

        self._connection = None
        self._goose_receiver = None
        self._goose_subscribers: List = []

    # --- Lifecycle ---

    def connect(self) -> None:
        """Connect to IED via MMS (TCP port 102)."""
        self._connection = iec61850.IedConnection_create()

        error = iec61850.IedConnection_connect(
            self._connection, self.ied_host, self.ied_port
        )

        if error != iec61850.IED_ERROR_OK:
            error_name = f"IED_ERROR_{error}"
            raise ConnectionError(
                f"IEC 61850 connection failed to {self.ied_host}:{self.ied_port} "
                f"(error={error_name})\n"
                f"Verify the IED is powered on and MMS is enabled."
            )

        self._connected = True
        logger.info(
            f"[{self.name}] Connected to IED at "
            f"{self.ied_host}:{self.ied_port} via MMS"
        )

    def close(self) -> None:
        """Disconnect from IED and stop GOOSE subscriptions."""
        # Stop GOOSE receiver
        if self._goose_receiver:
            try:
                iec61850.GooseReceiver_stop(self._goose_receiver)
                iec61850.GooseReceiver_destroy(self._goose_receiver)
            except Exception:
                pass

        # Close MMS connection
        if self._connection:
            try:
                iec61850.IedConnection_close(self._connection)
                iec61850.IedConnection_destroy(self._connection)
            except Exception:
                pass

        self._connected = False
        logger.info(f"[{self.name}] Disconnected from IED {self.ied_host}")

    # --- MMS Read (Polling Mode) ---

    def _read_float(self, path: str, fc: int = FC_MX) -> float:
        """Read a single float value from an IEC 61850 data attribute."""
        try:
            value = iec61850.IedConnection_readFloatValue(
                self._connection, path, fc
            )
            return float(value)
        except Exception as e:
            logger.warning(f"[{self.name}] Read failed: {path} — {e}")
            return 0.0

    def _read_state_impl(self) -> GridState:
        """Read all measurement nodes from the IED via MMS."""
        freq = self._read_float(self.tags.frequency_path, FC_MX)
        v_a = self._read_float(self.tags.voltage_a_path, FC_MX)
        v_b = self._read_float(self.tags.voltage_b_path, FC_MX)
        v_c = self._read_float(self.tags.voltage_c_path, FC_MX)
        p = self._read_float(self.tags.active_power_path, FC_MX)
        q = self._read_float(self.tags.reactive_power_path, FC_MX)
        pf = self._read_float(self.tags.power_factor_path, FC_MX)

        # Convert W to MW, VAr to MVAR, V to kV if needed
        # (IEC 61850 uses base SI units — W, V, A)
        p_mw = p / 1e6 if abs(p) > 1000 else p
        q_mvar = q / 1e6 if abs(q) > 1000 else q
        v_a_kv = v_a / 1000 if v_a > 1000 else v_a
        v_b_kv = v_b / 1000 if v_b > 1000 else v_b
        v_c_kv = v_c / 1000 if v_c > 1000 else v_c

        return GridState(
            frequency_hz=round(freq, 4),
            voltage_a_kv=round(v_a_kv, 2),
            voltage_b_kv=round(v_b_kv, 2),
            voltage_c_kv=round(v_c_kv, 2),
            active_power_mw=round(p_mw, 2),
            reactive_power_mvar=round(q_mvar, 2),
            power_factor=round(pf, 4) if pf != 0 else 1.0,
            node_id=self.node_id,
            market=self.market,
            timestamp=datetime.now(),
            quality="GOOD",
        )

    # --- MMS Write (Setpoint Mode) ---

    def _write_float(self, path: str, value: float, fc: int = FC_SP) -> bool:
        """Write a float value to an IEC 61850 data attribute."""
        try:
            iec61850.IedConnection_writeFloatValue(
                self._connection, path, fc, value
            )
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Write failed: {path} = {value} — {e}")
            return False

    def _write_setpoint_impl(self, setpoint: ControlSetpoint) -> bool:
        """Write optimal setpoint to IED control nodes via MMS."""
        success = True

        # Write active power setpoint (MW → W for IEC 61850)
        if not self._write_float(
            self.tags.mw_setpoint_path,
            setpoint.active_power_mw * 1e6,  # MW → W
            FC_SP,
        ):
            success = False

        # Write reactive power setpoint
        if not self._write_float(
            self.tags.mvar_setpoint_path,
            setpoint.reactive_power_mvar * 1e6,  # MVAR → VAr
            FC_SP,
        ):
            success = False

        # Write mode (integer)
        try:
            iec61850.IedConnection_writeInt32Value(
                self._connection,
                self.tags.mode_setpoint_path,
                FC_SP,
                int(setpoint.mode),
            )
        except Exception as e:
            logger.error(f"[{self.name}] Mode write failed: {e}")
            success = False

        if success:
            logger.debug(
                f"[{self.name}] IED setpoint: "
                f"{setpoint.active_power_mw:.1f} MW, "
                f"{setpoint.reactive_power_mvar:.1f} MVAR, "
                f"mode={setpoint.mode_label}"
            )

        return success

    # --- GOOSE (Sub-Millisecond Event-Driven Mode) ---

    def subscribe_goose(
        self,
        callback: Callable[[GridState], None],
        interface: str = "eth0",
    ) -> None:
        """Subscribe to GOOSE messages for < 4ms event notification.

        GOOSE (Generic Object Oriented Substation Event) is a Layer 2
        multicast protocol — no TCP overhead, no routing delay. This
        is what enables the < 0.5ms synthetic inertia response.

        Parameters
        ----------
        callback : Callable[[GridState], None]
            Function called on every GOOSE message with a fresh GridState.
        interface : str
            Network interface for GOOSE capture (must be in promiscuous mode).
        """
        if self._goose_receiver:
            logger.warning(f"[{self.name}] GOOSE already subscribed")
            return

        self._goose_receiver = iec61850.GooseReceiver_create()
        iec61850.GooseReceiver_setInterfaceId(self._goose_receiver, interface)

        # Create subscriber for the configured control block
        subscriber = iec61850.GooseSubscriber_create(
            self.tags.goose_control_block, None
        )
        iec61850.GooseSubscriber_setAppId(
            subscriber, self.tags.goose_app_id
        )

        # Wrap callback to convert GOOSE data into GridState
        def _goose_handler(subscriber, parameter):
            try:
                if not iec61850.GooseSubscriber_isValid(subscriber):
                    return

                # Extract values from GOOSE dataset
                dataset = iec61850.GooseSubscriber_getDataSetValues(subscriber)
                n_values = iec61850.MmsValue_getArraySize(dataset)

                # Typical GOOSE mapping: [freq, v_a, v_b, v_c, p, q]
                values = []
                for i in range(min(n_values, 7)):
                    val = iec61850.MmsValue_getElement(dataset, i)
                    values.append(iec61850.MmsValue_toFloat(val))

                state = GridState(
                    frequency_hz=round(values[0], 4) if len(values) > 0 else self.f_nom,
                    voltage_a_kv=round(values[1] / 1000, 2) if len(values) > 1 else 0,
                    voltage_b_kv=round(values[2] / 1000, 2) if len(values) > 2 else 0,
                    voltage_c_kv=round(values[3] / 1000, 2) if len(values) > 3 else 0,
                    active_power_mw=round(values[4] / 1e6, 2) if len(values) > 4 else 0,
                    reactive_power_mvar=round(values[5] / 1e6, 2) if len(values) > 5 else 0,
                    node_id=self.node_id,
                    market=self.market,
                    timestamp=datetime.now(),
                    source=f"{self.name}/GOOSE",
                    quality="GOOD",
                )

                callback(state)
                self._read_count += 1

            except Exception as e:
                logger.error(f"[{self.name}] GOOSE handler error: {e}")
                self._error_count += 1

        iec61850.GooseSubscriber_setListener(subscriber, _goose_handler, None)
        iec61850.GooseReceiver_addSubscriber(self._goose_receiver, subscriber)
        self._goose_subscribers.append(subscriber)

        # Start receiving
        iec61850.GooseReceiver_start(self._goose_receiver)
        logger.info(
            f"[{self.name}] GOOSE subscriber active on {interface} "
            f"(control block: {self.tags.goose_control_block})"
        )

    # --- Discovery ---

    def browse_logical_devices(self) -> List[str]:
        """List all logical devices on the IED (for site assessment)."""
        if not self._connection:
            raise RuntimeError("Not connected")

        devices = []
        try:
            ld_list = iec61850.IedConnection_getLogicalDeviceList(
                self._connection
            )
            ld = iec61850.LinkedList_getNext(ld_list)
            while ld:
                name = iec61850.LinkedList_getData(ld)
                devices.append(str(name))
                ld = iec61850.LinkedList_getNext(ld)
            iec61850.LinkedList_destroy(ld_list)
        except Exception as e:
            logger.error(f"[{self.name}] Browse failed: {e}")

        return devices
