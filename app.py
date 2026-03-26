import streamlit as st
import sys, os

# Ensure project root is on path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# ============================================================
#  PRIMEnergeia Sovereign — Unified Command Center
#  Multi-Page Hub for All PRIMEnergeia Products
# ============================================================

st.set_page_config(
    page_title="PRIMEnergeia Sovereign | Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Authentication Gate ────────────────────────────────────
from lib.auth_gate import require_auth, logout_button
require_auth()
logout_button()

# ─── Mode Banner ───────────────────────────────────────────
from lib.mode_gate import show_mode_banner
show_mode_banner()

# Premium CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

.main { background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background-color: #050810; }
[data-testid="stSidebar"] { background-color: #0a0f1a; }

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
    border: 1px solid #1a2744;
    border-radius: 8px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0, 209, 255, 0.04);
}
div[data-testid="stMetricValue"] {
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 34px;
    font-weight: 700;
    text-shadow: 0 0 12px rgba(0,209,255,0.3);
}
div[data-testid="stMetricDelta"] {
    font-size: 13px;
}
div[data-testid="stMetricLabel"] {
    color: #94a3b8;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

.product-card {
    background: linear-gradient(135deg, #0d1520, #111b2a);
    border: 1px solid #1a2744;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 16px;
    transition: border-color 0.3s;
}
.product-card:hover { border-color: #00d1ff; }
.product-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}
.product-desc {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.5;
}
.product-badge {
    display: inline-block;
    background: rgba(0, 209, 255, 0.12);
    color: #00d1ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 4px 10px;
    border-radius: 4px;
    margin-right: 8px;
    margin-top: 12px;
}
.status-live {
    display: inline-block;
    background: rgba(0, 255, 136, 0.12);
    color: #00ff88;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 4px;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

/* Animated welcome typing caret */
.hero-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #00d1ff;
    white-space: nowrap;
    overflow: hidden;
    border-right: 2px solid #00d1ff;
    animation: typing 3.5s steps(55, end), blink-caret 0.75s step-end infinite;
    max-width: fit-content;
}
@keyframes typing { from { max-width: 0 } to { max-width: 100% } }
@keyframes blink-caret { 50% { border-color: transparent; } }

/* Glow card hover effect */
.product-card { transition: border-color 0.3s, box-shadow 0.3s, transform 0.2s; }
.product-card:hover {
    border-color: #00d1ff;
    box-shadow: 0 0 20px rgba(0,209,255,0.12);
    transform: translateY(-2px);
}

/* Flagship CTA card */
.cta-card {
    background: linear-gradient(135deg, #0d1a30, #1a1040);
    border: 1px solid rgba(99,102,241,0.4);
    border-radius: 14px;
    padding: 32px;
    text-align: center;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.cta-card:hover {
    border-color: #818cf8;
    box-shadow: 0 0 30px rgba(99,102,241,0.15);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
#  HEADER
# ============================================================
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("# ⚡ PRIMEnergeia Sovereign")
    st.markdown("<div class='hero-tagline'>Dispatching the future of energy — one HJB solve at a time.</div>", unsafe_allow_html=True)
with h2:
    st.markdown("<span class='status-live'>● SYSTEMS ONLINE</span>", unsafe_allow_html=True)
    st.link_button("🌐 PRIME Platform ↗", "https://cordiego.github.io/PRIME-Platform/", type="primary")

st.divider()

# ─── Sidebar Quick-Launch ──────────────────────────────────
st.sidebar.markdown("### 🚀 Quick Launch")
_quick = {
    "⚡ Co-Optimization": "pages/24_⚡_Co_Optimization.py",
    "⚡ Grid Control":    "pages/1_⚡_Grid_Control.py",
    "🧪 Granas Optimizer":"pages/3_🧪_Granas_Optimizer.py",
    "🧠 HJB Control":     "pages/19_🧠_HJB_Control.py",
    "🏭 PRIMStack":       "pages/21_🏭_PRIMStack.py",
    "🔬 Engine Research":  "pages/20_🔬_Engine_Research.py",
    "📂 Data Upload":     "pages/25_📂_Data_Upload.py",
}
for _label, _page in _quick.items():
    st.sidebar.page_link(_page, label=_label)
st.sidebar.divider()

# ============================================================
#  PRODUCT SUITE — ORGANIZED BY DIVISION
# ============================================================

# ────────────────────────────────────────────────────────────
#  ⚡ DIVISION 1: GRID CONTROL & ENERGY
# ────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-top: 24px; margin-bottom: 20px; padding: 16px 24px;
     background: linear-gradient(135deg, #0a1628 0%, #0d1f3c 100%);
     border: 1px solid rgba(0, 209, 255, 0.25); border-radius: 12px;'>
    <div style='font-family: JetBrains Mono; font-size: 11px; color: #00d1ff;
                letter-spacing: 2px; font-weight: 600; margin-bottom: 4px;'>DIVISION 1</div>
    <div style='font-size: 20px; font-weight: 700; color: white;'>⚡ Grid Control & Energy</div>
    <div style='color: #94a3b8; font-size: 13px; margin-top: 4px;'>
        HJB-optimal dispatch across 17 global markets — 1,700+ GW coverage.
    </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00d1ff;'>⚡ Grid Control</div>
        <div class='product-desc'>HJB frequency control. 17 global ISOs — 1,700+ GW</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>17 MARKETS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_⚡_Grid_Control.py", label="Open →", icon="⚡")

with c2:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #26C6DA;'>🔋 Battery Storage</div>
        <div class='product-desc'>LFP / Solid-State / Flow. 400 MWh grid-scale. Degradation + revenue.</div>
        <div>
            <span class='product-badge'>LFP</span>
            <span class='product-badge'>400 MWh</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/15_PRIMEnergeia_Battery.py", label="Open →", icon="🔋")

with c3:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #42A5F5;'>🌊 PRIM Wind</div>
        <div class='product-desc'>Offshore + onshore. 15 MW direct-drive turbines. Green H₂ integration.</div>
        <div>
            <span class='product-badge'>15 MW</span>
            <span class='product-badge'>H₂ READY</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/17_PRIM_Wind.py", label="Open →", icon="🌊")

c4, c5, c6 = st.columns(3)

with c4:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #AB47BC;'>🧠 HJB Control</div>
        <div class='product-desc'>Hamilton-Jacobi-Bellman dispatch optimizer. Min-fuel engine scheduling.</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>DISPATCH</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/19_🧠_HJB_Control.py", label="Open →", icon="🧠")

with c5:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #78909C;'>🏭 PRIMStack</div>
        <div class='product-desc'>Unified plant integrator. Solar+Wind+Engines+BESS+H₂ as one system.</div>
        <div>
            <span class='product-badge'>STACK</span>
            <span class='product-badge'>MULTI-HJB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/21_🏭_PRIMStack.py", label="Open →", icon="🏭")

with c6:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00d1ff;'>📂 Data Upload</div>
        <div class='product-desc'>Upload client CSV. Auto-detect format. Quality report + validation.</div>
        <div>
            <span class='product-badge'>UPLOAD</span>
            <span class='product-badge'>VALIDATE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/25_📂_Data_Upload.py", label="Open →", icon="📂")

# ── Flagship CTA — Co-Optimization ──
st.markdown("")
st.markdown("""
<div class='cta-card'>
    <div style='font-family: JetBrains Mono; font-size: 11px; color: #818cf8;
                letter-spacing: 2px; font-weight: 600; margin-bottom: 8px;'>FLAGSHIP TOOL</div>
    <div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 700;
                color: white; margin-bottom: 8px;'>⚡ Multi-Market Co-Optimization Engine</div>
    <div style='color: #94a3b8; font-size: 14px; margin-bottom: 16px;'>
        55.7% dispatch uplift · 36.9× price spread · 25% value share<br>
        17 global markets · 1,700+ GW — Configure your fleet and see your ROI in seconds.
    </div>
    <span class='product-badge'>HJB TWO-PASS</span>
    <span class='product-badge'>17 MARKETS</span>
    <span class='product-badge'>BACKTEST-VALIDATED</span>
</div>
""", unsafe_allow_html=True)
st.page_link("pages/24_⚡_Co_Optimization.py", label="🚀 Launch Co-Optimizer →", icon="⚡")

# ────────────────────────────────────────────────────────────
#  🏛️ DIVISION 2: EUREKA TRADING
# ────────────────────────────────────────────────────────────
st.markdown("")
st.markdown("""
<div style='margin-top: 32px; margin-bottom: 20px; padding: 16px 24px;
     background: linear-gradient(135deg, #1a1a0a 0%, #2a2200 100%);
     border: 1px solid rgba(241, 196, 15, 0.25); border-radius: 12px;'>
    <div style='font-family: JetBrains Mono; font-size: 11px; color: #F1C40F;
                letter-spacing: 2px; font-weight: 600; margin-bottom: 4px;'>DIVISION 2</div>
    <div style='font-size: 20px; font-weight: 700; color: white;'>🏛️ Eureka Trading</div>
    <div style='color: #94a3b8; font-size: 13px; margin-top: 4px;'>
        VIX-regime volatility targeting. Automated daily signals & portfolio allocation.
    </div>
</div>
""", unsafe_allow_html=True)

eu1, eu2 = st.columns([2, 1])

with eu1:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #F1C40F;'>🏛️ Eureka Sovereign</div>
        <div class='product-desc'>VIX-Regime Volatility Targeting. 5-asset allocation (equities, bonds, commodities, crypto, alternatives). GBM simulation + Markowitz optimization + Kelly criterion. Automated daily signals via Telegram.</div>
        <div>
            <span class='product-badge'>VIX REGIME</span>
            <span class='product-badge'>5 ASSETS</span>
            <span class='product-badge'>KELLY</span>
            <span class='product-badge'>TELEGRAM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_🏛️_Eureka_Sovereign.py", label="Open Eureka →", icon="🏛️")

with eu2:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1a1a0a, #2a2200);
         border: 1px solid rgba(241, 196, 15, 0.15); border-radius: 12px;
         padding: 24px; text-align: center;'>
        <div style='font-size: 36px; margin-bottom: 8px;'>📈</div>
        <div style='font-family: JetBrains Mono; font-size: 13px; color: #F1C40F;
                    font-weight: 600;'>Model: 2/20</div>
        <div style='color: #94a3b8; font-size: 12px; margin-top: 4px;'>
            2% management + 20% performance
        </div>
    </div>
    """, unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
#  🔬 DIVISION 3: MATERIALS, ENGINES & RESEARCH
# ────────────────────────────────────────────────────────────
st.markdown("")
st.markdown("""
<div style='margin-top: 32px; margin-bottom: 20px; padding: 16px 24px;
     background: linear-gradient(135deg, #0a1a0f 0%, #0d2a1a 100%);
     border: 1px solid rgba(0, 255, 136, 0.20); border-radius: 12px;'>
    <div style='font-family: JetBrains Mono; font-size: 11px; color: #00ff88;
                letter-spacing: 2px; font-weight: 600; margin-bottom: 4px;'>DIVISION 3</div>
    <div style='font-size: 20px; font-weight: 700; color: white;'>🔬 Materials, Engines & Research</div>
    <div style='color: #94a3b8; font-size: 13px; margin-top: 4px;'>
        Granas perovskite suite · PRIMEngines propulsion · Circular economy · Platform core
    </div>
</div>
""", unsafe_allow_html=True)

# Granas Row 1
g1, g2, g3 = st.columns(3)

with g1:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00ff88;'>🧪 Granas Optimizer</div>
        <div class='product-desc'>Bayesian perovskite optimizer. 6D GP + EI acquisition.</div>
        <div>
            <span class='product-badge'>BAYESIAN</span>
            <span class='product-badge'>6D</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_🧪_Granas_Optimizer.py", label="Open →", icon="🧪")

with g2:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #8a2be2;'>🔬 Granas Optics</div>
        <div class='product-desc'>Mie + TMM light-trapping. AM1.5G + HJB optimizer.</div>
        <div>
            <span class='product-badge'>MIE + TMM</span>
            <span class='product-badge'>HJB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_🔬_Granas_Optics.py", label="Open →", icon="🔬")

with g3:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00ffcc;'>🧬 Granas SDL</div>
        <div class='product-desc'>Self-Driving Lab. HJB fabrication + active learning.</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>SDL</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/5_🧬_Granas_SDL.py", label="Open →", icon="🧬")

# Granas Row 2
g4, g5, g6 = st.columns(3)

with g4:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #ffd700;'>📊 Granas Metrics</div>
        <div class='product-desc'>Holistic twin. Cross-product performance analytics.</div>
        <div>
            <span class='product-badge'>RADAR</span>
            <span class='product-badge'>PARETO</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/6_📊_Granas_Metrics.py", label="Open →", icon="📊")

with g5:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00c878;'>🏗️ Granas CFRP</div>
        <div class='product-desc'>Structural skeleton. Kirchhoff orthotropic plate + photon recycling.</div>
        <div>
            <span class='product-badge'>KIRCHHOFF</span>
            <span class='product-badge'>17×10.5</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/7_🏗️_Granas_CFRP.py", label="Open →", icon="🏗️")

with g6:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #7B68EE;'>⚗️ Granas GHB</div>
        <div class='product-desc'>Green Haber-Bosch NRR. Mo-N₄ catalyst + decentralized NH₃.</div>
        <div>
            <span class='product-badge'>NRR</span>
            <span class='product-badge'>Mo-N₄</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/8_⚗️_Granas_GHB.py", label="Open →", icon="⚗️")

# Granas Row 3
g7, g8, g9 = st.columns(3)

with g7:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #2ecc71;'>🌿 Granas Albedo</div>
        <div class='product-desc'>535nm spectral selection. Junction cooling + Arrhenius control.</div>
        <div>
            <span class='product-badge'>ALBEDO</span>
            <span class='product-badge'>ARRHENIUS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/9_🌿_Granas_Albedo.py", label="Open →", icon="🌿")

with g8:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00BFFF;'>🛡️ Granas ETFE</div>
        <div class='product-desc'>96% transmittance front encapsulation. Self-cleaning lotus.</div>
        <div>
            <span class='product-badge'>ETFE</span>
            <span class='product-badge'>96% T</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/10_🛡️_Granas_ETFE.py", label="Open →", icon="🛡️")

with g9:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #FF6347;'>🔬 Granas TOPCon</div>
        <div class='product-desc'>n-type Cz silicon bottom cell. 1.5nm tunnel oxide + >720mV Voc.</div>
        <div>
            <span class='product-badge'>TOPCon</span>
            <span class='product-badge'>n-Cz</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/11_🔬_Granas_TOPCon.py", label="Open →", icon="🔬")

# Granas Row 4 + Engines
g10, g11, g12 = st.columns(3)

with g10:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00c878;'>📐 Granas Blueprint</div>
        <div class='product-desc'>Master geometric engine. COMSOL-validated optomechanics.</div>
        <div>
            <span class='product-badge'>COMSOL</span>
            <span class='product-badge'>RTM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/12_📐_Granas_Blueprint.py", label="Open →", icon="📐")

with g11:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #FF8C00;'>🏭 Granas Scale</div>
        <div class='product-desc'>Industrial scaling 100MW→10GW. BOM, LCOE, multi-revenue.</div>
        <div>
            <span class='product-badge'>100MW→10GW</span>
            <span class='product-badge'>BOM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/13_🏭_Granas_Scale.py", label="Open →", icon="🏭")

with g12:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #E040FB;'>🧠 SIBO API</div>
        <div class='product-desc'>Sol-Ink Bayesian Optimizer. GP Matern 5/2 + EI. SaaS-ready.</div>
        <div>
            <span class='product-badge'>GP</span>
            <span class='product-badge'>SaaS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/14_🧠_SIBO_API.py", label="Open →", icon="🧠")

# Engines + Circular + Platform
g13, g14, g15 = st.columns(3)

with g13:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #EF5350;'>🚀 PRIMEngines</div>
        <div class='product-desc'>Zero-carbon propulsion. NH₃ ICE · PEM fuel cell · H₂ turbine.</div>
        <div>
            <span class='product-badge'>NH₃/H₂</span>
            <span class='product-badge'>ZERO CO₂</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/18_PRIMEngines.py", label="Open →", icon="🚀")

with g14:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #FFA726;'>🔬 Engine Research</div>
        <div class='product-desc'>Live physics lab. Performance maps, polarization curves, Brayton.</div>
        <div>
            <span class='product-badge'>6 ENGINES</span>
            <span class='product-badge'>PHYSICS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/20_🔬_Engine_Research.py", label="Open →", icon="🔬")

with g15:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #66BB6A;'>♻️ PRIMEcycle</div>
        <div class='product-desc'>Circular economy. 97.3% material recovery. Zero-waste EOL.</div>
        <div>
            <span class='product-badge'>RECYCLE</span>
            <span class='product-badge'>97.3%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/16_PRIMEcycle.py", label="Open →", icon="♻️")

# Platform Core
g16, g17 = st.columns([1, 1])

with g16:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00ffcc;'>🧠 PRIME Kernel</div>
        <div class='product-desc'>Shared IP core. Physics constants, HJB solver, telemetry across all divisions.</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>3 DIVS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/22_🧠_PRIME_Kernel.py", label="Open →", icon="🧠")

with g17:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #F1C40F;'>📊 CEO Dashboard</div>
        <div class='product-desc'>Fleet monitor. 22 repos, 3 divisions, $5B+ TAM. Git status + LOC + revenue.</div>
        <div>
            <span class='product-badge'>FLEET</span>
            <span class='product-badge'>$5B+ TAM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/23_📊_CEO_Dashboard.py", label="Open →", icon="📊")

st.markdown("")
st.divider()

# ============================================================
#  KEY METRICS
# ============================================================
st.markdown("### Platform Metrics")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("MARKETS", "17", "1,700+ GW Global")
m2.metric("PAGES", "25", "Full Product Suite")
m3.metric("DIVISIONS", "3", "Grid · Eureka · Research")
m4.metric("ENGINES", "6", "NH₃ · H₂ · Turbine")
m5.metric("REPOS", "22", "Enterprise Fleet")
m6.metric("FREQUENCY", "50/60 Hz", "Multi-Standard")

st.markdown("")

# ============================================================
#  FOOTER
# ============================================================
st.divider()
st.markdown("""
<div style='text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;'>
    PRIMEnergeia S.A.S. | Lead Computational Physicist: Diego Córdoba Urrutia<br>
    <a href="https://cordiego.github.io/PRIME-Platform/" target="_blank" style="color: #00d1ff; text-decoration: none; font-weight: 600;">🌐 PRIME Platform</a>
    &nbsp;·&nbsp; Soberanía Energética Global ⚡🇲🇽🇺🇸🇪🇸🇵🇹
</div>
""", unsafe_allow_html=True)
