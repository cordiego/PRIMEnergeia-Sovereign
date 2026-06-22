#!/usr/bin/env python3
"""
PRIMEnergeia — Pre-Flight Checklist Script
=============================================
One-command validation for guaranteed success with real data.

Usage:
    python preflight.py <csv_file> [--market ercot|sen|mibel] [--node 07-HER-230]
    python preflight.py --all              # Test all default datasets
    python preflight.py --demo             # Run full demo pipeline

Exit codes:
    0 = GO (all checks passed)
    1 = NO-GO (critical failures)
    2 = WARNING (non-critical issues)

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import argparse
import traceback
import numpy as np
from datetime import datetime

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


class PreFlightChecker:
    """Pre-flight validation for real data presentation."""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0
        self.results = []

    def _record(self, name: str, status: str, detail: str = ""):
        """Record a check result."""
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[status]
        self.results.append((name, status, detail))
        if status == "PASS":
            self.checks_passed += 1
        elif status == "FAIL":
            self.checks_failed += 1
        else:
            self.checks_warned += 1
        print(f"  {icon} {name}: {detail}" if detail else f"  {icon} {name}")

    # ─── Check: File Exists ─────────────────────────────────
    def check_file_exists(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            self._record("File Exists", "FAIL", f"Not found: {filepath}")
            return False
        size_kb = os.path.getsize(filepath) / 1024
        self._record("File Exists", "PASS", f"{filepath} ({size_kb:.1f} KB)")
        return True

    # ─── Check: Encoding ────────────────────────────────────
    def check_encoding(self, filepath: str) -> str:
        from data.data_loader import detect_encoding
        enc = detect_encoding(filepath)
        self._record("Encoding Detection", "PASS", f"Detected: {enc}")
        return enc

    # ─── Check: Column Matching ─────────────────────────────
    def check_columns(self, filepath: str, market: str = None) -> bool:
        import csv
        from data.data_loader import detect_encoding, match_columns

        enc = detect_encoding(filepath)
        with open(filepath, 'r', encoding=enc) as f:
            reader = csv.reader(f)
            headers = next(reader)

        # Try all market formats
        from data.data_loader import COLUMN_ALIASES

        # SEN nodo format
        mapping1, missing1 = match_columns(headers, ["actual_mw", "theoretical_mw", "pml_usd"])
        # DA/RT format
        mapping2, missing2 = match_columns(headers, ["dam_lmp", "rtm_lmp"])

        if not missing1:
            self._record("Column Matching", "PASS",
                          f"SEN nodo format: {list(mapping1.values())}")
            return True
        elif not missing2:
            self._record("Column Matching", "PASS",
                          f"DA/RT format: {list(mapping2.values())}")
            return True
        else:
            self._record("Column Matching", "FAIL",
                          f"Headers: {headers}. Could not match to any known format.")
            return False

    # ─── Check: Data Loading ────────────────────────────────
    def check_data_loading(self, filepath: str, market: str = None,
                           node_id: str = None):
        from data.data_loader import load_dataset
        try:
            ds = load_dataset(market=market, filepath=filepath, node_id=node_id)
            self._record("Data Loading", "PASS",
                          f"{ds.hours} intervals, market={ds.market}")

            # Check for NaN contamination
            nan_da = int(np.sum(np.isnan(ds.da_prices)))
            nan_rt = int(np.sum(np.isnan(ds.rt_prices)))
            if nan_da > 0 or nan_rt > 0:
                self._record("NaN Check", "WARN",
                              f"DA NaN: {nan_da}, RT NaN: {nan_rt}")
            else:
                self._record("NaN Check", "PASS", "No NaN values")

            # Check price distribution
            da_min = float(np.nanmin(ds.da_prices))
            da_max = float(np.nanmax(ds.da_prices))
            da_mean = float(np.nanmean(ds.da_prices))
            self._record("Price Range", "PASS",
                          f"DA: ${da_min:.2f} – ${da_max:.2f} (mean ${da_mean:.2f})")

            # Check data completeness
            if ds.quality:
                pct = ds.quality.completeness_pct
                if pct < 90:
                    self._record("Completeness", "WARN", f"{pct}% valid rows")
                else:
                    self._record("Completeness", "PASS", f"{pct}% valid rows")

            return ds
        except Exception as e:
            self._record("Data Loading", "FAIL", str(e))
            return None

    # ─── Check: Savings Pipeline ────────────────────────────
    def check_savings_pipeline(self, dataset) -> bool:
        from core.software_core import PRIMEnergeiaSoftware
        try:
            engine = PRIMEnergeiaSoftware()
            df = engine.load_from_dataset(dataset)
            savings = engine.calculate_savings(df)

            if savings['loss_total'] <= 0:
                self._record("Savings Calculation", "WARN",
                              f"Savings ≤ 0: ${savings['loss_total']:,.2f}")
            else:
                self._record("Savings Calculation", "PASS",
                              f"${savings['loss_total']:,.2f} recovery potential")
            return True
        except Exception as e:
            self._record("Savings Pipeline", "FAIL", str(e))
            return False

    # ─── Check: PDF Generation ──────────────────────────────
    def check_pdf_generation(self, dataset) -> bool:
        import tempfile
        from core.software_core import PRIMEnergeiaSoftware
        try:
            engine = PRIMEnergeiaSoftware()
            out = os.path.join(tempfile.mkdtemp(), "test_report.pdf")
            path = engine.run_from_dataset(dataset, output_path=out)
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                size_kb = os.path.getsize(path) / 1024
                self._record("PDF Generation", "PASS",
                              f"Generated: {size_kb:.1f} KB")
                os.unlink(path)
                return True
            else:
                self._record("PDF Generation", "FAIL", "PDF too small or missing")
                return False
        except Exception as e:
            self._record("PDF Generation", "FAIL", str(e))
            return False

    # ─── Check: Dependencies ────────────────────────────────
    def check_dependencies(self) -> bool:
        deps = [
            ('numpy', 'numpy'),
            ('pandas', 'pandas'),
            ('matplotlib', 'matplotlib'),
            ('fpdf', 'fpdf'),
            ('streamlit', 'streamlit'),
            ('plotly', 'plotly'),
            ('scipy', 'scipy'),
        ]
        all_ok = True
        for name, module in deps:
            try:
                __import__(module)
                self._record(f"Dep: {name}", "PASS")
            except ImportError:
                self._record(f"Dep: {name}", "FAIL", "Not installed")
                all_ok = False
        return all_ok

    # ─── Full Check Suite ───────────────────────────────────
    def run_full_check(self, filepath: str = None, market: str = None,
                       node_id: str = None) -> int:
        """
        Run the complete pre-flight checklist.

        Returns:
            0 = GO, 1 = NO-GO, 2 = WARNINGS
        """
        print("\n" + "=" * 65)
        print("  PRIMEnergeia — PRE-FLIGHT CHECKLIST")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 65 + "\n")

        # Phase 1: Dependencies
        print("── Phase 1: Dependencies ──")
        self.check_dependencies()
        print()

        # Phase 2: Data Validation
        print("── Phase 2: Data Validation ──")
        dataset = None

        if filepath:
            if self.check_file_exists(filepath):
                self.check_encoding(filepath)
                self.check_columns(filepath, market)
                dataset = self.check_data_loading(filepath, market, node_id)
        else:
            # Test default datasets
            print("  (No file specified — testing defaults)")
            defaults = [
                ("ERCOT", "data/ercot/ercot_historical.csv", "ercot", None),
                ("SEN", "data/nodos/data_07-HER-230.csv", "sen", "07-HER-230"),
            ]
            for label, path, mkt, nid in defaults:
                full = os.path.join(PROJECT_ROOT, path)
                print(f"\n  [{label}]")
                if os.path.exists(full):
                    self.check_file_exists(full)
                    ds = self.check_data_loading(full, mkt, nid)
                    if ds and dataset is None:
                        dataset = ds
                else:
                    self._record(f"{label} default data", "WARN", "Not found (OK if not needed)")

        print()

        # Phase 3: Pipeline
        print("── Phase 3: Report Pipeline ──")
        if dataset:
            self.check_savings_pipeline(dataset)
            self.check_pdf_generation(dataset)
        else:
            self._record("Pipeline Test", "WARN", "No dataset loaded — skipped")
        print()

        # Verdict
        print("=" * 65)
        if self.checks_failed > 0:
            verdict = "❌ NO-GO"
            exit_code = 1
        elif self.checks_warned > 0:
            verdict = "⚠️  GO WITH WARNINGS"
            exit_code = 2
        else:
            verdict = "✅ GO — ALL SYSTEMS GREEN"
            exit_code = 0

        print(f"\n  VERDICT: {verdict}")
        print(f"  Passed: {self.checks_passed} | "
              f"Failed: {self.checks_failed} | "
              f"Warnings: {self.checks_warned}")
        print("=" * 65 + "\n")

        return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="PRIMEnergeia Pre-Flight Checklist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python preflight.py data/ercot/ercot_historical.csv --market ercot
  python preflight.py client_data.csv                          # auto-detect
  python preflight.py --all                                    # test defaults
  python preflight.py data/nodos/data_07-HER-230.csv --market sen --node 07-HER-230
        """,
    )
    parser.add_argument("filepath", nargs="?", help="Path to CSV file to validate")
    parser.add_argument("--market", choices=["ercot", "sen", "mibel"],
                        help="Market type (auto-detected if not specified)")
    parser.add_argument("--node", default=None, help="SEN node ID (e.g., 07-HER-230)")
    parser.add_argument("--all", action="store_true",
                        help="Test all default datasets")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo pipeline")

    args = parser.parse_args()

    checker = PreFlightChecker()

    if args.demo:
        print("\n[DEMO MODE] Running synthetic data pipeline...")
        from core.software_core import PRIMEnergeiaSoftware
        engine = PRIMEnergeiaSoftware()
        path = engine.run_demo()
        print(f"✅ Demo report generated: {path}")
        sys.exit(0)

    filepath = args.filepath
    if args.all:
        filepath = None  # Will test all defaults

    exit_code = checker.run_full_check(
        filepath=filepath,
        market=args.market,
        node_id=args.node,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
