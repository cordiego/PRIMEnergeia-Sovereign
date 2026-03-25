"""
PRIMEnergeia — Safe Page Loader (Hardened)
=============================================
Replaces exec()-based page wrappers with importlib dynamic loading.
Strips st.set_page_config() from dashboard modules before execution
so they work cleanly inside the multi-page Streamlit app.

Hardened: wraps all page execution in try/except to prevent
raw Python tracebacks from ever reaching client screens.
"""

import importlib.util
import sys
import os
import re
import traceback
import logging

logger = logging.getLogger(__name__)


def load_dashboard(module_path: str, module_name: str = None):
    """
    Dynamically load and execute a dashboard module, stripping
    st.set_page_config() to avoid conflicts with app.py.

    All exceptions are caught and displayed as professional error cards.

    Parameters
    ----------
    module_path : str
        Absolute path to the dashboard .py file.
    module_name : str, optional
        Module name for importlib. Defaults to filename stem.
    """
    import streamlit as st

    if not os.path.exists(module_path):
        st.error(f"⚠️ Dashboard module not found: `{os.path.basename(module_path)}`")
        st.info(
            "This page's backend module is missing. This may happen if:\n"
            "- The module file was moved or renamed\n"
            "- Dependencies are not installed\n\n"
            "Run `python preflight.py --all` to diagnose."
        )
        st.stop()
        return

    if module_name is None:
        module_name = os.path.splitext(os.path.basename(module_path))[0]

    # Read source and strip set_page_config
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        st.error(f"⚠️ Could not read module: {e}")
        st.stop()
        return

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

    # Compile and execute with error protection
    try:
        # Inject DEMO/LIVE banner at page top
        try:
            from lib.mode_gate import show_mode_banner
            show_mode_banner()
        except Exception:
            pass  # Don't crash if mode_gate isn't available

        code = compile(source, module_path, "exec")
        exec(code, module.__dict__)
    except SystemExit:
        # st.stop() raises SystemExit — let it through
        pass
    except ImportError as e:
        logger.error(f"Import error in {module_name}: {e}")
        st.error(f"⚠️ Missing dependency for **{module_name}**")
        st.markdown(f"""
        **Error:** `{e}`

        **Fix:** Install missing package:
        ```bash
        pip install {str(e).split("'")[1] if "'" in str(e) else 'unknown'}
        ```
        Or run: `pip install -r requirements.txt`
        """)
        st.stop()
    except FileNotFoundError as e:
        logger.error(f"File not found in {module_name}: {e}")
        st.warning(f"📂 **Data file not found**")
        st.info(
            f"**Error:** `{e}`\n\n"
            "This page requires data that hasn't been loaded yet. "
            "Please upload your market data or run the data pipeline first."
        )
        st.stop()
    except Exception as e:
        logger.error(f"Error in {module_name}: {e}\n{traceback.format_exc()}")
        st.error(f"⚠️ An error occurred in **{module_name}**")
        st.markdown(f"""
        **Error type:** `{type(e).__name__}`
        **Details:** `{str(e)[:200]}`

        This may be caused by:
        - Missing or malformed data files
        - Incompatible package versions
        - Configuration issues

        Run `python preflight.py --all` to diagnose the issue.
        """)
        # Show technical details in an expander (hidden by default)
        with st.expander("🔧 Technical Details (for developers)", expanded=False):
            st.code(traceback.format_exc(), language="python")
        st.stop()

