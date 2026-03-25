"""
PRIMEngine API — Grid Dispatch Optimization SaaS
===================================================
FastAPI wrapper for the PRIMEngine HJB dispatch optimizer.
Enables SaaS licensing for grid operators via API key authentication
with tiered rate limiting.

PRIMEnergeia S.A.S. — Grid Optimization Division

Endpoints:
    POST /v1/dispatch/optimize    — Run HJB dispatch optimization
    POST /v1/dispatch/cooptimize   — DA/RT co-optimization with battery degradation
    POST /v1/dispatch/sessions    — Create persistent session
    GET  /v1/dispatch/sessions/{id}/status  — Session progress
    GET  /v1/dispatch/sessions/{id}/results — Full dispatch results
    GET  /v1/markets              — List available markets
    GET  /v1/health               — Health check

Authentication:
    Header: X-API-Key: <key>

Tiers:
    PILOT       — 10 optimizations/day, 1 market, 1 session
    DASHBOARD   — 100 optimizations/day, 3 markets, 10 sessions
    API         — 1,000 optimizations/day, all markets, 100 sessions
    ENTERPRISE  — Unlimited
"""

import os
import uuid
import time
import json
from datetime import datetime
from typing import Optional, List
from collections import defaultdict
from dataclasses import dataclass, asdict

import numpy as np
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib", "engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "markets"))

# ============================================================
#  Engine imports
# ============================================================
try:
    from engine_hjb import EngineHJBDispatch, DispatchResult, generate_mission_profile
    HJB_AVAILABLE = True
except ImportError:
    HJB_AVAILABLE = False

try:
    from ercot.physics_ercot import ERCOTGridPhysics
    from sen.physics_sen import SENGridPhysics
    from mibel.physics_mibel import MIBELGridPhysics
    GRID_PHYSICS_AVAILABLE = True
except ImportError:
    GRID_PHYSICS_AVAILABLE = False

try:
    from ercot.dispatch_ercot import run_ercot_coopt
    from sen.dispatch_sen import run_sen_coopt
    from mibel.dispatch_mibel import run_mibel_coopt
    COOPT_AVAILABLE = True
except ImportError:
    COOPT_AVAILABLE = False

# ============================================================
#  Configuration
# ============================================================
VERSION = "1.1.0"
API_TITLE = "PRIMEngine API — Grid Dispatch Optimization"
DATA_DIR = os.environ.get("PRIMENGINE_DATA_DIR", os.path.expanduser("~/.prime_api"))

# Market configurations
MARKETS = {
    "ercot": {
        "name": "ERCOT",
        "region": "Texas, USA",
        "frequency": 60.0,
        "currency": "USD",
        "nodes": 25,
        "zones": 8,
        "description": "Electric Reliability Council of Texas — deregulated, islanded 60Hz grid",
        "capabilities": ["frequency_regulation", "dispatch_optimization", "ancillary_services"],
    },
    "sen": {
        "name": "SEN (Sistema Eléctrico Nacional)",
        "region": "Mexico",
        "frequency": 60.0,
        "currency": "MXN",
        "nodes": 30,
        "zones": 9,
        "description": "Mexico's national electric system — 9 CENACE regions",
        "capabilities": ["frequency_regulation", "dispatch_optimization"],
    },
    "mibel": {
        "name": "MIBEL",
        "region": "Spain & Portugal",
        "frequency": 50.0,
        "currency": "EUR",
        "nodes": 20,
        "zones": 6,
        "description": "Iberian electricity market — EU integrated",
        "capabilities": ["frequency_regulation", "dispatch_optimization"],
    },
}

# API Key tiers
API_KEYS = {
    os.environ.get("PRIME_API_KEY_PILOT", "prime_pilot_key"): {
        "tier": "PILOT", "ops_per_day": 10, "max_sessions": 1,
        "markets": ["ercot"], "org": "Pilot Trial",
    },
    os.environ.get("PRIME_API_KEY_DASHBOARD", "prime_dashboard_key"): {
        "tier": "DASHBOARD", "ops_per_day": 100, "max_sessions": 10,
        "markets": ["ercot", "sen", "mibel"], "org": "Dashboard License",
    },
    os.environ.get("PRIME_API_KEY_API", "prime_api_key"): {
        "tier": "API", "ops_per_day": 1000, "max_sessions": 100,
        "markets": ["ercot", "sen", "mibel"], "org": "API License",
    },
    os.environ.get("PRIME_API_KEY_ENTERPRISE", "prime_enterprise_key"): {
        "tier": "ENTERPRISE", "ops_per_day": 999999, "max_sessions": 9999,
        "markets": ["ercot", "sen", "mibel"], "org": "Enterprise License",
    },
}

# ============================================================
#  FastAPI App
# ============================================================
app = FastAPI(
    title=API_TITLE,
    version=VERSION,
    description=(
        "HJB-Optimal Grid Dispatch Optimization SaaS | PRIMEnergeia S.A.S.\n\n"
        "Mathematically provable optimal dispatch for ERCOT, SEN (Mexico), "
        "and MIBEL (Iberia) electricity markets."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
#  Models
# ============================================================
class DispatchRequest(BaseModel):
    market: str = Field(..., description="Target market: ercot, sen, or mibel")
    fleet_mw: float = Field(100.0, ge=1, le=10000, description="Fleet capacity (MW)")
    duration_hours: float = Field(24.0, ge=1, le=168, description="Optimization horizon (hours)")
    battery_mwh: Optional[float] = Field(None, ge=0, description="Battery storage capacity (MWh)")
    solar_mw: Optional[float] = Field(None, ge=0, description="Solar capacity (MW)")
    wind_mw: Optional[float] = Field(None, ge=0, description="Wind capacity (MW)")
    engine_type: str = Field("AICE", description="Engine type: AICE (NH₃), PEM (H₂), HYP (H₂ Turbine)")
    mission_profile: str = Field("Grid Peaking", description="Demand profile type")
    dt_hours: float = Field(0.25, ge=0.01, le=1.0, description="Timestep resolution (hours)")

class SessionCreate(BaseModel):
    name: str = Field("dispatch-session", description="Session name for tracking")
    market: str = Field("ercot", description="Target market")
    fleet_mw: float = Field(100.0, ge=1, le=10000, description="Fleet capacity (MW)")

class DispatchResponse(BaseModel):
    session_id: str
    market: str
    fleet_mw: float
    duration_hours: float
    total_fuel_kg: float
    avg_efficiency_pct: float
    baseline_fuel_kg: float
    fuel_savings_pct: float
    dispatch_cost_usd: float
    baseline_cost_usd: float
    savings_usd: float
    roi_multiple: float
    n_timesteps: int
    time_grid: List[float]
    power_trajectory_kw: List[float]
    load_trajectory_pct: List[float]
    efficiency_trajectory_pct: List[float]
    fuel_trajectory_kg: List[float]
    demand_profile_kw: List[float]
    solver_time_ms: float
    engine_type: str
    co2_emissions_kg: float

class SessionResponse(BaseModel):
    session_id: str
    name: str
    market: str
    fleet_mw: float
    created_at: str
    tier: str
    status: str

class MarketResponse(BaseModel):
    market_id: str
    name: str
    region: str
    frequency: float
    currency: str
    nodes: int
    zones: int
    description: str
    capabilities: List[str]


# ============================================================
#  Session Storage
# ============================================================
@dataclass
class DispatchSession:
    session_id: str
    name: str
    market: str
    fleet_mw: float
    created_at: str
    status: str  # "created", "running", "completed", "failed"
    last_result: Optional[dict] = None

sessions: dict[str, dict[str, DispatchSession]] = defaultdict(dict)
rate_log: dict[str, list] = defaultdict(list)


# ============================================================
#  Auth & Rate Limiting
# ============================================================
api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_config(api_key: str = Depends(api_key_header)):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key. Get one at primenergeia.com")
    return {"key": api_key, **API_KEYS[api_key]}

def check_rate_limit(api_key: str, tier_config: dict):
    now = time.time()
    cutoff = now - 86400
    rate_log[api_key] = [t for t in rate_log[api_key] if t > cutoff]
    if len(rate_log[api_key]) >= tier_config["ops_per_day"]:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: {tier_config['ops_per_day']} ops/day "
                f"for {tier_config['tier']} tier. Upgrade at primenergeia.com"
            )
        )
    rate_log[api_key].append(now)

def check_market_access(market: str, tier_config: dict):
    if market not in tier_config["markets"]:
        raise HTTPException(
            status_code=403,
            detail=f"Market '{market}' not available on {tier_config['tier']} tier. Upgrade at primenergeia.com"
        )


# ============================================================
#  Cost Model
# ============================================================
FUEL_COST = {
    "NH₃": 0.60,   # $/kg green ammonia
    "H₂": 5.00,    # $/kg green hydrogen
}

MARKET_ELECTRICITY_PRICE = {
    "ercot": 45.0,  # $/MWh average LMP
    "sen": 55.0,    # $/MWh (MXN converted)
    "mibel": 60.0,  # $/MWh (EUR converted)
}

def compute_dispatch_economics(result: "DispatchResult", market: str, fleet_mw: float):
    """Translate physical dispatch into financial metrics."""
    fuel_type = "NH₃" if "NH" in str(getattr(result, 'demand_profile', [''])) else "H₂"
    # Use fleet scaling factor
    scale = fleet_mw / 335.0  # Normalize to rated engine power

    fuel_cost_per_kg = FUEL_COST.get(fuel_type, 1.0)
    dispatch_cost = result.total_fuel_kg * scale * fuel_cost_per_kg
    baseline_cost = result.baseline_fuel_kg * scale * fuel_cost_per_kg
    savings = max(0, baseline_cost - dispatch_cost)

    # Annual projection
    hours_per_year = 8760
    annual_savings = savings * (hours_per_year / max(1, len(result.time_grid) * 0.25))

    return {
        "dispatch_cost_usd": round(dispatch_cost, 2),
        "baseline_cost_usd": round(baseline_cost, 2),
        "savings_usd": round(savings, 2),
        "annual_savings_usd": round(annual_savings, 2),
        "roi_multiple": round(annual_savings / 200000, 1) if annual_savings > 0 else 0,  # vs $200K license
    }


# ============================================================
#  Endpoints
# ============================================================

# --- Health ---
@app.get("/v1/health")
async def health():
    return {
        "status": "operational",
        "service": "PRIMEngine API",
        "version": VERSION,
        "hjb_solver": "active" if HJB_AVAILABLE else "unavailable",
        "grid_physics": "active" if GRID_PHYSICS_AVAILABLE else "unavailable",
        "markets": list(MARKETS.keys()),
        "timestamp": datetime.now().isoformat(),
        "company": "PRIMEnergeia S.A.S.",
    }


# --- Markets ---
@app.get("/v1/markets", response_model=List[MarketResponse])
async def list_markets(auth: dict = Depends(get_api_config)):
    return [
        MarketResponse(market_id=mid, **mdata)
        for mid, mdata in MARKETS.items()
        if mid in auth["markets"]
    ]


# --- Dispatch Optimization ---
@app.post("/v1/dispatch/optimize", response_model=DispatchResponse)
async def optimize_dispatch(req: DispatchRequest, auth: dict = Depends(get_api_config)):
    check_rate_limit(auth["key"], auth)
    check_market_access(req.market, auth)

    if not HJB_AVAILABLE:
        raise HTTPException(status_code=503, detail="HJB solver not available on this server")

    if req.market not in MARKETS:
        raise HTTPException(status_code=400, detail=f"Unknown market: {req.market}. Available: {list(MARKETS.keys())}")

    t_start = time.time()
    session_id = str(uuid.uuid4())[:12]

    # Generate demand profile scaled to fleet
    rated_kw = req.fleet_mw * 1000  # Convert MW to kW
    demand = generate_mission_profile(
        req.mission_profile, req.duration_hours,
        dt_h=req.dt_hours, rated_kw=rated_kw,
    )

    # Run HJB optimizer
    optimizer = EngineHJBDispatch(engine_type=req.engine_type)
    result = optimizer.optimize_dispatch(demand, dt_h=req.dt_hours)

    solver_ms = (time.time() - t_start) * 1000

    # Economics
    econ = compute_dispatch_economics(result, req.market, req.fleet_mw)

    return DispatchResponse(
        session_id=session_id,
        market=req.market,
        fleet_mw=req.fleet_mw,
        duration_hours=req.duration_hours,
        total_fuel_kg=round(float(result.total_fuel_kg), 2),
        avg_efficiency_pct=round(float(result.avg_efficiency_pct), 2),
        baseline_fuel_kg=round(float(result.baseline_fuel_kg), 2),
        fuel_savings_pct=round(float(result.fuel_savings_pct), 2),
        dispatch_cost_usd=econ["dispatch_cost_usd"],
        baseline_cost_usd=econ["baseline_cost_usd"],
        savings_usd=econ["savings_usd"],
        roi_multiple=econ["roi_multiple"],
        n_timesteps=len(result.time_grid),
        time_grid=[round(float(t), 3) for t in result.time_grid],
        power_trajectory_kw=[round(float(p), 1) for p in result.power_trajectory],
        load_trajectory_pct=[round(float(l), 1) for l in result.load_trajectory],
        efficiency_trajectory_pct=[round(float(e), 1) for e in result.efficiency_trajectory],
        fuel_trajectory_kg=[round(float(f), 3) for f in result.fuel_trajectory],
        demand_profile_kw=[round(float(d), 1) for d in result.demand_profile],
        solver_time_ms=round(solver_ms, 1),
        engine_type=req.engine_type,
        co2_emissions_kg=0.0,
    )


# --- Sessions ---
@app.post("/v1/dispatch/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreate, auth: dict = Depends(get_api_config)):
    key = auth["key"]
    check_market_access(req.market, auth)

    if len(sessions[key]) >= auth["max_sessions"]:
        raise HTTPException(
            status_code=403,
            detail=f"Max sessions ({auth['max_sessions']}) reached for {auth['tier']} tier."
        )

    session = DispatchSession(
        session_id=str(uuid.uuid4())[:12],
        name=req.name,
        market=req.market,
        fleet_mw=req.fleet_mw,
        created_at=datetime.now().isoformat(),
        status="created",
    )
    sessions[key][session.session_id] = session

    return SessionResponse(
        session_id=session.session_id,
        name=session.name,
        market=session.market,
        fleet_mw=session.fleet_mw,
        created_at=session.created_at,
        tier=auth["tier"],
        status=session.status,
    )


@app.get("/v1/dispatch/sessions/{session_id}/status")
async def session_status(session_id: str, auth: dict = Depends(get_api_config)):
    key = auth["key"]
    session = sessions.get(key, {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session.session_id,
        "name": session.name,
        "market": session.market,
        "fleet_mw": session.fleet_mw,
        "status": session.status,
        "created_at": session.created_at,
        "has_results": session.last_result is not None,
    }


@app.get("/v1/dispatch/sessions/{session_id}/results")
async def session_results(session_id: str, auth: dict = Depends(get_api_config)):
    key = auth["key"]
    session = sessions.get(key, {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if not session.last_result:
        raise HTTPException(status_code=404, detail="No results yet. Run an optimization first.")
    return session.last_result


@app.get("/v1/dispatch/sessions")
async def list_sessions(auth: dict = Depends(get_api_config)):
    key = auth["key"]
    result = []
    for sid, sess in sessions.get(key, {}).items():
        result.append({
            "session_id": sid, "name": sess.name, "market": sess.market,
            "fleet_mw": sess.fleet_mw, "status": sess.status,
            "created_at": sess.created_at,
        })
    return {"sessions": result, "tier": auth["tier"], "used": len(result), "max": auth["max_sessions"]}


@app.delete("/v1/dispatch/sessions/{session_id}")
async def delete_session(session_id: str, auth: dict = Depends(get_api_config)):
    key = auth["key"]
    if session_id not in sessions.get(key, {}):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    del sessions[key][session_id]
    return {"status": "deleted", "session_id": session_id}


# --- Grid Frequency Simulation ---
@app.post("/v1/grid/simulate")
async def simulate_grid(
    market: str = "ercot",
    duration_seconds: float = 10.0,
    control_gain: float = 500.0,
    auth: dict = Depends(get_api_config),
):
    """Run a grid frequency simulation with synthetic inertia control."""
    check_market_access(market, auth)

    if not GRID_PHYSICS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Grid physics engine not available")

    if market == "ercot":
        grid = ERCOTGridPhysics()
    elif market == "sen":
        grid = SENGridPhysics()
    elif market == "mibel":
        grid = MIBELGridPhysics()
    else:
        raise HTTPException(status_code=400, detail=f"Grid simulation not available for {market}")

    n_steps = int(duration_seconds / grid.dt)
    freq_history = []
    rocof_history = []
    control_history = []
    savings = 0.0

    for _ in range(min(n_steps, 5000)):
        error = grid.f_nom - grid.f_actual
        u_control = max(0, error * control_gain)
        f, dfdt = grid.step(u_control)

        freq_history.append(round(float(f), 6))
        rocof_history.append(round(float(dfdt), 6))
        control_history.append(round(float(u_control), 4))

        penalty_threshold = 49.96 if market == "mibel" else 59.97
        penalty_rate = 280000 if market == "mibel" else (300000 if market == "ercot" else 250000)
        if f < penalty_threshold:
            savings += abs(error) * penalty_rate

    return {
        "market": market,
        "duration_seconds": duration_seconds,
        "n_steps": len(freq_history),
        "frequency_hz": freq_history,
        "rocof": rocof_history,
        "control_signal": control_history,
        "frequency_stats": {
            "mean": round(float(np.mean(freq_history)), 6),
            "min": round(float(np.min(freq_history)), 6),
            "max": round(float(np.max(freq_history)), 6),
            "std": round(float(np.std(freq_history)), 6),
        },
        "penalties_avoided_usd": round(savings, 2),
    }


# --- Co-Optimization (DA/RT + Battery Degradation) ---
class CoOptRequest(BaseModel):
    market: str = Field("ercot", description="Target market: ercot, sen, or mibel")
    fleet_mw: float = Field(100.0, ge=1, le=10000, description="Fleet capacity (MW)")
    battery_mwh: float = Field(400.0, ge=0, le=20000, description="Battery storage (MWh)")
    hours: int = Field(24, ge=1, le=168, description="Optimization horizon (hours)")


@app.post("/v1/dispatch/cooptimize")
async def cooptimize_dispatch(req: CoOptRequest, auth: dict = Depends(get_api_config)):
    """Run day-ahead + real-time co-optimization with battery degradation tracking.

    Returns market-specific results including energy revenue, battery SOH,
    degradation cost, hourly strategy, and carbon/CEL credit tracking.
    """
    check_rate_limit(auth["key"], auth)
    check_market_access(req.market, auth)

    if not COOPT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Co-optimization engine not available")

    t_start = time.time()

    if req.market == "ercot":
        result = run_ercot_coopt(fleet_mw=req.fleet_mw, battery_mwh=req.battery_mwh, hours=req.hours)
        return {
            "market": "ercot", "currency": "USD", "hours": result.hours,
            "energy_revenue": result.energy_revenue_usd,
            "ancillary_revenue": result.ancillary_revenue_usd,
            "total_revenue": result.total_revenue_usd,
            "baseline_revenue": result.baseline_revenue_usd,
            "uplift_pct": result.uplift_pct,
            "degradation_cost": result.degradation_cost_usd,
            "net_profit": result.net_profit_usd,
            "battery_soh_start": result.battery_soh_start,
            "battery_soh_end": result.battery_soh_end,
            "dispatch_mw": [round(float(d), 1) for d in result.dispatch_mw],
            "battery_soc": [round(float(s), 4) for s in result.battery_soc],
            "strategy": result.strategy,
            "solver_time_ms": round((time.time() - t_start) * 1000, 1),
        }

    elif req.market == "sen":
        result = run_sen_coopt(fleet_mw=req.fleet_mw, battery_mwh=req.battery_mwh, hours=req.hours)
        return {
            "market": "sen", "currency": "MXN", "hours": result.hours,
            "energy_revenue_mxn": result.energy_revenue_mxn,
            "cel_revenue_mxn": result.cel_revenue_mxn,
            "total_revenue_mxn": result.total_revenue_mxn,
            "total_revenue_usd": result.total_revenue_usd,
            "baseline_revenue_mxn": result.baseline_revenue_mxn,
            "uplift_pct": result.uplift_pct,
            "degradation_cost_mxn": result.degradation_cost_mxn,
            "net_profit_usd": result.net_profit_usd,
            "battery_soh_start": result.battery_soh_start,
            "battery_soh_end": result.battery_soh_end,
            "dispatch_mw": [round(float(d), 1) for d in result.dispatch_mw],
            "battery_soc": [round(float(s), 4) for s in result.battery_soc],
            "strategy": result.strategy,
            "region": result.region,
            "solver_time_ms": round((time.time() - t_start) * 1000, 1),
        }

    elif req.market == "mibel":
        result = run_mibel_coopt(fleet_mw=req.fleet_mw, battery_mwh=req.battery_mwh, hours=req.hours)
        return {
            "market": "mibel", "currency": "EUR", "hours": result.hours,
            "energy_revenue_eur": result.energy_revenue_eur,
            "carbon_savings_eur": result.carbon_savings_eur,
            "total_revenue_eur": result.total_revenue_eur,
            "baseline_revenue_eur": result.baseline_revenue_eur,
            "uplift_pct": result.uplift_pct,
            "degradation_cost_eur": result.degradation_cost_eur,
            "net_profit_eur": result.net_profit_eur,
            "co2_displaced_tonnes": result.co2_displaced_tonnes,
            "battery_soh_start": result.battery_soh_start,
            "battery_soh_end": result.battery_soh_end,
            "dispatch_mw": [round(float(d), 1) for d in result.dispatch_mw],
            "battery_soc": [round(float(s), 4) for s in result.battery_soc],
            "strategy": result.strategy,
            "zone": result.zone,
            "solver_time_ms": round((time.time() - t_start) * 1000, 1),
        }

    raise HTTPException(status_code=400, detail=f"Unknown market: {req.market}")


# ============================================================
#  Main
# ============================================================
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"PRIMEngine API v{VERSION} — Grid Dispatch Optimization")
    print(f"PRIMEnergeia S.A.S. | Grid Optimization Division")
    print(f"Markets: {', '.join(MARKETS.keys())}")
    print(f"HJB Solver: {'Active' if HJB_AVAILABLE else 'Unavailable'}")
    print(f"Grid Physics: {'Active' if GRID_PHYSICS_AVAILABLE else 'Unavailable'}")
    print(f"Docs: http://localhost:8081/docs")
    uvicorn.run(app, host="127.0.0.1", port=8081)
"""PRIMEngine API — Grid Dispatch Optimization SaaS"""
