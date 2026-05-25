"""
PRIMEnergeia — Granas Metrics Page Wrapper
"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
try:
    from lib.granas_handshake import show_handshake_sidebar
    show_handshake_sidebar()
except Exception: pass
# --- End Banner ---
import streamlit as st
import sys, os, re, importlib, importlib.util, types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Always register metrics_twin as "metrics" (force reload for new classes)
_metrics_twin = os.path.join(_root, "metrics_twin")
if os.path.exists(_metrics_twin):
    # Register package
    metrics_mod = types.ModuleType("metrics")
    metrics_mod.__path__ = [_metrics_twin]
    sys.modules["metrics"] = metrics_mod

    # Force-load granas_metrics with all classes
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
