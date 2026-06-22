"""
PRIMEnergeia — REST API Adapter
=================================
Client-side adapter for consuming the PRIMEngine FastAPI.
Used when the plant has a companion PC that can make HTTPS
calls to a cloud-hosted or on-prem PRIMEnergeia API server.

Best for: Battery dispatch, day-ahead scheduling, cloud-hosted SaaS.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict

from adapters.base_adapter import PlantAdapter, GridState, ControlSetpoint

logger = logging.getLogger("prime.adapters.api")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class APIAdapter(PlantAdapter):
    """REST API adapter for cloud/remote PRIMEnergeia integration.

    Usage:
        adapter = APIAdapter(
            base_url="https://api.primenergeia.com",
            api_key="prime_enterprise_key",
            market="ercot",
        )
        adapter.connect()

        state = adapter.read_state()
        setpoint = hjb.solve(state)
        adapter.write_setpoint(setpoint)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        api_key: str = "prime_pilot_key",
        market: str = "ercot",
        fleet_mw: float = 100.0,
        battery_mwh: float = 400.0,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(name=f"api:{market}", read_only=False)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.market = market
        self.fleet_mw = fleet_mw
        self.battery_mwh = battery_mwh
        self.timeout = timeout_seconds

        self._session: Optional[requests.Session] = None
        self._session_id: Optional[str] = None
        self._last_dispatch: Optional[dict] = None

    @property
    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "PRIMEnergeia-Adapter/1.0",
        }

    def connect(self) -> None:
        """Verify API connectivity and create a dispatch session."""
        if not REQUESTS_AVAILABLE:
            raise ImportError("Install 'requests' package: pip install requests")

        self._session = requests.Session()
        self._session.headers.update(self._headers)

        # Health check
        try:
            resp = self._session.get(
                f"{self.base_url}/v1/health",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            health = resp.json()
            logger.info(
                f"[{self.name}] Connected to {self.base_url} "
                f"(v{health.get('version', '?')}, "
                f"HJB={health.get('hjb_solver', '?')})"
            )
        except requests.RequestException as e:
            raise ConnectionError(f"API health check failed: {e}") from e

        # Create dispatch session
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/dispatch/sessions",
                json={
                    "name": f"adapter-{self.market}-{int(time.time())}",
                    "market": self.market,
                    "fleet_mw": self.fleet_mw,
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                session_data = resp.json()
                self._session_id = session_data.get("session_id")
                logger.info(f"[{self.name}] Session created: {self._session_id}")
        except requests.RequestException:
            logger.warning(f"[{self.name}] Session creation failed — operating stateless")

        self._connected = True

    def close(self) -> None:
        """Clean up API session."""
        if self._session_id and self._session:
            try:
                self._session.delete(
                    f"{self.base_url}/v1/dispatch/sessions/{self._session_id}",
                    timeout=5,
                )
            except Exception:
                pass

        if self._session:
            self._session.close()
        self._connected = False
        logger.info(f"[{self.name}] Disconnected from {self.base_url}")

    def _read_state_impl(self) -> GridState:
        """Fetch current grid state from API (or simulation endpoint)."""
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/grid/simulate",
                params={
                    "market": self.market,
                    "duration_seconds": 1.0,
                    "control_gain": 500.0,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            freq_hz = data.get("frequency_stats", {}).get("mean", 60.0)
            penalties = data.get("penalties_avoided_usd", 0.0)

            return GridState(
                frequency_hz=round(freq_hz, 4),
                voltage_a_kv=0.0,  # Not available from simulation endpoint
                active_power_mw=self.fleet_mw * 0.75,  # Estimated
                lmp_price=0.0,
                node_id="",
                market=self.market.upper(),
                timestamp=datetime.now(),
                quality="SIMULATED",
            )

        except requests.RequestException as e:
            logger.warning(f"[{self.name}] Grid simulate failed: {e}")
            # Return default state
            return GridState(
                frequency_hz=60.0 if self.market != "mibel" else 50.0,
                market=self.market.upper(),
                quality="BAD",
            )

    def _write_setpoint_impl(self, setpoint: ControlSetpoint) -> bool:
        """Request dispatch optimization from the API."""
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/dispatch/cooptimize",
                json={
                    "market": self.market,
                    "fleet_mw": self.fleet_mw,
                    "battery_mwh": self.battery_mwh,
                    "hours": 24,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._last_dispatch = resp.json()
            logger.info(
                f"[{self.name}] Dispatch optimized: "
                f"{self._last_dispatch.get('hours', 0)}h, "
                f"uplift={self._last_dispatch.get('uplift_pct', 0):+.1f}%"
            )
            return True

        except requests.RequestException as e:
            logger.error(f"[{self.name}] Dispatch request failed: {e}")
            return False

    def get_dispatch_schedule(self) -> Optional[dict]:
        """Return the last dispatch optimization result."""
        return self._last_dispatch

    def fetch_cooptimization(self, hours: int = 24) -> Optional[dict]:
        """Run a co-optimization and return full results."""
        if not self._session:
            return None

        try:
            resp = self._session.post(
                f"{self.base_url}/v1/dispatch/cooptimize",
                json={
                    "market": self.market,
                    "fleet_mw": self.fleet_mw,
                    "battery_mwh": self.battery_mwh,
                    "hours": hours,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._last_dispatch = resp.json()
            return self._last_dispatch

        except requests.RequestException as e:
            logger.error(f"[{self.name}] Co-optimization failed: {e}")
            return None
