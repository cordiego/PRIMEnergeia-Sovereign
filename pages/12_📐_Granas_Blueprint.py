"""PRIMEnergeia — Geometric Blueprint | CEO-Grade Dashboard"""
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
import numpy as np
import plotly.graph_objects as go

st.header("📐 Granas Blueprint — Master Geometric Engine")
st.caption("17×10.5 Dimensional Matrix | COMSOL-Validated Optomechanics | Continuous Fiber RTM")

# ─── KPIs ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📏 Module Area", "1.785 m²")
k2.metric("🔩 Total Vertices", "14")
k3.metric("♻️ Photon Recycling", "89%")
k4.metric("⬇️ Deflection", "1.8 mm")
k5.metric("💪 Rigidity Gain", "+42%")

st.divider()
c1, c2 = st.columns(2)
with c1:
    # Blueprint visualization
    fig = go.Figure()
    # Module outline
    fig.add_shape(type="rect", x0=0, y0=0, x1=17, y1=10.5,
        line=dict(color="#00c878", width=3), fillcolor='rgba(0,200,120,0.05)')
    # Peripheral edges (5.5)
    peripheral = [(0,0,5.5,0), (5.5,0,11,0), (11,0,17,0),
                  (0,10.5,5.5,10.5), (5.5,10.5,11,10.5), (11,10.5,17,10.5)]
    for x0,y0,x1,y1 in peripheral:
        fig.add_trace(go.Scatter(x=[x0,x1], y=[y0,y1], mode='lines',
            line=dict(color='#FF6347', width=4), showlegend=False))
    # Internal diagonal ridges (3.5)
    internal = [(0,0,5.5,5.25), (5.5,5.25,11,0), (11,0,17,5.25),
                (0,10.5,5.5,5.25), (5.5,5.25,11,10.5), (11,10.5,17,5.25)]
    for x0,y0,x1,y1 in internal:
        fig.add_trace(go.Scatter(x=[x0,x1], y=[y0,y1], mode='lines',
            line=dict(color='#FFD700', width=3), showlegend=False))
    # Central network (3.0)
    fig.add_trace(go.Scatter(x=[5.5,5.5], y=[0,10.5], mode='lines',
        line=dict(color='#00BFFF', width=2), showlegend=False))
    fig.add_trace(go.Scatter(x=[11,11], y=[0,10.5], mode='lines',
        line=dict(color='#00BFFF', width=2), showlegend=False))
    fig.add_trace(go.Scatter(x=[0,17], y=[5.25,5.25], mode='lines',
        line=dict(color='#00BFFF', width=2), showlegend=False))
    # Vertices
    vx = [0, 5.5, 11, 17, 0, 5.5, 11, 17, 5.5, 11, 0, 17, 5.5, 11]
    vy = [0, 0, 0, 0, 10.5, 10.5, 10.5, 10.5, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25]
    fig.add_trace(go.Scatter(x=vx, y=vy, mode='markers',
        marker=dict(size=10, color='white', line=dict(color='#00c878', width=2)),
        showlegend=False))
    fig.update_layout(title="17×10.5 Geometric Blueprint (unit scale)",
        xaxis=dict(range=[-1,18], showgrid=False, zeroline=False),
        yaxis=dict(range=[-1,11.5], showgrid=False, zeroline=False, scaleanchor="x"),
        height=350, margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    # Legend annotations
    fig.add_annotation(x=8.5, y=-0.5, text="🔴 5.5u peripheral  🟡 3.5u internal  🔵 3.0u central",
        showarrow=False, font=dict(size=11))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # COMSOL results radar
    cats = ['Rigidity<br>Gain', 'Photon<br>Recycling', 'Crack<br>Arrest',
            'EM Energy<br>Density', 'Weight<br>Savings', 'Jsc<br>Enhancement']
    vals = [42, 89, 95, 13, 77, 12]
    fig2 = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill='toself', fillcolor='rgba(0,200,120,0.15)',
        line=dict(color='#00c878', width=2),
        marker=dict(size=8, color='#00c878')))
    fig2.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100],
            tickfont=dict(size=9)), bgcolor='rgba(0,0,0,0)'),
        title="COMSOL Validation Results (%)",
        height=350, margin=dict(t=50, b=30, l=60, r=60),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)

# ─── Manufacturing ───
st.subheader("🏭 Manufacturing Translation")
m1, m2 = st.columns(2)
with m1:
    st.markdown("""
**Mold Specification:**
- 🔩 Material: CNC-machined aluminum
- 📐 Pattern: 17×10.5 unit matrix
- 🔴 5.5u: Deep channels (anchoring)
- 🟡 3.5u: Medium channels (stress routing)
- 🟢 3.0u: Fine channels (precision vertices)
- 📐 Chamfer: 15° on all ridge walls
    """)
with m2:
    st.markdown("""
**Critical Requirement:**

> ⚠️ Continuous fiber must be **UNINTERRUPTED** across all 3.0-unit central
> vertices and loop through 5.5-unit peripheral triangles — **NO cuts at intersections**

**Method:** Continuous multi-axis robotic resin transfer molding

**Verdict:** _"The exact geometric drawing is an inherently flawless
optomechanical blueprint for solar energy generation"_ — COMSOL validation
    """)
