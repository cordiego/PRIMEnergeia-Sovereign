"""
Granas Optimizer — Bayesian Optimization Page
Uses lib/page_loader for safe dynamic loading.
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from lib.page_loader import load_dashboard

load_dashboard(os.path.join(_root, "optimization", "granas_dashboard.py"))
