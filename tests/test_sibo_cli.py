"""
SIBO CLI — Test Suite
======================
Pytest tests for the Sol-Ink Bayesian Optimizer CLI interface.
Tests Bash-to-Python data handoff, state persistence, convergence,
and error handling per SIBO Technical Spec §4.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import sys
import json
import subprocess
import tempfile

import numpy as np
import pytest

# Ensure project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.sibo_cli import (
    SIBOState,
    SEARCH_SPACE,
    PARAM_NAMES,
    STATE_DIR,
    cmd_init,
    cmd_ask,
    cmd_tell,
    cmd_best,
    cmd_status,
    cmd_export,
    _save_state,
    _load_state,
    _ensure_state_dir,
)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def use_temp_state_dir(monkeypatch, tmp_path):
    """Redirect all SIBO state to a temp directory."""
    import optimization.sibo_cli as sibo_mod
    state_dir = str(tmp_path / ".sibo")
    monkeypatch.setattr(sibo_mod, "STATE_DIR", state_dir)
    monkeypatch.setattr(sibo_mod, "STATE_FILE", os.path.join(state_dir, "sibo_gp_state.pkl"))
    monkeypatch.setattr(sibo_mod, "LOG_FILE", os.path.join(state_dir, "sibo_experiment_log.csv"))
    monkeypatch.setattr(sibo_mod, "META_FILE", os.path.join(state_dir, "sibo_meta.json"))
    return state_dir


@pytest.fixture
def initialized_state(use_temp_state_dir):
    """A freshly initialized SIBO state."""
    cmd_init()
    return use_temp_state_dir


# ─────────────────────────────────────────────────────────────
# Initialization Tests
# ─────────────────────────────────────────────────────────────
class TestInit:
    """§4.1: --init purges existing state and initializes Matern 5/2 kernel."""

    def test_init_creates_state_file(self, use_temp_state_dir, capsys):
        import optimization.sibo_cli as sibo_mod
        cmd_init()
        assert os.path.exists(sibo_mod.STATE_FILE)

    def test_init_creates_meta_file(self, use_temp_state_dir):
        import optimization.sibo_cli as sibo_mod
        cmd_init()
        assert os.path.exists(sibo_mod.META_FILE)
        with open(sibo_mod.META_FILE) as f:
            meta = json.load(f)
        assert meta["version"] == "1.0.0"
        assert meta["iteration"] == 0

    def test_init_purges_existing(self, initialized_state):
        """Running --init again should reset the state."""
        import optimization.sibo_cli as sibo_mod
        # Tell some data first
        cmd_tell([1.0, 0.5, 2.0, 3000], 15.0)
        state = _load_state()
        assert state.iteration == 1

        # Re-init should purge
        cmd_init()
        state = _load_state()
        assert state.iteration == 0
        assert len(state.Y_observed) == 0


# ─────────────────────────────────────────────────────────────
# Ask Tests
# ─────────────────────────────────────────────────────────────
class TestAsk:
    """§4.1: --ask outputs next recipe coordinates to STDOUT."""

    def test_ask_returns_ok(self, initialized_state, capsys):
        result = cmd_ask()
        assert result == 0

    def test_ask_output_parseable(self, initialized_state, capsys):
        cmd_ask()
        captured = capsys.readouterr()
        # Filter out comment lines
        data_lines = [l for l in captured.out.strip().split("\n") if not l.startswith("#")]
        assert len(data_lines) == 1
        values = data_lines[0].split()
        assert len(values) == 4  # 4D: conc ratio additive speed

    def test_ask_values_in_bounds(self, initialized_state, capsys):
        cmd_ask()
        captured = capsys.readouterr()
        data_lines = [l for l in captured.out.strip().split("\n") if not l.startswith("#")]
        values = [float(v) for v in data_lines[0].split()]

        assert 0.8 <= values[0] <= 1.5   # molar_conc
        assert 0.0 <= values[1] <= 1.0   # solvent_ratio
        assert 0.0 <= values[2] <= 5.0   # additive_loading
        assert 1000 <= values[3] <= 6000  # spin_speed

    def test_ask_spin_speed_is_integer(self, initialized_state, capsys):
        cmd_ask()
        captured = capsys.readouterr()
        data_lines = [l for l in captured.out.strip().split("\n") if not l.startswith("#")]
        speed = float(data_lines[0].split()[3])
        assert speed == int(speed)


# ─────────────────────────────────────────────────────────────
# Tell Tests
# ─────────────────────────────────────────────────────────────
class TestTell:
    """§4.1: --tell updates surrogate model with new observation."""

    def test_tell_updates_state(self, initialized_state):
        cmd_tell([1.2, 0.7, 2.5, 4000], 21.3)
        state = _load_state()
        assert state.iteration == 1
        assert len(state.Y_observed) == 1
        assert state.Y_observed[0] == 21.3

    def test_tell_tracks_best(self, initialized_state):
        cmd_tell([1.0, 0.5, 1.0, 3000], 15.0)
        cmd_tell([1.2, 0.7, 2.5, 4000], 21.3)
        state = _load_state()
        assert state.best_pce == 21.3
        assert state.best_recipe[0] == 1.2

    def test_tell_clamps_out_of_bounds(self, initialized_state, capsys):
        # Value outside bounds should be clamped (with warning)
        cmd_tell([2.0, 0.5, 2.0, 3000], 10.0)  # molar_conc=2.0 > 1.5
        state = _load_state()
        assert state.X_observed[0][0] == 1.5  # Clamped to upper bound

    def test_tell_appends_log(self, initialized_state):
        import optimization.sibo_cli as sibo_mod
        cmd_tell([1.0, 0.5, 2.0, 3000], 15.0)
        assert os.path.exists(sibo_mod.LOG_FILE)
        with open(sibo_mod.LOG_FILE) as f:
            lines = f.readlines()
        assert len(lines) == 2  # header + 1 observation


# ─────────────────────────────────────────────────────────────
# Stagnation & Error Handling Tests
# ─────────────────────────────────────────────────────────────
class TestStagnation:
    """§4.2: Convergence failure triggers random exploration."""

    def test_stagnation_counter_increments(self, initialized_state):
        # First tell sets the best
        cmd_tell([1.2, 0.7, 2.5, 4000], 20.0)
        # Subsequent worse results increment stagnation
        cmd_tell([1.0, 0.5, 1.0, 3000], 15.0)
        cmd_tell([0.9, 0.3, 0.5, 2000], 12.0)
        state = _load_state()
        assert state.n_stagnant == 2

    def test_stagnation_resets_on_improvement(self, initialized_state):
        cmd_tell([1.0, 0.5, 1.0, 3000], 15.0)
        cmd_tell([0.9, 0.3, 0.5, 2000], 12.0)  # stagnant
        cmd_tell([1.2, 0.7, 2.5, 4000], 21.0)  # improvement!
        state = _load_state()
        assert state.n_stagnant == 0


class TestStateCorruption:
    """§4.2: Corrupted .pkl triggers CRITICAL exit code 1."""

    def test_corrupted_state_exits_critical(self, initialized_state):
        import optimization.sibo_cli as sibo_mod
        # Write garbage to state file
        with open(sibo_mod.STATE_FILE, "w") as f:
            f.write("corrupted garbage data")

        with pytest.raises(SystemExit) as exc:
            _load_state()
        assert exc.value.code == 1

    def test_missing_state_exits_critical(self, use_temp_state_dir):
        with pytest.raises(SystemExit) as exc:
            _load_state()
        assert exc.value.code == 1


# ─────────────────────────────────────────────────────────────
# Best & Status Tests
# ─────────────────────────────────────────────────────────────
class TestBestAndStatus:
    """--best and --status output tests."""

    def test_best_no_data(self, initialized_state):
        result = cmd_best()
        assert result == 2  # EXIT_NO_DATA

    def test_best_with_data(self, initialized_state, capsys):
        cmd_tell([1.2, 0.7, 2.5, 4000], 21.3)
        result = cmd_best()
        assert result == 0
        captured = capsys.readouterr()
        assert "21.3" in captured.out

    def test_status_shows_progress(self, initialized_state, capsys):
        cmd_tell([1.0, 0.5, 2.0, 3000], 15.0)
        cmd_tell([1.2, 0.7, 2.5, 4000], 21.3)
        result = cmd_status()
        assert result == 0
        captured = capsys.readouterr()
        assert "21.3" in captured.out
        assert "2" in captured.out  # 2 observations


# ─────────────────────────────────────────────────────────────
# Export Tests
# ─────────────────────────────────────────────────────────────
class TestExport:
    """--export CSV and JSON tests."""

    def test_export_csv(self, initialized_state, capsys):
        cmd_tell([1.0, 0.5, 2.0, 3000], 15.0)
        result = cmd_export("csv")
        assert result == 0
        captured = capsys.readouterr()
        assert "molar_conc" in captured.out

    def test_export_json(self, initialized_state, capsys):
        cmd_tell([1.0, 0.5, 2.0, 3000], 15.0)
        result = cmd_export("json")
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out.split("\n#")[0])  # Strip trailing comment
        assert len(data) == 1
        assert data[0]["pce"] == 15.0

    def test_export_no_data(self, initialized_state):
        result = cmd_export("csv")
        assert result == 2


# ─────────────────────────────────────────────────────────────
# Integration: Ask→Tell Cycle
# ─────────────────────────────────────────────────────────────
class TestAskTellCycle:
    """Full Ask→Tell integration loop."""

    def test_five_iteration_cycle(self, initialized_state, capsys):
        """Run 5 ask→tell iterations and verify convergence tracking."""
        for i in range(5):
            cmd_ask()
            captured = capsys.readouterr()
            data_lines = [l for l in captured.out.strip().split("\n") if not l.startswith("#")]
            values = [float(v) for v in data_lines[0].split()]

            # Simulate a PCE measurement
            pce = 10.0 + i * 2.0 + np.random.normal(0, 0.5)
            cmd_tell(values, pce)

        state = _load_state()
        assert state.iteration == 5
        assert len(state.Y_observed) == 5
        assert state.best_pce > 0


# ─────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────
class TestPerformance:
    """§5: Inference latency < 2 seconds."""

    def test_ask_latency(self, initialized_state):
        import time
        # Feed some data first
        for i in range(5):
            params = [1.0 + 0.1*i, 0.5, 2.0, 3000+i*200]
            cmd_tell(params, 10.0 + 2.0*i)

        start = time.time()
        cmd_ask()
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Inference took {elapsed:.2f}s (target < 2s)"
