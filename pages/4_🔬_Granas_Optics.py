"""
Granas Optics — Light-Trapping Simulator Page
Wraps the optics dashboard for the unified multi-page app.
"""
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "optics", "dashboard_optics.py")

if not os.path.exists(_dashboard_path):
    import streamlit as st
    st.error("⚠️ Optics dashboard not found at optics/dashboard_optics.py")
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
