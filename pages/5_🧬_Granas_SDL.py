"""
PRIMEnergeia — Granas SDL Page Wrapper
Integrates the Self-Driving Lab dashboard into the multi-page app.
"""
import streamlit as st
import sys
import os
import re

# Project root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Read dashboard code
_dashboard_path = os.path.join(_root, "sdl", "dashboard_sdl.py")

if not os.path.exists(_dashboard_path):
    st.error("⚠️ SDL engine not found. Copy `sdl/` folder from Granas-SDL repo.")
    st.code("cp -r ~/Granas-SDL/sdl/ ~/PRIMEnergeia-Sovereign/sdl/")
    st.stop()

with open(_dashboard_path, "r") as f:
    _code = f.read()

# Strip set_page_config (already handled by multi-page app)
_code = re.sub(
    r'st\.set_page_config\s*\(.*?\)',
    '# page_config handled by app.py',
    _code, count=1, flags=re.DOTALL
)

exec(_code)
