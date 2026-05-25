"""
PRIMEnergeia — Hardened Market Data Loader
============================================
Loads historical price data from CSV files for backtesting.
Validates data quality and returns numpy arrays for co-optimizer input.

Hardened for real-world data:
  - Column-name aliasing (fuzzy matching for common real-world headers)
  - safe_float() conversion (handles $, commas, N/A, empty cells)
  - Encoding detection (UTF-8, BOM, Latin-1, CP1252)
  - Per-market loaders: ERCOT, SEN (CENACE), MIBEL (OMIE)
  - Universal loader with auto-detection
  - Data quality report

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import csv
import io
import re
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [DataLoader] - %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__))


# ─────────────────────────────────────────────────────────────
# Column-Name Aliasing — maps real-world headers to internal names
# ─────────────────────────────────────────────────────────────
COLUMN_ALIASES: Dict[str, List[str]] = {
    # Internal name → list of known aliases (case-insensitive)
    "dam_lmp": [
        "dam_lmp", "da_price", "da_lmp", "day_ahead_price", "day_ahead_lmp",
        "settlement_point_price", "dam", "lmp_dam", "precio_mda", "mda_pml",
        "da_precio", "precio_da", "day_ahead", "dam_price", "dam_lmp_usd",
        "price_dam", "spp_dam", "spp_da", "pool_price_da", "spot_da",
    ],
    "rtm_lmp": [
        "rtm_lmp", "rt_price", "rt_lmp", "real_time_price", "real_time_lmp",
        "rtm", "lmp_rtm", "precio_mtr", "mtr_pml", "rt_precio", "precio_rt",
        "real_time", "rtm_price", "rtm_lmp_usd", "price_rtm", "spp_rtm",
        "spp_rt", "pool_price_rt", "spot_rt", "id_price", "intraday_price",
    ],
    "load_mw": [
        "load_mw", "load", "demand_mw", "demand", "system_load",
        "total_load", "carga_mw", "demanda_mw", "load_forecast",
    ],
    "wind_mw": [
        "wind_mw", "wind", "wind_gen", "wind_generation", "eolica_mw",
        "generacion_eolica", "wind_output",
    ],
    "solar_mw": [
        "solar_mw", "solar", "solar_gen", "solar_generation", "solar_fotovoltaica",
        "generacion_solar", "solar_output", "pv_mw",
    ],
    "date": [
        "date", "fecha", "delivery_date", "trading_date", "market_date",
        "fecha_mercado", "día", "dia",
    ],
    "hour": [
        "hour", "hora", "interval", "period", "he", "hour_ending",
        "delivery_hour", "hora_entrega", "time_period",
    ],
    "timestamp": [
        "timestamp", "datetime", "date_time", "fecha_hora", "ts",
        "delivery_timestamp", "interval_start", "time",
    ],
    "note": [
        "note", "notes", "nota", "notas", "comment", "comments",
        "observaciones", "remarks",
    ],
    # SEN / Software Core format columns
    "actual_mw": [
        "actual_mw", "actual", "gen_actual", "generation_actual",
        "potencia_actual", "p_actual", "measured_mw", "real_mw",
    ],
    "theoretical_mw": [
        "theoretical_mw", "theoretical", "gen_theoretical", "optimal_mw",
        "potencia_teorica", "p_teorica", "expected_mw", "forecast_mw",
        "setpoint_mw",
    ],
    "pml_usd": [
        "pml_usd", "pml", "precio_pml", "node_price", "nodal_price",
        "lmp", "price", "precio", "spot_price", "market_price",
    ],
}


# ─────────────────────────────────────────────────────────────
# safe_float — bulletproof numeric conversion
# ─────────────────────────────────────────────────────────────
def safe_float(value: Any, default: float = float('nan')) -> float:
    """
    Convert a value to float, handling common real-world CSV issues:
    - Empty strings, None
    - Currency symbols ($, €, MXN)
    - Comma-separated thousands (1,234.56)
    - Text values (N/A, null, #REF!, -, --)
    - Whitespace
    """
    if value is None:
        return default
    s = str(value).strip()
    if not s or s.lower() in ('n/a', 'na', 'null', 'none', '#ref!',
                               '#n/a', '#value!', '-', '--', '...', 'nan'):
        return default
    # Strip currency symbols and whitespace
    s = re.sub(r'[$ €£¥₱₩MXN]', '', s).strip()
    # Remove thousands separators (commas in "1,234.56")
    s = s.replace(',', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────
# Encoding Detection
# ─────────────────────────────────────────────────────────────
def detect_encoding(filepath: str) -> str:
    """Try multiple encodings and return the first that works."""
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read(4096)  # Read enough to trigger encoding errors
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    logger.warning(f"Could not detect encoding for {filepath}, falling back to latin-1")
    return 'latin-1'


# ─────────────────────────────────────────────────────────────
# Column Matching
# ─────────────────────────────────────────────────────────────
def match_columns(csv_headers: List[str], required: List[str],
                  optional: List[str] = None) -> Tuple[Dict[str, str], List[str]]:
    """
    Match CSV column headers to internal names using the alias table.

    Returns:
        mapping: dict of {internal_name: csv_column_name}
        missing: list of required internal names that couldn't be matched
    """
    optional = optional or []
    mapping = {}
    normalized_headers = {h.strip().lower().replace(' ', '_'): h for h in csv_headers}

    all_targets = required + optional
    for internal_name in all_targets:
        aliases = COLUMN_ALIASES.get(internal_name, [internal_name])
        found = False
        for alias in aliases:
            alias_norm = alias.strip().lower().replace(' ', '_')
            if alias_norm in normalized_headers:
                mapping[internal_name] = normalized_headers[alias_norm]
                found = True
                break
        if not found:
            # Fuzzy fallback: check if any header contains the internal name
            for norm_h, original_h in normalized_headers.items():
                if internal_name in norm_h or norm_h in internal_name:
                    mapping[internal_name] = original_h
                    found = True
                    break

    missing = [r for r in required if r not in mapping]
    return mapping, missing


# ─────────────────────────────────────────────────────────────
# Data Quality Report
# ─────────────────────────────────────────────────────────────
@dataclass
class DataQualityReport:
    """Summary of data quality for client-facing display."""
    filepath: str
    encoding: str
    total_rows: int
    valid_rows: int
    skipped_rows: int
    date_range: Tuple[str, str]  # (earliest, latest)
    columns_found: List[str]
    columns_missing: List[str]
    columns_mapped: Dict[str, str]  # internal → csv header
    nan_counts: Dict[str, int]      # column → count of NaN/missing
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

    @property
    def completeness_pct(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round(100.0 * self.valid_rows / self.total_rows, 1)

    def log_report(self):
        logger.info("=" * 60)
        logger.info(f" DATA QUALITY REPORT")
        logger.info(f" File:        {os.path.basename(self.filepath)}")
        logger.info(f" Encoding:    {self.encoding}")
        logger.info(f" Rows:        {self.valid_rows}/{self.total_rows} valid ({self.completeness_pct}%)")
        logger.info(f" Skipped:     {self.skipped_rows}")
        logger.info(f" Date range:  {self.date_range[0]} → {self.date_range[1]}")
        if self.columns_missing:
            logger.warning(f" MISSING:     {self.columns_missing}")
        for w in self.warnings:
            logger.warning(f" ⚠  {w}")
        logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────
# Market Dataset (unchanged public interface)
# ─────────────────────────────────────────────────────────────
@dataclass
class MarketDataset:
    """Validated market price dataset ready for co-optimizer input."""
    market: str
    hours: int
    da_prices: np.ndarray       # Day-ahead prices ($/MWh or local currency)
    rt_prices: np.ndarray       # Real-time prices
    load_mw: Optional[np.ndarray] = None
    wind_mw: Optional[np.ndarray] = None
    solar_mw: Optional[np.ndarray] = None
    dates: Optional[List[str]] = None
    timestamps: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    source_file: str = ""
    quality: Optional[DataQualityReport] = None
    # SEN/Software-Core compatible fields
    actual_mw: Optional[np.ndarray] = None
    theoretical_mw: Optional[np.ndarray] = None

    @property
    def price_spread(self) -> np.ndarray:
        """RT - DA price spread (positive = RT premium)."""
        return self.rt_prices - self.da_prices

    @property
    def stats(self) -> dict:
        return {
            "hours": self.hours,
            "da_mean": round(float(np.nanmean(self.da_prices)), 2),
            "da_min": round(float(np.nanmin(self.da_prices)), 2),
            "da_max": round(float(np.nanmax(self.da_prices)), 2),
            "da_std": round(float(np.nanstd(self.da_prices)), 2),
            "rt_mean": round(float(np.nanmean(self.rt_prices)), 2),
            "rt_min": round(float(np.nanmin(self.rt_prices)), 2),
            "rt_max": round(float(np.nanmax(self.rt_prices)), 2),
            "rt_std": round(float(np.nanstd(self.rt_prices)), 2),
            "spread_mean": round(float(np.nanmean(self.price_spread)), 2),
            "spike_hours": int(np.sum(self.rt_prices > 200)),
            "negative_hours": int(np.sum(self.da_prices < 0)),
        }


# ─────────────────────────────────────────────────────────────
# ERCOT Loader (hardened)
# ─────────────────────────────────────────────────────────────
def load_ercot_csv(filepath: str = None,
                   price_floor: float = -200.0,
                   price_cap: float = 9001.0) -> MarketDataset:
    """Load ERCOT historical price data from CSV with full hardening."""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "ercot", "ercot_historical.csv")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"ERCOT data not found at {filepath}. "
            f"Download from https://mis.ercot.com or create seed data."
        )

    encoding = detect_encoding(filepath)

    # Read headers to match columns
    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        raw_headers = next(reader)

    mapping, missing = match_columns(
        raw_headers,
        required=["dam_lmp", "rtm_lmp"],
        optional=["load_mw", "wind_mw", "solar_mw", "date", "hour", "note"]
    )

    if missing:
        raise ValueError(
            f"ERCOT CSV missing required columns: {missing}.\n"
            f"Found columns: {raw_headers}\n"
            f"Mapped: {mapping}\n"
            f"Expected one of these for each:\n"
            + "\n".join(f"  {m}: {COLUMN_ALIASES.get(m, [m])[:5]}" for m in missing)
        )

    da_prices, rt_prices = [], []
    load_mw, wind_mw, solar_mw = [], [], []
    dates, notes = [], []
    skipped = 0
    warnings_list = []

    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            da = safe_float(row.get(mapping["dam_lmp"], ""))
            rt = safe_float(row.get(mapping["rtm_lmp"], ""))

            # Skip rows where both prices are NaN
            if np.isnan(da) and np.isnan(rt):
                skipped += 1
                continue

            # Fill single NaN with the other price
            if np.isnan(da):
                da = rt
                warnings_list.append(f"Row {row_num}: DA price missing, filled with RT")
            if np.isnan(rt):
                rt = da
                warnings_list.append(f"Row {row_num}: RT price missing, filled with DA")

            # Clamp to bounds (warn, don't crash)
            if da < price_floor or da > price_cap:
                if len(warnings_list) < 20:
                    warnings_list.append(f"Row {row_num}: DA price {da} clamped to [{price_floor}, {price_cap}]")
                da = np.clip(da, price_floor, price_cap)
            if rt < price_floor or rt > price_cap:
                if len(warnings_list) < 20:
                    warnings_list.append(f"Row {row_num}: RT price {rt} clamped to [{price_floor}, {price_cap}]")
                rt = np.clip(rt, price_floor, price_cap)

            da_prices.append(da)
            rt_prices.append(rt)
            load_mw.append(safe_float(row.get(mapping.get("load_mw", "__none__"), ""), 0.0))
            wind_mw.append(safe_float(row.get(mapping.get("wind_mw", "__none__"), ""), 0.0))
            solar_mw.append(safe_float(row.get(mapping.get("solar_mw", "__none__"), ""), 0.0))
            dates.append(row.get(mapping.get("date", "__none__"), ""))
            notes.append(row.get(mapping.get("note", "__none__"), ""))

    da = np.array(da_prices)
    rt = np.array(rt_prices)

    if len(da) == 0:
        raise ValueError(f"Empty dataset — no valid rows found in {filepath}")

    # Build quality report
    nan_counts = {
        "da_prices": int(np.sum(np.isnan(da))),
        "rt_prices": int(np.sum(np.isnan(rt))),
    }
    date_range = (dates[0] if dates else "N/A", dates[-1] if dates else "N/A")

    quality = DataQualityReport(
        filepath=filepath,
        encoding=encoding,
        total_rows=len(da) + skipped,
        valid_rows=len(da),
        skipped_rows=skipped,
        date_range=date_range,
        columns_found=list(mapping.values()),
        columns_missing=missing,
        columns_mapped=mapping,
        nan_counts=nan_counts,
        warnings=warnings_list[:20],
    )
    quality.log_report()

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
        quality=quality,
    )


# ─────────────────────────────────────────────────────────────
# SEN (CENACE) Loader
# ─────────────────────────────────────────────────────────────
def load_sen_csv(filepath: str = None,
                 node_id: str = "07-HER-230",
                 price_floor: float = -50.0,
                 price_cap: float = 5000.0) -> MarketDataset:
    """
    Load SEN (CENACE) data from CSV.

    Supports two formats:
      1. Nodo format: timestamp, Actual_MW, Theoretical_MW, PML_USD
      2. Standard format: hour, mda_pml, mtr_pml, date
    """
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "nodos", f"data_{node_id}.csv")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"SEN data not found at {filepath}. "
            f"Provide CENACE PML data or create seed data."
        )

    encoding = detect_encoding(filepath)

    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        raw_headers = next(reader)

    # Try nodo format first (Actual_MW, Theoretical_MW, PML_USD)
    nodo_mapping, nodo_missing = match_columns(
        raw_headers,
        required=["actual_mw", "theoretical_mw", "pml_usd"],
        optional=["timestamp", "date"]
    )

    if not nodo_missing:
        return _load_sen_nodo_format(filepath, encoding, nodo_mapping, price_floor, price_cap)

    # Try standard CENACE format (mda_pml, mtr_pml)
    std_mapping, std_missing = match_columns(
        raw_headers,
        required=["dam_lmp", "rtm_lmp"],
        optional=["date", "hour", "timestamp", "note"]
    )

    if not std_missing:
        return _load_sen_standard_format(filepath, encoding, std_mapping, price_floor, price_cap)

    raise ValueError(
        f"SEN CSV format not recognized.\n"
        f"Found columns: {raw_headers}\n"
        f"Expected either:\n"
        f"  Nodo format: Actual_MW, Theoretical_MW, PML_USD (missing: {nodo_missing})\n"
        f"  Standard: dam/mda_pml, rtm/mtr_pml (missing: {std_missing})\n"
        f"Column aliases tried:\n"
        + "\n".join(f"  {m}: {COLUMN_ALIASES.get(m, [m])[:5]}" for m in set(nodo_missing + std_missing))
    )


def _load_sen_nodo_format(filepath, encoding, mapping, price_floor, price_cap):
    """Load SEN data in nodo format (Actual_MW, Theoretical_MW, PML_USD)."""
    actual_list, theo_list, pml_list = [], [], []
    timestamps = []
    skipped = 0
    warnings_list = []

    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            actual = safe_float(row.get(mapping["actual_mw"], ""))
            theo = safe_float(row.get(mapping["theoretical_mw"], ""))
            pml = safe_float(row.get(mapping["pml_usd"], ""))

            if np.isnan(pml):
                skipped += 1
                continue

            if np.isnan(actual):
                actual = 0.0
            if np.isnan(theo):
                theo = 0.0

            # Clamp PML
            if pml < price_floor or pml > price_cap:
                if len(warnings_list) < 20:
                    warnings_list.append(f"Row {row_num}: PML {pml} clamped to [{price_floor}, {price_cap}]")
                pml = np.clip(pml, price_floor, price_cap)

            actual_list.append(actual)
            theo_list.append(theo)
            pml_list.append(pml)
            ts = row.get(mapping.get("timestamp", "__none__"), "")
            if not ts:
                ts = row.get(mapping.get("date", "__none__"), "")
            timestamps.append(ts)

    actual_arr = np.array(actual_list)
    theo_arr = np.array(theo_list)
    pml_arr = np.array(pml_list)

    if len(pml_arr) == 0:
        raise ValueError(f"Empty dataset — no valid rows in {filepath}")

    date_range = (timestamps[0] if timestamps else "N/A",
                  timestamps[-1] if timestamps else "N/A")

    quality = DataQualityReport(
        filepath=filepath,
        encoding=encoding,
        total_rows=len(pml_arr) + skipped,
        valid_rows=len(pml_arr),
        skipped_rows=skipped,
        date_range=date_range,
        columns_found=list(mapping.values()),
        columns_missing=[],
        columns_mapped=mapping,
        nan_counts={"pml": int(np.sum(np.isnan(pml_arr)))},
        warnings=warnings_list[:20],
    )
    quality.log_report()

    return MarketDataset(
        market="sen",
        hours=len(pml_arr),
        da_prices=pml_arr,     # PML as DA proxy
        rt_prices=pml_arr,     # Same for SEN (single price)
        actual_mw=actual_arr,
        theoretical_mw=theo_arr,
        timestamps=timestamps,
        source_file=filepath,
        quality=quality,
    )


def _load_sen_standard_format(filepath, encoding, mapping, price_floor, price_cap):
    """Load SEN data in standard DA/RT format."""
    # Reuse the ERCOT loader logic with SEN market tag
    ds = _generic_da_rt_loader(filepath, encoding, mapping, "sen", price_floor, price_cap)
    return ds


# ─────────────────────────────────────────────────────────────
# MIBEL (OMIE) Loader
# ─────────────────────────────────────────────────────────────
def load_mibel_csv(filepath: str = None,
                   price_floor: float = 0.0,
                   price_cap: float = 3000.0) -> MarketDataset:
    """Load MIBEL (OMIE) data from CSV."""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "mibel", "mibel_historical.csv")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"MIBEL data not found at {filepath}. "
            f"Download from https://www.omie.es or create seed data."
        )

    encoding = detect_encoding(filepath)

    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        raw_headers = next(reader)

    mapping, missing = match_columns(
        raw_headers,
        required=["dam_lmp", "rtm_lmp"],
        optional=["date", "hour", "timestamp", "note"]
    )

    if missing:
        raise ValueError(
            f"MIBEL CSV missing required columns: {missing}.\n"
            f"Found columns: {raw_headers}\n"
            f"Mapped: {mapping}\n"
            + "\n".join(f"  {m}: {COLUMN_ALIASES.get(m, [m])[:5]}" for m in missing)
        )

    return _generic_da_rt_loader(filepath, encoding, mapping, "mibel", price_floor, price_cap)


# ─────────────────────────────────────────────────────────────
# Generic DA/RT Loader (shared by ERCOT, SEN-std, MIBEL)
# ─────────────────────────────────────────────────────────────
def _generic_da_rt_loader(filepath, encoding, mapping, market,
                          price_floor, price_cap) -> MarketDataset:
    """Generic loader for DA/RT price CSVs."""
    da_prices, rt_prices = [], []
    load_mw, wind_mw, solar_mw = [], [], []
    dates, notes, timestamps = [], [], []
    skipped = 0
    warnings_list = []

    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            da = safe_float(row.get(mapping["dam_lmp"], ""))
            rt = safe_float(row.get(mapping["rtm_lmp"], ""))

            if np.isnan(da) and np.isnan(rt):
                skipped += 1
                continue

            if np.isnan(da):
                da = rt
            if np.isnan(rt):
                rt = da

            da = float(np.clip(da, price_floor, price_cap))
            rt = float(np.clip(rt, price_floor, price_cap))

            da_prices.append(da)
            rt_prices.append(rt)
            load_mw.append(safe_float(row.get(mapping.get("load_mw", "__none__"), ""), 0.0))
            wind_mw.append(safe_float(row.get(mapping.get("wind_mw", "__none__"), ""), 0.0))
            solar_mw.append(safe_float(row.get(mapping.get("solar_mw", "__none__"), ""), 0.0))
            dates.append(row.get(mapping.get("date", "__none__"), ""))
            notes.append(row.get(mapping.get("note", "__none__"), ""))
            ts = row.get(mapping.get("timestamp", "__none__"), "")
            timestamps.append(ts)

    da = np.array(da_prices)
    rt = np.array(rt_prices)

    if len(da) == 0:
        raise ValueError(f"Empty dataset — no valid rows in {filepath}")

    date_range = (dates[0] if dates and dates[0] else
                  (timestamps[0] if timestamps else "N/A"),
                  dates[-1] if dates and dates[-1] else
                  (timestamps[-1] if timestamps else "N/A"))

    quality = DataQualityReport(
        filepath=filepath,
        encoding=encoding,
        total_rows=len(da) + skipped,
        valid_rows=len(da),
        skipped_rows=skipped,
        date_range=date_range,
        columns_found=list(mapping.values()),
        columns_missing=[],
        columns_mapped=mapping,
        nan_counts={
            "da_prices": int(np.sum(np.isnan(da))),
            "rt_prices": int(np.sum(np.isnan(rt))),
        },
        warnings=warnings_list[:20],
    )
    quality.log_report()

    return MarketDataset(
        market=market,
        hours=len(da),
        da_prices=da,
        rt_prices=rt,
        load_mw=np.array(load_mw) if any(v != 0 for v in load_mw) else None,
        wind_mw=np.array(wind_mw) if any(v != 0 for v in wind_mw) else None,
        solar_mw=np.array(solar_mw) if any(v != 0 for v in solar_mw) else None,
        dates=dates if any(d for d in dates) else None,
        timestamps=timestamps if any(t for t in timestamps) else None,
        notes=notes if any(n for n in notes) else None,
        source_file=filepath,
        quality=quality,
    )


# ─────────────────────────────────────────────────────────────
# Universal Auto-Detect Loader
# ─────────────────────────────────────────────────────────────
def load_dataset(market: str = None, filepath: str = None,
                 node_id: str = None) -> MarketDataset:
    """
    Load market data by market name or auto-detect from CSV headers.

    Parameters
    ----------
    market : str, optional
        Market name: 'ercot', 'sen', 'mibel'. If None, auto-detect.
    filepath : str, optional
        Path to CSV file. If None, use default path for the market.
    node_id : str, optional
        Node ID for SEN nodo format (default: '07-HER-230').

    Returns
    -------
    MarketDataset
    """
    if market:
        loaders = {
            "ercot": lambda: load_ercot_csv(filepath),
            "sen": lambda: load_sen_csv(filepath, node_id=node_id or "07-HER-230"),
            "cenace": lambda: load_sen_csv(filepath, node_id=node_id or "07-HER-230"),
            "mibel": lambda: load_mibel_csv(filepath),
            "omie": lambda: load_mibel_csv(filepath),
        }
        loader = loaders.get(market.lower())
        if loader is None:
            raise ValueError(
                f"No loader for market '{market}'. "
                f"Available: {list(loaders.keys())}"
            )
        return loader()

    # Auto-detect from file headers
    if filepath is None:
        raise ValueError("Either 'market' or 'filepath' must be provided.")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")

    encoding = detect_encoding(filepath)
    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        raw_headers = next(reader)

    headers_lower = [h.strip().lower() for h in raw_headers]

    # Detect SEN nodo format
    if any(h in headers_lower for h in ['actual_mw', 'theoretical_mw', 'pml_usd']):
        logger.info("Auto-detected SEN nodo format")
        return load_sen_csv(filepath)

    # Detect ERCOT format
    if any(h in headers_lower for h in ['dam_lmp', 'rtm_lmp', 'load_mw']):
        logger.info("Auto-detected ERCOT format")
        return load_ercot_csv(filepath)

    # Detect CENACE standard
    if any(h in headers_lower for h in ['mda_pml', 'precio_mda']):
        logger.info("Auto-detected SEN/CENACE standard format")
        return load_sen_csv(filepath)

    # Detect MIBEL/OMIE
    if any(h in headers_lower for h in ['da_price', 'id_price', 'pool_price']):
        logger.info("Auto-detected MIBEL/OMIE format")
        return load_mibel_csv(filepath)

    # Fallback: try generic with column aliasing
    logger.info("Unknown format — attempting generic DA/RT loader with column aliasing")
    mapping, missing = match_columns(raw_headers, required=["dam_lmp", "rtm_lmp"])
    if not missing:
        return _generic_da_rt_loader(filepath, encoding, mapping, "unknown", -500, 10000)

    raise ValueError(
        f"Could not auto-detect market format for {filepath}.\n"
        f"Found columns: {raw_headers}\n"
        f"None matched any known market format.\n"
        f"Please specify market='ercot'|'sen'|'mibel' explicitly."
    )


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Testing ERCOT loader ===")
    try:
        ds = load_ercot_csv()
        print(f"ERCOT: {ds.hours} intervals from {ds.source_file}")
        for k, v in ds.stats.items():
            print(f"  {k}: {v}")
    except FileNotFoundError as e:
        print(f"  [SKIP] {e}")

    print("\n=== Testing SEN loader ===")
    try:
        ds = load_sen_csv()
        print(f"SEN: {ds.hours} intervals from {ds.source_file}")
        print(f"  Actual MW range: {np.nanmin(ds.actual_mw):.1f} — {np.nanmax(ds.actual_mw):.1f}")
        print(f"  Theoretical MW range: {np.nanmin(ds.theoretical_mw):.1f} — {np.nanmax(ds.theoretical_mw):.1f}")
        print(f"  PML range: ${np.nanmin(ds.da_prices):.2f} — ${np.nanmax(ds.da_prices):.2f}")
    except FileNotFoundError as e:
        print(f"  [SKIP] {e}")
