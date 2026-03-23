import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "dashboard_primenergeia.py")
with open(_p) as f:
    _c = f.read()
_c = _c.replace('st.set_page_config(', '# st.set_page_config(').replace('initial_sidebar_state="expanded"\n)', 'initial_sidebar_state="expanded"#)')
exec(_c)
