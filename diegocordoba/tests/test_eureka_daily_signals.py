import sys
import os
import pytest

# Ensure scripts directory is in path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from eureka_daily_signals import classify_regime

def test_classify_regime_risk_on():
    """Test RISK-ON regime classification for VIX < 18."""
    assert classify_regime(10.0) == "RISK-ON"
    assert classify_regime(17.9) == "RISK-ON"
    assert classify_regime(0.0) == "RISK-ON"

def test_classify_regime_transition():
    """Test TRANSITION regime classification for 18 <= VIX <= 28."""
    assert classify_regime(18.0) == "TRANSITION"
    assert classify_regime(22.5) == "TRANSITION"
    assert classify_regime(28.0) == "TRANSITION"

def test_classify_regime_crisis():
    """Test CRISIS regime classification for VIX > 28."""
    assert classify_regime(28.1) == "CRISIS"
    assert classify_regime(35.0) == "CRISIS"
    assert classify_regime(100.0) == "CRISIS"
