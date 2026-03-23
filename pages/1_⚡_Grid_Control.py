"""
PRIMEnergeia Sovereign — Grid Control Page
Wraps the existing multi-market SCADA dashboard.
"""
import streamlit as st
import sys
import os
import re

# Add project root to path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_dashboard_path = os.path.join(_root, "dashboard", "dashboard_primenergeia.py")

if not os.path.exists(_dashboard_path):
    st.error("⚠️ Grid Control dashboard not found at dashboard/dashboard_primenergeia.py")
    st.stop()

with open(_dashboard_path, "r") as f:
    _code = f.read()

# Remove set_page_config (handled by app.py)
_code = re.sub(
    r'st\.set_page_config\s*\(.*?\)',
    '# page_config handled by app.py',
    _code, count=1, flags=re.DOTALL
)

exec(_code)
