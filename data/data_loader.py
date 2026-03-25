"""
PRIMEnergeia — Market Data Loader
===================================
Loads historical price data from CSV files for backtesting.
Validates data quality and returns numpy arrays for co-optimizer input.

Supported formats:
- ERCOT: hour, dam_lmp, rtm_lmp, load_mw, wind_mw, solar_mw, date
- CENACE: hour, mda_pml, mtr_pml, date
- OMIE: hour, da_price, id_price, date

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import csv
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple


DATA_DIR = os.path.join(os.path.dirname(__file__))


@dataclass
class MarketDataset:
    """Validated market price dataset ready for co-optimizer input."""
    market: str
    hours: int
    da_prices: np.ndarray    # Day-ahead prices ($/MWh or local currency)
    rt_prices: np.ndarray    # Real-time prices
    load_mw: Optional[np.ndarray] = None
    wind_mw: Optional[np.ndarray] = None
    solar_mw: Optional[np.ndarray] = None
    dates: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    source_file: str = ""

    @property
    def price_spread(self) -> np.ndarray:
        """RT - DA price spread (positive = RT premium)."""
        return self.rt_prices - self.da_prices

    @property
    def stats(self) -> dict:
        return {
            "hours": self.hours,
            "da_mean": round(float(np.mean(self.da_prices)), 2),
            "da_min": round(float(np.min(self.da_prices)), 2),
            "da_max": round(float(np.max(self.da_prices)), 2),
            "da_std": round(float(np.std(self.da_prices)), 2),
            "rt_mean": round(float(np.mean(self.rt_prices)), 2),
            "rt_min": round(float(np.min(self.rt_prices)), 2),
            "rt_max": round(float(np.max(self.rt_prices)), 2),
            "rt_std": round(float(np.std(self.rt_prices)), 2),
            "spread_mean": round(float(np.mean(self.price_spread)), 2),
            "spike_hours": int(np.sum(self.rt_prices > 200)),
            "negative_hours": int(np.sum(self.da_prices < 0)),
        }


def load_ercot_csv(filepath: str = None) -> MarketDataset:
    """Load ERCOT historical price data from CSV.

    Expected columns: hour, dam_lmp, rtm_lmp, load_mw, wind_mw, solar_mw, date, note
    """
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "ercot", "ercot_historical.csv")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"ERCOT data not found at {filepath}. "
            f"Download from https://mis.ercot.com or create seed data."
        )

    da_prices, rt_prices = [], []
    load_mw, wind_mw, solar_mw = [], [], []
    dates, notes = [], []

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            da = float(row["dam_lmp"])
            rt = float(row["rtm_lmp"])

            # Validate price bounds
            if da < -200 or da > 9001:
                raise ValueError(f"DAM price {da} out of ERCOT bounds [-200, 9001]")
            if rt < -200 or rt > 9001:
                raise ValueError(f"RTM price {rt} out of ERCOT bounds [-200, 9001]")

            da_prices.append(da)
            rt_prices.append(rt)
            load_mw.append(float(row.get("load_mw", 0)))
            wind_mw.append(float(row.get("wind_mw", 0)))
            solar_mw.append(float(row.get("solar_mw", 0)))
            dates.append(row.get("date", ""))
            notes.append(row.get("note", ""))

    da = np.array(da_prices)
    rt = np.array(rt_prices)

    # Validate array integrity
    if len(da) == 0:
        raise ValueError("Empty dataset — no rows found")
    if np.any(np.isnan(da)) or np.any(np.isnan(rt)):
        raise ValueError("Dataset contains NaN values")

    return MarketDataset(
        market="ercot",
        hours=len(da),
        da_prices=da,
        rt_prices=rt,
        load_mw=np.array(load_mw),
        wind_mw=np.array(wind_mw),
        solar_mw=np.array(solar_mw),
        dates=dates,
        notes=notes,
        source_file=filepath,
    )


def load_dataset(market: str, filepath: str = None) -> MarketDataset:
    """Load market data by market name."""
    loaders = {
        "ercot": load_ercot_csv,
    }
    loader = loaders.get(market)
    if loader is None:
        raise ValueError(f"No loader for market '{market}'. Available: {list(loaders.keys())}")
    return loader(filepath) if filepath else loader()


if __name__ == "__main__":
    ds = load_ercot_csv()
    print(f"\nERCOT Dataset: {ds.hours} hours from {ds.source_file}")
    for k, v in ds.stats.items():
        print(f"  {k}: {v}")
