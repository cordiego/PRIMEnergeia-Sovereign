"""
Granas Blueprint — Border-Only Geometric Visualization
========================================================
2.1m × 3.4m production module with CFRP skeleton tessellation.
Renders ONLY borders/outlines — no fill shading.

Architecture:
  - Outer perimeter border (2.1m × 3.4m)
  - 10×10 sub-cell grid (21cm × 34cm each)
  - CFRP skeleton edges: peripheral triangles, internal rhombi, central network
  - Dimension annotations

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from __future__ import annotations

import numpy as np

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from granas_module.module_spec import (
    MODULE_WIDTH_M, MODULE_HEIGHT_M,
    N_COLS, N_ROWS,
    SUBCELL_WIDTH_CM, SUBCELL_HEIGHT_CM,
)

# Convert to cm for visualization
W_CM = MODULE_WIDTH_M * 100  # 210 cm
H_CM = MODULE_HEIGHT_M * 100  # 340 cm
CELL_W = SUBCELL_WIDTH_CM      # 21 cm
CELL_H = SUBCELL_HEIGHT_CM     # 34 cm

# ─── Colors (border theme) ──────────────────────────────────
BORDER_COLOR = "#00ff64"       # Granas green
GRID_COLOR = "#1e3a2a"         # Subtle dark green grid
CFRP_COLOR = "#00d1ff"         # Cyan for CFRP skeleton
ANNOTATION_COLOR = "#94a3b8"   # Muted text
BG_COLOR = "#020608"           # Dark background
ACTIVE_BORDER = "#00ff64"              # Green for active zone (opacity set on trace)


def create_blueprint(show_annotations: bool = True,
                     show_cfrp_skeleton: bool = True,
                     show_subcell_grid: bool = True) -> "go.Figure":
    """
    Create the border-only blueprint for the 2.1m × 3.4m Granas module.

    Returns a Plotly figure with borders only (no fill).
    """
    if not HAS_PLOTLY:
        raise ImportError("plotly required: pip install plotly")

    fig = go.Figure()

    # ── 1. Outer Module Perimeter (thick green border) ───────
    fig.add_trace(go.Scatter(
        x=[0, W_CM, W_CM, 0, 0],
        y=[0, 0, H_CM, H_CM, 0],
        mode="lines",
        line=dict(color=BORDER_COLOR, width=4),
        name="Module Perimeter",
        hoverinfo="skip",
    ))

    # ── 2. Sub-cell Grid (10×10, thin borders) ───────────────
    if show_subcell_grid:
        # Vertical grid lines
        for col in range(1, N_COLS):
            x = col * CELL_W
            fig.add_trace(go.Scatter(
                x=[x, x], y=[0, H_CM],
                mode="lines",
                line=dict(color=GRID_COLOR, width=1),
                showlegend=False,
                hoverinfo="skip",
            ))
        # Horizontal grid lines
        for row in range(1, N_ROWS):
            y = row * CELL_H
            fig.add_trace(go.Scatter(
                x=[0, W_CM], y=[y, y],
                mode="lines",
                line=dict(color=GRID_COLOR, width=1),
                showlegend=False,
                hoverinfo="skip",
            ))

    # ── 3. CFRP Skeleton (structural edges) ──────────────────
    if show_cfrp_skeleton:
        _add_cfrp_skeleton(fig)

    # ── 4. Active Area Border ────────────────────────────────
    # Inset border showing active area within each cell
    inset = 1.3  # cm inset for CFRP frame
    for col in range(N_COLS):
        for row in range(N_ROWS):
            x0 = col * CELL_W + inset
            y0 = row * CELL_H + inset
            x1 = (col + 1) * CELL_W - inset
            y1 = (row + 1) * CELL_H - inset
            fig.add_trace(go.Scatter(
                x=[x0, x1, x1, x0, x0],
                y=[y0, y0, y1, y1, y0],
                mode="lines",
                line=dict(color=ACTIVE_BORDER, width=0.5),
                opacity=0.25,
                showlegend=False,
                hoverinfo="skip",
            ))

    # ── 5. Dimension Annotations ─────────────────────────────
    if show_annotations:
        _add_annotations(fig)

    # ── 6. Sub-cell Labels ───────────────────────────────────
    # Label corners with cell indices
    for col in range(N_COLS):
        for row in range(N_ROWS):
            cx = col * CELL_W + CELL_W / 2
            cy = row * CELL_H + CELL_H / 2
            idx = row * N_COLS + col + 1
            fig.add_annotation(
                x=cx, y=cy,
                text=str(idx),
                showarrow=False,
                font=dict(color="#1e3a2a", size=7, family="JetBrains Mono"),
            )

    # ── Layout ───────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        title=dict(
            text="📐 Granas Module Blueprint — 2.1m × 3.4m",
            font=dict(size=20, color=BORDER_COLOR, family="Inter"),
        ),
        xaxis=dict(
            range=[-20, W_CM + 20],
            scaleanchor="y",
            scaleratio=1,
            showgrid=False, zeroline=False,
            tickfont=dict(color=ANNOTATION_COLOR, size=10),
            title="Width (cm)",
        ),
        yaxis=dict(
            range=[-20, H_CM + 20],
            showgrid=False, zeroline=False,
            tickfont=dict(color=ANNOTATION_COLOR, size=10),
            title="Height (cm)",
        ),
        showlegend=True,
        legend=dict(
            font=dict(color="#e2e8f0", size=11, family="Inter"),
            bgcolor="rgba(0,0,0,0.3)",
        ),
        height=900,
        width=600,
        font=dict(family="Inter", color="#e2e8f0"),
        margin=dict(l=60, r=30, t=60, b=60),
    )

    return fig


def _add_cfrp_skeleton(fig: go.Figure):
    """Add CFRP structural skeleton edges — borders only."""

    # ── Peripheral triangles (6 at corners/edges) ────────────
    # Top-left triangle
    _add_border_triangle(fig,
        [(0, H_CM), (2*CELL_W, H_CM), (0, H_CM - 2*CELL_H)],
        name="Peripheral (5.5)")
    # Top-right triangle
    _add_border_triangle(fig,
        [(W_CM, H_CM), (W_CM - 2*CELL_W, H_CM), (W_CM, H_CM - 2*CELL_H)])
    # Bottom-left triangle
    _add_border_triangle(fig,
        [(0, 0), (2*CELL_W, 0), (0, 2*CELL_H)])
    # Bottom-right triangle
    _add_border_triangle(fig,
        [(W_CM, 0), (W_CM - 2*CELL_W, 0), (W_CM, 2*CELL_H)])
    # Mid-left triangle
    _add_border_triangle(fig,
        [(0, H_CM/2 - CELL_H), (CELL_W, H_CM/2), (0, H_CM/2 + CELL_H)])
    # Mid-right triangle
    _add_border_triangle(fig,
        [(W_CM, H_CM/2 - CELL_H), (W_CM - CELL_W, H_CM/2), (W_CM, H_CM/2 + CELL_H)])

    # ── Internal rhombi (8 stress distribution) ──────────────
    # Create rhombus patterns at internal junctions
    cx, cy = W_CM / 2, H_CM / 2  # center
    rhombus_offsets = [
        (-2*CELL_W, -CELL_H), (2*CELL_W, -CELL_H),
        (-2*CELL_W, CELL_H), (2*CELL_W, CELL_H),
        (-CELL_W, -3*CELL_H), (CELL_W, -3*CELL_H),
        (-CELL_W, 3*CELL_H), (CELL_W, 3*CELL_H),
    ]
    for i, (dx, dy) in enumerate(rhombus_offsets):
        rx, ry = cx + dx, cy + dy
        hw, hh = CELL_W * 0.7, CELL_H * 0.5
        _add_border_rhombus(fig, rx, ry, hw, hh,
                            name="Internal Rhombus (3.5)" if i == 0 else None)

    # ── Central network (12 crack-arrest vertices) ───────────
    # Radial pattern from center
    for angle in np.linspace(0, 2*np.pi, 13)[:-1]:
        r1 = CELL_W * 1.5
        r2 = CELL_W * 3.0
        x1 = cx + r1 * np.cos(angle)
        y1 = cy + r1 * np.sin(angle)
        x2 = cx + r2 * np.cos(angle)
        y2 = cy + r2 * np.sin(angle)
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2],
            mode="lines",
            line=dict(color=CFRP_COLOR, width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Central vertex marker
    fig.add_trace(go.Scatter(
        x=[cx], y=[cy],
        mode="markers",
        marker=dict(color=CFRP_COLOR, size=8, symbol="diamond"),
        name="Central Network (3.0)",
    ))


def _add_border_triangle(fig, pts, name=None):
    """Add a triangle with border only (no fill)."""
    xs = [p[0] for p in pts] + [pts[0][0]]
    ys = [p[1] for p in pts] + [pts[0][1]]
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color=CFRP_COLOR, width=2),
        name=name,
        showlegend=name is not None,
        hoverinfo="skip",
    ))


def _add_border_rhombus(fig, cx, cy, hw, hh, name=None):
    """Add a rhombus with border only (no fill)."""
    xs = [cx, cx + hw, cx, cx - hw, cx]
    ys = [cy + hh, cy, cy - hh, cy, cy + hh]
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color=CFRP_COLOR, width=1.5),
        name=name,
        showlegend=name is not None,
        hoverinfo="skip",
    ))


def _add_annotations(fig: go.Figure):
    """Add dimension annotations to the blueprint."""
    # Width annotation (bottom)
    fig.add_annotation(
        x=W_CM / 2, y=-12,
        text=f"← {MODULE_WIDTH_M} m ({W_CM:.0f} cm) →",
        showarrow=False,
        font=dict(color=BORDER_COLOR, size=14, family="JetBrains Mono"),
    )
    # Height annotation (left)
    fig.add_annotation(
        x=-15, y=H_CM / 2,
        text=f"↕ {MODULE_HEIGHT_M} m ({H_CM:.0f} cm)",
        showarrow=False,
        font=dict(color=BORDER_COLOR, size=14, family="JetBrains Mono"),
        textangle=-90,
    )
    # Cell size annotation
    fig.add_annotation(
        x=CELL_W / 2, y=H_CM + 10,
        text=f"Cell: {CELL_W:.0f} × {CELL_H:.0f} cm",
        showarrow=False,
        font=dict(color=ANNOTATION_COLOR, size=11, family="JetBrains Mono"),
    )
    # Area annotation
    area_m2 = MODULE_WIDTH_M * MODULE_HEIGHT_M
    fig.add_annotation(
        x=W_CM / 2, y=H_CM + 10,
        text=f"Total: {area_m2:.2f} m²  │  100 sub-cells  │  50S × 2P",
        showarrow=False,
        font=dict(color=ANNOTATION_COLOR, size=11, family="Inter"),
    )
