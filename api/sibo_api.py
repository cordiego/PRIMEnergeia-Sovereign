"""
SIBO API — Sol-Ink Bayesian Optimizer SaaS Endpoint
=====================================================
FastAPI wrapper for the SIBO perovskite optimization engine.
Enables SaaS licensing via API key authentication with tiered
rate limiting.

PRIMEnergeia S.A.S. — Granas Division

Endpoints:
    POST /v1/sessions          — Create new optimization session
    POST /v1/sessions/{id}/ask — Get next suggested recipe
    POST /v1/sessions/{id}/tell — Report lab result
    GET  /v1/sessions/{id}/status — Session progress
    GET  /v1/sessions/{id}/best   — Best recipe found
    GET  /v1/sessions/{id}/export — Export experiment log
    GET  /v1/health               — Health check

Authentication:
    Header: X-API-Key: <key>

Tiers:
    STARTER  — 100 asks/day, 1 session
    PRO      — 1,000 asks/day, 10 sessions
    ENTERPRISE — Unlimited
"""

import os
import uuid
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from collections import defaultdict

import numpy as np
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ─── Lazy imports for optimizer ───
try:
    import joblib
except ImportError:
    import pickle as joblib
    joblib.dump = lambda obj, path: open(path, 'wb').write(__import__('pickle').dumps(obj))
    joblib.load = lambda path: __import__('pickle').loads(open(path, 'rb').read())

try:
    from skopt import Optimizer
    from skopt.space import Real, Integer
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False


# ============================================================
#  Configuration
# ============================================================
VERSION = "1.0.0"
API_TITLE = "SIBO API — Sol-Ink Bayesian Optimizer"
DATA_DIR = os.environ.get("SIBO_DATA_DIR", os.path.expanduser("~/.sibo_api"))

# Search Space (4D — per SIBO Spec §3.1)
SEARCH_SPACE = [
    Real(0.8, 1.5, name="molar_conc", prior="uniform"),
    Real(0.0, 1.0, name="solvent_ratio", prior="uniform"),
    Real(0.0, 5.0, name="additive_loading", prior="uniform"),
    Integer(1000, 6000, name="spin_speed"),
] if SKOPT_AVAILABLE else []

PARAM_NAMES = ["molar_conc", "solvent_ratio", "additive_loading", "spin_speed"]
MAX_STAGNATION = 10

# API Key tiers
API_KEYS = {
    os.environ.get("SIBO_API_KEY_STARTER", "sibo_starter_key"): {
        "tier": "STARTER", "asks_per_day": 100, "max_sessions": 1,
        "org": "Trial User",
    },
    os.environ.get("SIBO_API_KEY_PRO", "sibo_pro_key"): {
        "tier": "PRO", "asks_per_day": 1000, "max_sessions": 10,
        "org": "Pro License",
    },
    os.environ.get("SIBO_API_KEY_ENTERPRISE", "sibo_enterprise_key"): {
        "tier": "ENTERPRISE", "asks_per_day": 999999, "max_sessions": 999,
        "org": "Enterprise License",
    },
}


# ============================================================
#  FastAPI App
# ============================================================
app = FastAPI(
    title=API_TITLE,
    version=VERSION,
    description="Bayesian Optimization SaaS for Perovskite Solar Cell Fabrication | PRIMEnergeia S.A.S.",
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
class SessionCreate(BaseModel):
    name: str = Field("default", description="Session name for tracking")
    search_space: Optional[dict] = Field(None, description="Custom search space overrides (optional)")

class TellRequest(BaseModel):
    molar_conc: float = Field(..., ge=0.8, le=1.5, description="Molar concentration (M)")
    solvent_ratio: float = Field(..., ge=0.0, le=1.0, description="DMF:DMSO ratio")
    additive_loading: float = Field(..., ge=0.0, le=5.0, description="Additive vol%")
    spin_speed: int = Field(..., ge=1000, le=6000, description="Spin speed (RPM)")
    pce: float = Field(..., ge=0.0, le=35.0, description="Measured PCE (%)")

class RecipeResponse(BaseModel):
    molar_conc: float
    solvent_ratio: float
    additive_loading: float
    spin_speed: int
    iteration: int
    inference_ms: float
    acquisition: str = "Expected Improvement"
    kernel: str = "Matern 5/2"

class SessionResponse(BaseModel):
    session_id: str
    name: str
    created_at: str
    tier: str

class StatusResponse(BaseModel):
    session_id: str
    name: str
    iteration: int
    observations: int
    best_pce: Optional[float]
    best_recipe: Optional[dict]
    pce_range: Optional[list]
    pce_mean: Optional[float]
    pce_std: Optional[float]
    stagnation: str
    created_at: str

class TellResponse(BaseModel):
    status: str
    iteration: int
    pce: float
    is_new_best: bool
    best_pce: float
    improvement: Optional[float]
    stagnation: str


# ============================================================
#  Session Storage
# ============================================================
class SIBOSession:
    """In-memory optimizer session."""

    def __init__(self, name: str):
        self.session_id = str(uuid.uuid4())[:12]
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.iteration = 0
        self.X_observed = []
        self.Y_observed = []
        self.best_pce = -np.inf
        self.best_recipe = None
        self.n_stagnant = 0

        if SKOPT_AVAILABLE:
            self.optimizer = Optimizer(
                dimensions=SEARCH_SPACE,
                base_estimator="GP",
                acq_func="EI",
                acq_func_kwargs={"xi": 0.01},
                n_initial_points=5,
                random_state=42,
            )
        else:
            self.optimizer = None


# Session store: api_key -> {session_id: SIBOSession}
sessions: dict[str, dict[str, SIBOSession]] = defaultdict(dict)

# Rate limiting: api_key -> [(timestamp, ...)]
rate_log: dict[str, list] = defaultdict(list)


# ============================================================
#  Auth & Rate Limiting
# ============================================================
api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_config(api_key: str = Depends(api_key_header)):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"key": api_key, **API_KEYS[api_key]}

def check_rate_limit(api_key: str, tier_config: dict):
    now = time.time()
    cutoff = now - 86400  # 24h window
    rate_log[api_key] = [t for t in rate_log[api_key] if t > cutoff]

    if len(rate_log[api_key]) >= tier_config["asks_per_day"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {tier_config['asks_per_day']} asks/day for {tier_config['tier']} tier. Upgrade at primenergeia.com"
        )
    rate_log[api_key].append(now)


# ============================================================
#  Endpoints
# ============================================================

@app.get("/v1/health")
async def health():
    return {
        "status": "operational",
        "service": "SIBO API",
        "version": VERSION,
        "engine": "Gaussian Process (Matern 5/2)" if SKOPT_AVAILABLE else "UNAVAILABLE",
        "timestamp": datetime.now().isoformat(),
        "company": "PRIMEnergeia S.A.S.",
    }


@app.post("/v1/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreate, auth: dict = Depends(get_api_config)):
    key = auth["key"]

    if len(sessions[key]) >= auth["max_sessions"]:
        raise HTTPException(
            status_code=403,
            detail=f"Max sessions ({auth['max_sessions']}) reached for {auth['tier']} tier. Upgrade at primenergeia.com"
        )

    if not SKOPT_AVAILABLE:
        raise HTTPException(status_code=503, detail="scikit-optimize not installed on server")

    session = SIBOSession(name=req.name)
    sessions[key][session.session_id] = session

    return SessionResponse(
        session_id=session.session_id,
        name=session.name,
        created_at=session.created_at,
        tier=auth["tier"],
    )


def _get_session(session_id: str, auth: dict) -> SIBOSession:
    key = auth["key"]
    session = sessions.get(key, {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@app.post("/v1/sessions/{session_id}/ask", response_model=RecipeResponse)
async def ask(session_id: str, auth: dict = Depends(get_api_config)):
    check_rate_limit(auth["key"], auth)
    session = _get_session(session_id, auth)

    t_start = time.time()

    if session.n_stagnant >= MAX_STAGNATION:
        point = [
            float(np.random.uniform(0.8, 1.5)),
            float(np.random.uniform(0.0, 1.0)),
            float(np.random.uniform(0.0, 5.0)),
            int(np.random.randint(1000, 6001)),
        ]
    else:
        point = session.optimizer.ask()

    point[3] = int(round(point[3]))
    elapsed_ms = (time.time() - t_start) * 1000

    return RecipeResponse(
        molar_conc=round(float(point[0]), 4),
        solvent_ratio=round(float(point[1]), 4),
        additive_loading=round(float(point[2]), 4),
        spin_speed=int(point[3]),
        iteration=session.iteration + 1,
        inference_ms=round(elapsed_ms, 1),
    )


@app.post("/v1/sessions/{session_id}/tell", response_model=TellResponse)
async def tell(session_id: str, req: TellRequest, auth: dict = Depends(get_api_config)):
    session = _get_session(session_id, auth)

    params = [req.molar_conc, req.solvent_ratio, req.additive_loading, req.spin_speed]

    # Update optimizer
    session.optimizer.tell(params, -req.pce)
    session.X_observed.append(params[:])
    session.Y_observed.append(req.pce)
    session.iteration += 1

    is_new_best = False
    improvement = None

    if req.pce > session.best_pce:
        improvement = float(req.pce - session.best_pce) if session.best_pce > -np.inf else float(req.pce)
        session.best_pce = req.pce
        session.best_recipe = params[:]
        session.n_stagnant = 0
        is_new_best = True
    else:
        session.n_stagnant += 1

    return TellResponse(
        status="ok",
        iteration=session.iteration,
        pce=req.pce,
        is_new_best=is_new_best,
        best_pce=float(session.best_pce),
        improvement=improvement,
        stagnation=f"{session.n_stagnant}/{MAX_STAGNATION}",
    )


@app.get("/v1/sessions/{session_id}/status", response_model=StatusResponse)
async def status(session_id: str, auth: dict = Depends(get_api_config)):
    session = _get_session(session_id, auth)

    best_recipe = None
    if session.best_recipe:
        best_recipe = {
            name: round(val, 4) if isinstance(val, float) else val
            for name, val in zip(PARAM_NAMES, session.best_recipe)
        }

    pce_range = None
    pce_mean = None
    pce_std = None
    if session.Y_observed:
        pce_range = [round(min(session.Y_observed), 4), round(max(session.Y_observed), 4)]
        pce_mean = round(float(np.mean(session.Y_observed)), 4)
        pce_std = round(float(np.std(session.Y_observed)), 4)

    return StatusResponse(
        session_id=session.session_id,
        name=session.name,
        iteration=session.iteration,
        observations=len(session.Y_observed),
        best_pce=round(float(session.best_pce), 4) if session.best_pce > -np.inf else None,
        best_recipe=best_recipe,
        pce_range=pce_range,
        pce_mean=pce_mean,
        pce_std=pce_std,
        stagnation=f"{session.n_stagnant}/{MAX_STAGNATION}",
        created_at=session.created_at,
    )


@app.get("/v1/sessions/{session_id}/best")
async def best(session_id: str, auth: dict = Depends(get_api_config)):
    session = _get_session(session_id, auth)

    if not session.best_recipe:
        raise HTTPException(status_code=404, detail="No observations yet")

    return {
        "best_pce": round(float(session.best_pce), 4),
        "recipe": {
            name: round(val, 4) if isinstance(val, float) else val
            for name, val in zip(PARAM_NAMES, session.best_recipe)
        },
        "iteration": session.iteration,
        "observations": len(session.Y_observed),
    }


@app.get("/v1/sessions/{session_id}/export")
async def export(session_id: str, fmt: str = "json", auth: dict = Depends(get_api_config)):
    session = _get_session(session_id, auth)

    if not session.Y_observed:
        raise HTTPException(status_code=404, detail="No observations to export")

    records = []
    for i, (x, y) in enumerate(zip(session.X_observed, session.Y_observed)):
        records.append({
            "iteration": i + 1,
            "molar_conc": round(x[0], 4),
            "solvent_ratio": round(x[1], 4),
            "additive_loading": round(x[2], 4),
            "spin_speed": x[3],
            "pce": round(y, 4),
        })

    return {"experiments": records, "total": len(records)}


@app.get("/v1/sessions")
async def list_sessions(auth: dict = Depends(get_api_config)):
    key = auth["key"]
    result = []
    for sid, sess in sessions.get(key, {}).items():
        result.append({
            "session_id": sid,
            "name": sess.name,
            "iteration": sess.iteration,
            "best_pce": round(float(sess.best_pce), 4) if sess.best_pce > -np.inf else None,
            "created_at": sess.created_at,
        })
    return {
        "sessions": result,
        "tier": auth["tier"],
        "max_sessions": auth["max_sessions"],
        "used": len(result),
    }


@app.delete("/v1/sessions/{session_id}")
async def delete_session(session_id: str, auth: dict = Depends(get_api_config)):
    key = auth["key"]
    if session_id not in sessions.get(key, {}):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    del sessions[key][session_id]
    return {"status": "deleted", "session_id": session_id}


# ============================================================
#  Main
# ============================================================
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"SIBO API v{VERSION} — Sol-Ink Bayesian Optimizer")
    print(f"PRIMEnergeia S.A.S. | Granas Division")
    print(f"Docs: http://localhost:8080/docs")
    uvicorn.run(app, host="127.0.0.1", port=8080)
