#!/usr/bin/env python3
"""
PRIMEnergeia — Health Check & Monitoring Endpoint
====================================================
Lightweight health check for monitoring deployments.

Can be called by:
  - Uptime monitoring (UptimeRobot, Pingdom, etc.)
  - CI/CD pipelines
  - Cron jobs
  - Load balancers

Usage:
    python healthcheck.py           # Run all checks
    python healthcheck.py --json    # Output as JSON

Exit codes: 0 = healthy, 1 = unhealthy

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import sys
import json
import time
import importlib
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def check_imports():
    """Verify all critical imports work."""
    critical = [
        'numpy', 'pandas', 'matplotlib', 'fpdf',
        'streamlit', 'plotly', 'scipy',
    ]
    results = {}
    for mod in critical:
        try:
            importlib.import_module(mod)
            results[mod] = "ok"
        except ImportError as e:
            results[mod] = f"FAIL: {e}"
    return results


def check_data_files():
    """Verify critical data files exist."""
    files = {
        "ercot_historical": "data/ercot/ercot_historical.csv",
        "sen_node_data": "data/nodos/data_07-HER-230.csv",
        "data_loader": "data/data_loader.py",
        "software_core": "core/software_core.py",
        "dispatch_engine": "markets/ercot/dispatch_ercot.py",
        "app_entry": "app.py",
    }
    results = {}
    for name, path in files.items():
        full = os.path.join(PROJECT_ROOT, path)
        if os.path.exists(full):
            size = os.path.getsize(full)
            results[name] = f"ok ({size} bytes)"
        else:
            results[name] = "MISSING"
    return results


def check_data_loader():
    """Verify data loader can actually parse files."""
    try:
        from data.data_loader import load_ercot_csv
        ds = load_ercot_csv()
        return {"status": "ok", "rows": ds.hours, "market": ds.market}
    except Exception as e:
        return {"status": f"FAIL: {e}"}


def check_dispatch_engine():
    """Verify dispatch engine runs."""
    try:
        from markets.ercot.dispatch_ercot import run_ercot_coopt
        result = run_ercot_coopt(hours=24)
        return {
            "status": "ok",
            "revenue": result.total_revenue_usd,
            "uplift": result.uplift_pct,
        }
    except Exception as e:
        return {"status": f"FAIL: {e}"}


def check_report_engine():
    """Verify report engine can generate PDFs."""
    try:
        import tempfile
        from core.software_core import PRIMEnergeiaSoftware
        engine = PRIMEnergeiaSoftware()
        df = engine.generate_demo_data()
        out = os.path.join(tempfile.mkdtemp(), "healthcheck.pdf")
        path = engine.generate_report(df, output_path=out)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        if os.path.exists(path):
            os.unlink(path)
        return {"status": "ok" if size > 1000 else "FAIL", "pdf_bytes": size}
    except Exception as e:
        return {"status": f"FAIL: {e}"}


def run_healthcheck(as_json=False):
    """Run all health checks."""
    start = time.time()

    checks = {
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "imports": check_imports(),
        "data_files": check_data_files(),
        "data_loader": check_data_loader(),
        "dispatch_engine": check_dispatch_engine(),
        "report_engine": check_report_engine(),
    }

    elapsed = time.time() - start
    checks["elapsed_seconds"] = round(elapsed, 2)

    # Determine overall health
    all_values = json.dumps(checks)
    healthy = "FAIL" not in all_values and "MISSING" not in all_values
    checks["healthy"] = healthy

    if as_json:
        print(json.dumps(checks, indent=2))
    else:
        status_icon = "✅" if healthy else "❌"
        print(f"\n{status_icon} PRIMEnergeia Health Check — {'HEALTHY' if healthy else 'UNHEALTHY'}")
        print(f"   Time: {checks['timestamp']} ({elapsed:.1f}s)")
        print()

        for section, results in checks.items():
            if isinstance(results, dict):
                has_fail = "FAIL" in json.dumps(results) or "MISSING" in json.dumps(results)
                icon = "❌" if has_fail else "✅"
                print(f"  {icon} {section}:")
                for k, v in results.items():
                    sub_icon = "❌" if ("FAIL" in str(v) or "MISSING" in str(v)) else "  "
                    print(f"     {sub_icon} {k}: {v}")
                print()

    return 0 if healthy else 1


if __name__ == "__main__":
    as_json = "--json" in sys.argv
    exit_code = run_healthcheck(as_json=as_json)
    sys.exit(exit_code)
