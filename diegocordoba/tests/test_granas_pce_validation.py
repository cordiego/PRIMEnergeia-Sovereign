import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from granas_module.pce_physics import GranasPCEValidator, TargetMetrics

class TestGranasPCEValidation:
    @pytest.fixture
    def validator(self):
        return GranasPCEValidator()

    @pytest.fixture
    def targets(self):
        return TargetMetrics()

    def test_target_pce(self, validator, targets):
        results = validator.evaluate_model()
        # Accept within small rounding tolerance
        assert abs(results["pce_pct"] - targets.pce_target) < 0.1, \
            f"Expected PCE {targets.pce_target}%, got {results['pce_pct']}%"

    def test_target_voc(self, validator, targets):
        results = validator.evaluate_model()
        assert abs(results["voc_mv"] - targets.voc_target_mv) < 1.0, \
            f"Expected Voc {targets.voc_target_mv}mV, got {results['voc_mv']}mV"

    def test_target_grain_size(self, validator, targets):
        results = validator.evaluate_model()
        assert abs(results["grain_size_nm"] - targets.grain_size_nm) < 1.0, \
            f"Expected Grain Size {targets.grain_size_nm}nm, got {results['grain_size_nm']}nm"

    def test_target_defect_density(self, validator, targets):
        results = validator.evaluate_model()
        assert abs(results["defect_density"] - targets.defect_density) < 0.01, \
            f"Expected Defect Density {targets.defect_density}, got {results['defect_density']}"

    def test_target_stability(self, validator, targets):
        results = validator.evaluate_model()
        assert abs(results["stability_score"] - targets.stability_score) < 0.01, \
            f"Expected Stability Score {targets.stability_score}, got {results['stability_score']}"
