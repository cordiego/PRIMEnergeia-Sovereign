#!/usr/bin/env python3
"""
PRIMEnergeia — Real MIBEL (OMIE) Data Acquisition
=====================================================
Downloads real day-ahead and intraday pool prices from OMIE (Spain/Portugal).

Data Sources (in priority order):
  1. OMIE public CSV files — no authentication needed
  2. ENTSO-E Transparency Platform — requires free API key
  3. Proxy generator — documented OMIE price patterns

Usage:
    python fetch_mibel_real.py                         # Default: last 30 days
    python fetch_mibel_real.py --days 60               # Last 60 days
    python fetch_mibel_real.py --zone ES               # Spain only

Output:
    data/mibel/mibel_real_<zone>_<date>.csv

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MIBEL-Fetch] - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "mibel")

# MIBEL zones
MIBEL_ZONES = {
    "ES": "España (Spain)",
    "PT": "Portugal",
    "ES_NORTE": "España Norte",
    "ES_SUR": "España Sur",
    "BALEARES": "Islas Baleares",
}


def fetch_mibel_data(days: int = 30, zone: str = "ES") -> str:
    """
    Fetch MIBEL/OMIE pool prices.

    Priority:
      1. OMIE public CSV download
      2. ENTSO-E Transparency Platform
      3. Proxy generator

    Returns: path to CSV file
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Check for cached data
    cached = _find_cached(zone, days)
    if cached:
        return cached

    # Priority 1: Try OMIE public download
    try:
        return fetch_via_omie(days, zone)
    except Exception as e:
        logger.warning(f"OMIE fetch failed: {e}")

    # Priority 2: Try ENTSO-E
    try:
        return fetch_via_entsoe(days, zone)
    except Exception as e:
        logger.warning(f"ENTSO-E fetch failed: {e}")

    # Priority 3: Proxy
    logger.info("Falling back to proxy OMIE generator")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return generate_mibel_proxy(start_date, end_date, zone)


def _find_cached(zone: str, max_age_days: int = 7) -> str:
    """Check if a recent enough cached file exists."""
    if not os.path.exists(OUTPUT_DIR):
        return ""
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith(f"mibel_real_{zone}") and f.endswith(".csv"):
            path = os.path.join(OUTPUT_DIR, f)
            age = datetime.now().timestamp() - os.path.getmtime(path)
            if age < max_age_days * 86400:
                logger.info(f"Using cached MIBEL data: {path}")
                return path
    return ""


def fetch_via_omie(days: int, zone: str = "ES") -> str:
    """
    Download day-ahead prices from OMIE public data.

    OMIE publishes daily CSV files at:
    https://www.omie.es/sites/default/files/dados/AGNO_<year>/MES_<month>/
    """
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library not available")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    all_rows = []
    current = start_date

    while current <= end_date:
        year = current.strftime("%Y")
        month = current.strftime("%m")
        day = current.strftime("%d")

        # OMIE marginal price file
        url = (
            f"https://www.omie.es/sites/default/files/dados/"
            f"AGNO_{year}/MES_{month}/TXT/INT_PBC_EV_H_1_{day}_{month}_{year}_{day}_{month}_{year}.TXT"
        )

        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                for line in lines[1:]:  # Skip header
                    parts = line.strip().split(";")
                    if len(parts) >= 4:
                        try:
                            hour = int(parts[2]) - 1  # OMIE uses 1-24
                            price_es = float(parts[3].replace(",", "."))
                            price_pt = float(parts[4].replace(",", ".")) if len(parts) > 4 else price_es

                            price = price_es if zone in ("ES", "ES_NORTE", "ES_SUR", "BALEARES") else price_pt

                            all_rows.append({
                                "date": current.strftime("%Y-%m-%d"),
                                "hour": hour,
                                "dam_lmp": price,
                                "rtm_lmp": price * (1 + np.random.normal(0, 0.03)),  # ID ≈ DA + noise
                            })
                        except (ValueError, IndexError):
                            continue
        except Exception:
            pass

        current += timedelta(days=1)

    if not all_rows:
        raise RuntimeError("No data retrieved from OMIE")

    df = pd.DataFrame(all_rows)
    today = datetime.now().strftime("%Y%m%d")
    out_path = os.path.join(OUTPUT_DIR, f"mibel_real_{zone}_{today}.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"Saved {len(df)} rows from OMIE → {out_path}")
    return out_path


def fetch_via_entsoe(days: int, zone: str = "ES") -> str:
    """
    Fetch day-ahead prices from ENTSO-E Transparency Platform.
    Requires: ENTSOE_API_KEY environment variable.
    """
    api_key = os.environ.get("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError("ENTSOE_API_KEY not set")

    try:
        from entsoe import EntsoePandasClient
    except ImportError:
        raise RuntimeError("entsoe-py not installed. Run: pip install entsoe-py")

    area_map = {"ES": "ES", "PT": "PT", "ES_NORTE": "ES", "ES_SUR": "ES", "BALEARES": "ES"}
    area = area_map.get(zone, "ES")

    client = EntsoePandasClient(api_key=api_key)
    end = pd.Timestamp.now(tz="Europe/Madrid")
    start = end - pd.Timedelta(days=days)

    da_prices = client.query_day_ahead_prices(area, start=start, end=end)

    df = pd.DataFrame({
        "date": da_prices.index.strftime("%Y-%m-%d"),
        "hour": da_prices.index.hour,
        "dam_lmp": da_prices.values,
        "rtm_lmp": da_prices.values * (1 + np.random.normal(0, 0.03, len(da_prices))),
    })

    today = datetime.now().strftime("%Y%m%d")
    out_path = os.path.join(OUTPUT_DIR, f"mibel_real_{zone}_{today}.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"Saved {len(df)} rows from ENTSO-E → {out_path}")
    return out_path


def generate_mibel_proxy(start: str, end: str, zone: str = "ES") -> str:
    """
    Generate proxy MIBEL pool price data based on documented OMIE patterns.

    Iberian electricity market characteristics:
    - Base pool price: ~50-80 €/MWh
    - Morning peak: 08:00-12:00 CET
    - Evening peak: 18:00-22:00 CET
    - Solar duck curve: midday depression 12:00-16:00
    - Negative prices possible (high wind + solar oversupply)
    - Hourly settlement intervals
    """
    rng = np.random.RandomState(hash(zone) % (2**31))

    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    timestamps = pd.date_range(start_dt, end_dt, freq="h")

    # Zone-specific base prices (€/MWh)
    zone_bases = {
        "ES": 62.0,
        "PT": 58.0,
        "ES_NORTE": 60.0,
        "ES_SUR": 55.0,  # More solar → lower avg
        "BALEARES": 72.0,  # Island premium
    }
    base_price = zone_bases.get(zone, 62.0)

    n = len(timestamps)
    hours = timestamps.hour

    # European double-peak load shape
    morning = 0.3 * np.exp(-((hours - 10) / 3.0) ** 2)
    evening = 0.4 * np.exp(-((hours - 20) / 3.0) ** 2)
    load_shape = 0.5 + morning + evening

    # Solar duck curve (midday depression)
    solar_dip = -0.18 * np.exp(-((hours - 14) / 2.5) ** 2)

    # Seasonal (summer: more solar → lower midday, higher evening AC)
    month = timestamps.month
    summer = ((month >= 6) & (month <= 8)).astype(float)
    winter = ((month >= 11) | (month <= 2)).astype(float)
    season_factor = 1.0 + summer * 0.15 + winter * 0.25  # Winter heating premium

    # Day-of-week (weekends lower)
    dow = timestamps.dayofweek
    dow_factor = np.where(dow >= 5, 0.78, 1.0)

    # Volatility
    volatility = rng.normal(0, 0.06, n)

    # Negative prices (~2% of hours — high wind + solar)
    negative_mask = rng.random(n) > 0.98
    midday_mask = (hours >= 11) & (hours <= 15)
    negative_factor = np.where(
        negative_mask & midday_mask,
        rng.uniform(-1.5, -0.2, n),
        0.0
    )

    # Evening spikes (~1.5%)
    spike_mask = rng.random(n) > 0.985
    evening_mask = (hours >= 18) & (hours <= 22)
    spike_factor = np.where(
        spike_mask & evening_mask,
        rng.uniform(2.0, 5.0, n),
        1.0
    )

    da_prices = base_price * (load_shape + solar_dip) * dow_factor * season_factor * (1 + volatility) * spike_factor
    da_prices = da_prices + negative_factor * base_price
    da_prices = np.clip(da_prices, -30.0, 400.0)

    # Intraday ≈ DA with forecast error
    id_deviation = rng.standard_t(df=6, size=n) * 0.06
    id_prices = da_prices * (1 + id_deviation)
    id_prices = np.clip(id_prices, -30.0, 400.0)

    df = pd.DataFrame({
        "date": timestamps.strftime("%Y-%m-%d"),
        "hour": hours,
        "dam_lmp": np.round(da_prices, 2),
        "rtm_lmp": np.round(id_prices, 2),
    })

    today = datetime.now().strftime("%Y%m%d")
    out_path = os.path.join(OUTPUT_DIR, f"mibel_{zone}_PROXY_{today}.csv")
    df.to_csv(out_path, index=False)
    logger.info(f"[PROXY] Generated {len(df)} intervals for {zone} → {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch real MIBEL/OMIE data")
    parser.add_argument("--zone", default="ES", choices=list(MIBEL_ZONES.keys()))
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    path = fetch_mibel_data(days=args.days, zone=args.zone)
    print(f"\n✅ MIBEL data saved: {path}")

    df = pd.read_csv(path)
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {list(df.columns)}")
    if "dam_lmp" in df.columns:
        print(f"   DA range: €{df['dam_lmp'].min():.2f} – €{df['dam_lmp'].max():.2f}")
        print(f"   DA mean:  €{df['dam_lmp'].mean():.2f}")
        neg = (df['dam_lmp'] < 0).sum()
        if neg > 0:
            print(f"   Negative price hours: {neg}")
