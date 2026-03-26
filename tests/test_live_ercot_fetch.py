"""
PRIMEnergeia — Live ERCOT Data Pipeline Test
================================================
End-to-end test: fetch → load → validate → co-optimize.

Uses proxy data if gridstatus is not installed (CI-safe).

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_ercot_real import fetch_ercot_data, generate_realistic_proxy
from data.data_loader import load_ercot_csv, load_dataset, MarketDataset
from markets.ercot.dispatch_ercot import run_ercot_backtest


# ─────────────────────────────────────────────────────────────
# Data Fetch Tests
# ─────────────────────────────────────────────────────────────
class TestERCOTFetch:
    """Test that fetch_ercot_data produces a valid CSV."""

    def test_fetch_returns_csv_path(self):
        path = fetch_ercot_data(days=7, hub="HB_HOUSTON")
        assert os.path.exists(path)
        assert path.endswith(".csv")

    def test_fetch_csv_has_rows(self):
        path = fetch_ercot_data(days=7, hub="HB_HOUSTON")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) > 10, f"CSV only has {len(lines)} lines"

    def test_fetch_different_hubs(self):
        for hub in ["HB_HOUSTON", "HB_NORTH", "HB_WEST"]:
            path = fetch_ercot_data(days=7, hub=hub)
            assert os.path.exists(path)

    def test_proxy_generates_correct_length(self):
        df = generate_realistic_proxy("2025-01-01", "2025-01-07", "HB_HOUSTON")
        # 7 days = ~168 hours (+ buffer for range)
        assert len(df) >= 168

    def test_proxy_prices_reasonable(self):
        df = generate_realistic_proxy("2025-06-01", "2025-06-07", "HB_HOUSTON")
        assert df["dam_lmp"].mean() > 10, "DA mean too low"
        assert df["dam_lmp"].mean() < 500, "DA mean too high"
        assert df["dam_lmp"].min() >= -35, "DA floor violated"
        assert df["dam_lmp"].max() <= 5000, "DA cap violated"


# ─────────────────────────────────────────────────────────────
# Data Loader Integration Tests
# ─────────────────────────────────────────────────────────────
class TestDataLoaderIntegration:
    """Test that fetched CSV loads correctly through data_loader."""

    @pytest.fixture
    def ercot_csv_path(self):
        return fetch_ercot_data(days=7, hub="HB_HOUSTON")

    def test_load_returns_market_dataset(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path, market="ercot")
        assert isinstance(ds, MarketDataset)

    def test_dataset_has_correct_market(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path, market="ercot")
        assert ds.market == "ercot"

    def test_dataset_has_prices(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path, market="ercot")
        assert ds.hours > 0
        assert len(ds.da_prices) == ds.hours
        assert len(ds.rt_prices) == ds.hours

    def test_prices_are_finite(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path, market="ercot")
        assert np.all(np.isfinite(ds.da_prices)), "DA prices have NaN/Inf"
        assert np.all(np.isfinite(ds.rt_prices)), "RT prices have NaN/Inf"

    def test_quality_report_exists(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path, market="ercot")
        assert ds.quality is not None
        assert ds.quality.valid_rows > 0
        assert ds.quality.completeness_pct > 0

    def test_auto_detect_works(self, ercot_csv_path):
        ds = load_dataset(filepath=ercot_csv_path)
        assert ds.market in ("ercot", "unknown")
        assert ds.hours > 0


# ─────────────────────────────────────────────────────────────
# Full Pipeline Tests (Fetch → Load → Optimize)
# ─────────────────────────────────────────────────────────────
class TestFullPipeline:
    """Test the complete pipeline: fetch → load → co-optimize."""

    @pytest.fixture
    def dataset(self):
        path = fetch_ercot_data(days=7, hub="HB_HOUSTON")
        return load_dataset(filepath=path, market="ercot")

    def test_backtest_with_real_data(self, dataset):
        hours = min(24, dataset.hours)
        result = run_ercot_backtest(
            da_prices=dataset.da_prices[:hours],
            rt_prices=dataset.rt_prices[:hours],
            fleet_mw=100,
            battery_mwh=400,
        )
        assert result.hours == hours
        assert result.total_revenue_usd != 0
        assert len(result.strategy) == hours
        assert len(result.dispatch_mw) == hours

    def test_backtest_revenue_positive(self, dataset):
        """Over a full week, the optimizer should generate positive revenue."""
        hours = min(168, dataset.hours)
        result = run_ercot_backtest(
            da_prices=dataset.da_prices[:hours],
            rt_prices=dataset.rt_prices[:hours],
            fleet_mw=100,
            battery_mwh=400,
        )
        # Net profit should be positive for a well-functioning optimizer
        assert result.net_profit_usd > 0, (
            f"Net profit negative: ${result.net_profit_usd:.2f}"
        )

    def test_backtest_soh_tracks(self, dataset):
        hours = min(168, dataset.hours)
        result = run_ercot_backtest(
            da_prices=dataset.da_prices[:hours],
            rt_prices=dataset.rt_prices[:hours],
            fleet_mw=100,
            battery_mwh=400,
        )
        assert result.battery_soh_end <= result.battery_soh_start
        assert result.battery_soh_end > 0.7

    def test_backtest_strategies_valid(self, dataset):
        hours = min(24, dataset.hours)
        result = run_ercot_backtest(
            da_prices=dataset.da_prices[:hours],
            rt_prices=dataset.rt_prices[:hours],
            fleet_mw=100,
            battery_mwh=400,
        )
        valid = {"CHARGE", "DISCHARGE", "HOLD+AS"}
        for s in result.strategy:
            assert s in valid, f"Invalid strategy: {s}"

    def test_different_fleet_sizes(self, dataset):
        """Larger fleets should generate proportionally more revenue."""
        hours = min(48, dataset.hours)
        da, rt = dataset.da_prices[:hours], dataset.rt_prices[:hours]

        r100 = run_ercot_backtest(da, rt, fleet_mw=100, battery_mwh=400)
        r500 = run_ercot_backtest(da, rt, fleet_mw=500, battery_mwh=2000)

        # 5x fleet should yield roughly 5x revenue (within 2x tolerance)
        ratio = abs(r500.total_revenue_usd) / max(1, abs(r100.total_revenue_usd))
        assert 2.0 < ratio < 10.0, f"Revenue ratio {ratio:.1f}x not in expected range"
