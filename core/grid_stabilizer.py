"""
PRIMEnergeia — Closed-Loop Grid Stabilizer
=============================================
Wires HJB solver + Kalman state estimator + stochastic disturbances
into a real-time feedback loop. Includes PID baseline for benchmarking.

Usage:
    from core.grid_stabilizer import GridStabilizer, run_simulation
    results = run_simulation(duration_s=600, market="ERCOT")

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger("prime.grid_stabilizer")


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────

@dataclass
class GridSnapshot:
    """Full grid state at a single timestep."""
    time_s: float = 0.0
    frequency_hz: float = 60.0
    freq_deviation_hz: float = 0.0
    rocof_hz_s: float = 0.0
    voltage_pu: float = 1.0
    active_power_mw: float = 0.0
    reactive_power_mvar: float = 0.0
    injection_mw: float = 0.0
    disturbance_mw: float = 0.0
    lmp_price: float = 50.0
    soc_pct: float = 50.0
    controller: str = "HJB"


@dataclass
class SimulationResult:
    """Complete simulation output."""
    snapshots: List[GridSnapshot]
    total_cost: float = 0.0
    total_revenue: float = 0.0
    freq_violations: int = 0
    freq_stability_pct: float = 0.0
    max_deviation_hz: float = 0.0
    avg_deviation_hz: float = 0.0
    controller_name: str = ""
    market: str = ""
    duration_s: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"[{self.controller_name}] {self.market} | "
            f"{self.duration_s:.0f}s | "
            f"Stability: {self.freq_stability_pct:.2f}% | "
            f"Max Δf: {self.max_deviation_hz:.4f} Hz | "
            f"Revenue: ${self.total_revenue:,.2f} | "
            f"Violations: {self.freq_violations}"
        )


# ─────────────────────────────────────────────────────────────
# Market Configurations
# ─────────────────────────────────────────────────────────────

MARKET_PARAMS = {
    "ERCOT": {
        "f_nom": 60.0, "H": 4.5, "D": 1.0, "v_nom_kv": 345.0,
        "price_cap": 5000.0, "base_price": 45.0, "penalty_threshold_hz": 0.036,
        "penalty_rate": 15000.0, "freq_response_rate": 25.0,
    },
    "SEN": {
        "f_nom": 60.0, "H": 5.0, "D": 1.2, "v_nom_kv": 230.0,
        "price_cap": 750.0, "base_price": 42.0, "penalty_threshold_hz": 0.05,
        "penalty_rate": 8000.0, "freq_response_rate": 18.0,
    },
    "MIBEL": {
        "f_nom": 50.0, "H": 6.0, "D": 1.5, "v_nom_kv": 400.0,
        "price_cap": 3000.0, "base_price": 55.0, "penalty_threshold_hz": 0.05,
        "penalty_rate": 10000.0, "freq_response_rate": 20.0,
    },
    "NEM": {
        "f_nom": 50.0, "H": 3.5, "D": 0.8, "v_nom_kv": 330.0,
        "price_cap": 17500.0, "base_price": 60.0, "penalty_threshold_hz": 0.05,
        "penalty_rate": 20000.0, "freq_response_rate": 30.0,
    },
    "CAISO": {
        "f_nom": 60.0, "H": 5.0, "D": 1.1, "v_nom_kv": 500.0,
        "price_cap": 2000.0, "base_price": 50.0, "penalty_threshold_hz": 0.036,
        "penalty_rate": 12000.0, "freq_response_rate": 22.0,
    },
}


# ─────────────────────────────────────────────────────────────
# Kalman State Estimator
# ─────────────────────────────────────────────────────────────

class KalmanEstimator:
    """2D Kalman filter for [freq_deviation, power_injection] estimation."""

    def __init__(self, H: float = 5.0, D: float = 1.0, dt: float = 0.01,
                 process_noise: float = 0.001, measurement_noise: float = 0.005):
        self.H = H
        self.D = D
        self.dt = dt

        # State: [freq_deviation, injection_mw]
        self.x = np.array([0.0, 0.0])

        # State transition
        self.A = np.array([
            [1.0 - D * dt / (2 * H), dt / (2 * H)],
            [0.0, 1.0],
        ])

        # Observation matrix (we observe frequency directly)
        self.C = np.array([[1.0, 0.0], [0.0, 1.0]])

        # Covariances
        self.P = np.eye(2) * 0.1
        self.Q = np.eye(2) * process_noise
        self.R = np.eye(2) * measurement_noise

    def predict(self) -> np.ndarray:
        self.x = self.A @ self.x
        self.P = self.A @ self.P @ self.A.T + self.Q
        return self.x.copy()

    def update(self, measurement: np.ndarray) -> np.ndarray:
        y = measurement - self.C @ self.x
        S = self.C @ self.P @ self.C.T + self.R
        K = self.P @ self.C.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(2) - K @ self.C) @ self.P
        return self.x.copy()

    def step(self, measurement: np.ndarray) -> np.ndarray:
        self.predict()
        return self.update(measurement)


# ─────────────────────────────────────────────────────────────
# Stochastic Disturbance Generator
# ─────────────────────────────────────────────────────────────

class DisturbanceGenerator:
    """Generates realistic grid disturbance profiles."""

    def __init__(self, seed: int = 42, severity: float = 1.0):
        self.rng = np.random.RandomState(seed)
        self.severity = severity
        self._events = []
        self._generate_events()

    def _generate_events(self):
        """Pre-generate disturbance events."""
        n_events = self.rng.poisson(8)
        for _ in range(n_events):
            event_time = self.rng.uniform(10, 580)
            event_type = self.rng.choice(["step", "ramp", "oscillation"])
            magnitude = self.rng.uniform(20, 150) * self.severity

            if event_type == "step":
                self._events.append({
                    "type": "step", "time": event_time,
                    "magnitude": magnitude * self.rng.choice([-1, 1]),
                    "duration": self.rng.uniform(5, 30),
                })
            elif event_type == "ramp":
                self._events.append({
                    "type": "ramp", "time": event_time,
                    "magnitude": magnitude * 0.5 * self.rng.choice([-1, 1]),
                    "duration": self.rng.uniform(10, 60),
                })
            else:
                self._events.append({
                    "type": "oscillation", "time": event_time,
                    "magnitude": magnitude * 0.3,
                    "frequency": self.rng.uniform(0.1, 2.0),
                    "duration": self.rng.uniform(10, 40),
                })

    def get_disturbance(self, t: float) -> float:
        """Get total disturbance (MW) at time t."""
        d = self.rng.normal(0, 2.0 * self.severity)  # Background noise
        for event in self._events:
            t0 = event["time"]
            dur = event.get("duration", 20)
            if t0 <= t <= t0 + dur:
                progress = (t - t0) / dur
                if event["type"] == "step":
                    d += event["magnitude"]
                elif event["type"] == "ramp":
                    d += event["magnitude"] * progress
                elif event["type"] == "oscillation":
                    d += event["magnitude"] * np.sin(
                        2 * np.pi * event["frequency"] * (t - t0)
                    )
        return d


# ─────────────────────────────────────────────────────────────
# Swing Equation Physics Engine
# ─────────────────────────────────────────────────────────────

class SwingEquationEngine:
    """Continuous-time Swing Equation model with voltage dynamics."""

    def __init__(self, f_nom: float = 60.0, H: float = 5.0, D: float = 1.0,
                 v_nom_kv: float = 345.0, max_injection_mw: float = 100.0):
        self.f_nom = f_nom
        self.H = H
        self.D = D
        self.v_nom = v_nom_kv
        self.max_inj = max_injection_mw

        # State: [freq_deviation, injection, voltage_deviation]
        self.state = np.array([0.0, 0.0, 0.0])

    def step(self, control_mw: float, disturbance_mw: float, dt: float) -> np.ndarray:
        """Advance physics by dt seconds."""
        df, P_inj, dv = self.state

        # Swing equation: 2H * d(Δf)/dt = P_inj - D*Δf - P_disturbance
        ddf_dt = (P_inj - self.D * df - disturbance_mw) / (2 * self.H)

        # Injection ramp (control is desired injection, not ramp rate)
        ramp_limit = 50.0 * dt  # 50 MW/s max ramp
        dP = np.clip(control_mw - P_inj, -ramp_limit, ramp_limit)

        # Voltage dynamics (simplified reactive power coupling)
        ddv_dt = -0.5 * dv + 0.01 * disturbance_mw + np.random.normal(0, 0.001)

        # Integrate
        new_df = df + ddf_dt * dt
        new_P = np.clip(P_inj + dP, -self.max_inj, self.max_inj)
        new_dv = dv + ddv_dt * dt

        # Clamp
        new_df = np.clip(new_df, -3.0, 3.0)
        new_dv = np.clip(new_dv, -0.15, 0.15)

        self.state = np.array([new_df, new_P, new_dv])
        return self.state.copy()

    def get_frequency(self) -> float:
        return self.f_nom + self.state[0]

    def get_voltage_pu(self) -> float:
        return 1.0 + self.state[2]

    def reset(self):
        self.state = np.array([0.0, 0.0, 0.0])


# ─────────────────────────────────────────────────────────────
# PID Controller (Baseline)
# ─────────────────────────────────────────────────────────────

class PIDController:
    """Standard PID frequency controller for benchmarking."""

    def __init__(self, Kp: float = 50.0, Ki: float = 5.0, Kd: float = 10.0,
                 max_output: float = 100.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.max_output = max_output
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, freq_deviation: float, dt: float) -> float:
        """Compute PID output from frequency deviation."""
        error = -freq_deviation  # Negative feedback

        self._integral += error * dt
        self._integral = np.clip(self._integral, -20.0, 20.0)

        derivative = (error - self._prev_error) / max(dt, 1e-6)
        self._prev_error = error

        output = self.Kp * error + self.Ki * self._integral + self.Kd * derivative
        return np.clip(output, -self.max_output, self.max_output)

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


# ─────────────────────────────────────────────────────────────
# HJB Real-Time Controller
# ─────────────────────────────────────────────────────────────

class HJBController:
    """Real-time HJB optimal controller using pre-solved value function."""

    def __init__(self, market: str = "ERCOT", max_injection_mw: float = 100.0):
        params = MARKET_PARAMS.get(market, MARKET_PARAMS["ERCOT"])
        self.H = params["H"]
        self.D = params["D"]
        self.f_nom = params["f_nom"]
        self.penalty_threshold = params["penalty_threshold_hz"]
        self.penalty_rate = params["penalty_rate"]
        self.freq_response_rate = params["freq_response_rate"]
        self.max_inj = max_injection_mw

        # Pre-build value function via dynamic programming
        self._build_value_function()

    def _build_value_function(self):
        """Offline solve: discretize state space and compute V(x)."""
        # Grid for freq deviation and injection
        self.df_grid = np.linspace(-2.0, 2.0, 41)
        self.p_grid = np.linspace(-self.max_inj, self.max_inj, 21)
        self.u_grid = np.linspace(-self.max_inj, self.max_inj, 21)

        n_df, n_p = len(self.df_grid), len(self.p_grid)
        self.V = np.zeros((n_df, n_p))
        self.policy = np.zeros((n_df, n_p))

        dt = 0.5  # Value iteration timestep

        # Terminal cost
        for i, df in enumerate(self.df_grid):
            for j, p in enumerate(self.p_grid):
                self.V[i, j] = 200.0 * df ** 2 + 0.1 * abs(p)

        # Backward sweeps
        for sweep in range(6):
            V_old = self.V.copy()
            for i, df in enumerate(self.df_grid):
                for j, p in enumerate(self.p_grid):
                    best_cost = np.inf
                    best_u = 0.0
                    for u in self.u_grid:
                        # Running cost
                        L = 100.0 * df ** 2 + 0.01 * abs(u - p)
                        if abs(df) > self.penalty_threshold:
                            L += self.penalty_rate * (abs(df) - self.penalty_threshold) ** 2

                        # Next state (swing equation)
                        new_df = df + (p - self.D * df) / (2 * self.H) * dt
                        new_df = np.clip(new_df, -2.0, 2.0)

                        # Interpolate V(next)
                        idx_df = np.interp(new_df, self.df_grid, np.arange(n_df))
                        idx_p = np.interp(u, self.p_grid, np.arange(n_p))
                        i1, i2 = int(idx_df), min(int(idx_df) + 1, n_df - 1)
                        j1, j2 = int(idx_p), min(int(idx_p) + 1, n_p - 1)
                        a = idx_df - i1
                        b = idx_p - j1
                        V_next = (
                            self.V[i1, j1] * (1 - a) * (1 - b) +
                            self.V[i2, j1] * a * (1 - b) +
                            self.V[i1, j2] * (1 - a) * b +
                            self.V[i2, j2] * a * b
                        )

                        total = L * dt + V_next
                        if total < best_cost:
                            best_cost = total
                            best_u = u

                    self.V[i, j] = best_cost
                    self.policy[i, j] = best_u

            delta = np.max(np.abs(self.V - V_old))
            if delta < 0.01:
                break

        logger.info(f"HJB value function solved ({sweep + 1} sweeps, δ={delta:.4f})")

    def compute(self, freq_deviation: float, current_injection: float,
                lmp_price: float = 50.0) -> float:
        """Extract optimal control from value function."""
        n_df, n_p = len(self.df_grid), len(self.p_grid)

        # Interpolate policy
        idx_df = np.interp(freq_deviation, self.df_grid, np.arange(n_df))
        idx_p = np.interp(current_injection, self.p_grid, np.arange(n_p))

        i1, i2 = int(idx_df), min(int(idx_df) + 1, n_df - 1)
        j1, j2 = int(idx_p), min(int(idx_p) + 1, n_p - 1)
        a = idx_df - i1
        b = idx_p - j1

        u = (
            self.policy[i1, j1] * (1 - a) * (1 - b) +
            self.policy[i2, j1] * a * (1 - b) +
            self.policy[i1, j2] * (1 - a) * b +
            self.policy[i2, j2] * a * b
        )

        # Price-aware modulation: increase response when prices are high
        price_factor = 1.0 + 0.5 * np.clip((lmp_price - 100) / 500, 0, 2.0)
        u *= price_factor

        return np.clip(u, -self.max_inj, self.max_inj)


# ─────────────────────────────────────────────────────────────
# Price Generator
# ─────────────────────────────────────────────────────────────

class PriceGenerator:
    """Generate realistic LMP price trajectories."""

    def __init__(self, base_price: float = 50.0, price_cap: float = 5000.0,
                 seed: int = 42):
        self.base = base_price
        self.cap = price_cap
        self.rng = np.random.RandomState(seed)
        self._price = base_price

    def step(self, freq_deviation: float, dt: float) -> float:
        """Price evolves with mean-reversion + freq-correlated spikes."""
        mean_revert = 0.01 * (self.base - self._price)
        noise = self.rng.normal(0, 2.0)
        spike = 0.0
        if abs(freq_deviation) > 0.3:
            spike = 500.0 * abs(freq_deviation)
        if self.rng.random() < 0.002:
            spike += self.rng.uniform(200, 1500)
        self._price += (mean_revert + noise + spike) * dt
        self._price = np.clip(self._price, 5.0, self.cap)
        return self._price


# ─────────────────────────────────────────────────────────────
# Grid Stabilizer — Main Closed-Loop Controller
# ─────────────────────────────────────────────────────────────

class GridStabilizer:
    """Closed-loop grid stabilization controller.

    Orchestrates: Measurement → Estimation → Control → Injection → Physics
    """

    def __init__(self, market: str = "ERCOT", controller_type: str = "HJB",
                 max_injection_mw: float = 100.0, dt: float = 0.01,
                 disturbance_severity: float = 1.0, seed: int = 42):
        params = MARKET_PARAMS.get(market, MARKET_PARAMS["ERCOT"])
        self.market = market
        self.dt = dt
        self.controller_type = controller_type

        # Physics engine
        self.engine = SwingEquationEngine(
            f_nom=params["f_nom"], H=params["H"], D=params["D"],
            v_nom_kv=params["v_nom_kv"], max_injection_mw=max_injection_mw,
        )

        # State estimator
        self.estimator = KalmanEstimator(
            H=params["H"], D=params["D"], dt=dt,
        )

        # Controller
        if controller_type == "HJB":
            self.controller = HJBController(market=market, max_injection_mw=max_injection_mw)
        elif controller_type == "PID":
            self.controller = PIDController(max_output=max_injection_mw)
        elif controller_type == "NONE":
            self.controller = None
        else:
            raise ValueError(f"Unknown controller: {controller_type}")

        # Disturbance and price generators
        self.disturbance = DisturbanceGenerator(seed=seed, severity=disturbance_severity)
        self.price_gen = PriceGenerator(
            base_price=params["base_price"],
            price_cap=params["price_cap"],
            seed=seed + 1,
        )

        # Market params for revenue calculation
        self.penalty_threshold = params["penalty_threshold_hz"]
        self.penalty_rate = params["penalty_rate"]
        self.freq_response_rate = params["freq_response_rate"]

    def run(self, duration_s: float = 600.0) -> SimulationResult:
        """Run closed-loop simulation for the specified duration."""
        n_steps = int(duration_s / self.dt)
        snapshots = []
        total_revenue = 0.0
        total_cost = 0.0
        violations = 0

        self.engine.reset()
        if isinstance(self.controller, PIDController):
            self.controller.reset()

        logger.info(f"[{self.controller_type}] Starting {self.market} simulation: "
                    f"{duration_s}s, dt={self.dt}s, steps={n_steps}")

        sample_interval = max(1, int(0.1 / self.dt))  # Sample at 10 Hz for output

        for step in range(n_steps):
            t = step * self.dt
            df, P_inj, dv = self.engine.state

            # 1. Disturbance
            disturbance = self.disturbance.get_disturbance(t)

            # 2. Noisy measurement
            meas_f = df + np.random.normal(0, 0.003)
            meas_p = P_inj + np.random.normal(0, 0.5)

            # 3. Kalman estimation
            estimated = self.estimator.step(np.array([meas_f, meas_p]))

            # 4. Price
            lmp = self.price_gen.step(df, self.dt)

            # 5. Control
            if self.controller is None:
                control = 0.0
            elif isinstance(self.controller, HJBController):
                control = self.controller.compute(
                    estimated[0], estimated[1], lmp
                )
            elif isinstance(self.controller, PIDController):
                control = self.controller.compute(estimated[0], self.dt)

            # 6. Physics step
            self.engine.step(control, disturbance, self.dt)

            # 7. Revenue/cost tracking
            if abs(df) > self.penalty_threshold:
                penalty = self.penalty_rate * (abs(df) - self.penalty_threshold) ** 2 * self.dt
                total_cost += penalty
                violations += 1
            freq_response_payment = self.freq_response_rate * abs(P_inj) * self.dt / 3600
            total_revenue += freq_response_payment

            # 8. Record snapshot (subsampled)
            if step % sample_interval == 0:
                snapshots.append(GridSnapshot(
                    time_s=t,
                    frequency_hz=self.engine.get_frequency(),
                    freq_deviation_hz=df,
                    rocof_hz_s=(df - (snapshots[-1].freq_deviation_hz if snapshots else 0)) / (sample_interval * self.dt),
                    voltage_pu=self.engine.get_voltage_pu(),
                    active_power_mw=P_inj,
                    injection_mw=control,
                    disturbance_mw=disturbance,
                    lmp_price=lmp,
                    controller=self.controller_type,
                ))

        # Compute statistics
        deviations = [abs(s.freq_deviation_hz) for s in snapshots]
        nominal_count = sum(1 for d in deviations if d < self.penalty_threshold)
        stability = 100.0 * nominal_count / max(len(deviations), 1)

        result = SimulationResult(
            snapshots=snapshots,
            total_cost=total_cost,
            total_revenue=total_revenue - total_cost,
            freq_violations=violations,
            freq_stability_pct=stability,
            max_deviation_hz=max(deviations) if deviations else 0,
            avg_deviation_hz=np.mean(deviations) if deviations else 0,
            controller_name=self.controller_type,
            market=self.market,
            duration_s=duration_s,
        )

        logger.info(result.summary())
        return result


# ─────────────────────────────────────────────────────────────
# Convenience: Run Comparative Simulation
# ─────────────────────────────────────────────────────────────

def run_simulation(duration_s: float = 600.0, market: str = "ERCOT",
                   seed: int = 42, severity: float = 1.0) -> Dict[str, SimulationResult]:
    """Run HJB vs PID vs No-Control on identical disturbance profiles."""
    results = {}
    for ctrl in ["HJB", "PID", "NONE"]:
        stabilizer = GridStabilizer(
            market=market, controller_type=ctrl, dt=0.01,
            disturbance_severity=severity, seed=seed,
        )
        results[ctrl] = stabilizer.run(duration_s)
    return results


def print_comparison(results: Dict[str, SimulationResult]):
    """Print comparison table."""
    print("\n" + "=" * 80)
    print(" PRIMEnergeia Grid Stabilizer — Controller Comparison")
    print("=" * 80)
    print(f"{'Controller':<12} {'Stability %':>12} {'Max Δf Hz':>12} "
          f"{'Avg Δf Hz':>12} {'Revenue $':>12} {'Violations':>12}")
    print("-" * 80)
    for name, r in results.items():
        print(f"{name:<12} {r.freq_stability_pct:>11.2f}% "
              f"{r.max_deviation_hz:>12.4f} {r.avg_deviation_hz:>12.4f} "
              f"${r.total_revenue:>11,.2f} {r.freq_violations:>12}")
    print("=" * 80)

    # HJB improvement over PID
    if "HJB" in results and "PID" in results:
        hjb, pid = results["HJB"], results["PID"]
        improvement = hjb.freq_stability_pct - pid.freq_stability_pct
        rev_diff = hjb.total_revenue - pid.total_revenue
        print(f"\n  HJB vs PID: +{improvement:.2f}% stability, "
              f"+${rev_diff:,.2f} revenue")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(message)s")

    print("[⚡] PRIMEnergeia Grid Stabilizer — Full Simulation")
    print()

    for market in ["ERCOT", "SEN", "MIBEL"]:
        print(f"\n{'─' * 80}")
        print(f"  Market: {market}")
        print(f"{'─' * 80}")
        results = run_simulation(duration_s=300, market=market)
        print_comparison(results)
