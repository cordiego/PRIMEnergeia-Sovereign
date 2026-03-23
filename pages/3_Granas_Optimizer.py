import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "optimization", "granas_dashboard.py")
_c = open(_p).read()
_c = re.sub(r'st\.set_page_config\s*\(.*?\)', 'pass', _c, flags=re.DOTALL)
exec(_c)
