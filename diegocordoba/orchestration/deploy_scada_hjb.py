#!/usr/bin/env python3
"""
PRIMEnergeia — Turn-Key SCADA/HJB Deployment Script
======================================================
This executable script deploys the SCADA-HJB Closed Loop to a physical PLC
or runs a local SW-in-the-Loop simulation.

Usage:
  # Deploy to a real physical PLC over Modbus TCP (CENACE ISO settings)
  python3 orchestration/deploy_scada_hjb.py --protocol modbus_tcp --host 192.168.10.50 --port 502 --market CENACE

  # Run software-in-the-loop physics simulation
  python3 orchestration/deploy_scada_hjb.py --protocol simulated --market ERCOT --duration 30

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import argparse
import time
import sys
import logging
from pprint import pprint

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.industrial_scada import (
    ProtocolType,
    ISOMarket,
    create_adapter,
    SafetyInterlockAdapter,
    WatchdogAdapter,
    SimulatedAdapter
)
from core.scada_hjb_loop import SCADAHJBLoop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("deploy_scada")

def parse_args():
    parser = argparse.ArgumentParser(description="Deploy PRIMEnergeia SCADA-HJB Control Loop.")
    parser.add_argument("--protocol", type=str, default="simulated", choices=["simulated", "modbus_tcp", "dnp3"],
                        help="SCADA Protocol to use.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="PLC IP address.")
    parser.add_argument("--port", type=int, default=502, help="PLC port (502 for Modbus, 20000 for DNP3).")
    parser.add_argument("--market", type=str, default="CENACE", choices=[m.value.upper() for m in ISOMarket],
                        help="Target ISO Market (determines NERC limits and frequency).")
    parser.add_argument("--max-mw", type=float, default=50.0, help="Max BESS power injection (MW).")
    parser.add_argument("--dt", type=float, default=0.1, help="Polling interval / Control Loop dt in seconds.")
    parser.add_argument("--duration", type=float, default=60.0, help="How many seconds to run before stopping (0 for infinite).")
    parser.add_argument("--inject-disturbance", action="store_true", help="Inject a step disturbance if using simulated mode.")
    return parser.parse_args()

def main():
    args = parse_args()
    
    iso_market = ISOMarket(args.market.lower())
    proto = ProtocolType(args.protocol)
    
    logger.info(f"Building SCADA Adapter: Protocol={proto.value}, Host={args.host}:{args.port}, Market={iso_market.value.upper()}")
    
    # 1. Create Base SCADA Adapter
    if proto == ProtocolType.SIMULATED:
        base_adapter = SimulatedAdapter(market=iso_market, noise_std=0.005)
    else:
        # Pass host/port via kwargs to create_adapter
        base_adapter = create_adapter(
            protocol=proto,
            host=args.host,
            port=args.port,
            market=iso_market
        )
    
    # 2. Fortify Adapter (Tesis Chapter 2 & 3 Compliance)
    safe_adapter = SafetyInterlockAdapter(base_adapter, max_delta_mw=args.max_mw)
    watchdog_adapter = WatchdogAdapter(safe_adapter, timeout_s=5.0)
    
    # 3. Instantiate and Start HJB Loop
    loop = SCADAHJBLoop(
        adapter=watchdog_adapter,
        market=args.market.upper(),
        max_injection_mw=args.max_mw,
        dt_s=args.dt
    )
    
    try:
        loop.start()
        
        # Inject an arbitrary disturbance after 2 seconds to see the HJB react
        if args.inject_disturbance and isinstance(base_adapter, SimulatedAdapter):
            time.sleep(2.0)
            logger.warning(">>> Injecting +25 MW Grid Load Disturbance <<<")
            base_adapter.inject_disturbance(25.0)
        
        elapsed = 0.0
        while args.duration <= 0 or elapsed < args.duration:
            time.sleep(1.0)
            elapsed += 1.0
            
            # Print status periodically
            if int(elapsed) % 5 == 0:
                print("\n[📊] Real-time SCADA-HJB Health Report:")
                pprint(loop.get_status())
                print()
                
    except KeyboardInterrupt:
        logger.warning("Interrupted by Operator. Shutting down...")
    except Exception as e:
        logger.error(f"Critical Failure: {e}", exc_info=True)
    finally:
        loop.stop()
        logger.info("Deployment script terminated safely.")

if __name__ == "__main__":
    main()
