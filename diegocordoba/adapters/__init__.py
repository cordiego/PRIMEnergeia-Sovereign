"""
PRIMEnergeia — Protocol Adapter Module
=========================================
Unified interface for connecting HJB optimal control software
to power plant hardware via multiple industrial protocols.

Supported adapters:
  - CSVAdapter         — Offline batch analysis from data historian exports
  - APIAdapter         — REST API integration (HTTPS, cloud-hosted)
  - OPCUAAdapter       — OPC UA real-time plant bridge (industry standard)
  - ModbusTCPAdapter   — Modbus TCP for legacy PLCs/RTUs
  - IEC61850Adapter    — IEC 61850 / GOOSE for sub-ms substation automation

All adapters implement the PlantAdapter abstract interface:
  read_state()         → GridState
  write_setpoint()     → bool
  connect() / close()

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint
from adapters.csv_adapter import CSVAdapter
from adapters.api_adapter import APIAdapter

# Industrial protocol adapters — import only when dependencies are available
try:
    from adapters.opcua_adapter import OPCUAAdapter
except ImportError:
    OPCUAAdapter = None

try:
    from adapters.modbus_adapter import ModbusTCPAdapter
except ImportError:
    ModbusTCPAdapter = None

try:
    from adapters.iec61850_adapter import IEC61850Adapter
except ImportError:
    IEC61850Adapter = None


__all__ = [
    "PlantAdapter",
    "GridState",
    "ControlSetpoint",
    "CSVAdapter",
    "APIAdapter",
    "OPCUAAdapter",
    "ModbusTCPAdapter",
    "IEC61850Adapter",
]

__version__ = "1.0.0"
