"""
PRIMEnergeia — Granas Self-Driving Lab (SDL) Engine
====================================================
Closed-loop automation for perovskite solar cell fabrication.

Architecture:
  AI designs experiment → Infrastructure triggers hardware →
  Hardware streams raw data → AI analyzes & iterates

Layers:
  1. Edge Layer     — OPC-UA / MQTT device adapters
  2. Data Pipeline  — Kafka/Redpanda → InfluxDB time-series
  3. Orchestration — SiLA 2 / PyLabRobot instruction generation
  4. Feedback Loop  — Active learning triggers (pause/pivot/accelerate)

FAIR Principles: Findable, Accessible, Interoperable, Reusable

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - [SDL] - %(message)s")


# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────
class DeviceProtocol(Enum):
    OPC_UA = "opc-ua"
    MQTT = "mqtt"
    SILA2 = "sila2"
    REST_API = "rest-api"
    SERIAL = "serial"
    MODBUS = "modbus"
    CUSTOM = "custom"


class ExperimentPhase(Enum):
    IDLE = "idle"
    DESIGN = "design"           # AI designing experiment
    QUEUED = "queued"           # Waiting for hardware
    RUNNING = "running"        # Hardware executing
    STREAMING = "streaming"    # Data flowing in
    ANALYZING = "analyzing"    # AI processing results
    PIVOTING = "pivoting"      # Active learning trigger
    COMPLETED = "completed"
    FAILED = "failed"


class ActiveLearningAction(Enum):
    CONTINUE = "continue"
    PAUSE = "pause"
    PIVOT = "pivot"
    ACCELERATE = "accelerate"
    TERMINATE = "terminate"


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class DeviceConfig:
    """Configuration for a lab device on the edge layer."""
    device_id: str
    name: str
    protocol: DeviceProtocol
    endpoint: str                          # URI or address
    channels: List[str] = field(default_factory=list)
    sampling_rate_hz: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sila2_command(self, action: str, params: Dict) -> Dict:
        """Generate SiLA 2 compliant command."""
        return {
            "command": action,
            "device": self.device_id,
            "protocol": self.protocol.value,
            "parameters": params,
            "timestamp": datetime.now().isoformat(),
        }


@dataclass
class DataPoint:
    """Single measurement from a lab device (FAIR-compliant)."""
    device_id: str
    channel: str
    value: float
    unit: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    experiment_id: str = ""
    sample_id: str = ""

    def to_influx_line(self) -> str:
        """Convert to InfluxDB line protocol."""
        tags = f"device={self.device_id},channel={self.channel}"
        if self.experiment_id:
            tags += f",experiment={self.experiment_id}"
        fields = f"value={self.value}"
        ts = int(datetime.fromisoformat(self.timestamp).timestamp() * 1e9)
        return f"measurement,{tags} {fields} {ts}"


@dataclass
class ExperimentDesign:
    """AI-generated experiment specification."""
    experiment_id: str
    design_source: str               # "HJB" / "Bayesian" / "RL"
    parameters: Dict[str, float]     # Fabrication parameters
    predicted_pce: float             # AI-predicted PCE
    confidence: float                # AI confidence (0-1)
    instructions: List[Dict]         # Machine-readable steps
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetrySnapshot:
    """Real-time telemetry from a running experiment."""
    experiment_id: str
    phase: ExperimentPhase
    elapsed_s: float
    measurements: List[DataPoint]
    anomaly_score: float = 0.0         # 0 = normal, 1 = anomalous
    model_uncertainty: float = 0.0     # Epistemic uncertainty


@dataclass
class SDLResult:
    """Complete result from an SDL campaign."""
    campaign_id: str
    experiments_run: int
    best_pce: float
    best_parameters: Dict[str, float]
    pareto_front: List[Dict]
    telemetry_log: List[TelemetrySnapshot]
    active_learning_decisions: List[Dict]
    total_time_s: float


# ─────────────────────────────────────────────────────────────
# Edge Layer — Device Adapters
# ─────────────────────────────────────────────────────────────
class EdgeLayer:
    """
    Edge Layer: interfaces with lab equipment via OPC-UA, MQTT,
    SiLA 2, REST, Serial, or custom drivers.

    Provides unified abstraction over heterogeneous lab hardware.
    """

    def __init__(self):
        self.devices: Dict[str, DeviceConfig] = {}
        self.data_buffer: List[DataPoint] = []

    def register_device(self, config: DeviceConfig):
        """Register a lab device."""
        self.devices[config.device_id] = config
        logger.info(f"Registered device: {config.name} ({config.protocol.value})")

    def send_command(self, device_id: str, action: str,
                     params: Dict = None) -> Dict:
        """Send command to a device via its protocol."""
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not registered")

        cmd = device.to_sila2_command(action, params or {})
        logger.info(f"→ {device.name}: {action} {params}")

        # Simulate response (real implementation would use protocol adapters)
        return {
            "status": "accepted",
            "command_id": f"cmd_{int(time.time()*1000)}",
            "device": device_id,
            "latency_ms": np.random.uniform(5, 50),
        }

    def read_measurement(self, device_id: str, channel: str,
                         experiment_id: str = "") -> DataPoint:
        """Read a single measurement from a device."""
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not registered")

        # Simulate measurement (real implementation would read from hardware)
        dp = DataPoint(
            device_id=device_id,
            channel=channel,
            value=np.random.normal(0, 1),
            unit="a.u.",
            timestamp=datetime.now().isoformat(),
            experiment_id=experiment_id,
        )
        self.data_buffer.append(dp)
        return dp

    def configure_default_lab(self):
        """Register a standard perovskite fab line."""
        devices = [
            DeviceConfig("spincoater_01", "Spin Coater (Laurell WS-650)",
                         DeviceProtocol.SERIAL, "/dev/ttyUSB0",
                         ["rpm", "acceleration", "duration_s"]),
            DeviceConfig("hotplate_01", "Hot Plate (IKA C-MAG HS7)",
                         DeviceProtocol.MODBUS, "192.168.1.10:502",
                         ["temperature_C", "ramp_rate", "duration_s"]),
            DeviceConfig("uvvis_01", "UV-Vis Spectrometer (Ocean Insight)",
                         DeviceProtocol.REST_API, "http://192.168.1.20:8080",
                         ["wavelength_nm", "absorbance", "transmittance"]),
            DeviceConfig("xrd_01", "XRD (Rigaku MiniFlex)",
                         DeviceProtocol.OPC_UA, "opc.tcp://192.168.1.30:4840",
                         ["two_theta", "intensity", "peak_fwhm"]),
            DeviceConfig("solar_sim_01", "Solar Simulator (Newport Oriel)",
                         DeviceProtocol.SILA2, "sila://192.168.1.40:50051",
                         ["voltage_V", "current_mA", "pce_pct"]),
            DeviceConfig("liquid_handler_01", "Liquid Handler (Opentrons OT-2)",
                         DeviceProtocol.REST_API, "http://192.168.1.50:31950",
                         ["volume_uL", "pipette", "well_position"]),
            DeviceConfig("glovebox_01", "Glovebox (MBraun)",
                         DeviceProtocol.MQTT, "mqtt://192.168.1.60:1883",
                         ["o2_ppm", "h2o_ppm", "pressure_mbar"]),
        ]
        for d in devices:
            self.register_device(d)
        logger.info(f"Lab configured: {len(devices)} devices registered")


# ─────────────────────────────────────────────────────────────
# Data Pipeline — Kafka/InfluxDB Abstraction
# ─────────────────────────────────────────────────────────────
class DataPipeline:
    """
    Low-latency data pipeline for ingesting high-throughput raw data.

    Stack: Kafka/Redpanda → InfluxDB → Vector embeddings
    All data tagged with FAIR metadata.
    """

    def __init__(self, buffer_size: int = 10000):
        self.buffer: List[DataPoint] = []
        self.buffer_size = buffer_size
        self.total_ingested = 0
        self.topics: Dict[str, List[DataPoint]] = {}

    def ingest(self, data_point: DataPoint):
        """Ingest a data point into the pipeline."""
        topic = f"{data_point.device_id}.{data_point.channel}"
        if topic not in self.topics:
            self.topics[topic] = []
        self.topics[topic].append(data_point)
        self.buffer.append(data_point)
        self.total_ingested += 1

        if len(self.buffer) > self.buffer_size:
            self.flush()

    def flush(self):
        """Flush buffer to InfluxDB (simulated)."""
        n = len(self.buffer)
        self.buffer.clear()
        logger.info(f"Pipeline flushed {n} points to InfluxDB")

    def query_latest(self, device_id: str, channel: str,
                     n: int = 100) -> List[DataPoint]:
        """Query latest N measurements for a device/channel."""
        topic = f"{device_id}.{channel}"
        return self.topics.get(topic, [])[-n:]

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return {
            "total_ingested": self.total_ingested,
            "buffer_size": len(self.buffer),
            "topics": len(self.topics),
            "points_per_topic": {k: len(v) for k, v in self.topics.items()},
        }


# ─────────────────────────────────────────────────────────────
# Orchestration Layer — Experiment Orchestrator
# ─────────────────────────────────────────────────────────────
class Orchestrator:
    """
    Translates AI model outputs into machine-readable instructions.

    Supports: SiLA 2, PyLabRobot, custom middleware.
    Generates step-by-step fabrication protocols from design parameters.
    """

    def __init__(self, edge: EdgeLayer, pipeline: DataPipeline):
        self.edge = edge
        self.pipeline = pipeline
        self.current_experiment: Optional[ExperimentDesign] = None
        self.phase = ExperimentPhase.IDLE

    def design_to_protocol(self, design: ExperimentDesign) -> List[Dict]:
        """
        Convert experiment design parameters to executable protocol.

        Example: {radius: 250, density: 0.5, thickness: 800}
        → spin coat → anneal → characterize
        """
        params = design.parameters
        steps = [
            # Step 1: Prepare solution
            {
                "step": 1,
                "device": "liquid_handler_01",
                "action": "dispense",
                "params": {
                    "solution": "PbI2_MAI_DMF",
                    "volume_uL": params.get("precursor_volume_uL", 100),
                    "concentration_M": params.get("concentration_M", 1.2),
                },
            },
            # Step 2: Spin coat
            {
                "step": 2,
                "device": "spincoater_01",
                "action": "spin",
                "params": {
                    "rpm": params.get("spin_rpm", 4000),
                    "duration_s": params.get("spin_duration_s", 30),
                    "acceleration": params.get("spin_accel", 2000),
                },
            },
            # Step 3: Anneal (HJB-optimized schedule)
            {
                "step": 3,
                "device": "hotplate_01",
                "action": "run_schedule",
                "params": {
                    "schedule": params.get("anneal_schedule", [
                        {"temp_C": 100, "duration_s": 600},
                        {"temp_C": 150, "duration_s": 300},
                    ]),
                },
            },
            # Step 4: UV-Vis characterization
            {
                "step": 4,
                "device": "uvvis_01",
                "action": "scan",
                "params": {
                    "wavelength_range": [300, 1200],
                    "integration_time_ms": 100,
                },
            },
            # Step 5: Solar simulation (PCE measurement)
            {
                "step": 5,
                "device": "solar_sim_01",
                "action": "iv_curve",
                "params": {
                    "voltage_range": [-0.1, 1.2],
                    "scan_rate": 0.1,
                    "illumination": "AM1.5G",
                },
            },
        ]
        return steps

    def execute_experiment(self, design: ExperimentDesign,
                           simulate: bool = True) -> TelemetrySnapshot:
        """Execute the full experiment protocol."""
        self.current_experiment = design
        self.phase = ExperimentPhase.RUNNING

        protocol = self.design_to_protocol(design)
        measurements = []
        t_start = time.time()

        for step in protocol:
            device_id = step["device"]
            action = step["action"]
            params = step["params"]

            # Send command to device
            self.edge.send_command(device_id, action, params)

            if simulate:
                # Simulate measurement data
                for ch in self.edge.devices[device_id].channels:
                    dp = DataPoint(
                        device_id=device_id,
                        channel=ch,
                        value=np.random.normal(50, 10),
                        unit="a.u.",
                        timestamp=datetime.now().isoformat(),
                        experiment_id=design.experiment_id,
                        sample_id=f"sample_{design.experiment_id}",
                    )
                    self.pipeline.ingest(dp)
                    measurements.append(dp)

        elapsed = time.time() - t_start
        self.phase = ExperimentPhase.COMPLETED

        return TelemetrySnapshot(
            experiment_id=design.experiment_id,
            phase=self.phase,
            elapsed_s=elapsed,
            measurements=measurements,
            anomaly_score=np.random.uniform(0, 0.3),
            model_uncertainty=np.random.uniform(0.05, 0.3),
        )


# ─────────────────────────────────────────────────────────────
# Feedback Loop — Active Learning
# ─────────────────────────────────────────────────────────────
class ActiveLearningLoop:
    """
    Active learning feedback controller.

    Decides whether to:
      - CONTINUE: proceed with current exploration
      - PAUSE: wait for human review
      - PIVOT: change exploration direction
      - ACCELERATE: intensify around promising region
      - TERMINATE: stop campaign (convergence or budget)

    Uses uncertainty quantification and information gain to trigger decisions.
    """

    def __init__(
        self,
        uncertainty_threshold: float = 0.7,
        anomaly_threshold: float = 0.8,
        improvement_threshold: float = 0.01,
        max_stagnation: int = 5,
    ):
        self.uncertainty_threshold = uncertainty_threshold
        self.anomaly_threshold = anomaly_threshold
        self.improvement_threshold = improvement_threshold
        self.max_stagnation = max_stagnation
        self.history: List[Dict] = []
        self.stagnation_count = 0
        self.best_pce = 0.0

    def evaluate(self, telemetry: TelemetrySnapshot,
                 predicted_pce: float,
                 measured_pce: float) -> ActiveLearningAction:
        """
        Evaluate telemetry and decide next action.
        """
        decision_data = {
            "experiment_id": telemetry.experiment_id,
            "anomaly_score": telemetry.anomaly_score,
            "model_uncertainty": telemetry.model_uncertainty,
            "predicted_pce": predicted_pce,
            "measured_pce": measured_pce,
            "prediction_error": abs(predicted_pce - measured_pce),
        }

        action = ActiveLearningAction.CONTINUE

        # Check for anomaly
        if telemetry.anomaly_score > self.anomaly_threshold:
            action = ActiveLearningAction.PAUSE
            decision_data["reason"] = "High anomaly detected"

        # Check for high uncertainty → explore
        elif telemetry.model_uncertainty > self.uncertainty_threshold:
            action = ActiveLearningAction.PIVOT
            decision_data["reason"] = "High uncertainty — explore new region"

        # Check for improvement
        elif measured_pce > self.best_pce + self.improvement_threshold:
            self.best_pce = measured_pce
            self.stagnation_count = 0
            action = ActiveLearningAction.ACCELERATE
            decision_data["reason"] = "New best found — exploit"

        else:
            self.stagnation_count += 1
            if self.stagnation_count >= self.max_stagnation:
                action = ActiveLearningAction.TERMINATE
                decision_data["reason"] = "Stagnation limit reached"

        decision_data["action"] = action.value
        self.history.append(decision_data)

        logger.info(f"Active Learning: {action.value} — "
                    f"PCE={measured_pce:.2f}% (pred={predicted_pce:.2f}%)")

        return action


# ─────────────────────────────────────────────────────────────
# SDL Campaign Orchestrator
# ─────────────────────────────────────────────────────────────
class SDLCampaign:
    """
    Top-level Self-Driving Lab campaign.

    Runs a full closed-loop optimization:
    AI designs → Execute → Measure → Learn → Iterate
    """

    def __init__(self, campaign_id: str = "SDL_Alpha"):
        self.campaign_id = campaign_id
        self.edge = EdgeLayer()
        self.pipeline = DataPipeline()
        self.orchestrator = Orchestrator(self.edge, self.pipeline)
        self.active_learning = ActiveLearningLoop()
        self.experiments: List[ExperimentDesign] = []
        self.results: List[TelemetrySnapshot] = []

        # Initialize default lab
        self.edge.configure_default_lab()

    def run_campaign(self, n_experiments: int = 10,
                     design_fn: Optional[Callable] = None
                     ) -> SDLResult:
        """
        Run a full SDL campaign.

        Parameters
        ----------
        n_experiments : int
            Maximum number of experiments
        design_fn : callable, optional
            Function(iteration, history) → ExperimentDesign.
            If None, uses random exploration.
        """
        logger.info("=" * 60)
        logger.info(f" SDL CAMPAIGN: {self.campaign_id}")
        logger.info(f" Max experiments: {n_experiments}")
        logger.info("=" * 60)

        t_start = time.time()
        pareto_front = []

        for i in range(n_experiments):
            # Step 1: Design experiment
            if design_fn:
                design = design_fn(i, self.experiments)
            else:
                design = self._random_design(i)

            self.experiments.append(design)

            # Step 2: Execute
            telemetry = self.orchestrator.execute_experiment(design)
            self.results.append(telemetry)

            # Step 3: Simulate PCE measurement
            measured_pce = self._simulate_pce(design.parameters)

            # Step 4: Active learning decision
            action = self.active_learning.evaluate(
                telemetry, design.predicted_pce, measured_pce
            )

            # Update Pareto front
            pareto_front.append({
                "experiment": i,
                "parameters": design.parameters,
                "pce": measured_pce,
                "predicted_pce": design.predicted_pce,
            })

            if action == ActiveLearningAction.TERMINATE:
                logger.info(f"Campaign terminated at experiment {i+1}")
                break

        total_time = time.time() - t_start
        best = max(pareto_front, key=lambda x: x["pce"])

        logger.info("=" * 60)
        logger.info(f" Campaign Complete: {len(self.experiments)} experiments")
        logger.info(f" Best PCE: {best['pce']:.2f}%")
        logger.info(f" Total time: {total_time:.1f}s")
        logger.info("=" * 60)

        return SDLResult(
            campaign_id=self.campaign_id,
            experiments_run=len(self.experiments),
            best_pce=best["pce"],
            best_parameters=best["parameters"],
            pareto_front=sorted(pareto_front, key=lambda x: -x["pce"]),
            telemetry_log=self.results,
            active_learning_decisions=self.active_learning.history,
            total_time_s=total_time,
        )

    def _random_design(self, iteration: int) -> ExperimentDesign:
        """Generate a random experiment design for exploration."""
        params = {
            "granule_radius_nm": np.random.uniform(100, 500),
            "packing_density": np.random.uniform(0.2, 0.7),
            "thickness_nm": np.random.uniform(300, 1500),
            "spin_rpm": np.random.uniform(2000, 6000),
            "spin_duration_s": np.random.uniform(20, 60),
            "concentration_M": np.random.uniform(0.8, 1.5),
            "precursor_volume_uL": np.random.uniform(50, 150),
        }

        return ExperimentDesign(
            experiment_id=f"exp_{self.campaign_id}_{iteration:03d}",
            design_source="Random",
            parameters=params,
            predicted_pce=np.random.uniform(10, 22),
            confidence=0.3,
            instructions=[],
        )

    def _simulate_pce(self, params: Dict) -> float:
        """Simulate PCE from design parameters (proxy model)."""
        r = params.get("granule_radius_nm", 250)
        d = params.get("packing_density", 0.5)
        t = params.get("thickness_nm", 800)

        # Proxy: PCE responds to radius, density, thickness
        r_opt = 280
        d_opt = 0.55
        t_opt = 900

        score = (
            15.0
            - 3.0 * ((r - r_opt) / 200)**2
            - 4.0 * ((d - d_opt) / 0.3)**2
            - 2.0 * ((t - t_opt) / 500)**2
            + np.random.normal(0, 0.5)
        )
        return float(np.clip(score, 5, 25))


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    campaign = SDLCampaign("Granas_SDL_v1")
    result = campaign.run_campaign(n_experiments=8)

    print(f"\n{'='*55}")
    print(f" 🧬 SDL CAMPAIGN RESULTS")
    print(f"{'─'*55}")
    print(f" Experiments: {result.experiments_run}")
    print(f" Best PCE:    {result.best_pce:.2f}%")
    print(f" Time:        {result.total_time_s:.1f}s")
    print(f"{'='*55}")
