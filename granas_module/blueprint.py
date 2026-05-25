"""
Granas Blueprint — Master Geometric Tessellation Visualization
================================================================
Faithful reproduction of the hand-drawn master blueprint:
  2.1m × 3.4m production module
  4 interlocking rhombi (2 columns × 2 rows) + edge triangles
  CFRP structural ridges at every edge

Geometry (derived from hand-drawn reference Granas_Module_ref.png):
  - 7 vertex rows (alternating 3-2-3-2-3-2-3)
  - Triangle edges at top/bottom corners: 0.9 m
  - Rhombus edges in the interior: ~0.714 m
  - 4 main diamond facets in the center
  - Triangles fill corners and sides

Vertex y-positions (calculated from 0.9m triangle constraint):
  y₁ = √(0.9² - (W/4)²) = 0.731 m     (bottom interior row)
  y₂ = (y₁ + H/2) / 2   = 1.216 m     (lower-middle edge row)
  y₃ = H/2              = 1.700 m     (center interior row)
  y₄ = H - y₂           = 2.184 m     (upper-middle edge row)
  y₅ = H - y₁           = 2.669 m     (top interior row)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import math

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# ─── Module Dimensions (meters) ─────────────────────────────
W = 2.1    # Module width  (m)
H = 3.4    # Module height (m)

# ─── Vertex Positions ───────────────────────────────────────
# X-positions
X_L  = 0.0          # Left edge
X_Q1 = W / 4        # 0.525 m  (quarter)
X_M  = W / 2        # 1.05 m   (center)
X_Q3 = 3 * W / 4    # 1.575 m  (three-quarter)
X_R  = W             # 2.1 m    (right edge)

# Y-positions (from 0.9m triangle edge constraint)
TRIANGLE_EDGE = 0.9   # meters — top/bottom diagonal edges
Y1 = math.sqrt(TRIANGLE_EDGE**2 - X_Q1**2)   # 0.731 m
Y2 = (Y1 + H / 2) / 2                         # 1.216 m (equal rhombus edges)
Y3 = H / 2                                     # 1.700 m
Y4 = H - Y2                                    # 2.184 m
Y5 = H - Y1                                    # 2.669 m

# Edge lengths
RHOMBUS_EDGE = math.sqrt(X_Q1**2 + (Y2 - Y1)**2)  # ~0.714 m


def _build_vertices():
    """
    Build vertex rows for the 7-row diamond tessellation.

    Row 0: y=0      → 3 pts (bottom edge)
    Row 1: y=Y1     → 2 pts (interior)
    Row 2: y=Y2     → 3 pts (lower-middle, on perimeter + center)
    Row 3: y=Y3     → 2 pts (center interior)
    Row 4: y=Y4     → 3 pts (upper-middle, on perimeter + center)
    Row 5: y=Y5     → 2 pts (interior)
    Row 6: y=H      → 3 pts (top edge)
    """
    return [
        [(X_L, 0),  (X_M, 0),  (X_R, 0)],      # Row 0
        [(X_Q1, Y1), (X_Q3, Y1)],                 # Row 1
        [(X_L, Y2), (X_M, Y2), (X_R, Y2)],       # Row 2
        [(X_Q1, Y3), (X_Q3, Y3)],                 # Row 3
        [(X_L, Y4), (X_M, Y4), (X_R, Y4)],       # Row 4
        [(X_Q1, Y5), (X_Q3, Y5)],                 # Row 5
        [(X_L, H),  (X_M, H),  (X_R, H)],        # Row 6
    ]


def _build_edges(rows):
    """
    Build all edges: diagonals between adjacent rows + perimeter.
    """
    edges = []

    # Diagonal edges between adjacent rows
    for i in range(len(rows) - 1):
        lo, hi = rows[i], rows[i + 1]
        if len(lo) == 3 and len(hi) == 2:
            edges += [(lo[0], hi[0]), (lo[1], hi[0]),
                      (lo[1], hi[1]), (lo[2], hi[1])]
        elif len(lo) == 2 and len(hi) == 3:
            edges += [(lo[0], hi[0]), (lo[0], hi[1]),
                      (lo[1], hi[1]), (lo[1], hi[2])]

    # Perimeter: top edge
    edges += [(rows[-1][0], rows[-1][1]), (rows[-1][1], rows[-1][2])]
    # Perimeter: bottom edge
    edges += [(rows[0][0], rows[0][1]), (rows[0][1], rows[0][2])]
    # Perimeter: left side (connect x=0 vertices in even rows)
    left = [rows[i][0] for i in range(0, len(rows), 2)]
    for j in range(len(left) - 1):
        edges.append((left[j], left[j + 1]))
    # Perimeter: right side
    right = [rows[i][-1] for i in range(0, len(rows), 2)]
    for j in range(len(right) - 1):
        edges.append((right[j], right[j + 1]))

    return edges


# ─── Colors ─────────────────────────────────────────────────
CFRP_COLOR    = "#00d1ff"     # Cyan — CFRP structural ridges
PERIMETER_CLR = "#00ff64"     # Granas green — module border
VERTEX_CLR    = "#ffffff"     # White vertex markers
VERTEX_EDGE   = "#00ff64"    # Green vertex outline
ANNOT_CLR     = "#94a3b8"     # Muted gray for annotations
BG_COLOR      = "#020608"     # Near-black background


def create_blueprint(
    show_annotations: bool = True,
    show_vertices: bool = True,
    show_edge_labels: bool = False,
) -> "go.Figure":
    """
    Create the master geometric blueprint for the 2.1m × 3.4m Granas module.

    Faithfully reproduces the hand-drawn tessellation:
    4 interlocking rhombi + triangles at edges/corners.
    """
    if not HAS_PLOTLY:
        raise ImportError("plotly required: pip install plotly")

    rows = _build_vertices()
    edges = _build_edges(rows)

    fig = go.Figure()

    # ── 1. Draw all edges ────────────────────────────────────
    internal_done = False
    perim_done = False
    for (x0, y0), (x1, y1) in edges:
        is_perim = (
            (x0 == x1 == 0) or (x0 == x1 == W) or
            (y0 == y1 == 0) or (y0 == y1 == H)
        )
        if is_perim:
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(color=PERIMETER_CLR, width=4),
                name="Module Perimeter" if not perim_done else None,
                showlegend=not perim_done, hoverinfo="skip",
            ))
            perim_done = True
        else:
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(color=CFRP_COLOR, width=2),
                name="CFRP Skeleton" if not internal_done else None,
                showlegend=not internal_done, hoverinfo="skip",
            ))
            internal_done = True

    # ── 2. Vertex markers ────────────────────────────────────
    if show_vertices:
        vx, vy = [], []
        for row in rows:
            for (px, py) in row:
                vx.append(px)
                vy.append(py)
        fig.add_trace(go.Scatter(
            x=vx, y=vy, mode="markers",
            marker=dict(size=8, color=VERTEX_CLR,
                        line=dict(color=VERTEX_EDGE, width=2)),
            name="Structural Vertices",
            hovertemplate="(%{x:.3f}, %{y:.3f}) m<extra></extra>",
        ))

    # ── 3. Edge length labels (optional) ─────────────────────
    if show_edge_labels:
        seen = set()
        for (x0, y0), (x1, y1) in edges:
            length = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            key = (round(mx, 2), round(my, 2))
            if key not in seen:
                seen.add(key)
                fig.add_annotation(
                    x=mx, y=my, text=f"{length:.2f}m",
                    showarrow=False,
                    font=dict(color=ANNOT_CLR, size=7, family="JetBrains Mono"),
                )

    # ── 4. Dimension annotations ─────────────────────────────
    if show_annotations:
        fig.add_annotation(
            x=W / 2, y=-0.12, text=f"← {W} m →", showarrow=False,
            font=dict(color=PERIMETER_CLR, size=15, family="JetBrains Mono"),
        )
        fig.add_annotation(
            x=-0.14, y=H / 2, text=f"↕ {H} m", showarrow=False,
            font=dict(color=PERIMETER_CLR, size=15, family="JetBrains Mono"),
            textangle=-90,
        )
        fig.add_annotation(
            x=W / 2, y=H + 0.10,
            text=f"Module: {W*H:.2f} m²  │  CFRP Skeleton Tessellation",
            showarrow=False,
            font=dict(color=ANNOT_CLR, size=12, family="Inter"),
        )
        fig.add_annotation(
            x=W / 2, y=-0.25,
            text=(
                f"△ edge: {TRIANGLE_EDGE:.2f} m  │  "
                f"◇ edge: {RHOMBUS_EDGE:.3f} m"
            ),
            showarrow=False,
            font=dict(color=ANNOT_CLR, size=10, family="JetBrains Mono"),
        )

    # ── 5. Layout ────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        title=dict(
            text="📐 Granas Blueprint — 2.1m × 3.4m Master Geometric Tessellation",
            font=dict(size=18, color=PERIMETER_CLR, family="Inter"),
        ),
        xaxis=dict(
            range=[-0.25, W + 0.25],
            scaleanchor="y", scaleratio=1,
            showgrid=False, zeroline=False,
            tickfont=dict(color=ANNOT_CLR, size=10),
            title="Width (m)",
        ),
        yaxis=dict(
            range=[-0.35, H + 0.18],
            showgrid=False, zeroline=False,
            tickfont=dict(color=ANNOT_CLR, size=10),
            title="Height (m)",
        ),
        showlegend=True,
        legend=dict(
            font=dict(color="#e2e8f0", size=11, family="Inter"),
            bgcolor="rgba(0,0,0,0.3)",
        ),
        height=900, width=600,
        font=dict(family="Inter", color="#e2e8f0"),
        margin=dict(l=60, r=30, t=60, b=75),
    )

    return fig


def save_blueprint(filepath: str = "granas_blueprint.html", **kwargs) -> str:
    """Create and save blueprint to HTML file."""
    fig = create_blueprint(**kwargs)
    fig.write_html(filepath)
    return filepath


if __name__ == "__main__":
    fig = create_blueprint()
    fig.show()
