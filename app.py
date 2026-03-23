import streamlit as st

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
    font-size: 28px;
    font-weight: 700;
}
div[data-testid="stMetricLabel"] {
    color: #6b7fa3;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 1.5px;
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
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
}
.product-desc {
    color: #6b7fa3;
    font-size: 14px;
    line-height: 1.6;
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
    st.caption("Navigate using the sidebar →")

st.divider()

# ============================================================
#  PRODUCT CARDS
# ============================================================
st.markdown("### Product Suite")
st.markdown("")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00d1ff;'>⚡ Grid Control</div>
        <div class='product-desc'>
            Multi-market HJB optimal frequency control.
            SCADA for SEN 🇲🇽, ERCOT 🇺🇸, MIBEL 🇪🇸🇵🇹.
        </div>
        <div>
            <span class='product-badge'>HJB CONTROL</span>
            <span class='product-badge'>3 MARKETS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_⚡_Grid_Control.py", label="Open Grid Control →", icon="⚡")

with c2:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #F1C40F;'>🏛️ Eureka Sovereign</div>
        <div class='product-desc'>
            VIX-Regime Volatility Targeting Engine.
            Regime-switching allocation across 5 assets.
        </div>
        <div>
            <span class='product-badge'>VIX REGIMES</span>
            <span class='product-badge'>5 ASSETS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_🏛️_Eureka_Sovereign.py", label="Open Eureka →", icon="🏛️")

with c3:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #00ff88;'>🧪 Granas Optimizer</div>
        <div class='product-desc'>
            Bayesian Optimizer for perovskite solar cells.
            6D physics-informed GP + EI acquisition.
        </div>
        <div>
            <span class='product-badge'>BAYESIAN OPT</span>
            <span class='product-badge'>6D SEARCH</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_🧪_Granas_Optimizer.py", label="Open Granas →", icon="🧪")

with c4:
    st.markdown("""
    <div class='product-card'>
        <div class='product-title' style='color: #8a2be2;'>🔬 Granas Optics</div>
        <div class='product-desc'>
            Mie scattering + TMM light-trapping sim.
            AM1.5G solar, Yablonovitch limit analysis.
        </div>
        <div>
            <span class='product-badge'>MIE + TMM</span>
            <span class='product-badge'>PHOTON CAGE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_🔬_Granas_Optics.py", label="Open Optics →", icon="🔬")

st.markdown("")
st.divider()

# ============================================================
#  KEY METRICS
# ============================================================
st.markdown("### Platform Metrics")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("MARKETS", "3", "SEN · ERCOT · MIBEL")
m2.metric("GRID NODES", "72", "Multi-Continental")
m3.metric("PORTFOLIO ASSETS", "5", "VIX-Regime Managed")
m4.metric("OPTIMIZATION", "6D", "Perovskite Search Space")
m5.metric("FREQUENCY", "50/60 Hz", "Multi-Standard")

st.markdown("")

# ============================================================
#  FOOTER
# ============================================================
st.divider()
st.markdown("""
<div style='text-align: center; color: #3a4a6b; font-family: JetBrains Mono; font-size: 11px; padding: 16px 0;'>
    PRIMEnergeia S.A.S. | Lead Computational Physicist: Diego Córdoba Urrutia<br>
    Soberanía Energética Global ⚡🇲🇽🇺🇸🇪🇸🇵🇹
</div>
""", unsafe_allow_html=True)
