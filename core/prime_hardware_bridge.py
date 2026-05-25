"""
PRIMEnergeia — Multi-Market Grid Stabilizer Bridge
=====================================================
Simulates (or bridges to real) grid-level telemetry for ALL 17
global markets simultaneously.  Writes a unified ``grid_state.json``
used by the Granas Handshake protocol and the Sovereign dashboard.

Each market emits:
  - Frequency (Hz) around its nominal (50 or 60 Hz)
  - Voltage (kV) around its nominal
  - Status (NOMINAL / ALERT)
  - Master node ID

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

# ─── 17 Global Markets ─────────────────────────────────────
MARKETS = {
    "SEN":       {"flag": "🇲🇽", "f_nom": 60.0, "v_nom": 115.0,  "f_sigma": 0.008, "v_sigma": 0.20, "master": "05-VZA-400",    "full": "Sistema Eléctrico Nacional", "source": "public_cenace_data"},
    "ERCOT":     {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 345.0,  "f_sigma": 0.010, "v_sigma": 0.50, "master": "HOU-345-01",    "full": "Electric Reliability Council of Texas"},
    "MIBEL":     {"flag": "🇪🇸🇵🇹", "f_nom": 50.0, "v_nom": 220.0,  "f_sigma": 0.006, "v_sigma": 0.30, "master": "ES-MAD-400",   "full": "Mercado Ibérico de Electricidad"},
    "PJM":       {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 500.0,  "f_sigma": 0.007, "v_sigma": 0.60, "master": "PJM-WH-500",    "full": "PJM Interconnection"},
    "CAISO":     {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 500.0,  "f_sigma": 0.008, "v_sigma": 0.55, "master": "CA-LA-500",      "full": "California ISO"},
    "NYISO":     {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 345.0,  "f_sigma": 0.007, "v_sigma": 0.45, "master": "NY-NYC-345",     "full": "New York ISO"},
    "SPP":       {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 345.0,  "f_sigma": 0.009, "v_sigma": 0.50, "master": "SPP-OKC-345",    "full": "Southwest Power Pool"},
    "MISO":      {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 345.0,  "f_sigma": 0.008, "v_sigma": 0.48, "master": "MISO-CHI-345",   "full": "Midcontinent ISO"},
    "ISO-NE":    {"flag": "🇺🇸", "f_nom": 60.0, "v_nom": 345.0,  "f_sigma": 0.007, "v_sigma": 0.42, "master": "NE-BOS-345",     "full": "ISO New England"},
    "AESO":      {"flag": "🇨🇦", "f_nom": 60.0, "v_nom": 240.0,  "f_sigma": 0.009, "v_sigma": 0.35, "master": "AB-CGY-240",     "full": "Alberta Electric System Operator"},
    "IESO":      {"flag": "🇨🇦", "f_nom": 60.0, "v_nom": 500.0,  "f_sigma": 0.007, "v_sigma": 0.55, "master": "ON-TOR-500",     "full": "Independent Electricity System Operator"},
    "NEM":       {"flag": "🇦🇺", "f_nom": 50.0, "v_nom": 330.0,  "f_sigma": 0.009, "v_sigma": 0.45, "master": "AU-SYD-330",     "full": "National Electricity Market"},
    "JEPX":      {"flag": "🇯🇵", "f_nom": 50.0, "v_nom": 275.0,  "f_sigma": 0.006, "v_sigma": 0.35, "master": "JP-TKY-500",     "full": "Japan Electric Power Exchange"},
    "NORD POOL": {"flag": "🇳🇴🇸🇪", "f_nom": 50.0, "v_nom": 400.0,  "f_sigma": 0.006, "v_sigma": 0.40, "master": "NO-OSL-400",    "full": "Nordic Power Exchange"},
    "EPEX":      {"flag": "🇩🇪🇫🇷", "f_nom": 50.0, "v_nom": 380.0,  "f_sigma": 0.006, "v_sigma": 0.38, "master": "DE-BER-380",    "full": "European Power Exchange"},
    "EMC":       {"flag": "🇸🇬", "f_nom": 50.0, "v_nom": 230.0,  "f_sigma": 0.006, "v_sigma": 0.28, "master": "SG-TUA-230",     "full": "Energy Market Company"},
    "CCEE":      {"flag": "🇧🇷", "f_nom": 60.0, "v_nom": 500.0,  "f_sigma": 0.008, "v_sigma": 0.55, "master": "BR-SPO-500",     "full": "Câmara de Comercialização de Energia Elétrica"},
}


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
    nominals_kv = [13.8, 34.5, 69.0, 115.0, 138.0, 220.0, 230.0,
                   240.0, 275.0, 330.0, 345.0, 380.0, 400.0, 500.0]
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


# ─── Multi-Market Grid Simulator ───────────────────────────
def simular_red_global(output_path: str = None):
    """Run stochastic grid-physics for ALL 17 markets simultaneously."""
    out = output_path or _GRID_STATE_FILE

    n_markets = len(MARKETS)
    print(f"[🛰️] PRIMEnergeia MULTI-MARKET GRID STABILIZER")
    print(f"[📂] Writing to: {out}")
    print(f"[🌐] Markets: {n_markets}")
    print(f"{'─' * 65}")

    # Print header for all markets
    for iso, cfg in MARKETS.items():
        print(f"  {cfg['flag']} {iso:10s} │ {cfg['f_nom']:.0f} Hz │ {cfg['v_nom']:.0f} kV │ {cfg['master']}")
    print(f"{'─' * 65}")
    print()

    try:
        tick = 0
        while True:
            ts = time.time()
            markets_state = {}
            all_verified = True

            for iso, cfg in MARKETS.items():
                f = cfg["f_nom"] + np.random.normal(0, cfg["f_sigma"])
                v = cfg["v_nom"] + np.random.normal(0, cfg["v_sigma"])

                estado = {
                    "f": round(f, 3),
                    "v": round(v, 2),
                    "status": "NOMINAL",
                    "timestamp": ts,
                    "master_node": cfg["master"],
                    "nominal_f": cfg["f_nom"],
                    "nominal_v": cfg["v_nom"],
                    "market": iso,
                }

                sig = verify_signature(estado)
                estado["verified"] = sig["verified"]
                if not sig["verified"]:
                    all_verified = False

                markets_state[iso] = estado

            # Build unified state file
            # Keep backward-compatible "f", "v", "status" at top level (from SEN master)
            sen = markets_state.get("SEN", list(markets_state.values())[0])
            unified = {
                # Backward-compatible global fields (SEN master)
                "f": sen["f"],
                "v": sen["v"],
                "status": sen["status"],
                "timestamp": ts,
                # Multi-market payload
                "markets": markets_state,
                "n_markets": n_markets,
                "all_verified": all_verified,
            }

            with open(out, "w") as f_out:
                json.dump(unified, f_out, indent=1)

            # Print rotating status (one market per tick for readability)
            display_markets = list(MARKETS.keys())
            idx = tick % n_markets
            iso = display_markets[idx]
            m = markets_state[iso]
            cfg = MARKETS[iso]
            sig_icon = "✅" if m["verified"] else "⚠️"

            print(
                f"[📡] {cfg['flag']} {iso:10s} │ "
                f"{m['f']:.3f} Hz │ {m['v']:.2f} kV │ "
                f"{m['master_node']:14s} │ SIG {sig_icon}   ",
                end="\r",
            )

            # Every 17 ticks (~8.5s), print a full summary line
            if tick % n_markets == 0 and tick > 0:
                verified_count = sum(1 for m in markets_state.values() if m["verified"])
                print(
                    f"\n[🌐] TICK {tick:>5d} │ {verified_count}/{n_markets} VERIFIED │ "
                    f"{'ALL NOMINAL ✅' if all_verified else 'DEGRADED ⚠️'}  "
                )

            tick += 1
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n[🛑] Multi-Market Grid Stabilizer OFF. ({n_markets} markets halted)")


# ─── Single-Market Fallback ────────────────────────────────
def simular_red(output_path: str = None, market: str = "SEN"):
    """Run single-market grid physics (backward compatible)."""
    cfg = MARKETS.get(market, MARKETS["SEN"])
    out = output_path or _GRID_STATE_FILE
    print(f"[🛰️] NODO {cfg['master']}: GENERANDO FÍSICA DE RED ({market})")
    print(f"[📂] Writing to: {out}")

    try:
        while True:
            f = cfg["f_nom"] + np.random.normal(0, cfg["f_sigma"])
            v = cfg["v_nom"] + np.random.normal(0, cfg["v_sigma"])

            estado = {
                "f": round(f, 3),
                "v": round(v, 2),
                "status": "NOMINAL",
                "timestamp": time.time(),
                "master_node": cfg["master"],
                "market": market,
            }

            sig = verify_signature(estado)

            with open(out, "w") as f_out:
                json.dump(estado, f_out)

            sig_tag = "✅" if sig["verified"] else "⚠️"
            print(
                f"[📡] {cfg['flag']} {market} │ {f:.3f} Hz │ {v:.2f} kV │ "
                f"SIG {sig_tag}   ",
                end="\r",
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n[🛑] {market} Grid OFF.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        # Single market mode: python3 core/prime_hardware_bridge.py ERCOT
        simular_red(market=sys.argv[1].upper())
    else:
        # Default: all 17 markets
        simular_red_global()

