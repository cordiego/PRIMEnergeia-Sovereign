"""PRIMEnergeia — CEO Executive Dashboard (Streamlit)"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
# --- End Banner ---
import streamlit as st
import subprocess
import os
from datetime import datetime

st.markdown("""<style>
[data-testid="stMetricValue"] {font-size: 26px !important}
[data-testid="stMetricLabel"] {font-size: 13px !important; font-weight: 600}
.sbu-card {
    background: linear-gradient(135deg, #0d1520, #111b2a);
    border: 1px solid #1a2744;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
}
.sbu-title { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; }
.repo-row { font-size: 13px; color: #94a3b8; margin: 4px 0; }
</style>""", unsafe_allow_html=True)

st.header("📊 CEO Executive Dashboard")
st.caption("Fleet Monitor — 22 Repos · 5 SBUs · $216M TAM | PRIMEnergeia S.A.S.")

st.divider()

# ═══════════════════════════════════════════════════════════════
#  SBU DEFINITIONS
# ═══════════════════════════════════════════════════════════════
SBUS = {
    "🔌 PRIME Grid": {
        "color": "#00d1ff", "tam": 48, "status": "🟢 LIVE",
        "model": "Enterprise Contracts + 25% Royalties",
        "repos": ["PRIMEnergeia-Sovereign", "PRIMStack"],
    },
    "⚡ PRIME Power": {
        "color": "#ff6347", "tam": 25, "status": "🟢 LIVE",
        "model": "IP Licensing to Manufacturers",
        "repos": ["PRIMEngines-AICE", "PRIMEngines-PEM", "PRIMEngines-HYP",
                  "PRIMEnergeia-Battery", "PRIM-Wind"],
    },
    "♻️ PRIME Circular": {
        "color": "#2ecc71", "tam": 8, "status": "🟡 ACTIVE",
        "model": "Carbon Credits + Consulting",
        "repos": ["PRIMEcycle"],
    },
    "📈 PRIME Quant": {
        "color": "#F1C40F", "tam": 15, "status": "🟢 LIVE",
        "model": "Fund Management + Hedge Fund",
        "repos": ["Eureka-Sovereign"],
    },
    "🧪 PRIME Materials": {
        "color": "#8a2be2", "tam": 120, "status": "🔵 R&D",
        "model": "Deep Tech IP + Patents",
        "repos": ["Granas-Sovereign", "Granas-Optics", "Granas-SDL", "Granas-CFRP",
                  "Granas-GHB", "Granas-Albedo", "Granas-ETFE", "Granas-TOPCon",
                  "Granas-Blueprint", "Granas-Metrics", "Granas-Scale"],
    },
    "🧠 PRIME Kernel": {
        "color": "#00ffcc", "tam": 0, "status": "⚙️ INFRA",
        "model": "Shared IP Core",
        "repos": ["PRIME-Kernel", "PRIME-Dashboard"],
    },
}

BASE = os.path.expanduser("~")


def scan_repo(name):
    """Quick scan of a repo."""
    path = os.path.join(BASE, name)
    info = {"name": name, "exists": os.path.isdir(os.path.join(path, ".git"))}
    if not info["exists"]:
        info.update({"status": "❌ MISSING", "commit": "—", "loc": 0})
        return info
    try:
        r = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                           capture_output=True, text=True, timeout=3)
        dirty = len(r.stdout.strip()) > 0
        info["status"] = "📝 DIRTY" if dirty else "✅ CLEAN"
    except Exception:
        info["status"] = "❓"
    try:
        r = subprocess.run(["git", "-C", path, "log", "-1", "--format=%ar"],
                           capture_output=True, text=True, timeout=3)
        info["commit"] = r.stdout.strip() or "—"
    except Exception:
        info["commit"] = "—"
    # Count Python LOC
    loc = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "build")]
        for f in files:
            if f.endswith(".py"):
                try:
                    with open(os.path.join(root, f), errors="ignore") as fh:
                        loc += sum(1 for l in fh if l.strip() and not l.strip().startswith("#"))
                except Exception:
                    pass
    info["loc"] = loc
    return info


# ═══════════════════════════════════════════════════════════════
#  FLEET SCAN
# ═══════════════════════════════════════════════════════════════
if st.button("🔍 Scan Fleet", type="primary"):
    all_scans = []
    total_loc = 0
    progress = st.progress(0, text="Scanning repos...")
    all_repos = [r for sbu in SBUS.values() for r in sbu["repos"]]

    for i, repo in enumerate(all_repos):
        scan = scan_repo(repo)
        all_scans.append(scan)
        total_loc += scan["loc"]
        progress.progress((i + 1) / len(all_repos), text=f"Scanning {repo}...")

    progress.empty()

    # Summary
    st.markdown("### 🏁 Fleet Summary")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("REPOS", len(all_scans))
    m2.metric("TOTAL LOC", f"{total_loc:,}")
    m3.metric("CLEAN", sum(1 for s in all_scans if "CLEAN" in s["status"]))
    m4.metric("DIRTY", sum(1 for s in all_scans if "DIRTY" in s["status"]))
    m5.metric("TAM", f"${sum(s['tam'] for s in SBUS.values())}M")

    st.divider()

    # Per-SBU breakdown
    for sbu_name, sbu in SBUS.items():
        color = sbu["color"]
        st.markdown(f"""<div class="sbu-card">
            <div class="sbu-title" style="color: {color};">{sbu_name}</div>
            <div class="repo-row">{sbu['status']} · TAM: ${sbu['tam']}M · {sbu['model']}</div>
        </div>""", unsafe_allow_html=True)

        for repo_name in sbu["repos"]:
            scan = next((s for s in all_scans if s["name"] == repo_name), None)
            if scan:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
                c1.markdown(f"**{scan['name']}**")
                c2.markdown(f"`{scan['loc']:,}` LOC")
                c3.markdown(scan["status"])
                c4.markdown(f"_{scan['commit']}_")

        st.markdown("")

    st.session_state["last_scan"] = all_scans
    st.session_state["last_scan_time"] = datetime.now().strftime("%H:%M:%S")

else:
    # Static view without scan
    st.markdown("### 🏗️ Strategic Business Units")

    total_tam = 0
    total_repos = 0
    for sbu_name, sbu in SBUS.items():
        color = sbu["color"]
        total_tam += sbu["tam"]
        total_repos += len(sbu["repos"])

        st.markdown(f"""<div class="sbu-card">
            <div class="sbu-title" style="color: {color};">{sbu_name}</div>
            <div class="repo-row">{sbu['status']} · TAM: ${sbu['tam']}M · {len(sbu['repos'])} repos · {sbu['model']}</div>
            <div class="repo-row">{'  ·  '.join(sbu['repos'])}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL REPOS", total_repos)
    m2.metric("TOTAL TAM", f"${total_tam}M")
    m3.metric("SBUs", len(SBUS))

    st.info("Press **🔍 Scan Fleet** to get live git status, LOC counts, and commit history for all repos.")

# ═══════════════════════════════════════════════════════════════
#  TAM BREAKDOWN CHART
# ═══════════════════════════════════════════════════════════════
st.divider()
st.markdown("### 💰 TAM Distribution")

import plotly.graph_objects as go

names = [n for n in SBUS.keys() if SBUS[n]["tam"] > 0]
tams = [SBUS[n]["tam"] for n in names]
colors = [SBUS[n]["color"] for n in names]

fig = go.Figure(data=[go.Pie(
    labels=names, values=tams,
    marker=dict(colors=colors),
    textinfo="label+percent",
    textfont=dict(size=13),
    hole=0.45,
)])
fig.update_layout(
    template="plotly_dark", height=400,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    showlegend=False,
    annotations=[dict(text=f"${sum(tams)}M", x=0.5, y=0.5,
                      font_size=28, font_color="#00d1ff", showarrow=False)],
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(f"PRIMEnergeia S.A.S. — CEO Executive Dashboard | "
           f"Last scan: {st.session_state.get('last_scan_time', 'not yet')}")
