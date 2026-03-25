"""
PRIMEngine API — Test Suite
===============================
Pytest tests for the Grid Dispatch Optimization API.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import sys
import json
import numpy as np
import pytest

# Ensure project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.primengine_api import app, API_KEYS, MARKETS


client = TestClient(app)

# Test API keys
PILOT_KEY = "prime_pilot_key"
DASHBOARD_KEY = "prime_dashboard_key"
API_KEY = "prime_api_key"
ENTERPRISE_KEY = "prime_enterprise_key"
INVALID_KEY = "invalid_key_12345"


# ─────────────────────────────────────────────────────────────
# Health Check Tests
# ─────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_returns_200(self):
        response = client.get("/v1/health")
        assert response.status_code == 200

    def test_health_contains_service_info(self):
        data = client.get("/v1/health").json()
        assert data["service"] == "PRIMEngine API"
        assert data["company"] == "PRIMEnergeia S.A.S."
        assert "markets" in data
        assert "ercot" in data["markets"]

    def test_health_reports_solver_status(self):
        data = client.get("/v1/health").json()
        assert data["hjb_solver"] in ("active", "unavailable")


# ─────────────────────────────────────────────────────────────
# Authentication Tests
# ─────────────────────────────────────────────────────────────
class TestAuth:
    def test_no_api_key_returns_403(self):
        response = client.get("/v1/markets")
        assert response.status_code in (401, 403, 422)

    def test_invalid_key_returns_401(self):
        response = client.get("/v1/markets", headers={"X-API-Key": INVALID_KEY})
        assert response.status_code == 401

    def test_valid_key_returns_200(self):
        response = client.get("/v1/markets", headers={"X-API-Key": DASHBOARD_KEY})
        assert response.status_code == 200

    def test_pilot_key_limited_markets(self):
        data = client.get("/v1/markets", headers={"X-API-Key": PILOT_KEY}).json()
        market_ids = [m["market_id"] for m in data]
        assert "ercot" in market_ids
        assert "mibel" not in market_ids  # Pilot only gets ERCOT

    def test_dashboard_key_all_markets(self):
        data = client.get("/v1/markets", headers={"X-API-Key": DASHBOARD_KEY}).json()
        market_ids = [m["market_id"] for m in data]
        assert "ercot" in market_ids
        assert "sen" in market_ids
        assert "mibel" in market_ids


# ─────────────────────────────────────────────────────────────
# Markets Tests
# ─────────────────────────────────────────────────────────────
class TestMarkets:
    def test_markets_returns_list(self):
        data = client.get("/v1/markets", headers={"X-API-Key": ENTERPRISE_KEY}).json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_market_has_required_fields(self):
        data = client.get("/v1/markets", headers={"X-API-Key": ENTERPRISE_KEY}).json()
        for market in data:
            assert "market_id" in market
            assert "name" in market
            assert "frequency" in market
            assert "capabilities" in market


# ─────────────────────────────────────────────────────────────
# Dispatch Optimization Tests
# ─────────────────────────────────────────────────────────────
class TestDispatchOptimization:
    def test_optimize_returns_200(self):
        response = client.post(
            "/v1/dispatch/optimize",
            json={"market": "ercot", "fleet_mw": 100, "duration_hours": 6,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking", "dt_hours": 0.5},
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code == 200

    def test_optimize_returns_valid_result(self):
        data = client.post(
            "/v1/dispatch/optimize",
            json={"market": "ercot", "fleet_mw": 50, "duration_hours": 4,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking", "dt_hours": 0.5},
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()

        assert data["market"] == "ercot"
        assert data["fleet_mw"] == 50
        assert data["total_fuel_kg"] > 0
        assert data["fuel_savings_pct"] >= 0
        assert data["co2_emissions_kg"] == 0.0
        assert len(data["time_grid"]) > 0
        assert len(data["power_trajectory_kw"]) == len(data["time_grid"])

    def test_optimize_savings_positive(self):
        data = client.post(
            "/v1/dispatch/optimize",
            json={"market": "ercot", "fleet_mw": 100, "duration_hours": 8,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking", "dt_hours": 0.25},
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()

        assert data["fuel_savings_pct"] >= 0
        assert data["baseline_fuel_kg"] >= data["total_fuel_kg"]

    def test_optimize_solver_time_reasonable(self):
        data = client.post(
            "/v1/dispatch/optimize",
            json={"market": "ercot", "fleet_mw": 100, "duration_hours": 6,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking", "dt_hours": 0.5},
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()

        assert data["solver_time_ms"] < 30000  # Should complete in <30s

    def test_optimize_pem_engine(self):
        data = client.post(
            "/v1/dispatch/optimize",
            json={"market": "sen", "fleet_mw": 50, "duration_hours": 4,
                  "engine_type": "PEM", "mission_profile": "Grid Peaking", "dt_hours": 0.5},
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()

        assert data["engine_type"] == "PEM"
        assert data["co2_emissions_kg"] == 0.0

    def test_optimize_invalid_market(self):
        response = client.post(
            "/v1/dispatch/optimize",
            json={"market": "caiso", "fleet_mw": 100, "duration_hours": 6,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking"},
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code in (400, 403)

    def test_optimize_market_access_denied(self):
        response = client.post(
            "/v1/dispatch/optimize",
            json={"market": "mibel", "fleet_mw": 100, "duration_hours": 6,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking"},
            headers={"X-API-Key": PILOT_KEY},  # Pilot only has ERCOT
        )
        assert response.status_code == 403

    def test_optimize_economics(self):
        data = client.post(
            "/v1/dispatch/optimize",
            json={"market": "ercot", "fleet_mw": 200, "duration_hours": 12,
                  "engine_type": "AICE", "mission_profile": "Grid Peaking", "dt_hours": 0.5},
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()

        assert "dispatch_cost_usd" in data
        assert "baseline_cost_usd" in data
        assert "savings_usd" in data
        assert data["savings_usd"] >= 0


# ─────────────────────────────────────────────────────────────
# Session Tests
# ─────────────────────────────────────────────────────────────
class TestSessions:
    def test_create_session(self):
        response = client.post(
            "/v1/dispatch/sessions",
            json={"name": "test-session", "market": "ercot", "fleet_mw": 100},
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-session"
        assert data["market"] == "ercot"
        assert "session_id" in data

    def test_list_sessions(self):
        # Create a session first
        client.post(
            "/v1/dispatch/sessions",
            json={"name": "list-test", "market": "ercot", "fleet_mw": 50},
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        data = client.get(
            "/v1/dispatch/sessions",
            headers={"X-API-Key": ENTERPRISE_KEY},
        ).json()
        assert isinstance(data["sessions"], list)
        assert data["tier"] == "ENTERPRISE"

    def test_session_not_found(self):
        response = client.get(
            "/v1/dispatch/sessions/nonexistent/status",
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────
# Grid Simulation Tests
# ─────────────────────────────────────────────────────────────
class TestGridSimulation:
    def test_simulate_ercot(self):
        response = client.post(
            "/v1/grid/simulate?market=ercot&duration_seconds=1.0",
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["market"] == "ercot"
        assert len(data["frequency_hz"]) > 0
        assert data["frequency_stats"]["mean"] > 59.0

    def test_simulate_sen(self):
        response = client.post(
            "/v1/grid/simulate?market=sen&duration_seconds=1.0",
            headers={"X-API-Key": ENTERPRISE_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["market"] == "sen"
