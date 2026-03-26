#!/usr/bin/env python3
"""
PRIMEnergeia — Real SEN (CENACE) Data Acquisition
=====================================================
Downloads real Precios Marginales Locales (PML) from Mexico's CENACE.

Data Sources (in priority order):
  1. Local nodo CSVs (data/nodos/data_<node_id>.csv) — pre-downloaded
  2. CENACE SIM API — public endpoint for PML data
  3. Proxy generator — documented CENACE PML patterns

Usage:
    python fetch_sen_real.py                           # Default: node 07-HER-230
    python fetch_sen_real.py --node 04-MTY-400         # Monterrey
    python fetch_sen_real.py --node 05-VZA-400         # VZA-400 (validated)
    python fetch_sen_real.py --days 30                 # Last 30 days

Output:
    data/nodos/data_<node_id>.csv  (or proxy CSV)

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SEN-Fetch] - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
NODOS_DIR = os.path.join(PROJECT_ROOT, "data", "nodos")

# Available SEN nodes with pre-downloaded data
SEN_NODES = {
    "07-HER-230": "Hermosillo (Noroeste)",
    "05-VZA-400": "VZA-400 — Validated ($231K rescued)",
    "04-MTY-400": "Monterrey (Noreste)",
    "03-GDL-400": "Guadalajara (Occidental)",
    "01-QRO-230": "Querétaro (Central)",
    "02-OAX-230": "Oaxaca (Oriental)",
    "10-MER-230": "Mérida (Peninsular)",
    "08-TIJ-230": "Tijuana (Baja California)",
    "09-LAP-115": "La Paz (BCS)",
    "06-SLP-400": "San Luis Potosí",
    "05-CHI-400": "Chihuahua (Norte)",
    "05-LAG-230": "La Laguna (Norte)",
    "07-CUL-230": "Culiacán (Noroeste)",
    "08-ENS-230": "Ensenada (BC)",
    "08-MXL-230": "Mexicali (BC)",
    "04-SAL-400": "Saltillo (Noreste)",
    "04-TAM-230": "Tampico (Noreste)",
    "05-DGO-230": "Durango (Norte)",
    "05-JRZ-230": "Juárez (Norte)",
    "03-COL-115": "Colima (Occidental)",
    "03-MAN-400": "Manzanillo (Occidental)",
    "03-AGS-230": "Aguascalientes (Occidental)",
    "02-PUE-400": "Puebla (Oriental)",
    "02-TEH-400": "Tehuacán (Oriental)",
    "02-VER-230": "Veracruz (Oriental)",
    "01-TUL-400": "Tula (Central)",
    "07-NAV-230": "Navojoa (Noroeste)",
    "07-GUY-230": "Guaymas (Noroeste)",
    "07-CUM-115": "Ciudad Obregón (Noroeste)",
    "10-CAN-230": "Cancún (Peninsular)",
}


def fetch_sen_data(node_id: str = "07-HER-230", days: int = 30) -> str:
    """
    Fetch SEN PML data for a specific node.

    Priority:
      1. Local nodo CSV (pre-downloaded real data)
      2. CENACE SIM API (if available)
      3. Proxy generator (fallback)

    Returns: path to CSV file
    """
    os.makedirs(NODOS_DIR, exist_ok=True)

    # Priority 1: Local nodo CSV
    local_path = os.path.join(NODOS_DIR, f"data_{node_id}.csv")
    if os.path.exists(local_path):
        logger.info(f"Found local nodo data: {local_path}")
        # Verify file has data
        try:
            df = pd.read_csv(local_path)
            if len(df) > 10:
                logger.info(f"  → {len(df)} rows, columns: {list(df.columns)}")
                return local_path
        except Exception as e:
            logger.warning(f"  → Local file exists but couldn't read: {e}")

    # Priority 2: Try CENACE SIM API
    try:
        return fetch_via_cenace_api(node_id, days)
    except Exception as e:
        logger.warning(f"CENACE API fetch failed: {e}")

    # Priority 3: Proxy generator
    logger.info("Falling back to proxy PML generator")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return generate_sen_proxy(start_date, end_date, node_id)


def fetch_via_cenace_api(node_id: str, days: int = 30) -> str:
    """
    Attempt to fetch PML data from CENACE SIM public endpoint.
    Note: CENACE API availability varies; may require periodic updates.
    """
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library not available for CENACE API fetch")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # CENACE SIM REST endpoint for PML data
    base_url = "https://ws01.cenace.gob.mx:8082/SWPML/SIM"
    region = node_id.split("-")[0]  # e.g., "07" from "07-HER-230"

    url = (
        f"{base_url}/{region}/MDA/{node_id}/"
        f"{start_date.strftime('%Y/%m/%d')}/{end_date.strftime('%Y/%m/%d')}/JSON"
    )

    logger.info(f"Fetching from CENACE SIM: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "Resultados" not in data:
        raise ValueError("Unexpected CENACE response format")

    rows = []
    for result in data["Resultados"]:
        for val in result.get("Valores", []):
            rows.append({
                "timestamp": val.get("fecha", ""),
                "Actual_MW": 0.0,
                "Theoretical_MW": 0.0,
                "PML_USD": float(val.get("pml", 0)) / 17.5,  # MXN→USD
            })

    df = pd.DataFrame(rows)
    out_path = os.path.join(NODOS_DIR, f"data_{node_id}_live.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"Saved {len(df)} rows → {out_path}")
    return out_path


def generate_sen_proxy(start: str, end: str, node_id: str = "07-HER-230") -> str:
    """
    Generate proxy SEN PML data based on documented CENACE price patterns.

    Mexican electricity market characteristics:
    - Base PML: ~800-1200 MXN/MWh ($45-70 USD/MWh)
    - Afternoon peaks: 14:00-20:00 CT (AC load)
    - Occasional congestion spikes: up to 5000 MXN ($285 USD)
    - 15-minute settlement intervals
    """
    rng = np.random.RandomState(hash(node_id) % (2**31))

    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    timestamps = pd.date_range(start_dt, end_dt, freq="15min")

    # Regional base PML (USD/MWh)
    region_bases = {
        "01": 42.0,  # Central (QRO, TUL)
        "02": 40.0,  # Oriental (OAX, PUE, TEH, VER)
        "03": 43.0,  # Occidental (GDL, AGS, COL, MAN)
        "04": 48.0,  # Noreste (MTY, SAL, TAM) - industrial load
        "05": 45.0,  # Norte (CHI, DGO, JRZ, LAG, VZA)
        "06": 44.0,  # SLP
        "07": 46.0,  # Noroeste (HER, CUL, CUM, GUY, NAV)
        "08": 50.0,  # Baja California (TIJ, ENS, MXL) - islanded
        "09": 55.0,  # BCS (LAP) - islanded, diesel-heavy
        "10": 41.0,  # Peninsular (CAN, MER)
    }
    region_code = node_id.split("-")[0]
    base_pml = region_bases.get(region_code, 45.0)

    n = len(timestamps)
    hours = timestamps.hour + timestamps.minute / 60.0

    # Mexican load shape: peaks at 14-20h (afternoon/evening heat)
    load_shape = 0.55 + 0.45 * np.exp(-((hours - 17) / 5) ** 2)

    # Day-of-week effect (weekends lower)
    dow = timestamps.dayofweek
    dow_factor = np.where(dow >= 5, 0.82, 1.0)

    # Seasonal variation (summer premium for AC)
    month = timestamps.month
    season = np.where((month >= 5) & (month <= 9), 1.25, 1.0)

    # Random volatility
    volatility = rng.normal(0, 0.08, n)

    # Congestion spikes (~3% of intervals)
    spike_mask = rng.random(n) > 0.97
    afternoon_mask = (hours >= 14) & (hours <= 20)
    spike_factor = np.where(
        spike_mask & afternoon_mask,
        rng.uniform(3.0, 12.0, n),
        1.0
    )

    pml_usd = base_pml * load_shape * dow_factor * season * (1 + volatility) * spike_factor
    pml_usd = np.clip(pml_usd, 15.0, 300.0)

    # Generate actual/theoretical MW (solar-like profile)
    solar_peak = 100.0 * np.exp(-((hours - 12.5) / 3.5) ** 2)
    solar_peak = np.where((hours < 6) | (hours > 18.5), 0, solar_peak)
    actual_mw = solar_peak * (0.85 + rng.normal(0, 0.08, n))
    actual_mw = np.clip(actual_mw, 0, 120)
    theoretical_mw = solar_peak * (0.95 + rng.normal(0, 0.03, n))
    theoretical_mw = np.clip(theoretical_mw, 0, 120)
    theoretical_mw = np.maximum(theoretical_mw, actual_mw)

    df = pd.DataFrame({
        "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
        "Actual_MW": np.round(actual_mw, 2),
        "Theoretical_MW": np.round(theoretical_mw, 2),
        "PML_USD": np.round(pml_usd, 2),
    })

    out_path = os.path.join(NODOS_DIR, f"data_{node_id}_PROXY.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated {len(df)} intervals for {node_id} → {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch real SEN PML data")
    parser.add_argument("--node", default="07-HER-230", help="SEN node ID")
    parser.add_argument("--days", type=int, default=30, help="Days of history")
    args = parser.parse_args()

    path = fetch_sen_data(node_id=args.node, days=args.days)
    print(f"\n✅ SEN data saved: {path}")

    df = pd.read_csv(path)
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {list(df.columns)}")
    if "PML_USD" in df.columns:
        print(f"   PML range: ${df['PML_USD'].min():.2f} – ${df['PML_USD'].max():.2f}")
        print(f"   PML mean:  ${df['PML_USD'].mean():.2f}")
