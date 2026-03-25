#!/usr/bin/env python3
"""
PRIMEnergeia — Real ERCOT Data Acquisition
=============================================
Downloads REAL settlement point prices from ERCOT.

Data Sources (in priority order):
  1. gridstatus library (pip install gridstatus) — cleanest API
  2. Direct ERCOT public CSV download — no authentication needed
  3. Offline mode — uses cached data if available

Usage:
    python fetch_ercot_real.py                        # Default: last 7 days
    python fetch_ercot_real.py --days 30              # Last 30 days
    python fetch_ercot_real.py --start 2025-01-01 --end 2025-01-31
    python fetch_ercot_real.py --hub HB_HOUSTON       # Specific hub

Output:
    data/ercot/ercot_real_<hub>_<date>.csv

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ERCOT-Fetch] - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "ercot")

# ERCOT Trading Hubs
ERCOT_HUBS = {
    "HB_HOUSTON": "Houston Hub",
    "HB_NORTH": "North Hub",
    "HB_SOUTH": "South Hub",
    "HB_WEST": "West Hub",
    "HB_BUSAVG": "Bus Average (system-wide)",
}


def fetch_via_gridstatus(start: str, end: str, hub: str = "HB_HOUSTON") -> pd.DataFrame:
    """
    Fetch real ERCOT prices using the gridstatus library.

    Requires: pip install gridstatus
    No API key needed for historical data.
    """
    try:
        import gridstatus
    except ImportError:
        logger.warning("gridstatus not installed. Run: pip install gridstatus")
        raise

    logger.info(f"Fetching ERCOT data via gridstatus: {start} → {end}, hub={hub}")
    ercot = gridstatus.Ercot()

    # Fetch Day-Ahead Settlement Point Prices
    logger.info("  Downloading Day-Ahead SPP...")
    da_df = ercot.get_spp(
        date=start,
        end=end,
        market="DAM",
        location_type="Trading Hub",
    )

    # Fetch Real-Time Settlement Point Prices
    logger.info("  Downloading Real-Time SPP...")
    rt_df = ercot.get_spp(
        date=start,
        end=end,
        market="RTM15",
        location_type="Trading Hub",
    )

    # Filter to requested hub
    if hub in da_df.columns or 'Location' in da_df.columns:
        if 'Location' in da_df.columns:
            da_hub = da_df[da_df['Location'] == hub].copy()
            rt_hub = rt_df[rt_df['Location'] == hub].copy()
        else:
            da_hub = da_df.copy()
            rt_hub = rt_df.copy()
    else:
        da_hub = da_df.copy()
        rt_hub = rt_df.copy()

    # Merge DA and RT on timestamp
    da_hub = da_hub.rename(columns={'SPP': 'dam_lmp', 'Interval Start': 'timestamp'})
    rt_hub = rt_hub.rename(columns={'SPP': 'rtm_lmp', 'Interval Start': 'timestamp'})

    # Resample RT to hourly to match DA
    if len(rt_hub) > 0:
        rt_hub['timestamp'] = pd.to_datetime(rt_hub['timestamp'])
        rt_hourly = rt_hub.set_index('timestamp').resample('h')['rtm_lmp'].mean().reset_index()
    else:
        rt_hourly = pd.DataFrame(columns=['timestamp', 'rtm_lmp'])

    da_hub['timestamp'] = pd.to_datetime(da_hub['timestamp'])
    merged = pd.merge(da_hub[['timestamp', 'dam_lmp']],
                       rt_hourly[['timestamp', 'rtm_lmp']],
                       on='timestamp', how='outer')
    merged = merged.sort_values('timestamp').reset_index(drop=True)

    # Fill any gaps
    merged['dam_lmp'] = merged['dam_lmp'].ffill().bfill()
    merged['rtm_lmp'] = merged['rtm_lmp'].ffill().bfill()

    # Add derived columns
    merged['date'] = merged['timestamp'].dt.date
    merged['hour'] = merged['timestamp'].dt.hour

    logger.info(f"  Retrieved {len(merged)} hourly intervals")
    return merged


def fetch_via_direct_download(start: str, end: str, hub: str = "HB_HOUSTON") -> pd.DataFrame:
    """
    Fetch ERCOT data via direct HTTP download from ERCOT public reports.

    Uses the ERCOT MIS public reports (no auth needed for historical).
    """
    import urllib.request
    import io
    import zipfile

    logger.info(f"Fetching ERCOT data via direct download: {start} → {end}")

    # ERCOT publishes DAM SPP at this URL pattern
    # https://www.ercot.com/files/docs/yyyy/mm/dd/dam_spp.csv
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    all_rows = []
    current = start_dt

    while current <= end_dt:
        year = current.strftime('%Y')
        month = current.strftime('%m')
        day = current.strftime('%d')

        # Try ERCOT's historical data endpoint
        url = (
            f"https://mis.ercot.com/misapp/GetReports.do?"
            f"reportTypeId=12331&reportId=NP4-190-CD&"
            f"date={month}/{day}/{year}"
        )

        try:
            logger.info(f"  Downloading {current.strftime('%Y-%m-%d')}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'PRIMEnergeia/1.0'})
            response = urllib.request.urlopen(req, timeout=15)
            data = response.read()

            # Try to parse as CSV or ZIP
            try:
                df = pd.read_csv(io.BytesIO(data))
                all_rows.append(df)
            except Exception:
                # Might be a ZIP file
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as z:
                        for fname in z.namelist():
                            if fname.endswith('.csv'):
                                with z.open(fname) as f:
                                    df = pd.read_csv(f)
                                    all_rows.append(df)
                except Exception:
                    logger.warning(f"  Could not parse data for {current.strftime('%Y-%m-%d')}")
        except Exception as e:
            logger.warning(f"  Download failed for {current.strftime('%Y-%m-%d')}: {e}")

        current += timedelta(days=1)

    if not all_rows:
        raise RuntimeError("No data downloaded from ERCOT")

    combined = pd.concat(all_rows, ignore_index=True)
    logger.info(f"  Downloaded {len(combined)} rows")
    return combined


def generate_realistic_proxy(start: str, end: str, hub: str = "HB_HOUSTON") -> pd.DataFrame:
    """
    Generate realistic ERCOT price data based on known market patterns.

    This is NOT random — it uses documented ERCOT price patterns:
    - Summer peak pricing (July/Aug afternoon spikes)
    - Duck curve solar suppression
    - Wind ramp evening patterns
    - Weekend load drops
    - Seasonal baselines from ERCOT annual reports

    USE ONLY when real data download fails. Clearly labelled as PROXY.
    """
    logger.warning("⚠  GENERATING PROXY DATA — NOT REAL ERCOT PRICES")
    logger.warning("   Install 'gridstatus' and reconnect to internet for real data")

    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    hours = int((end_dt - start_dt).total_seconds() / 3600) + 24

    timestamps = pd.date_range(start=start_dt, periods=hours, freq='h')
    rng = np.random.RandomState(42)

    # --- Seasonal base (ERCOT 2024 averages from annual report) ---
    month = timestamps.month
    seasonal_base = np.where(
        (month >= 6) & (month <= 8), 55.0,    # Summer: $55/MWh avg
        np.where(
            (month >= 12) | (month <= 2), 38.0,  # Winter: $38/MWh avg
            np.where(
                (month >= 3) & (month <= 5), 28.0,  # Spring: $28/MWh (wind/solar surplus)
                32.0  # Fall: $32/MWh
            )
        )
    )

    # --- Hourly shape (documented ERCOT load curve) ---
    hour = timestamps.hour
    hourly_factor = np.ones(hours)

    # Pre-dawn valley (HE 1-5): 60-70% of base
    hourly_factor = np.where((hour >= 1) & (hour <= 5), 0.65, hourly_factor)
    # Morning ramp (HE 6-9): 80-110%
    hourly_factor = np.where((hour >= 6) & (hour <= 9), 0.8 + (hour - 6) * 0.1, hourly_factor)
    # Midday solar suppression (HE 10-14): 70-90% (duck curve)
    hourly_factor = np.where((hour >= 10) & (hour <= 14), 0.80, hourly_factor)
    # Afternoon peak (HE 15-19): 130-250% (AC load + solar decline)
    hourly_factor = np.where(hour == 15, 1.4, hourly_factor)
    hourly_factor = np.where(hour == 16, 1.8, hourly_factor)
    hourly_factor = np.where(hour == 17, 2.2, hourly_factor)
    hourly_factor = np.where(hour == 18, 1.9, hourly_factor)
    hourly_factor = np.where(hour == 19, 1.3, hourly_factor)
    # Evening decline (HE 20-23): 90-70%
    hourly_factor = np.where((hour >= 20) & (hour <= 23), 0.9 - (hour - 20) * 0.05, hourly_factor)

    # --- Weekend discount (-20%) ---
    weekday = timestamps.weekday
    weekend_factor = np.where(weekday >= 5, 0.80, 1.0)

    # --- Day-Ahead prices ---
    da_prices = seasonal_base * hourly_factor * weekend_factor

    # Add realistic volatility (ERCOT std dev ~$15-25)
    da_prices += rng.normal(0, 12, hours)

    # Add price spikes (ERCOT: ~2% of summer hours spike above $200)
    summer_mask = (month >= 6) & (month <= 8) & (hour >= 15) & (hour <= 18)
    spike_mask = summer_mask & (rng.random(hours) > 0.97)
    da_prices = np.where(spike_mask, da_prices * rng.uniform(3, 15, hours), da_prices)

    # Winter storm spikes (rare but extreme — Feb events)
    winter_spike = (month == 2) & (rng.random(hours) > 0.995)
    da_prices = np.where(winter_spike, da_prices * rng.uniform(10, 50, hours), da_prices)

    # Floor at -$35 (ERCOT allows negative, but rarely below -$35)
    da_prices = np.clip(da_prices, -35.0, 5000.0)

    # --- Real-Time prices (deviate from DA with fat-tailed distribution) ---
    rt_deviation = rng.standard_t(df=4, size=hours) * 0.12  # ±12% with fat tails
    rt_prices = da_prices * (1 + rt_deviation)
    rt_prices = np.clip(rt_prices, -50.0, 9000.0)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'hour': hour,
        'dam_lmp': np.round(da_prices, 2),
        'rtm_lmp': np.round(rt_prices, 2),
        'date': timestamps.date,
        'note': np.where(spike_mask, 'PRICE_SPIKE', ''),
    })

    # Add PROXY label
    df['note'] = df['note'].astype(str).replace('', '[PROXY DATA]')

    logger.info(f"  Generated {len(df)} hours of proxy data")
    logger.info(f"  DA mean: ${da_prices.mean():.2f}/MWh, max: ${da_prices.max():.2f}")
    return df


def fetch_ercot_data(start: str = None, end: str = None,
                     days: int = 7, hub: str = "HB_HOUSTON",
                     output_dir: str = None) -> str:
    """
    Main entry point. Downloads real ERCOT data (or proxy if offline).

    Returns path to saved CSV.
    """
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d')
    if start is None:
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    filename = f"ercot_real_{hub.lower()}_{start}_to_{end}.csv"
    output_path = os.path.join(output_dir, filename)

    # Check cache first
    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        logger.info(f"Using cached data: {output_path} ({size_kb:.1f} KB)")
        return output_path

    # Try sources in priority order
    df = None

    # Source 1: gridstatus
    try:
        df = fetch_via_gridstatus(start, end, hub)
        logger.info("✅ Real data from gridstatus")
    except Exception as e:
        logger.warning(f"gridstatus failed: {e}")

    # Source 2: direct download
    if df is None:
        try:
            df = fetch_via_direct_download(start, end, hub)
            logger.info("✅ Real data from ERCOT direct download")
        except Exception as e:
            logger.warning(f"Direct download failed: {e}")

    # Source 3: realistic proxy (last resort)
    if df is None:
        df = generate_realistic_proxy(start, end, hub)
        filename = f"ercot_PROXY_{hub.lower()}_{start}_to_{end}.csv"
        output_path = os.path.join(output_dir, filename)
        logger.warning(f"⚠  Using PROXY data — not real ERCOT prices")

    # Save
    df.to_csv(output_path, index=False)
    size_kb = os.path.getsize(output_path) / 1024
    logger.info(f"Saved: {output_path} ({size_kb:.1f} KB, {len(df)} rows)")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Fetch real ERCOT price data")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=30, help="Days of history (default: 30)")
    parser.add_argument("--hub", default="HB_HOUSTON",
                        choices=list(ERCOT_HUBS.keys()),
                        help="ERCOT trading hub")
    parser.add_argument("--list-hubs", action="store_true", help="List available hubs")

    args = parser.parse_args()

    if args.list_hubs:
        for k, v in ERCOT_HUBS.items():
            print(f"  {k:20s} — {v}")
        return

    path = fetch_ercot_data(
        start=args.start,
        end=args.end,
        days=args.days,
        hub=args.hub,
    )

    # Quick validation
    sys.path.insert(0, PROJECT_ROOT)
    from data.data_loader import load_dataset
    try:
        ds = load_dataset(filepath=path, market="ercot")
        print(f"\n✅ Loaded {ds.hours} intervals from {path}")
        print(f"   DA: ${np.nanmean(ds.da_prices):.2f}/MWh avg, "
              f"${np.nanmax(ds.da_prices):.2f} max")
        print(f"   RT: ${np.nanmean(ds.rt_prices):.2f}/MWh avg, "
              f"${np.nanmax(ds.rt_prices):.2f} max")
        print(f"   Spike hours (>$200): {int(np.sum(ds.rt_prices > 200))}")
    except Exception as e:
        print(f"⚠  Validation warning: {e}")

    return path


if __name__ == "__main__":
    main()
