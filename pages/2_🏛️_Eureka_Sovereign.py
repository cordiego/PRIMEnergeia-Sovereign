"""
Eureka Sovereign — VIX-Regime Vol-Targeting Page
Wraps the Eureka dashboard for the unified multi-page app.
"""
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check candidate paths for the Eureka dashboard
_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "dashboard", "dashboard_eureka.py"),
    os.path.expanduser("~/Eureka-Sovereign/dashboard/dashboard_eureka.py"),
]

_dashboard_path = None
for _p in _candidates:
    if os.path.exists(_p):
        _dashboard_path = _p
        break

if _dashboard_path is None:
    import streamlit as st
    st.error("⚠️ Eureka dashboard not found. Please copy dashboard_eureka.py to dashboard/")
    st.stop()

with open(_dashboard_path, "r") as f:
    _code = f.read()

# Robustly remove set_page_config block (handles any formatting)
_code = re.sub(
    r'st\.set_page_config\s*\(.*?\)',
    '# page_config handled by app.py',
    _code,
    count=1,
    flags=re.DOTALL
)

exec(_code)
