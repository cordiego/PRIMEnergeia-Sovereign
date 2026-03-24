"""
PRIMEnergeia — Safe Page Loader
================================
Replaces exec()-based page wrappers with importlib dynamic loading.
Strips st.set_page_config() from dashboard modules before execution
so they work cleanly inside the multi-page Streamlit app.
"""

import importlib.util
import sys
import os
import re


def load_dashboard(module_path: str, module_name: str = None):
    """
    Dynamically load and execute a dashboard module, stripping
    st.set_page_config() to avoid conflicts with app.py.
    
    Parameters
    ----------
    module_path : str
        Absolute path to the dashboard .py file.
    module_name : str, optional
        Module name for importlib. Defaults to filename stem.
    """
    import streamlit as st

    if not os.path.exists(module_path):
        st.error(f"⚠️ Dashboard not found: {module_path}")
        st.stop()
        return

    if module_name is None:
        module_name = os.path.splitext(os.path.basename(module_path))[0]

    # Read source and strip set_page_config
    with open(module_path, "r") as f:
        source = f.read()

    source = re.sub(
        r'st\.set_page_config\s*\(.*?\)',
        '# page_config handled by app.py',
        source,
        count=1,
        flags=re.DOTALL,
    )

    # Create a proper module spec and execute
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = importlib.util.module_from_spec(spec)

    # Ensure project root is on path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Set module attributes for correct __file__ resolution
    module.__file__ = module_path
    module.__name__ = module_name

    # Register the module so internal imports work
    sys.modules[module_name] = module

    # Compile and execute
    code = compile(source, module_path, "exec")
    exec(code, module.__dict__)
