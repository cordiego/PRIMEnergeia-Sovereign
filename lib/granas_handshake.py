"""
PRIMEnergeia — Granas Grid Handshake Protocol
================================================
Verified power-input signature that connects the Grid Stabilizer
(prime_hardware_bridge.py / grid_state.json) to the Granas agent
pages.  Without a valid handshake the agents stay in a dormant,
low-power state and never unlock high-load simulation capabilities.

Usage in a page:
    from lib.granas_handshake import verify_power_input, show_handshake_banner

    handshake = verify_power_input()
    show_handshake_banner()

    if handshake.mode == "HIGH_LOAD":
        run_full_resolution_sim()

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import json
import os
import time
import logging
from dataclasses import dataclass
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

# ─── Physical Thresholds ────────────────────────────────────
# Nominal grids supported: 50 Hz (EU/Asia/Africa) and 60 Hz (Americas)
FREQ_NOMINAL_60 = 60.0
FREQ_NOMINAL_50 = 50.0
FREQ_TOLERANCE_HZ = 0.05       # ±0.05 Hz for NOMINAL
VOLTAGE_TOLERANCE_PCT = 0.05   # ±5 % of nominal
FRESHNESS_LIVE_S = 30.0        # ≤ 30 s → LIVE
FRESHNESS_STALE_S = 300.0      # ≤ 300 s → STALE (usable but degraded)

# Grid‑state file (written by prime_hardware_bridge.py)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GRID_STATE_PATHS = [
    os.path.join(_PROJECT_ROOT, "grid_state.json"),
    os.path.join(os.path.expanduser("~"), "grid_state.json"),
]


# ─── Data Model ─────────────────────────────────────────────
@dataclass
class GranasHandshake:
    """Result of grid power‑input verification."""
    verified: bool
    grid_freq_hz: float
    grid_voltage_kv: float
    grid_status: str
    freshness_s: float
    confidence_level: str   # LIVE | STALE | OFFLINE
    mode: str               # HIGH_LOAD | LOW_POWER | DORMANT
    reason: str             # Human‑readable explanation


# ─── Core Verification ──────────────────────────────────────
def _read_grid_state() -> Optional[dict]:
    """Read the latest grid state from session state or file."""
    # 1. In‑process handshake (set by hardware bridge running in‑process)
    if "prime_grid_state" in st.session_state:
        return st.session_state["prime_grid_state"]

    # 2. File‑based handshake
    for path in _GRID_STATE_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if "f" in data and "v" in data and "timestamp" in data:
                    return data
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("Failed to read grid_state from %s: %s", path, exc)

    return None


def _detect_nominal_freq(measured_hz: float) -> float:
    """Identify whether the grid is 50 Hz or 60 Hz based on measurement."""
    if abs(measured_hz - FREQ_NOMINAL_60) < 5.0:
        return FREQ_NOMINAL_60
    elif abs(measured_hz - FREQ_NOMINAL_50) < 5.0:
        return FREQ_NOMINAL_50
    # Default to 60 Hz (Americas bias) if ambiguous
    return FREQ_NOMINAL_60


def _detect_nominal_voltage(measured_kv: float) -> float:
    """Derive nominal voltage from the measurement."""
    # Common distribution‑level voltages (kV)
    nominals = [13.8, 34.5, 69.0, 115.0, 138.0, 230.0, 345.0, 500.0]
    closest = min(nominals, key=lambda n: abs(n - measured_kv))
    return closest


def verify_power_input() -> GranasHandshake:
    """
    Verify the Grid Stabilizer's power‑input signature.

    Returns a GranasHandshake describing the current coupling
    state between the grid and the Granas agent suite.
    """
    state = _read_grid_state()

    # ── No telemetry ────────────────────────────────────────
    if state is None:
        hs = GranasHandshake(
            verified=False,
            grid_freq_hz=0.0,
            grid_voltage_kv=0.0,
            grid_status="UNKNOWN",
            freshness_s=float("inf"),
            confidence_level="OFFLINE",
            mode="DORMANT",
            reason="Grid Stabilizer not connected — no grid_state.json found.",
        )
        st.session_state["granas_grid_handshake"] = hs
        return hs

    # ── Parse telemetry ─────────────────────────────────────
    freq = float(state.get("f", 0.0))
    voltage = float(state.get("v", 0.0))
    status = str(state.get("status", "UNKNOWN")).upper()
    ts = float(state.get("timestamp", 0.0))
    age = time.time() - ts if ts > 0 else float("inf")

    # ── Freshness classification ────────────────────────────
    if age <= FRESHNESS_LIVE_S:
        confidence = "LIVE"
    elif age <= FRESHNESS_STALE_S:
        confidence = "STALE"
    else:
        confidence = "OFFLINE"

    # ── Frequency check ─────────────────────────────────────
    nominal_f = _detect_nominal_freq(freq)
    freq_ok = abs(freq - nominal_f) <= FREQ_TOLERANCE_HZ

    # ── Voltage check ───────────────────────────────────────
    nominal_v = _detect_nominal_voltage(voltage)
    voltage_ok = abs(voltage - nominal_v) / nominal_v <= VOLTAGE_TOLERANCE_PCT if nominal_v > 0 else False

    # ── Status check ────────────────────────────────────────
    status_ok = status == "NOMINAL"

    # ── Compose handshake ───────────────────────────────────
    all_ok = freq_ok and voltage_ok and status_ok

    if confidence == "LIVE" and all_ok:
        mode = "HIGH_LOAD"
        reason = (
            f"Grid Stabilizer verified — {freq:.3f} Hz │ {voltage:.2f} kV │ "
            f"Status: {status} │ Age: {age:.1f}s"
        )
        verified = True
    elif confidence in ("LIVE", "STALE") and (freq_ok or status_ok):
        mode = "LOW_POWER"
        issues = []
        if not freq_ok:
            issues.append(f"freq deviation {abs(freq - nominal_f):.3f} Hz")
        if not voltage_ok:
            issues.append(f"voltage deviation {abs(voltage - nominal_v):.2f} kV")
        if not status_ok:
            issues.append(f"status = {status}")
        if confidence == "STALE":
            issues.append(f"signal age {age:.0f}s")
        reason = (
            f"Grid signal degraded — {', '.join(issues)}. "
            f"Running at LOW-POWER resolution."
        )
        verified = False
    else:
        mode = "DORMANT"
        reason = (
            f"Grid Stabilizer offline or critically degraded — "
            f"confidence: {confidence}, status: {status}, age: {age:.0f}s."
        )
        verified = False

    hs = GranasHandshake(
        verified=verified,
        grid_freq_hz=freq,
        grid_voltage_kv=voltage,
        grid_status=status,
        freshness_s=round(age, 1),
        confidence_level=confidence,
        mode=mode,
        reason=reason,
    )
    st.session_state["granas_grid_handshake"] = hs
    return hs


# ─── Visual Banners ─────────────────────────────────────────

def show_handshake_banner():
    """Inject a visual banner showing the Granas ↔ Grid coupling status."""
    hs = verify_power_input()

    if hs.mode == "HIGH_LOAD":
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, #00ff88, #00cc66);
                    color: #050810; padding: 8px 16px; border-radius: 6px;
                    margin-bottom: 8px; font-weight: 600; font-size: 13px;
                    font-family: "JetBrains Mono", monospace;
                    display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 16px;'>⚡</span>
            GRID HANDSHAKE VERIFIED — {hs.grid_freq_hz:.3f} Hz │ {hs.grid_voltage_kv:.2f} kV │ HIGH-LOAD READY
        </div>
        """, unsafe_allow_html=True)

    elif hs.mode == "LOW_POWER":
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, #ff8c00, #ff4500);
                    color: white; padding: 8px 16px; border-radius: 6px;
                    margin-bottom: 8px; font-weight: 600; font-size: 13px;
                    font-family: "JetBrains Mono", monospace;
                    display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 16px;'>⚠</span>
            GRID SIGNAL DEGRADED — Last update {hs.freshness_s:.0f}s ago │ Running at LOW-POWER
        </div>
        """, unsafe_allow_html=True)

    else:  # DORMANT
        st.markdown("""
        <div style='background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    color: white; padding: 8px 16px; border-radius: 6px;
                    margin-bottom: 8px; font-weight: 600; font-size: 13px;
                    font-family: "JetBrains Mono", monospace;
                    display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 16px;'>🔌</span>
            GRID STABILIZER OFFLINE — Connect hardware bridge for high-load simulations
        </div>
        """, unsafe_allow_html=True)


def show_handshake_sidebar():
    """Compact sidebar widget showing Grid Stabilizer status."""
    hs = verify_power_input()

    if hs.mode == "HIGH_LOAD":
        color = "#00ff88"
        icon = "⚡"
        label = "VERIFIED"
    elif hs.mode == "LOW_POWER":
        color = "#ff8c00"
        icon = "⚠"
        label = "LOW-POWER"
    else:
        color = "#6366f1"
        icon = "🔌"
        label = "OFFLINE"

    st.sidebar.markdown(f"""
    <div style='background: rgba(13, 21, 32, 0.9); border: 1px solid {color}33;
                border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;'>
        <div style='font-family: "JetBrains Mono", monospace; font-size: 10px;
                    color: {color}; letter-spacing: 1.5px; font-weight: 600;
                    margin-bottom: 6px;'>
            {icon} GRID STABILIZER │ {label}
        </div>
        <div style='font-family: "JetBrains Mono", monospace; font-size: 18px;
                    color: {color}; font-weight: 700;'>
            {hs.grid_freq_hz:.3f} <span style='font-size: 11px; color: #94a3b8;'>Hz</span>
            &nbsp;│&nbsp;
            {hs.grid_voltage_kv:.2f} <span style='font-size: 11px; color: #94a3b8;'>kV</span>
        </div>
        <div style='font-size: 11px; color: #64748b; margin-top: 4px;'>
            Mode: {hs.mode} │ Age: {hs.freshness_s:.0f}s
        </div>
    </div>
    """, unsafe_allow_html=True)


def require_grid_handshake(page_name: str = "this simulation") -> bool:
    """
    Gate a page behind grid handshake verification.

    Does NOT block access — returns False with a warning if unverified
    so the caller can adjust simulation resolution/defaults.
    """
    show_handshake_banner()

    hs = st.session_state.get("granas_grid_handshake")
    if hs is None:
        hs = verify_power_input()

    if hs.mode == "HIGH_LOAD":
        return True

    if hs.mode == "LOW_POWER":
        st.info(
            f"**{page_name}** is running at reduced resolution. "
            f"Grid signal is degraded ({hs.reason}). "
            f"Start the Grid Stabilizer for full high-load capability."
        )
        return False

    # DORMANT
    st.info(
        f"**{page_name}** is running in demonstration mode. "
        f"Connect the Grid Stabilizer (`python core/prime_hardware_bridge.py`) "
        f"for high-load simulations with verified power-input."
    )
    return False


def get_simulation_defaults() -> dict:
    """
    Return recommended simulation defaults based on handshake state.

    HIGH_LOAD → full resolution
    LOW_POWER → moderate resolution
    DORMANT  → minimal (demo)
    """
    hs = st.session_state.get("granas_grid_handshake")
    if hs is None:
        hs = verify_power_input()

    if hs.mode == "HIGH_LOAD":
        return {
            "n_calls": 200,
            "n_initial": 15,
            "hjb_grid_points": 50,
            "monte_carlo_paths": 10_000,
            "label": "HIGH-LOAD (Grid Verified)",
        }
    elif hs.mode == "LOW_POWER":
        return {
            "n_calls": 80,
            "n_initial": 10,
            "hjb_grid_points": 30,
            "monte_carlo_paths": 3_000,
            "label": "LOW-POWER (Grid Degraded)",
        }
    else:
        return {
            "n_calls": 50,
            "n_initial": 8,
            "hjb_grid_points": 20,
            "monte_carlo_paths": 1_000,
            "label": "DORMANT (Demo Mode)",
        }
