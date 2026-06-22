#!/usr/bin/env python3
"""
Unit tests for eureka_markov.py — Markov Day Chain Module.
"""

import sys
import os
import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.eureka_markov import MarkovDayChain, GREEN, RED, STATE_LABELS


# ── FIXTURES ─────────────────────────────────────────────────

@pytest.fixture
def trending_green_returns():
    """Returns that strongly trend green (80% green days)."""
    np.random.seed(42)
    n = 200
    # Bias towards positive returns
    returns = np.random.normal(0.005, 0.01, n)
    # Force 80% green
    for i in range(n):
        if np.random.random() < 0.80:
            returns[i] = abs(returns[i])
        else:
            returns[i] = -abs(returns[i])
    return pd.Series(returns, index=pd.date_range("2020-01-01", periods=n, freq="B"))


@pytest.fixture
def choppy_returns():
    """Returns that alternate green/red (choppy market)."""
    n = 200
    returns = []
    for i in range(n):
        if i % 2 == 0:
            returns.append(0.01)   # green
        else:
            returns.append(-0.01)  # red
    # Add slight noise
    np.random.seed(99)
    noise = np.random.normal(0, 0.001, n)
    returns = np.array(returns) + noise
    return pd.Series(returns, index=pd.date_range("2020-01-01", periods=n, freq="B"))


@pytest.fixture
def balanced_returns():
    """Returns with roughly 50/50 green/red split."""
    np.random.seed(7)
    returns = np.random.normal(0.0, 0.015, 300)
    return pd.Series(returns, index=pd.date_range("2019-01-01", periods=300, freq="B"))


# ── TRANSITION MATRIX TESTS ─────────────────────────────────

class TestFit:

    def test_transition_matrix_rows_sum_to_one(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        for row in range(2):
            assert abs(chain.transition_matrix[row].sum() - 1.0) < 1e-10

    def test_fit_marks_fitted(self, balanced_returns):
        chain = MarkovDayChain()
        assert not chain._fitted
        chain.fit(balanced_returns)
        assert chain._fitted

    def test_fit_with_insufficient_data(self):
        short = pd.Series([0.01, -0.01, 0.02], index=pd.date_range("2020-01-01", periods=3, freq="B"))
        chain = MarkovDayChain().fit(short, min_periods=60)
        # Should still be fitted (with uniform priors)
        assert chain._fitted
        assert len(chain.states) == 0  # no states stored

    def test_states_correctly_assigned(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        # Verify green = 0, red = 1
        for i, ret in enumerate(balanced_returns.dropna().values):
            expected = GREEN if ret >= 0 else RED
            assert chain.states[i] == expected, f"Day {i}: ret={ret}, expected={STATE_LABELS[expected]}"


# ── REGIME DETECTION TESTS ───────────────────────────────────

class TestRegime:

    def test_choppy_detected(self, choppy_returns):
        chain = MarkovDayChain().fit(choppy_returns)
        assert chain.get_regime(window=20) == "CHOPPY"

    def test_trending_detected(self, trending_green_returns):
        chain = MarkovDayChain().fit(trending_green_returns)
        regime = chain.get_regime(window=20)
        assert regime == "TRENDING", f"Expected TRENDING, got {regime}"

    def test_neutral_for_empty(self):
        chain = MarkovDayChain()
        assert chain.get_regime() == "NEUTRAL"


# ── PREDICTION TESTS ─────────────────────────────────────────

class TestPrediction:

    def test_predict_probabilities_sum_to_one(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        pred = chain.predict_next_day()
        assert abs(pred["p_green"] + pred["p_red"] - 1.0) < 1e-10

    def test_predict_trending_green_favors_green(self, trending_green_returns):
        chain = MarkovDayChain().fit(trending_green_returns)
        pred = chain.predict_next_day()
        # After a strong green trend, P(green) should be elevated
        assert pred["p_green"] > 0.5

    def test_predict_returns_current_state(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        pred = chain.predict_next_day()
        assert pred["current_state"] in ("GREEN", "RED")

    def test_predict_unknown_when_empty(self):
        chain = MarkovDayChain()
        pred = chain.predict_next_day()
        assert pred["current_state"] == "UNKNOWN"
        assert pred["p_green"] == 0.5


# ── STREAK ANALYSIS TESTS ───────────────────────────────────

class TestStreaks:

    def test_streak_analysis_keys(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        sa = chain.streak_analysis()
        expected_keys = [
            "current_streak_length", "current_streak_direction",
            "avg_green_streak", "avg_red_streak",
            "max_green_streak", "max_red_streak",
            "green_streak_dist", "red_streak_dist"
        ]
        for key in expected_keys:
            assert key in sa, f"Missing key: {key}"

    def test_streak_length_positive(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        sa = chain.streak_analysis()
        assert sa["current_streak_length"] >= 1

    def test_streak_direction_valid(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        sa = chain.streak_analysis()
        assert sa["current_streak_direction"] in ("GREEN", "RED")

    def test_known_streak_sequence(self):
        """Test with a known sequence: 3 green, 2 red, 1 green."""
        returns = pd.Series(
            [0.01, 0.02, 0.01, -0.01, -0.02, 0.03],
            index=pd.date_range("2020-01-01", periods=6, freq="B")
        )
        chain = MarkovDayChain().fit(returns, min_periods=1)
        sa = chain.streak_analysis()
        assert sa["current_streak_length"] == 1
        assert sa["current_streak_direction"] == "GREEN"

    def test_choppy_alternating_streaks(self, choppy_returns):
        chain = MarkovDayChain().fit(choppy_returns)
        sa = chain.streak_analysis()
        # In a choppy market, streaks should be short
        assert sa["avg_green_streak"] < 2.0
        assert sa["avg_red_streak"] < 2.0


# ── ROLLING TRANSITION MATRIX TESTS ─────────────────────────

class TestRolling:

    def test_rolling_has_correct_columns(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        rtm = chain.rolling_transition_matrix(window=20)
        for col in ["date", "p_gg", "p_gr", "p_rg", "p_rr", "regime"]:
            assert col in rtm.columns, f"Missing column: {col}"

    def test_rolling_probabilities_valid(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        rtm = chain.rolling_transition_matrix(window=20)
        for _, row in rtm.iterrows():
            assert abs(row["p_gg"] + row["p_gr"] - 1.0) < 1e-10
            assert abs(row["p_rg"] + row["p_rr"] - 1.0) < 1e-10


# ── DECAY-ADJUSTED RETURN TESTS ──────────────────────────────

class TestDecayAdjusted:

    def test_choppy_penalizes_more(self, choppy_returns):
        chain = MarkovDayChain().fit(choppy_returns)
        ret = chain.decay_adjusted_expected_return(0.01, 0.02)
        # Choppy regime should have higher decay penalty
        assert ret < 0.01

    def test_trending_penalizes_less(self, trending_green_returns):
        chain = MarkovDayChain().fit(trending_green_returns)
        ret = chain.decay_adjusted_expected_return(0.01, 0.02)
        # Trending regime should have lower decay penalty
        assert ret > chain.decay_adjusted_expected_return(0.01, 0.02, decay_lambda=0.01)

    def test_zero_vol_no_decay(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        ret = chain.decay_adjusted_expected_return(0.05, 0.0)
        assert ret == 0.05  # no decay when vol is zero


# ── GAP-CONDITIONED PROBABILITY TESTS ───────────────────────

class TestGapConditional:

    def test_gap_bins_exist(self, balanced_returns):
        n = len(balanced_returns)
        opens = balanced_returns + np.random.normal(0, 0.001, n)
        prev_closes = balanced_returns.shift(1)

        chain = MarkovDayChain().fit(balanced_returns)
        gaps = chain.conditional_gap_probability(balanced_returns, opens, prev_closes.dropna())

        expected_bins = ["large_negative", "small_negative", "small_positive", "large_positive"]
        for b in expected_bins:
            assert b in gaps, f"Missing bin: {b}"
            assert 0 <= gaps[b] <= 1, f"Invalid probability for {b}: {gaps[b]}"


# ── REPR TEST ────────────────────────────────────────────────

class TestRepr:

    def test_repr_unfitted(self):
        chain = MarkovDayChain()
        assert "not fitted" in repr(chain)

    def test_repr_fitted(self, balanced_returns):
        chain = MarkovDayChain().fit(balanced_returns)
        r = repr(chain)
        assert "MarkovDayChain" in r
        assert "P(G->G)" in r
        assert "regime=" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
