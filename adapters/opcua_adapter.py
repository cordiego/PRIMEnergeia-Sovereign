"""
PRIMEnergeia — OPC UA Adapter
================================
Real-time bidirectional bridge to power plant SCADA/DCS systems
using OPC Unified Architecture (IEC 62541).

OPC UA is the industry standard for modern SCADA integration.
Most SCADA systems from ABB, Siemens, GE, Schneider, Honeywell,
and Yokogawa include an OPC UA server out of the box.

Dependencies:
    pip install opcua
    # or for async: pip install asyncua

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import logging
import time
from datetime import datetime
from typing import Optional, Dict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.adapters.opcua")

try:
    from opcua import Client as OPCUAClient
    from opcua import ua
    OPCUA_AVAILABLE = True
except ImportError:
    try:
        from asyncua.sync import Client as OPCUAClient
        OPCUA_AVAILABLE = True
    except ImportError:
        OPCUA_AVAILABLE = False
        OPCUAClient = None


# ============================================================
#  Default Tag Mapping (override with YAML per client)
# ============================================================
DEFAULT_READ_TAGS = {
    "frequency_hz":        "ns=2;s=Grid.Frequency.Hz",
    "voltage_a_kv":        "ns=2;s=Grid.Voltage.PhaseA.kV",
    "voltage_b_kv":        "ns=2;s=Grid.Voltage.PhaseB.kV",
    "voltage_c_kv":        "ns=2;s=Grid.Voltage.PhaseC.kV",
    "active_power_mw":     "ns=2;s=Gen.ActivePower.MW",
    "reactive_power_mvar": "ns=2;s=Gen.ReactivePower.MVAR",
    "power_factor":        "ns=2;s=Grid.PowerFactor",
}

DEFAULT_WRITE_TAGS = {
    "mw_setpoint":   "ns=2;s=Control.MW.Setpoint",
    "mvar_setpoint":  "ns=2;s=Control.MVAR.Setpoint",
    "mode":           "ns=2;s=Control.Mode",
}


class OPCUAAdapter(PlantAdapter):
    """OPC UA real-time adapter for plant SCADA integration.

    Usage:
        adapter = OPCUAAdapter(
            server_url="opc.tcp://192.168.1.100:4840",
            tag_mapping="adapters/config/vza400_tags.yaml",
            market="SEN",
            node_id="05-VZA-400",
        )

        with adapter:
            state = adapter.read_state()
            setpoint = hjb.solve(state)
            adapter.write_setpoint(setpoint)

    Tag Mapping YAML format:
        read_tags:
            frequency_hz: "ns=2;s=Grid.Frequency.Hz"
            voltage_a_kv: "ns=2;s=Grid.Voltage.PhaseA.kV"
            active_power_mw: "ns=2;s=Gen.ActivePower.MW"
        write_tags:
            mw_setpoint: "ns=2;s=Control.MW.Setpoint"
            mode: "ns=2;s=Control.Mode"
    """

    def __init__(
        self,
        server_url: str = "opc.tcp://localhost:4840",
        tag_mapping: Optional[str] = None,
        market: str = "ERCOT",
        node_id: str = "",
        f_nom: float = 60.0,
        security_policy: Optional[str] = None,
        certificate_path: Optional[str] = None,
        private_key_path: Optional[str] = None,
        read_only: bool = False,
    ):
        super().__init__(name=f"opcua:{node_id or market}", read_only=read_only)

        if not OPCUA_AVAILABLE:
            raise ImportError(
                "OPC UA library not found. Install with:\n"
                "  pip install opcua\n"
                "  # or: pip install asyncua"
            )

        self.server_url = server_url
        self.market = market
        self.node_id = node_id
        self.f_nom = f_nom

        # Load tag mapping
        self.read_tags = dict(DEFAULT_READ_TAGS)
        self.write_tags = dict(DEFAULT_WRITE_TAGS)
        if tag_mapping and os.path.exists(tag_mapping):
            self._load_tag_mapping(tag_mapping)

        # Security
        self.security_policy = security_policy
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path

        # OPC UA client
        self._client: Optional[OPCUAClient] = None
        self._read_nodes: Dict = {}
        self._write_nodes: Dict = {}

    def _load_tag_mapping(self, path: str):
        """Load per-client tag mapping from YAML file."""
        if not YAML_AVAILABLE:
            logger.warning(f"[{self.name}] PyYAML not installed — using default tags")
            return

        with open(path, "r") as f:
            mapping = yaml.safe_load(f)

        if "read_tags" in mapping:
            self.read_tags.update(mapping["read_tags"])
        if "write_tags" in mapping:
            self.write_tags.update(mapping["write_tags"])

        logger.info(f"[{self.name}] Loaded tag mapping from {path}")

    def connect(self) -> None:
        """Connect to OPC UA server and resolve tag node IDs."""
        self._client = OPCUAClient(self.server_url)

        # Apply security if configured
        if self.security_policy and self.certificate_path:
            self._client.set_security_string(
                f"{self.security_policy},"
                f"SignAndEncrypt,"
                f"{self.certificate_path},"
                f"{self.private_key_path or ''}"
            )

        try:
            self._client.connect()
            logger.info(f"[{self.name}] Connected to {self.server_url}")
        except Exception as e:
            raise ConnectionError(
                f"OPC UA connection failed to {self.server_url}: {e}\n"
                f"Verify the server is running and the URL is correct."
            ) from e

        # Resolve read tags to node objects
        for signal_name, tag_id in self.read_tags.items():
            try:
                node = self._client.get_node(tag_id)
                self._read_nodes[signal_name] = node
                logger.debug(f"  READ  {signal_name:25s} ← {tag_id}")
            except Exception as e:
                logger.warning(f"  READ  {signal_name:25s} ← {tag_id} [FAILED: {e}]")

        # Resolve write tags
        if not self.read_only:
            for signal_name, tag_id in self.write_tags.items():
                try:
                    node = self._client.get_node(tag_id)
                    self._write_nodes[signal_name] = node
                    logger.debug(f"  WRITE {signal_name:25s} → {tag_id}")
                except Exception as e:
                    logger.warning(f"  WRITE {signal_name:25s} → {tag_id} [FAILED: {e}]")

        self._connected = True
        logger.info(
            f"[{self.name}] Resolved {len(self._read_nodes)} read tags, "
            f"{len(self._write_nodes)} write tags"
        )

    def close(self) -> None:
        """Disconnect from OPC UA server."""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False
        self._read_nodes.clear()
        self._write_nodes.clear()
        logger.info(f"[{self.name}] Disconnected from {self.server_url}")

    def _read_state_impl(self) -> GridState:
        """Read all measurement tags from OPC UA server in one pass."""
        values = {}
        for signal_name, node in self._read_nodes.items():
            try:
                raw_value = node.get_value()
                values[signal_name] = float(raw_value)
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to read {signal_name}: {e}")
                values[signal_name] = 0.0

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
        """Write optimal setpoint to OPC UA server control tags."""
        success = True

        # Write MW setpoint
        if "mw_setpoint" in self._write_nodes:
            try:
                node = self._write_nodes["mw_setpoint"]
                dv = ua.DataValue(ua.Variant(
                    float(setpoint.active_power_mw), ua.VariantType.Float
                ))
                node.set_value(dv)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to write MW setpoint: {e}")
                success = False

        # Write MVAR setpoint
        if "mvar_setpoint" in self._write_nodes:
            try:
                node = self._write_nodes["mvar_setpoint"]
                dv = ua.DataValue(ua.Variant(
                    float(setpoint.reactive_power_mvar), ua.VariantType.Float
                ))
                node.set_value(dv)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to write MVAR setpoint: {e}")
                success = False

        # Write mode
        if "mode" in self._write_nodes:
            try:
                node = self._write_nodes["mode"]
                dv = ua.DataValue(ua.Variant(
                    int(setpoint.mode), ua.VariantType.Int16
                ))
                node.set_value(dv)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to write mode: {e}")
                success = False

        if success:
            logger.debug(
                f"[{self.name}] Setpoint written: "
                f"{setpoint.active_power_mw:.1f} MW, "
                f"{setpoint.reactive_power_mvar:.1f} MVAR, "
                f"mode={setpoint.mode_label}"
            )

        return success

    def browse_tags(self, depth: int = 3) -> list:
        """Browse the OPC UA server tag tree for discovery.

        Useful during site assessment to learn what tags are available.
        """
        if not self._client:
            raise RuntimeError("Not connected")

        root = self._client.get_root_node()
        tags = []

        def _browse(node, level=0):
            if level >= depth:
                return
            try:
                children = node.get_children()
                for child in children:
                    try:
                        name = child.get_browse_name().to_string()
                        node_id = child.nodeid.to_string()
                        tags.append({
                            "name": name,
                            "node_id": node_id,
                            "level": level,
                        })
                        _browse(child, level + 1)
                    except Exception:
                        pass
            except Exception:
                pass

        _browse(root)
        return tags
