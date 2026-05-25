#!/usr/bin/env python3
"""
SIBO — Sol-Ink Bayesian Optimizer
==================================
CLI-driven Bayesian Optimization tool for perovskite solar cell
ink-recipe fabrication. Designed for Bash-based lab hardware
controller integration with stateless --init / --ask / --tell
interface.

Specification: SIBO Technical Spec v1.0 (Granas et al.)
Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.

Usage:
    python sibo_cli.py --init                           # Initialize fresh GP model
    python sibo_cli.py --ask                            # Get next suggested recipe
    python sibo_cli.py --tell 1.2 0.7 2.5 4000 21.3    # Report result (conc ratio additive speed PCE)
    python sibo_cli.py --status                         # Show optimization progress
    python sibo_cli.py --best                           # Print best recipe found
    python sibo_cli.py --export [csv|json]              # Export experiment log

Architecture:
    Optimization Engine:  scikit-optimize (Gaussian Process, Matern 5/2 kernel)
    Persistence Layer:    Joblib (.pkl) — serialized GP state between iterations
    Orchestration:        Bash (POSIX) — manages Ask/Tell loop with lab hardware
    Model Type:           GP with Matern 5/2 kernel + Expected Improvement (EI)

Performance Constraints:
    Inference Latency:    < 2 seconds per --ask
    Memory Footprint:     < 500 MB RAM (edge-device compatible)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import joblib
except ImportError:
    # Fallback to pickle if joblib unavailable
    import pickle as joblib
    joblib.dump = lambda obj, path: open(path, 'wb').write(__import__('pickle').dumps(obj))
    joblib.load = lambda path: __import__('pickle').loads(open(path, 'rb').read())

try:
    from skopt import Optimizer
    from skopt.space import Real, Integer
except ImportError:
    print("CRITICAL: scikit-optimize not installed.", file=sys.stderr)
    print("Install with: pip install scikit-optimize", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Constants & Configuration
# ─────────────────────────────────────────────────────────────
VERSION = "1.0.0"
STATE_DIR = os.environ.get("SIBO_STATE_DIR", os.path.expanduser("~/.sibo"))
STATE_FILE = os.path.join(STATE_DIR, "sibo_gp_state.pkl")
LOG_FILE = os.path.join(STATE_DIR, "sibo_experiment_log.csv")
META_FILE = os.path.join(STATE_DIR, "sibo_meta.json")

# 4D Search Space (per SIBO Spec §3.1)
SEARCH_SPACE = [
    Real(0.8, 1.5, name="molar_conc", prior="uniform"),         # Molar Concentration (M)
    Real(0.0, 1.0, name="solvent_ratio", prior="uniform"),      # DMF:DMSO ratio (α)
    Real(0.0, 5.0, name="additive_loading", prior="uniform"),   # Additive vol% (γ)
    Integer(1000, 6000, name="spin_speed"),                      # Spin speed RPM (ω)
]

PARAM_NAMES = [s.name for s in SEARCH_SPACE]

# Convergence: if no improvement in N iterations, switch to random exploration
MAX_STAGNATION = 10

# Exit codes
EXIT_OK = 0
EXIT_CRITICAL = 1
EXIT_NO_DATA = 2


# ─────────────────────────────────────────────────────────────
# State Management
# ─────────────────────────────────────────────────────────────
class SIBOState:
    """Serializable state container for the SIBO optimizer."""

    def __init__(self):
        self.optimizer = Optimizer(
            dimensions=SEARCH_SPACE,
            base_estimator="GP",
            acq_func="EI",
            acq_func_kwargs={"xi": 0.01},
            n_initial_points=5,
            random_state=42,
            # Matern 5/2 kernel via base_estimator_kwargs
        )
        self.X_observed = []      # List of observed parameter vectors
        self.Y_observed = []      # List of observed PCE values (negated for minimization)
        self.best_pce = -np.inf
        self.best_recipe = None
        self.n_stagnant = 0       # Iterations without improvement
        self.created_at = datetime.now().isoformat()
        self.iteration = 0


def _ensure_state_dir():
    """Ensure the state directory exists."""
    os.makedirs(STATE_DIR, exist_ok=True)


def _save_state(state: SIBOState):
    """Serialize the optimizer state to disk."""
    _ensure_state_dir()
    joblib.dump(state, STATE_FILE)


def _load_state() -> SIBOState:
    """Load the optimizer state from disk."""
    if not os.path.exists(STATE_FILE):
        print("CRITICAL: No SIBO state found. Run --init first.", file=sys.stderr)
        sys.exit(EXIT_CRITICAL)

    try:
        state = joblib.load(STATE_FILE)
        if not isinstance(state, SIBOState):
            raise ValueError("Corrupted state object")
        return state
    except Exception as e:
        print(f"CRITICAL: State file corrupted: {e}", file=sys.stderr)
        print("Run --init to reinitialize.", file=sys.stderr)
        sys.exit(EXIT_CRITICAL)


def _append_log(params: list, pce: float, iteration: int):
    """Append an observation to the CSV experiment log."""
    _ensure_state_dir()
    header_needed = not os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a") as f:
        if header_needed:
            f.write("iteration,timestamp,molar_conc,solvent_ratio,additive_loading,spin_speed,pce\n")
        ts = datetime.now().isoformat()
        conc, ratio, additive, speed = params
        f.write(f"{iteration},{ts},{conc:.4f},{ratio:.4f},{additive:.4f},{speed},{pce:.4f}\n")


def _update_meta(state: SIBOState):
    """Update metadata JSON."""
    _ensure_state_dir()
    meta = {
        "version": VERSION,
        "created_at": state.created_at,
        "last_updated": datetime.now().isoformat(),
        "iteration": state.iteration,
        "best_pce": round(state.best_pce, 4) if state.best_pce > -np.inf else None,
        "best_recipe": {
            PARAM_NAMES[i]: round(v, 4) if isinstance(v, float) else v
            for i, v in enumerate(state.best_recipe)
        } if state.best_recipe else None,
        "n_observations": len(state.Y_observed),
        "state_file": STATE_FILE,
        "log_file": LOG_FILE,
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


# ─────────────────────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────────────────────
def cmd_init():
    """
    --init: Purge existing state and initialize a fresh Matern 5/2 GP.
    """
    _ensure_state_dir()

    # Purge existing state files
    for f in [STATE_FILE, LOG_FILE, META_FILE]:
        if os.path.exists(f):
            os.remove(f)

    state = SIBOState()
    _save_state(state)
    _update_meta(state)

    print(f"SIBO v{VERSION} — Sol-Ink Bayesian Optimizer")
    print(f"State initialized: {STATE_FILE}")
    print(f"Kernel: Matern 5/2 | Acquisition: EI")
    print(f"Search Space: {len(SEARCH_SPACE)}D")
    for s in SEARCH_SPACE:
        print(f"  {s.name}: [{s.low}, {s.high}]")
    print(f"Ready. Use --ask to get the first recipe suggestion.")
    return EXIT_OK


def cmd_ask():
    """
    --ask: Output the next suggested recipe coordinates to STDOUT.
    Returns a single line: molar_conc solvent_ratio additive_loading spin_speed
    """
    t_start = time.time()
    state = _load_state()

    # Check stagnation → switch to random exploration
    if state.n_stagnant >= MAX_STAGNATION:
        print(f"# WARNING: No improvement in {MAX_STAGNATION} iterations. "
              f"Switching to random exploration.", file=sys.stderr)
        # Force random point
        point = [
            np.random.uniform(0.8, 1.5),
            np.random.uniform(0.0, 1.0),
            np.random.uniform(0.0, 5.0),
            np.random.randint(1000, 6001),
        ]
    else:
        point = state.optimizer.ask()

    # Ensure spin_speed is integer
    point[3] = int(round(point[3]))

    elapsed = time.time() - t_start

    # Output format: space-separated values for Bash parsing
    # Header comment for human readability (Bash can grep -v '^#')
    print(f"# SIBO --ask | Iteration {state.iteration + 1} | {elapsed:.3f}s")
    print(f"# molar_conc  solvent_ratio  additive_loading  spin_speed")
    print(f"{point[0]:.4f} {point[1]:.4f} {point[2]:.4f} {point[3]}")

    if elapsed > 2.0:
        print(f"# WARNING: Inference took {elapsed:.1f}s (target < 2s)", file=sys.stderr)

    return EXIT_OK


def cmd_tell(params: list, pce: float):
    """
    --tell: Update the surrogate model with a new lab observation.
    params: [molar_conc, solvent_ratio, additive_loading, spin_speed]
    pce: measured Power Conversion Efficiency (%)
    """
    state = _load_state()

    # Validate bounds
    bounds = [(0.8, 1.5), (0.0, 1.0), (0.0, 5.0), (1000, 6000)]
    for i, (val, (lo, hi)) in enumerate(zip(params, bounds)):
        if val < lo or val > hi:
            print(f"WARNING: {PARAM_NAMES[i]}={val} outside bounds [{lo}, {hi}]. "
                  f"Clamping.", file=sys.stderr)
            params[i] = max(lo, min(hi, val))

    # Ensure spin_speed is integer
    params[3] = int(round(params[3]))

    # Tell the optimizer (minimize negative PCE)
    state.optimizer.tell(params, -pce)

    # Track observations
    state.X_observed.append(params[:])
    state.Y_observed.append(pce)
    state.iteration += 1

    # Check for improvement
    if pce > state.best_pce:
        improvement = pce - state.best_pce if state.best_pce > -np.inf else pce
        state.best_pce = pce
        state.best_recipe = params[:]
        state.n_stagnant = 0
        print(f"# NEW BEST: PCE = {pce:.4f}% (+{improvement:.4f}%)")
    else:
        state.n_stagnant += 1
        print(f"# Recorded: PCE = {pce:.4f}% | Best: {state.best_pce:.4f}% "
              f"| Stagnant: {state.n_stagnant}/{MAX_STAGNATION}")

    # Persist
    _save_state(state)
    _append_log(params, pce, state.iteration)
    _update_meta(state)

    # Output confirmation for Bash parsing
    print(f"OK {state.iteration} {pce:.4f}")

    return EXIT_OK


def cmd_status():
    """
    --status: Show current optimization progress.
    """
    state = _load_state()

    print(f"SIBO v{VERSION} — Status Report")
    print(f"{'─' * 45}")
    print(f"  Iterations:      {state.iteration}")
    print(f"  Observations:    {len(state.Y_observed)}")

    if state.best_recipe:
        print(f"  Best PCE:        {state.best_pce:.4f}%")
        print(f"  Best Recipe:")
        for name, val in zip(PARAM_NAMES, state.best_recipe):
            print(f"    {name:>20s}: {val}")
    else:
        print(f"  Best PCE:        (no observations yet)")

    print(f"  Stagnation:      {state.n_stagnant}/{MAX_STAGNATION}")
    print(f"  State File:      {STATE_FILE}")
    print(f"  Log File:        {LOG_FILE}")

    if state.Y_observed:
        print(f"  PCE Range:       [{min(state.Y_observed):.4f}%, {max(state.Y_observed):.4f}%]")
        print(f"  PCE Mean:        {np.mean(state.Y_observed):.4f}%")
        print(f"  PCE Std:         {np.std(state.Y_observed):.4f}%")

    return EXIT_OK


def cmd_best():
    """
    --best: Print the best recipe found so far as machine-readable output.
    """
    state = _load_state()

    if not state.best_recipe:
        print("# No observations recorded yet. Run --tell with lab results.", file=sys.stderr)
        return EXIT_NO_DATA

    # Machine-readable output
    print(f"# SIBO --best | Iteration {state.iteration}")
    print(f"# molar_conc  solvent_ratio  additive_loading  spin_speed  pce")
    r = state.best_recipe
    print(f"{r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]} {state.best_pce:.4f}")

    return EXIT_OK


def cmd_export(fmt: str = "csv"):
    """
    --export: Export experiment log in CSV or JSON format.
    """
    state = _load_state()

    if not state.Y_observed:
        print("# No observations to export.", file=sys.stderr)
        return EXIT_NO_DATA

    if fmt == "json":
        records = []
        for i, (x, y) in enumerate(zip(state.X_observed, state.Y_observed)):
            records.append({
                "iteration": i + 1,
                "molar_conc": round(x[0], 4),
                "solvent_ratio": round(x[1], 4),
                "additive_loading": round(x[2], 4),
                "spin_speed": x[3],
                "pce": round(y, 4),
            })
        output = json.dumps(records, indent=2)
        out_path = os.path.join(STATE_DIR, "sibo_export.json")
        with open(out_path, "w") as f:
            f.write(output)
        print(output)
        print(f"\n# Exported to {out_path}", file=sys.stderr)
    else:
        # CSV to stdout
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                print(f.read(), end="")
        else:
            print("# No log file found.", file=sys.stderr)
            return EXIT_NO_DATA

    return EXIT_OK


# ─────────────────────────────────────────────────────────────
# Bash Integration Examples (printed with --help)
# ─────────────────────────────────────────────────────────────
BASH_EXAMPLE = """
# ──── Bash Integration: Ask/Tell Loop ────
# Initialize
python sibo_cli.py --init

# Ask → Lab → Tell loop
for i in $(seq 1 30); do
    # Ask the optimizer for the next recipe
    RECIPE=$(python sibo_cli.py --ask | grep -v '^#')
    CONC=$(echo $RECIPE | awk '{print $1}')
    RATIO=$(echo $RECIPE | awk '{print $2}')
    ADDITIVE=$(echo $RECIPE | awk '{print $3}')
    SPEED=$(echo $RECIPE | awk '{print $4}')

    echo "Experiment $i: conc=$CONC ratio=$RATIO additive=$ADDITIVE speed=$SPEED"

    # --- Run your lab experiment here ---
    # PCE=$(./run_experiment.sh $CONC $RATIO $ADDITIVE $SPEED)
    PCE="18.5"  # placeholder

    # Tell the optimizer the result
    python sibo_cli.py --tell $CONC $RATIO $ADDITIVE $SPEED $PCE
done

# Get the best recipe
python sibo_cli.py --best
python sibo_cli.py --status
"""


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="sibo",
        description="SIBO — Sol-Ink Bayesian Optimizer for Perovskite Solar Cells",
        epilog=BASH_EXAMPLE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true",
                       help="Initialize fresh GP model (purges existing state)")
    group.add_argument("--ask", action="store_true",
                       help="Get next suggested recipe (outputs to STDOUT)")
    group.add_argument("--tell", nargs=5, type=float, metavar=("CONC", "RATIO", "ADDITIVE", "SPEED", "PCE"),
                       help="Report lab result: molar_conc solvent_ratio additive spin_speed PCE")
    group.add_argument("--status", action="store_true",
                       help="Show optimization progress")
    group.add_argument("--best", action="store_true",
                       help="Print best recipe found")
    group.add_argument("--export", nargs="?", const="csv", choices=["csv", "json"],
                       help="Export experiment log (default: csv)")
    group.add_argument("--version", action="store_true",
                       help="Show version")

    args = parser.parse_args()

    if args.version:
        print(f"SIBO v{VERSION} — Sol-Ink Bayesian Optimizer")
        print(f"PRIMEnergeia S.A.S. | Granas™ Division")
        return EXIT_OK

    if args.init:
        return cmd_init()
    elif args.ask:
        return cmd_ask()
    elif args.tell:
        params = args.tell[:4]
        pce = args.tell[4]
        return cmd_tell(params, pce)
    elif args.status:
        return cmd_status()
    elif args.best:
        return cmd_best()
    elif args.export is not None:
        return cmd_export(args.export)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
