"""
PRIMEnergeia — Granas Metrics Page Wrapper
"""
import streamlit as st
import sys, os, re, importlib, importlib.util, types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Remap: metrics_twin → metrics (so dashboard_metrics.py can import from "metrics.granas_metrics")
_metrics_twin = os.path.join(_root, "metrics_twin")
if os.path.exists(_metrics_twin) and "metrics" not in sys.modules:
    metrics_mod = types.ModuleType("metrics")
    metrics_mod.__path__ = [_metrics_twin]
    sys.modules["metrics"] = metrics_mod

    spec = importlib.util.spec_from_file_location(
        "metrics.granas_metrics",
        os.path.join(_metrics_twin, "granas_metrics.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["metrics.granas_metrics"] = mod

_dashboard = os.path.join(_metrics_twin, "dashboard_metrics.py")
if not os.path.exists(_dashboard):
    st.error("⚠️ Metrics engine not found. Ensure `metrics_twin/` folder exists.")
    st.stop()

with open(_dashboard, "r") as f:
    _code = f.read()

_code = re.sub(
    r'st\.set_page_config\s*\(.*?\)',
    '# page_config handled by app.py',
    _code, count=1, flags=re.DOTALL
)
exec(_code)
