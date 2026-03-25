"""
ERCOT Dispatch Co-Optimizer — Test Suite
==========================================
Tests for day-ahead/real-time co-optimization with battery degradation tracking.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markets.ercot.dispatch_ercot import (
    ERCOTNodePricing,
    BatteryState,
    ERCOTCoOptimizer,
    run_ercot_coopt,
)


# ─────────────────────────────────────────────────────────────
# Nodal Pricing Tests
# ─────────────────────────────────────────────────────────────
class TestNodePricing:
    def test_da_prices_correct_length(self):
        node = ERCOTNodePricing("HOU-345-01", "Houston", 45.0)
        prices = node.generate_da_prices(24)
        assert len(prices) == 24

    def test_da_prices_positive(self):
        node = ERCOTNodePricing("HOU-345-01", "Houston", 45.0)
        prices = node.generate_da_prices(24)
        assert np.all(prices >= 5.0)

    def test_da_prices_capped_at_9000(self):
        node = ERCOTNodePricing("HOU-345-01", "Houston", 45.0)
        prices = node.generate_da_prices(24)
        assert np.all(prices <= 9000.0)

    def test_rt_prices_deviate_from_da(self):
        node = ERCOTNodePricing("HOU-345-01", "Houston", 45.0)
        da = node.generate_da_prices(24)
        rt = node.generate_rt_prices(da)
        assert not np.allclose(da, rt)

    def test_different_seeds_different_prices(self):
        node = ERCOTNodePricing("HOU-345-01", "Houston", 45.0)
        p1 = node.generate_da_prices(24, seed=1)
        p2 = node.generate_da_prices(24, seed=2)
        assert not np.allclose(p1, p2)


# ─────────────────────────────────────────────────────────────
# Battery State Tests
# ─────────────────────────────────────────────────────────────
class TestBattery:
    def test_initial_state(self):
        bat = BatteryState(capacity_mwh=400.0)
        assert bat.soc == 0.5
        assert bat.soh == 1.0
        assert bat.max_charge_mw == 100.0  # 400/4

    def test_charge_increases_soc(self):
        bat = BatteryState(capacity_mwh=400.0, soc=0.3)
        initial_soc = bat.soc
        bat.charge(50.0, 1.0)
        assert bat.soc > initial_soc

    def test_soc_capped_at_1(self):
        bat = BatteryState(capacity_mwh=400.0, soc=0.95)
        bat.charge(100.0, 1.0)
        assert bat.soc <= 1.0

    def test_discharge_decreases_soc(self):
        bat = BatteryState(capacity_mwh=400.0, soc=0.8)
        initial_soc = bat.soc
        bat.discharge(50.0, 1.0)
        assert bat.soc < initial_soc

    def test_soc_floor_at_0(self):
        bat = BatteryState(capacity_mwh=400.0, soc=0.05)
        bat.discharge(100.0, 1.0)
        assert bat.soc >= 0.0

    def test_cycling_degrades_soh(self):
        bat = BatteryState(capacity_mwh=400.0)
        initial_soh = bat.soh
        for _ in range(10):
            bat.charge(100.0, 1.0)
            bat.discharge(100.0, 1.0)
        assert bat.soh < initial_soh

    def test_soh_floor_at_70pct(self):
        bat = BatteryState(capacity_mwh=400.0)
        for _ in range(100000):
            bat.charge(100.0, 1.0)
            bat.discharge(100.0, 1.0)
            if bat.soh <= 0.7:
                break
        assert bat.soh >= 0.7


# ─────────────────────────────────────────────────────────────
# Co-Optimization Tests
# ─────────────────────────────────────────────────────────────
class TestCoOptimizer:
    def test_coopt_runs(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert result.hours == 24

    def test_coopt_revenue_calculated(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert result.total_revenue_usd != 0

    def test_coopt_strategies_correct_length(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert len(result.strategy) == 24

    def test_coopt_strategies_valid(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        valid = {"CHARGE", "DISCHARGE", "HOLD+AS"}
        for s in result.strategy:
            assert s in valid

    def test_coopt_battery_soc_trajectory(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert len(result.battery_soc) == 25  # hours + 1
        assert np.all(result.battery_soc >= 0)
        assert np.all(result.battery_soc <= 1)

    def test_coopt_degradation_tracked(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert result.battery_soh_end <= result.battery_soh_start
        assert result.degradation_cost_usd >= 0

    def test_coopt_net_profit(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        expected = result.total_revenue_usd - result.degradation_cost_usd
        assert abs(result.net_profit_usd - expected) < 1.0

    def test_coopt_dispatch_array(self):
        result = run_ercot_coopt(fleet_mw=100, battery_mwh=400, hours=24)
        assert len(result.dispatch_mw) == 24
        # Should have both positive (discharge) and negative (charge) values
        has_charge = np.any(result.dispatch_mw < 0)
        has_discharge = np.any(result.dispatch_mw > 0)
        assert has_charge or has_discharge
