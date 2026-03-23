import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "optimization", "granas_dashboard.py")
with open(_p) as f:
          _c = f.read()
      import re
_c = re.sub(r'st\.set_page_config\s*\(.*?\)', 'pass', _c, flags=re.DOTALL)
exec(_c)
