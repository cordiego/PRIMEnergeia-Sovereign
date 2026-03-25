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
</style>
""", unsafe_allow_html=True)

# ============================================================
#  HEADER
# ============================================================
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("# ⚡ PRIMEnergeia Sovereign")
    st.caption("UNIFIED COMMAND CENTER — ENERGY · FINANCE · MATERIALS SCIENCE")
with h2:
    st.markdown("<span class='status-live'>● SYSTEMS ONLINE</span>", unsafe_allow_html=True)
    st.link_button("🌐 PRIME Platform ↗", "https://cordiego.github.io/PRIME-Platform/", type="primary")

st.divider()

# ============================================================
#  PRODUCT CARDS
# ============================================================
st.markdown("### Product Suite")
st.markdown("")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00d1ff;'>⚡ Grid Control</div>
        <div class='product-desc'>HJB frequency control. SEN 🇲🇽 ERCOT 🇺🇸 MIBEL 🇪🇸🇵🇹</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>3 MARKETS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_⚡_Grid_Control.py", label="Open →", icon="⚡")

with c2:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #F1C40F;'>🏛️ Eureka Sovereign</div>
        <div class='product-desc'>VIX-Regime Volatility Targeting. 5-asset allocation.</div>
        <div>
            <span class='product-badge'>VIX</span>
            <span class='product-badge'>5 ASSETS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_🏛️_Eureka_Sovereign.py", label="Open →", icon="🏛️")

with c3:
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

c4, c5, c6 = st.columns(3)

with c4:
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

with c5:
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

with c6:
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

c7, c8, c9 = st.columns(3)

with c7:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00c878;'>🏗️ Granas CFRP</div>
        <div class='product-desc'>Structural skeleton. Kirchhoff orthotropic plate + photon recycling ridges.</div>
        <div>
            <span class='product-badge'>KIRCHHOFF</span>
            <span class='product-badge'>17×10.5</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/7_🏗️_Granas_CFRP.py", label="Open →", icon="🏗️")

with c8:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #7B68EE;'>⚗️ Granas GHB</div>
        <div class='product-desc'>Green Haber-Bosch NRR. Mo-N₄ single-site catalyst + decentralized NH₃.</div>
        <div>
            <span class='product-badge'>NRR</span>
            <span class='product-badge'>Mo-N₄</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/8_⚗️_Granas_GHB.py", label="Open →", icon="⚗️")

with c9:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #2ecc71;'>🌿 Granas Albedo</div>
        <div class='product-desc'>535nm spectral selection. Junction cooling + Arrhenius degradation control.</div>
        <div>
            <span class='product-badge'>ALBEDO</span>
            <span class='product-badge'>ARRHENIUS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/9_🌿_Granas_Albedo.py", label="Open →", icon="🌿")

c10, c11, c12 = st.columns(3)

with c10:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00BFFF;'>🛡️ Granas ETFE</div>
        <div class='product-desc'>96% transmittance front encapsulation. Self-cleaning lotus effect.</div>
        <div>
            <span class='product-badge'>ETFE</span>
            <span class='product-badge'>96% T</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/10_🛡️_Granas_ETFE.py", label="Open →", icon="🛡️")

with c11:
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

with c12:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00c878;'>📐 Granas Blueprint</div>
        <div class='product-desc'>Master geometric engine. COMSOL-validated optomechanics + continuous fiber RTM.</div>
        <div>
            <span class='product-badge'>COMSOL</span>
            <span class='product-badge'>RTM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/12_📐_Granas_Blueprint.py", label="Open →", icon="📐")

c13, c14, c15 = st.columns(3)

with c13:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00ffcc;'>🧠 PRIME Kernel</div>
        <div class='product-desc'>Shared IP core. Physics constants, HJB solver, telemetry across all SBUs.</div>
        <div>
            <span class='product-badge'>HJB</span>
            <span class='product-badge'>5 SBUs</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/22_🧠_PRIME_Kernel.py", label="Open →", icon="🧠")

with c14:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #F1C40F;'>📊 CEO Dashboard</div>
        <div class='product-desc'>Fleet monitor. 22 repos, 5 SBUs, $216M TAM. Git status + LOC + revenue.</div>
        <div>
            <span class='product-badge'>FLEET</span>
            <span class='product-badge'>$216M TAM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/23_📊_CEO_Dashboard.py", label="Open →", icon="📊")

with c15:
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

st.markdown("")
st.divider()

# ============================================================
#  KEY METRICS
# ============================================================
st.markdown("### Platform Metrics")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("MARKETS", "3", "SEN · ERCOT · MIBEL")
m2.metric("PAGES", "23", "Full Product Suite")
m3.metric("SBUs", "5", "$216M TAM")
m4.metric("REPOS", "22", "Enterprise Fleet")
m5.metric("FREQUENCY", "50/60 Hz", "Multi-Standard")

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
