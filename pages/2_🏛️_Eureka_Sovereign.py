"""
Eureka Sovereign — VIX-Regime Vol-Targeting Page
Uses lib/page_loader for safe dynamic loading.
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from lib.page_loader import load_dashboard

# Try local copy first, then external Eureka repo
_candidates = [
    os.path.join(_root, "dashboard", "dashboard_eureka.py"),
    os.path.expanduser("~/Eureka-Sovereign/dashboard/dashboard_eureka.py"),
]

_path = next((p for p in _candidates if os.path.exists(p)), None)

if _path is None:
    import streamlit as st
    st.error("⚠️ Eureka dashboard not found. Copy dashboard_eureka.py to dashboard/")
    st.stop()
else:
    load_dashboard(_path)
