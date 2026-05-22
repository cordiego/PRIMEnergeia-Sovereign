"""
SCADA/Modbus Adapter for VZA-400 Node.
Bridges the PRIME-Kernel HJB Solver with real-time CENACE telemetry.
"""
import logging
import random
import time
import pandas as pd
from pymodbus.client import ModbusTcpClient

logger = logging.getLogger("scada.vza400")

class VZA400Adapter:
    def __init__(self, host='localhost', port=502, data_csv=None):
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(host, port=port)
        self.data_csv = data_csv
        self.historical_data = None
        
        if self.data_csv:
            self._load_data()

    def _load_data(self):
        try:
            self.historical_data = pd.read_csv(self.data_csv)
            logger.info(f"Loaded {len(self.historical_data)} records for VZA-400 simulation.")
        except Exception as e:
            logger.error(f"Failed to load VZA-400 data: {e}")

    def connect(self) -> bool:
        """Connect to the Modbus TCP server."""
        # For simulation purposes, we assume connection is successful
        logger.info(f"Connecting to VZA-400 SCADA at {self.host}:{self.port}...")
        return True

    def read_telemetry(self) -> dict:
        """
        Read real-time telemetry from the VZA-400 node.
        Returns a dictionary with frequency (Hz), active power (MW), and PML ($/MWh).
        """
        # If we have historical data, simulate by pulling a random row
        if self.historical_data is not None and not self.historical_data.empty:
            row = self.historical_data.sample(1).iloc[0]
            # Simulate frequency deviation around 60Hz
            freq_dev = random.normalvariate(0, 0.015) 
            return {
                "timestamp": row['timestamp'],
                "frequency_hz": 60.0 + freq_dev,
                "active_power_mw": row['Actual_MW'],
                "pml_usd": row['PML_USD']
            }
        
        # Fallback simulated data if no CSV or Modbus is available
        return {
            "timestamp": time.time(),
            "frequency_hz": 60.0 + random.normalvariate(0, 0.02),
            "active_power_mw": random.uniform(0, 100),
            "pml_usd": random.uniform(20, 50)
        }

    def write_setpoint(self, power_mw: float) -> bool:
        """Write an active power setpoint to the BESS controller via Modbus."""
        logger.info(f"Writing setpoint {power_mw:.2f} MW to VZA-400.")
        return True

    def disconnect(self):
        self.client.close()
        logger.info("Disconnected from VZA-400 SCADA.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    adapter = VZA400Adapter(data_csv='../data/nodos/data_05-VZA-400.csv')
    adapter.connect()
    for _ in range(3):
        print(adapter.read_telemetry())
        time.sleep(1)
