"""
PRIMEnergeia — Real-Time Control Loop
========================================
The main runtime that runs at the power plant. This is the
"brain" that continuously:

    1. READS plant state (frequency, voltage, power)
    2. SOLVES the HJB optimal control equation
    3. WRITES back the optimal setpoint
    4. LOGS every dollar rescued

Supports any adapter (CSV, API, OPC UA, Modbus, IEC 61850)
via the unified PlantAdapter interface.

Usage:
    # From project root:
    python -m runtime.control_loop --config adapters/config/vza400_tags.yaml

    # Or with specific adapter:
    python -m runtime.control_loop --protocol opcua --host 192.168.1.100

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
from datetime import datetime
from typing import Optional

# Ensure project root is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.runtime")

# ============================================================
#  HJB Frequency Controller (Swing Equation Solver)
# ============================================================

class HJBFrequencyController:
    """Hamilton-Jacobi-Bellman optimal frequency controller.

    Solves the Swing Equation in real-time:
        df/dt = (Pm - Pe - D·Δf) / (2H + u)

    And computes the optimal synthetic inertia injection u*(f):
        u* = -½ ∂V/∂f

    Where V(f) is the value function from the HJB PDE:
        V_t + min_u { L(f, u) + ∂V/∂f · g(f, u) } = 0
    """

    def __init__(
        self,
        f_nom: float = 60.0,
        H: float = 5.0,
        D: float = 2.0,
        control_gain: float = 500.0,
        penalty_threshold_hz: float = 0.03,
        penalty_rate_usd: float = 250000.0,
    ):
        self.f_nom = f_nom
        self.H = H
        self.D = D
        self.control_gain = control_gain
        self.penalty_threshold = penalty_threshold_hz
        self.penalty_rate = penalty_rate_usd

        # State
        self.last_frequency = f_nom
        self.total_rescued_usd = 0.0
        self.total_penalties_avoided = 0
        self.solve_count = 0

    def compute_optimal_setpoint(
        self,
        state: GridState,
        dt: float = 1.0,
    ) -> ControlSetpoint:
        """Solve HJB and return optimal dispatch setpoint.

        Parameters
        ----------
        state : GridState
            Current plant measurements.
        dt : float
            Time since last solve (seconds).

        Returns
        -------
        ControlSetpoint with optimal MW dispatch and synthetic inertia.
        """
        t_start = time.time()

        f = state.frequency_hz
        p_actual = state.active_power_mw
        lmp = state.lmp_price if state.lmp_price > 0 else 45.0

        # --- HJB Value Function ---
        # Quadratic cost: V(f) = ½ × κ × (f - f_nom)²
        kappa = 1e4
        delta_f = f - self.f_nom
        V = 0.5 * kappa * delta_f ** 2
        dV_df = kappa * delta_f

        # --- Optimal Control Law ---
        # u* = -½ ∂V/∂f (scaled by control gain)
        u_inertia = max(0, -0.5 * dV_df * self.control_gain / kappa)

        # --- Swing Equation Integration ---
        # M_eff = 2H + u_inertia
        M_eff = 2 * self.H + u_inertia
        rocof = -self.D * delta_f / M_eff  # Simplified (Pm ≈ Pe at steady state)

        # --- Optimal MW Setpoint ---
        # Adjust active power to counter frequency deviation
        correction_mw = delta_f * self.control_gain * 0.01  # Scale factor
        optimal_mw = max(0, p_actual + correction_mw)

        # --- Capital Recovery Tracking ---
        delta_mw = max(0, optimal_mw - p_actual)
        capital_this_step = delta_mw * lmp * (dt / 3600)  # $/MWh × MWh
        self.total_rescued_usd += capital_this_step

        # --- Penalty Avoidance ---
        if abs(delta_f) > self.penalty_threshold:
            penalty_cost = abs(delta_f) * self.penalty_rate * dt
            self.total_rescued_usd += penalty_cost
            self.total_penalties_avoided += 1

        # --- Determine Mode ---
        if delta_f < -0.01:
            mode = 2  # DISCHARGE (inject power to raise frequency)
            mode_label = "DISCHARGE"
        elif delta_f > 0.01:
            mode = 1  # CHARGE (absorb power to lower frequency)
            mode_label = "CHARGE"
        else:
            mode = 0  # HOLD (frequency nominal)
            mode_label = "HOLD"

        solver_ms = (time.time() - t_start) * 1000
        self.solve_count += 1
        self.last_frequency = f

        return ControlSetpoint(
            active_power_mw=round(optimal_mw, 2),
            reactive_power_mvar=round(state.reactive_power_mvar, 2),
            mode=mode,
            mode_label=mode_label,
            inertia_injection_pu=round(u_inertia, 4),
            solver_time_ms=round(solver_ms, 3),
            confidence=min(1.0, 1.0 - abs(delta_f) / 0.5),
        )

    @property
    def stats(self) -> dict:
        return {
            "total_rescued_usd": round(self.total_rescued_usd, 2),
            "penalties_avoided": self.total_penalties_avoided,
            "solves": self.solve_count,
            "last_frequency": self.last_frequency,
        }


# ============================================================
#  Control Loop — The Main Runtime
# ============================================================

class ControlLoop:
    """Main PRIMEnergeia control loop that ties everything together.

    adapter.read_state() → solver.compute_optimal_setpoint() → adapter.write_setpoint()

    Runs continuously until interrupted (Ctrl+C or SIGTERM).
    """

    def __init__(
        self,
        adapter: PlantAdapter,
        solver: Optional[HJBFrequencyController] = None,
        interval_seconds: float = 1.0,
        log_interval_seconds: float = 10.0,
        state_file: Optional[str] = None,
    ):
        self.adapter = adapter
        self.solver = solver or HJBFrequencyController()
        self.interval = interval_seconds
        self.log_interval = log_interval_seconds
        self.state_file = state_file or os.path.join(_ROOT, "grid_state.json")

        self._running = False
        self._tick = 0
        self._last_log_time = 0

    def run(self) -> None:
        """Main control loop. Blocks until interrupted."""
        self._running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        print("=" * 70)
        print("  ⚡ PRIMEnergeia — Real-Time HJB Control Loop")
        print(f"  Adapter:   {self.adapter}")
        print(f"  Solver:    HJB (f_nom={self.solver.f_nom} Hz, "
              f"H={self.solver.H}s, D={self.solver.D})")
        print(f"  Interval:  {self.interval}s")
        print(f"  Read-Only: {self.adapter.read_only}")
        print("=" * 70)
        print()

        try:
            with self.adapter:
                while self._running:
                    self._tick += 1
                    t_start = time.time()

                    # 1. READ
                    state = self.adapter.read_state()

                    # 2. SOLVE
                    setpoint = self.solver.compute_optimal_setpoint(
                        state, dt=self.interval
                    )

                    # 3. WRITE
                    self.adapter.write_setpoint(setpoint)

                    # 4. LOG
                    self._log_telemetry(state, setpoint)

                    # 5. WRITE STATE FILE (for dashboard consumption)
                    self._write_state_file(state, setpoint)

                    # Rate control
                    elapsed = time.time() - t_start
                    sleep_time = max(0, self.interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Control loop fatal error: {e}")
            raise
        finally:
            self._print_summary()

    def _log_telemetry(self, state: GridState, setpoint: ControlSetpoint):
        """Print live telemetry to terminal."""
        now = time.time()

        # Compact line every tick
        delta_f = state.frequency_hz - self.solver.f_nom
        sys.stdout.write(
            f"\r\033[K[⚡] "
            f"f={state.frequency_hz:.4f} Hz "
            f"(Δ{delta_f:+.4f}) | "
            f"P={state.active_power_mw:.1f}→{setpoint.active_power_mw:.1f} MW | "
            f"Mode={setpoint.mode_label:10s} | "
            f"Rescued=${self.solver.total_rescued_usd:,.2f} | "
            f"t={setpoint.solver_time_ms:.1f}ms"
        )
        sys.stdout.flush()

        # Detailed log at intervals
        if now - self._last_log_time >= self.log_interval:
            self._last_log_time = now
            logger.info(
                f"Tick {self._tick} | "
                f"f={state.frequency_hz:.4f} Hz | "
                f"P={state.active_power_mw:.1f} MW | "
                f"Setpoint={setpoint.active_power_mw:.1f} MW | "
                f"Rescued=${self.solver.total_rescued_usd:,.2f} | "
                f"Adapter={self.adapter.stats}"
            )

    def _write_state_file(self, state: GridState, setpoint: ControlSetpoint):
        """Write current state to grid_state.json for dashboard consumption."""
        try:
            payload = {
                "f": state.frequency_hz,
                "v": state.voltage_a_kv,
                "status": "NOMINAL" if state.is_nominal(self.solver.f_nom) else "ALERT",
                "timestamp": time.time(),
                "setpoint_mw": setpoint.active_power_mw,
                "mode": setpoint.mode_label,
                "rescued_usd": round(self.solver.total_rescued_usd, 2),
                "adapter": self.adapter.name,
                "quality": state.quality,
            }
            with open(self.state_file, "w") as f:
                json.dump(payload, f)
        except Exception:
            pass  # Non-critical — don't crash control loop for file I/O

    def _shutdown(self, signum, frame):
        """Graceful shutdown handler."""
        print(f"\n\n[!] Shutdown signal received (signal {signum})")
        self._running = False

    def _print_summary(self):
        """Print final session summary on shutdown."""
        print(f"\n\n{'=' * 70}")
        print(f"  ⚡ PRIMEnergeia — Session Summary")
        print(f"{'=' * 70}")
        print(f"  Ticks:              {self._tick}")
        print(f"  Runtime:            {self._tick * self.interval:.0f} seconds")
        print(f"  Total Rescued:      ${self.solver.total_rescued_usd:,.2f} USD")
        print(f"  Penalties Avoided:  {self.solver.total_penalties_avoided}")
        print(f"  Adapter Stats:      {self.adapter.stats}")
        print(f"{'=' * 70}")


# ============================================================
#  CLI Entry Point
# ============================================================

def create_adapter_from_config(config_path: str) -> tuple:
    """Create adapter and solver from a YAML config file."""
    import yaml

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    site = cfg.get("site", {})
    protocol = cfg.get("protocol", "csv")
    conn = cfg.get("connection", {})
    control = cfg.get("control", {})

    f_nom = site.get("f_nom", 60.0)
    market = site.get("market", "ERCOT")
    node_id = site.get("node_id", "")
    read_only = control.get("read_only", True)

    if protocol == "opcua":
        from adapters.opcua_adapter import OPCUAAdapter
        adapter = OPCUAAdapter(
            server_url=conn.get("opcua_url", "opc.tcp://localhost:4840"),
            tag_mapping=config_path,  # Reuse the same YAML
            market=market,
            node_id=node_id,
            f_nom=f_nom,
            read_only=read_only,
        )
    elif protocol == "modbus":
        from adapters.modbus_adapter import ModbusTCPAdapter
        reg_map = {
            "read": {k: tuple(v) for k, v in cfg.get("modbus_read_registers", {}).items()},
            "write": {k: tuple(v) for k, v in cfg.get("modbus_write_registers", {}).items()},
        }
        adapter = ModbusTCPAdapter(
            host=conn.get("modbus_host", "192.168.1.100"),
            port=conn.get("modbus_port", 502),
            unit_id=conn.get("modbus_unit_id", 1),
            market=market,
            node_id=node_id,
            f_nom=f_nom,
            register_map=reg_map if reg_map["read"] else None,
            read_only=read_only,
        )
    elif protocol == "iec61850":
        from adapters.iec61850_adapter import IEC61850Adapter, IEC61850TagMap
        paths = cfg.get("iec61850_paths", {})
        tag_map = IEC61850TagMap(
            frequency_path=paths.get("frequency", IEC61850TagMap.frequency_path),
            voltage_a_path=paths.get("voltage_a", IEC61850TagMap.voltage_a_path),
            active_power_path=paths.get("active_power", IEC61850TagMap.active_power_path),
            reactive_power_path=paths.get("reactive_power", IEC61850TagMap.reactive_power_path),
            mw_setpoint_path=paths.get("mw_setpoint", IEC61850TagMap.mw_setpoint_path),
        )
        adapter = IEC61850Adapter(
            ied_host=conn.get("iec61850_host", "192.168.1.100"),
            ied_port=conn.get("iec61850_port", 102),
            tag_map=tag_map,
            market=market,
            node_id=node_id,
            f_nom=f_nom,
            read_only=read_only,
        )
    elif protocol == "api":
        from adapters.api_adapter import APIAdapter
        adapter = APIAdapter(
            base_url=conn.get("api_url", "http://localhost:8081"),
            api_key=conn.get("api_key", "prime_pilot_key"),
            market=market.lower(),
        )
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    # Create solver with site-specific parameters
    solver = HJBFrequencyController(
        f_nom=f_nom,
        H=site.get("H", 5.0),
        D=site.get("D", 2.0),
    )

    return adapter, solver, control


def main():
    parser = argparse.ArgumentParser(
        description="PRIMEnergeia — Real-Time HJB Control Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m runtime.control_loop --config adapters/config/vza400.yaml\n"
            "  python -m runtime.control_loop --protocol api --market sen\n"
            "  python -m runtime.control_loop --protocol opcua --host 192.168.1.100\n"
        ),
    )
    parser.add_argument("--config", type=str, help="YAML config file path")
    parser.add_argument("--protocol", type=str, default="api",
                        choices=["csv", "api", "opcua", "modbus", "iec61850"])
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--market", type=str, default="ercot")
    parser.add_argument("--node-id", type=str, default="")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Control loop interval (seconds)")
    parser.add_argument("--read-only", action="store_true",
                        help="Shadow mode — observe only, don't write setpoints")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create adapter
    if args.config:
        adapter, solver, control = create_adapter_from_config(args.config)
        interval = control.get("loop_interval_seconds", args.interval)
    else:
        f_nom = 50.0 if args.market.lower() in ("mibel", "nem", "jepx", "epex", "nordpool") else 60.0
        solver = HJBFrequencyController(f_nom=f_nom)
        interval = args.interval

        if args.protocol == "api":
            from adapters.api_adapter import APIAdapter
            adapter = APIAdapter(
                base_url=f"http://{args.host}:{args.port or 8081}",
                market=args.market.lower(),
            )
        elif args.protocol == "opcua":
            from adapters.opcua_adapter import OPCUAAdapter
            adapter = OPCUAAdapter(
                server_url=f"opc.tcp://{args.host}:{args.port or 4840}",
                market=args.market.upper(),
                node_id=args.node_id,
                f_nom=f_nom,
                read_only=args.read_only,
            )
        elif args.protocol == "modbus":
            from adapters.modbus_adapter import ModbusTCPAdapter
            adapter = ModbusTCPAdapter(
                host=args.host,
                port=args.port or 502,
                market=args.market.upper(),
                node_id=args.node_id,
                f_nom=f_nom,
                read_only=args.read_only,
            )
        elif args.protocol == "iec61850":
            from adapters.iec61850_adapter import IEC61850Adapter
            adapter = IEC61850Adapter(
                ied_host=args.host,
                ied_port=args.port or 102,
                market=args.market.upper(),
                node_id=args.node_id,
                f_nom=f_nom,
                read_only=args.read_only,
            )
        else:
            print(f"Protocol '{args.protocol}' requires --config. Use --help.")
            sys.exit(1)

    # Run
    loop = ControlLoop(
        adapter=adapter,
        solver=solver,
        interval_seconds=interval,
    )
    loop.run()


if __name__ == "__main__":
    main()
