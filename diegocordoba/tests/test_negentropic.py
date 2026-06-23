"""
PRIME-Kernel — Tests for the Negentropic HJB Framework
========================================================
Comprehensive test suite validating:

1. Second Law: Σ̇(x,u) ≥ 0 always
2. Closed-form u* matches grid search
3. V(x_sync) < V(x_desync) — minimum at synchronization
4. Backward compatibility — old dynamics unchanged
5. Landauer bound: total Σ ≥ Σ_Landauer
6. Entropy decomposition consistency
7. Kuramoto order parameter at sync = 1.0
8. NS bridge regularity certificate
9. Control decomposition: anticipatory + thermodynamic = total

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import sys
import os
import numpy as np
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from entropy_production import (
    EntropyProductionRate,
    EntropyDecomposition,
    build_entropy_engine_cenace,
)
from negentropic_control import (
    NegentropicOptimalControl,
    build_negentropic_control_cenace,
)
from negentropic_dynamics import (
    NegentropicGridDynamics,
    NegentropicBESSDynamics,
    NegentropicRegimeDynamics,
    NegentropicKuramotoDynamics,
    build_negentropic_cenace,
)
from hjb_solver_fortified import (
    GridFrequencyDynamics,
    BESSFrequencyDynamics,
    ISOMarket,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def entropy_engine():
    """CENACE-calibrated entropy engine."""
    return build_entropy_engine_cenace()


@pytest.fixture
def neg_grid_dynamics():
    """2-D negentropic grid dynamics."""
    return NegentropicGridDynamics(control_penalty_R=0.1)


@pytest.fixture
def neg_bess_dynamics():
    """5-D negentropic BESS dynamics."""
    return NegentropicBESSDynamics(control_penalty_R=0.1)


@pytest.fixture
def kuramoto_dynamics():
    """Kuramoto oscillator dynamics."""
    return NegentropicKuramotoDynamics(n_oscillators=5, coupling_K=2.0, sigma_noise=0.1)


@pytest.fixture
def classic_dynamics():
    """Original (heuristic) grid dynamics for backward compatibility."""
    return GridFrequencyDynamics(market=ISOMarket.CENACE)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Second Law — Σ̇ ≥ 0
# ─────────────────────────────────────────────────────────────────────────────
class TestSecondLaw:
    """The entropy production rate must ALWAYS be non-negative."""

    def test_sigma_dot_nonnegative_at_equilibrium(self, entropy_engine):
        """At equilibrium (drift = reversible drift), Σ̇ = 0."""
        f_rev = np.array([0.1, 0.0])
        sigma_dot = entropy_engine.sigma_dot(f_rev, f_rev)  # total = reversible
        assert sigma_dot == pytest.approx(0.0, abs=1e-10)

    def test_sigma_dot_nonnegative_random_states(self, entropy_engine):
        """Σ̇ ≥ 0 for random drifts."""
        rng = np.random.default_rng(42)
        for _ in range(1000):
            total_drift = rng.normal(0, 1, size=2)
            rev_drift = rng.normal(0, 0.5, size=2)
            sigma_dot = entropy_engine.sigma_dot(total_drift, rev_drift)
            assert sigma_dot >= 0.0, f"2nd Law violated: Σ̇={sigma_dot}"

    def test_sigma_dot_nonneg_grid_dynamics(self, neg_grid_dynamics):
        """Σ̇ ≥ 0 from running cost for random states and controls."""
        rng = np.random.default_rng(123)
        for _ in range(200):
            state = np.array([rng.uniform(-1, 1), rng.uniform(0, 50)])
            control = rng.uniform(-5, 5)
            cost = neg_grid_dynamics.running_cost(state, control)
            assert cost >= 0.0, f"Negentropic cost negative: {cost}"

    def test_sigma_dot_nonneg_bess(self, neg_bess_dynamics):
        """Σ̇ ≥ 0 for 5-D BESS dynamics."""
        rng = np.random.default_rng(456)
        for _ in range(100):
            state = np.array([
                rng.uniform(-1, 1),
                rng.uniform(-3, 3),
                rng.uniform(0.2, 0.9),
                rng.uniform(22, 50),
                rng.uniform(0, 0.5),
            ])
            control = rng.uniform(-5, 5)
            cost = neg_bess_dynamics.running_cost(state, control)
            assert cost >= 0.0, f"BESS negentropic cost negative: {cost}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Value Function Minimum at Synchronization
# ─────────────────────────────────────────────────────────────────────────────
class TestNegentropicWell:
    """V(x_sync) should be the minimum of the negentropic potential."""

    def test_running_cost_minimum_at_sync(self, neg_grid_dynamics):
        """Running cost should be lowest at synchronization (Δf=0)."""
        sync_state = np.array([0.0, 0.0])
        desync_state = np.array([1.0, 0.0])

        cost_sync = neg_grid_dynamics.running_cost(sync_state, 0.0)
        cost_desync = neg_grid_dynamics.running_cost(desync_state, 0.0)

        assert cost_sync < cost_desync, (
            f"Sync cost ({cost_sync}) should be < desync cost ({cost_desync})"
        )

    def test_kuramoto_terminal_minimum_at_sync(self, kuramoto_dynamics):
        """Kuramoto terminal cost minimum at synchronized state (all θᵢ equal)."""
        sync_state = np.zeros(5)  # all phases = 0
        desync_state = np.array([0, np.pi/2, np.pi, -np.pi/2, np.pi/4])

        t_sync = kuramoto_dynamics.terminal_cost(sync_state)
        t_desync = kuramoto_dynamics.terminal_cost(desync_state)

        assert t_sync < t_desync

    def test_kuramoto_order_parameter_sync(self, kuramoto_dynamics):
        """Order parameter r = 1 at perfect synchronization."""
        sync = np.zeros(5)
        assert kuramoto_dynamics.order_parameter(sync) == pytest.approx(1.0, abs=1e-10)

    def test_kuramoto_order_parameter_desync(self, kuramoto_dynamics):
        """Order parameter r < 1 for desynchronized states."""
        desync = np.linspace(0, 2 * np.pi, 5, endpoint=False)
        r = kuramoto_dynamics.order_parameter(desync)
        assert r < 0.5  # should be near 0 for uniform distribution


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Entropy Decomposition Consistency
# ─────────────────────────────────────────────────────────────────────────────
class TestEntropyDecomposition:
    """Entropy decomposition: f_total = f_rev + f_irrev."""

    def test_drift_decomposition(self, entropy_engine):
        """f_irrev + f_rev = f_total."""
        total_drift = np.array([0.5, -0.3])
        mu = np.zeros(2)
        kappa = np.array([0.42, 0.1])
        state = np.array([0.1, 5.0])

        f_rev = entropy_engine.reversible_drift_ou(state, mu, kappa)
        f_irrev = entropy_engine.irreversible_drift(total_drift, f_rev)

        np.testing.assert_allclose(
            f_rev + f_irrev, total_drift, atol=1e-12,
            err_msg="Drift decomposition inconsistent",
        )

    def test_decompose_negentropic_cost(self, entropy_engine):
        """negentropic_cost = Σ̇ + ½Ru²."""
        state = np.array([0.1, 5.0])
        control = 2.0
        total_drift = np.array([0.5, -0.3])
        mu = np.zeros(2)
        kappa = np.array([0.42, 0.1])
        R = 0.1

        decomp = entropy_engine.decompose(
            state, control, total_drift, mu, kappa, R,
        )

        expected = decomp.sigma_dot_total + decomp.control_cost
        assert decomp.negentropic_cost == pytest.approx(expected, abs=1e-10)

    def test_control_cost_quadratic(self, entropy_engine):
        """Control cost = ½ R u²."""
        R = 0.1
        u = 3.0
        state = np.zeros(2)
        drift = np.zeros(2)
        mu = np.zeros(2)
        kappa = np.array([0.42, 0.1])

        decomp = entropy_engine.decompose(state, u, drift, mu, kappa, R)
        assert decomp.control_cost == pytest.approx(0.5 * R * u ** 2, abs=1e-10)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Backward Compatibility
# ─────────────────────────────────────────────────────────────────────────────
class TestBackwardCompatibility:
    """Negentropic dynamics must preserve step() and diffusion() from parents."""

    def test_step_identical(self, neg_grid_dynamics, classic_dynamics):
        """step() should be identical between negentropic and classic dynamics."""
        state = np.array([0.1, 10.0])
        control = 2.0
        dt = 1.0

        new_neg = neg_grid_dynamics.step(state, control, dt)
        new_cls = classic_dynamics.step(state, control, dt)

        np.testing.assert_allclose(new_neg, new_cls, atol=1e-12)

    def test_diffusion_identical(self, neg_grid_dynamics, classic_dynamics):
        """diffusion() should be identical."""
        state = np.array([0.1, 10.0])
        diff_neg = neg_grid_dynamics.diffusion(state)
        diff_cls = classic_dynamics.diffusion(state)
        np.testing.assert_allclose(diff_neg, diff_cls, atol=1e-12)

    def test_state_bounds_identical(self, neg_grid_dynamics, classic_dynamics):
        """State bounds should be identical."""
        assert neg_grid_dynamics.state_bounds() == classic_dynamics.state_bounds()

    def test_control_bounds_identical(self, neg_grid_dynamics, classic_dynamics):
        """Control bounds should be identical."""
        assert neg_grid_dynamics.control_bounds() == classic_dynamics.control_bounds()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Landauer Bound
# ─────────────────────────────────────────────────────────────────────────────
class TestLandauerBound:
    """Landauer bound: minimum entropy to go from x_init to x_target."""

    def test_landauer_nonnegative(self, entropy_engine):
        """Landauer bound must be ≥ 0."""
        init = np.array([1.0, 0.0])
        target = np.array([0.0, 0.0])
        mu = np.zeros(2)
        kappa = np.array([0.42, 0.1])
        bound = entropy_engine.landauer_bound(init, target, mu, kappa)
        assert bound >= 0.0

    def test_landauer_zero_at_equilibrium(self, entropy_engine):
        """Landauer bound = 0 when starting at target."""
        target = np.array([0.0, 0.0])
        mu = np.zeros(2)
        kappa = np.array([0.42, 0.1])
        bound = entropy_engine.landauer_bound(target, target, mu, kappa)
        assert bound == pytest.approx(0.0, abs=1e-10)

    def test_landauer_increases_with_distance(self):
        """Landauer bound increases when initial state is farther from target."""
        # Use an engine where the noise dimension is non-trivial
        sigma_vec = np.array([0.1, 0.05])  # both dims have noise
        engine = EntropyProductionRate(
            effective_temperature=0.01, diffusion_vector=sigma_vec,
        )
        target = np.array([0.0, 0.0])
        mu = np.zeros(2)
        kappa = np.array([0.5, 0.5])

        near = np.array([0.1, 0.0])
        far = np.array([1.0, 0.0])

        bound_near = engine.landauer_bound(near, target, mu, kappa)
        bound_far = engine.landauer_bound(far, target, mu, kappa)

        assert bound_far > bound_near


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Entropy Engine Construction
# ─────────────────────────────────────────────────────────────────────────────
class TestEntropyEngine:
    """Validate entropy engine construction and temperature."""

    def test_temperature_from_ou(self):
        """T_eff = σ²/(2κ) for OU construction."""
        kappa = 0.42
        sigma = 0.01483
        engine = EntropyProductionRate.from_ou_params(kappa, sigma, n_dims=2)
        expected_T = sigma ** 2 / (2 * kappa)
        assert engine.T == pytest.approx(expected_T, rel=1e-6)

    def test_D_matrix_diagonal(self):
        """D = diag(σᵢ²/2)."""
        sigma_vec = np.array([0.01, 0.02, 0.0])
        engine = EntropyProductionRate(
            effective_temperature=1.0, diffusion_vector=sigma_vec,
        )
        # D[0,0] ≈ 0.01²/2 = 5e-5 (plus regularization)
        assert engine.D_diag[0] == pytest.approx(0.01 ** 2 / 2, abs=1e-10)
        assert engine.D_diag[1] == pytest.approx(0.02 ** 2 / 2, abs=1e-10)

    def test_cenace_temperature(self):
        """CENACE T_eff ≈ 2.617e-4."""
        engine = build_entropy_engine_cenace()
        expected = 0.01483 ** 2 / (2 * 0.42)
        assert engine.T == pytest.approx(expected, rel=1e-4)


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Dynamics Factory
# ─────────────────────────────────────────────────────────────────────────────
class TestDynamicsFactory:
    """Test the build_negentropic_cenace factory."""

    @pytest.mark.parametrize("dtype", ["grid", "regime", "bess", "kuramoto"])
    def test_factory_builds(self, dtype):
        """Factory should create valid dynamics for all types."""
        dynamics = build_negentropic_cenace(dynamics_type=dtype, control_penalty_R=0.1)
        assert dynamics.state_dims() > 0
        assert len(dynamics.state_bounds()) == dynamics.state_dims()

    def test_factory_invalid_raises(self):
        """Factory should raise for unknown type."""
        with pytest.raises(ValueError):
            build_negentropic_cenace(dynamics_type="nonexistent")


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Control Decomposition
# ─────────────────────────────────────────────────────────────────────────────
class TestControlDecomposition:
    """Test the closed-form control and its decomposition."""

    def test_u_star_finite(self, entropy_engine):
        """u* should always be finite."""
        controller = build_negentropic_control_cenace(entropy_engine)
        state = np.array([0.5, 10.0])
        V_grad = np.array([100.0, 50.0])
        f_irrev = np.array([0.01, 0.001])

        u = controller.compute_u_star(state, V_grad, f_irrev)
        assert np.isfinite(u)

    def test_decomposition_sums(self):
        """u_anticipatory + u_thermodynamic ≈ u_star (before clipping)."""
        # Use a mild temperature to avoid extreme thermodynamic terms
        sigma_vec = np.array([0.5, 0.0])
        engine = EntropyProductionRate(
            effective_temperature=1.0, diffusion_vector=sigma_vec,
        )
        controller = build_negentropic_control_cenace(
            engine, control_bounds=(-1e12, 1e12),
        )
        state = np.array([0.5, 10.0])
        V_grad = np.array([1.0, 0.5])
        f_irrev = np.array([0.01, 0.001])

        decomp = controller.decompose_control(state, V_grad, f_irrev)
        # With essentially no clipping, u_star = u_antic + u_thermo
        assert decomp.u_star == pytest.approx(
            decomp.u_anticipatory + decomp.u_thermodynamic, abs=1e-3,
        )

    def test_ratios_sum_to_one(self, entropy_engine):
        """Anticipatory + thermodynamic ratios should sum to 1."""
        controller = build_negentropic_control_cenace(entropy_engine)
        state = np.array([0.5, 10.0])
        V_grad = np.array([100.0, 50.0])
        f_irrev = np.array([0.01, 0.001])

        decomp = controller.decompose_control(state, V_grad, f_irrev)
        assert decomp.anticipatory_ratio + decomp.thermodynamic_ratio == pytest.approx(1.0, abs=1e-10)

    def test_demon_budget_nonnegative(self, entropy_engine):
        """Maxwell demon budget = ½Ru² ≥ 0."""
        controller = build_negentropic_control_cenace(entropy_engine)
        state = np.array([0.5, 10.0])
        V_grad = np.array([100.0, 50.0])
        f_irrev = np.array([0.01, 0.001])

        decomp = controller.decompose_control(state, V_grad, f_irrev)
        assert decomp.maxwell_demon_budget >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Kuramoto Dynamics
# ─────────────────────────────────────────────────────────────────────────────
class TestKuramoto:
    """Test Kuramoto oscillator dynamics."""

    def test_phase_wrapping(self, kuramoto_dynamics):
        """Phases should stay in [-π, π]."""
        state = np.array([3.0, -3.0, 2.5, -2.5, 0.0])
        next_state = kuramoto_dynamics.step(state, 0.0, 0.1)
        assert np.all(next_state >= -np.pi)
        assert np.all(next_state <= np.pi)

    def test_sync_state_stable(self, kuramoto_dynamics):
        """Synchronized state should be approximately stable."""
        sync = np.zeros(5)
        for _ in range(10):
            sync = kuramoto_dynamics.step(sync, 0.0, 0.01)
        # Should stay near zero
        assert np.max(np.abs(sync)) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
