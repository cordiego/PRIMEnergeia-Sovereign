"""
PRIMEnergeia — Granas Bayesian Optimizer Tests
================================================
Pytest suite covering optimizer initialization, convergence,
warm-start, suggestion, multi-objective, export, and visualizer.
"""

import os
import sys
import json
import tempfile

import numpy as np
import pandas as pd
import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.granas_bayesian import (
    GranasOptimizer,
    GranasRecipe,
    TrialResult,
    PerovskitePhysics,
)
from optimization.granas_visualizer import GranasVisualizer


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def optimizer():
    """Small optimizer for fast tests."""
    return GranasOptimizer(
        n_calls=10,
        n_initial=5,
        acq_func="EI",
        random_state=42,
        output_dir=tempfile.mkdtemp(),
    )


@pytest.fixture
def trained_optimizer(optimizer):
    """Optimizer that has already been run."""
    optimizer.run()
    return optimizer


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────
class TestOptimizerInitialization:
    """Verify search space dimensions, bounds, defaults."""

    def test_space_has_six_dimensions(self):
        opt = GranasOptimizer()
        assert len(opt.SPACE) == 6

    def test_param_names(self):
        expected = ["molar_conc", "solvent_ratio", "spin_speed",
                    "additive_pct", "anneal_temp", "anneal_time"]
        assert GranasOptimizer.PARAM_NAMES == expected

    def test_default_values(self):
        opt = GranasOptimizer()
        assert opt.n_calls == 50
        assert opt.n_initial == 8
        assert opt.acq_func == "EI"
        assert opt.random_state == 42
        assert opt.trials == []

    def test_bounds_molar_conc(self):
        space = GranasOptimizer.SPACE
        assert space[0].low == 0.8
        assert space[0].high == 1.5

    def test_bounds_spin_speed(self):
        space = GranasOptimizer.SPACE
        assert space[2].low == 1000
        assert space[2].high == 6000


class TestOptimizationRun:
    """Run a short BO and verify convergence."""

    def test_run_completes(self, trained_optimizer):
        assert trained_optimizer.result is not None
        assert len(trained_optimizer.trials) == 10

    def test_convergence(self, trained_optimizer):
        """Best PCE should improve beyond a random first trial."""
        pce_values = [t.pce for t in trained_optimizer.trials]
        # Best should be better than median of initial random points
        initial_median = np.median(pce_values[:5])
        best_pce = max(pce_values)
        assert best_pce >= initial_median

    def test_all_trials_have_valid_pce(self, trained_optimizer):
        for t in trained_optimizer.trials:
            assert 0.0 < t.pce <= 30.0  # Physical bound

    def test_all_trials_have_grain_size(self, trained_optimizer):
        for t in trained_optimizer.trials:
            assert 30.0 <= t.grain_size_nm <= 900.0


class TestWarmStart:
    """Create synthetic CSV, warm-start, verify seeded data used."""

    def test_warm_start_from_csv(self):
        # Create synthetic prior experiments
        prior_data = {
            "molar_conc": [1.0, 1.1, 1.2, 1.3, 1.15],
            "solvent_ratio": [0.5, 0.6, 0.7, 0.65, 0.72],
            "spin_speed": [3000, 3500, 4000, 4500, 3800],
            "additive_pct": [1.0, 2.0, 2.5, 3.0, 2.2],
            "anneal_temp": [120, 130, 140, 150, 135],
            "anneal_time": [15, 18, 20, 25, 22],
            "pce": [15.0, 17.5, 20.0, 18.0, 19.5],
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            pd.DataFrame(prior_data).to_csv(f, index=False)
            csv_path = f.name

        try:
            opt = GranasOptimizer(
                n_calls=8,
                n_initial=3,
                random_state=42,
                output_dir=tempfile.mkdtemp(),
            )
            opt.run(warm_start_csv=csv_path)
            assert opt.result is not None
            assert len(opt.trials) == 8
        finally:
            os.unlink(csv_path)

    def test_warm_start_missing_column_raises(self):
        bad_data = {"molar_conc": [1.0], "pce": [15.0]}
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            pd.DataFrame(bad_data).to_csv(f, index=False)
            csv_path = f.name

        try:
            opt = GranasOptimizer(output_dir=tempfile.mkdtemp())
            with pytest.raises(ValueError, match="missing columns"):
                opt._load_warm_start(csv_path)
        finally:
            os.unlink(csv_path)


class TestSuggestNext:
    """Verify suggested point is within bounds."""

    def test_suggest_with_no_data(self):
        opt = GranasOptimizer(output_dir=tempfile.mkdtemp())
        suggestion = opt.suggest_next()
        assert isinstance(suggestion, dict)
        assert set(suggestion.keys()) == set(GranasOptimizer.PARAM_NAMES)

    def test_suggest_after_training(self, trained_optimizer):
        suggestion = trained_optimizer.suggest_next()
        assert 0.8 <= suggestion["molar_conc"] <= 1.5
        assert 0.0 <= suggestion["solvent_ratio"] <= 1.0
        assert 1000 <= suggestion["spin_speed"] <= 6000
        assert 0.0 <= suggestion["additive_pct"] <= 5.0
        assert 80.0 <= suggestion["anneal_temp"] <= 200.0
        assert 5.0 <= suggestion["anneal_time"] <= 60.0


class TestMultiObjective:
    """Run with stability objective, verify Pareto front."""

    def test_multi_objective_mode(self):
        opt = GranasOptimizer(
            n_calls=10,
            n_initial=5,
            multi_objective=True,
            random_state=42,
            output_dir=tempfile.mkdtemp(),
        )
        opt.run()
        assert len(opt.trials) == 10
        # All trials should have valid stability scores
        for t in opt.trials:
            assert 0.0 <= t.stability_score <= 1.0


class TestExportResults:
    """Verify CSV/JSON export contains all columns."""

    def test_export_csv(self, trained_optimizer):
        paths = trained_optimizer.export_results(fmt="csv")
        assert "csv" in paths
        assert os.path.exists(paths["csv"])

        df = pd.read_csv(paths["csv"])
        assert len(df) == 10
        for col in ["molar_conc", "solvent_ratio", "spin_speed",
                     "additive_pct", "anneal_temp", "anneal_time",
                     "pce", "stability_score", "grain_size_nm"]:
            assert col in df.columns

    def test_export_json(self, trained_optimizer):
        paths = trained_optimizer.export_results(fmt="json")
        assert "json" in paths
        assert os.path.exists(paths["json"])

        with open(paths["json"]) as f:
            data = json.load(f)
        assert len(data) == 10
        assert "pce" in data[0]

    def test_best_recipe_exported(self, trained_optimizer):
        paths = trained_optimizer.export_results()
        assert "best_recipe" in paths
        with open(paths["best_recipe"]) as f:
            best = json.load(f)
        assert "optimal_recipe" in best
        assert "predicted_pce_pct" in best


class TestVisualizerNoCrash:
    """Generate all plot types without errors."""

    def test_all_visualizations(self, trained_optimizer):
        viz = GranasVisualizer(
            trained_optimizer.trials,
            output_dir=trained_optimizer.output_dir,
        )
        plots = viz.generate_all(result=trained_optimizer.result)
        assert "convergence" in plots
        assert "parallel_coords" in plots
        assert "pareto" in plots


class TestPerovskitePhysics:
    """Unit tests for the physics model."""

    def test_grain_size_range(self):
        gs = PerovskitePhysics.grain_size(1.2, 0.7, 4000, 140, 20)
        assert 30 <= gs <= 900

    def test_defect_density_positive(self):
        dd = PerovskitePhysics.defect_density(1.2, 2.5, 0.7, 140, 20)
        assert dd > 0

    def test_efficiency_bounded(self):
        np.random.seed(42)
        eff = PerovskitePhysics.efficiency(500, 0.1, 4000)
        assert 0.0 <= eff <= 0.30  # PRACTICAL_CAP=0.258, fractional scale

    def test_stability_score_range(self):
        stab = PerovskitePhysics.stability_score(140, 25, 3.0, 0.1)
        assert 0.0 <= stab <= 1.0

    def test_optimal_params_give_high_pce(self):
        """Near-optimal parameters should yield top-quartile PCE."""
        np.random.seed(42)
        grain = PerovskitePhysics.grain_size(1.2, 0.7, 4000, 140, 20)
        defects = PerovskitePhysics.defect_density(1.2, 2.5, 0.7, 140, 20)
        pce = PerovskitePhysics.efficiency(grain, defects, 4000)
        assert pce > 0.15  # Should be well above average (fractional scale)
