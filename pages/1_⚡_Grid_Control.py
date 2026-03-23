"""
PRIMEnergeia Sovereign — Grid Control Page
Wraps the existing multi-market SCADA dashboard.
"""
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "dashboard", "dashboard_primenergeia.py")

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
