"""
Granas Optimizer — Bayesian Optimization Page
Wraps the Granas dashboard for the unified multi-page app.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Read and exec the Granas dashboard
_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "optimization", "granas_dashboard.py")

if not os.path.exists(_dashboard_path):
    import streamlit as st
    st.error("⚠️ Granas dashboard not found at optimization/granas_dashboard.py")
    st.stop()

with open(_dashboard_path, "r") as f:
    _code = f.read()

# Remove set_page_config block
_code = _code.replace(
    """st.set_page_config(
    page_title="Granas Sovereign | Perovskite Optimizer",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)""",
    "# page_config handled by app.py"
)

exec(_code)
