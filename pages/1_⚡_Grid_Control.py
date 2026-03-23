"""
PRIMEnergeia Sovereign — Grid Control Page
Wraps the existing multi-market SCADA dashboard.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import time

# Read and exec the dashboard, skipping set_page_config
_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "dashboard", "dashboard_primenergeia.py")

with open(_dashboard_path, "r") as f:
    _code = f.read()

# Remove set_page_config block (it's already set by app.py)
_code = _code.replace(
    """st.set_page_config(
    page_title="PRIMEnergeia Sovereign | Grid Control",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)""",
    "# page_config handled by app.py"
)

exec(_code)
