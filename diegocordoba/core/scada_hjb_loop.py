"""
PRIMEnergeia — SCADA HJB Closed-Loop Controller
=================================================
Connects the mathematical HJB optimal control framework to physical OT
infrastructure (Modbus TCP / DNP3) via the fortified SafetyInterlockAdapter.

This module provides the missing physical bridge between abstract 
mathematical policies and the plant floor, enabling direct deployment 
into ENGIE / Grid Operator environments.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import time
import logging
import threading
import numpy as np
from typing import Optional

from adapters.industrial_scada import (
    BaseAdapter, 
    SafetyInterlockAdapter,
    ControlCommand,
    GridMeasurement,
    ProtocolType,
    ISOMarket,
    create_adapter
)
from core.grid_stabilizer import HJBController, KalmanEstimator, MARKET_PARAMS

logger = logging.getLogger("prime.scada_hjb_loop")

class SCADAHJBLoop:
    """
    Real-Time Execution Loop for HJB Optimal Control over SCADA.
    
    Reads 10 Hz / 1 Hz telemetry from a Modbus/DNP3 adapter,
    runs a Kalman filter to estimate true states from noisy sensors,
    queries the HJB value function for optimal setpoints,
    and dispatches commands safely back through the Interlock.
    """
    
    def __init__(
        self,
        adapter: BaseAdapter,
        market: str = "ERCOT",
        max_injection_mw: float = 50.0,
        dt_s: float = 0.1,  # Target polling rate (10 Hz)
        operator_id: str = "prime_auto"
    ):
        self.adapter = adapter
        self.market_name = market
        self.max_inj_mw = max_injection_mw
        self.dt = dt_s
        self.operator_id = operator_id
        
        # Load market physics constants for the Kalman filter
        params = MARKET_PARAMS.get(market, MARKET_PARAMS["ERCOT"])
        
        # Core components
        self.hjb = HJBController(market=market, max_injection_mw=max_injection_mw)
        self.estimator = KalmanEstimator(H=params["H"], D=params["D"], dt=dt_s)
        
        # Concurrency
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # Metrics
        self.cycles = 0
        self.last_latency_ms = 0.0

    def start(self):
        """Start the control loop in a background thread."""
        if self._is_running:
            logger.warning("SCADA loop is already running.")
            return
            
        if not self.adapter.is_connected:
            logger.info("Connecting SCADA adapter...")
            if not self.adapter.connect():
                raise ConnectionError(f"Failed to connect adapter: {self.adapter.name}")
        
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_loop, 
            name="SCADA-HJB-Loop",
            daemon=True
        )
        self._thread.start()
        logger.info(f"🚀 SCADA-HJB Loop STARTED on {self.adapter.name} [{self.market_name}] (dt={self.dt}s)")

    def stop(self):
        """Stop the control loop gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._is_running = False
        self.adapter.disconnect()
        logger.info("🛑 SCADA-HJB Loop STOPPED and adapter disconnected.")

    def _run_loop(self):
        """The 10 Hz synchronous control loop."""
        while not self._stop_event.is_set():
            t_start = time.perf_counter()
            
            # 1. READ Telemetry via SCADA (with fallback for disconnection)
            meas: Optional[GridMeasurement] = self.adapter.read_state()
            
            if meas is not None and meas.quality_ok:
                # 2. FILTER Sensor Noise
                # We feed the measured freq deviation and measured active power to Kalman
                z = np.array([meas.freq_deviation_hz, meas.active_power_mw])
                est_state = self.estimator.step(z)
                est_df, est_P = est_state[0], est_state[1]
                
                # Assume average LMP price (or inject via external oracle)
                current_lmp = MARKET_PARAMS.get(self.market_name, {}).get("base_price", 50.0)
                
                # 3. OPTIMIZE via HJB Dynamic Programming Policy
                optimal_mw = self.hjb.compute(
                    freq_deviation=est_df,
                    current_injection=est_P,
                    lmp_price=current_lmp
                )
                
                # 4. DISPATCH through OT layer (with SafetyInterlocks)
                cmd = ControlCommand(
                    delta_power_mw=optimal_mw,
                    timestamp=time.time(),
                    source="HJB",
                    operator_id=self.operator_id
                )
                success = self.adapter.write_control(cmd)
                
                if success:
                    logger.debug(f"HJB Loop Cycle {self.cycles} | Δf={est_df:+.3f}Hz | CMD={optimal_mw:+.2f}MW")
            else:
                logger.warning("SCADA read failed or bad quality flag. HJB loop skipping cycle.")
                # We could run the predictor step of the Kalman filter here without measurement update
                self.estimator.predict()

            self.cycles += 1
            
            # Rate limiting / Sleep to maintain accurate dt polling frequency
            elapsed = time.perf_counter() - t_start
            self.last_latency_ms = elapsed * 1000.0
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_status(self) -> dict:
        return {
            "running": self._is_running,
            "cycles": self.cycles,
            "latency_ms": round(self.last_latency_ms, 2),
            "adapter_health": self.adapter.health_report()
        }
