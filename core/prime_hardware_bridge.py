"""
PRIMEnergeia — Grid Stabilizer Hardware Bridge
================================================
Simulates (or bridges to real) grid-level telemetry: frequency,
voltage, status.  Writes to ``grid_state.json`` for inter-process
handshake with the Streamlit dashboard.

Also exposes ``verify_signature()`` for stateless power-input
validation used by the Granas Handshake protocol.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import time
import os
import json
import numpy as np

# ─── Constants ──────────────────────────────────────────────
FREQ_NOMINAL_60 = 60.0
FREQ_NOMINAL_50 = 50.0
FREQ_TOLERANCE_HZ = 0.05
VOLTAGE_TOLERANCE_PCT = 0.05

_GRID_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "grid_state.json",
)


# ─── Signature Verification ────────────────────────────────
def verify_signature(state: dict) -> dict:
    """
    Stateless verification of a grid-state dict.

    Parameters
    ----------
    state : dict
        Must contain keys ``f`` (Hz), ``v`` (kV), ``status``, ``timestamp``.

    Returns
    -------
    dict with keys:
        verified (bool), freq_ok (bool), voltage_ok (bool),
        status_ok (bool), nominal_f (float), nominal_v (float).
    """
    freq = float(state.get("f", 0.0))
    voltage = float(state.get("v", 0.0))
    status = str(state.get("status", "UNKNOWN")).upper()

    # Auto-detect 50/60 Hz
    if abs(freq - FREQ_NOMINAL_60) < 5.0:
        nominal_f = FREQ_NOMINAL_60
    elif abs(freq - FREQ_NOMINAL_50) < 5.0:
        nominal_f = FREQ_NOMINAL_50
    else:
        nominal_f = FREQ_NOMINAL_60

    # Auto-detect nominal voltage
    nominals_kv = [13.8, 34.5, 69.0, 115.0, 138.0, 230.0, 345.0, 500.0]
    nominal_v = min(nominals_kv, key=lambda n: abs(n - voltage))

    freq_ok = abs(freq - nominal_f) <= FREQ_TOLERANCE_HZ
    voltage_ok = (
        abs(voltage - nominal_v) / nominal_v <= VOLTAGE_TOLERANCE_PCT
        if nominal_v > 0
        else False
    )
    status_ok = status == "NOMINAL"

    return {
        "verified": freq_ok and voltage_ok and status_ok,
        "freq_ok": freq_ok,
        "voltage_ok": voltage_ok,
        "status_ok": status_ok,
        "nominal_f": nominal_f,
        "nominal_v": nominal_v,
    }


# ─── Grid Simulator ────────────────────────────────────────
def simular_red(output_path: str = None):
    """Run the stochastic grid-physics loop, emitting telemetry."""
    out = output_path or _GRID_STATE_FILE
    print("[🛰️] NODO VZA-400: GENERANDO FÍSICA DE RED")
    print(f"[📂] Writing to: {out}")

    try:
        while True:
            # Física estocástica de red
            f = 60.0 + np.random.normal(0, 0.01)
            v = 115.0 + np.random.normal(0, 0.2)

            estado = {
                "f": round(f, 3),
                "v": round(v, 2),
                "status": "NOMINAL",
                "timestamp": time.time(),
            }

            # Verify own signature (sanity)
            sig = verify_signature(estado)

            # Write state for dashboard handshake
            with open(out, "w") as f_out:
                json.dump(estado, f_out)

            sig_tag = "✅" if sig["verified"] else "⚠️"
            print(
                f"[📡] LIVE: {f:.3f} Hz | {v:.2f} kV | "
                f"SIG {sig_tag}",
                end="\r",
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[🛑] Nodo OFF.")


if __name__ == "__main__":
    simular_red()
