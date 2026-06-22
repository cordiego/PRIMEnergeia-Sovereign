"""
PRIMEnergeia — Granas Optics Visualizer
=========================================
Investor-grade Plotly visualizations for Granas optical simulations.

Plots:
  - E-field heatmap (photon cage)
  - A/R/T spectral curves with AM1.5G overlay
  - EQE vs wavelength
  - Jsc optimization surface (radius × density)
  - 3D granule packing scatter
  - Mie efficiency spectra

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import numpy as np
from typing import Optional, Dict

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ─────────────────────────────────────────────────────────────
# Color Palette (PRIMEnergeia Design Language)
# ─────────────────────────────────────────────────────────────
C = {
    "bg": "#050810",
    "cyan": "#00d1ff",
    "green": "#00ff88",
    "gold": "#fbc02d",
    "red": "#ff3b5c",
    "purple": "#a78bfa",
    "white": "#e0e6ed",
    "muted": "#6b7fa3",
    "border": "#1a2744",
}

LAYOUT_BASE = dict(
    template="plotly_dark",
    paper_bgcolor=C["bg"],
    plot_bgcolor="#0a0f1a",
    font=dict(family="JetBrains Mono, Inter, sans-serif",
              size=11, color=C["white"]),
)


class GranasOpticsVisualizer:
    """Investor-grade visualizations for Granas optical simulations."""

    def __init__(self, output_dir: str = "granas_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ─── E-field Heatmap (Photon Cage) ─────────────────────
    def plot_efield_heatmap(self, result, save: bool = True):
        """
        E-field intensity heatmap showing light trapped
        in the granular structure. 'The Photon Cage.'
        """
        if not HAS_PLOTLY or result.efield_map is None:
            return None

        fig = go.Figure(go.Heatmap(
            z=result.efield_map.T,
            colorscale=[
                [0.0, "#050810"],
                [0.15, "#0a1628"],
                [0.3, "#003366"],
                [0.45, "#0066cc"],
                [0.6, "#00d1ff"],
                [0.75, "#00ff88"],
                [0.9, "#fbc02d"],
                [1.0, "#ff3b5c"],
            ],
            colorbar=dict(title="|E|²", tickfont=dict(size=10)),
        ))

        # Mark granule positions (z-slice)
        domain_z = 500  # mid-slice
        for g in result.granule_positions:
            if abs(g.z - domain_z) < g.radius_nm * 3:
                fig.add_shape(
                    type="circle",
                    x0=(g.x - g.radius_nm) / 10,
                    y0=(g.y - g.radius_nm) / 10,
                    x1=(g.x + g.radius_nm) / 10,
                    y1=(g.y + g.radius_nm) / 10,
                    line=dict(color="rgba(255,255,255,0.15)", width=1),
                )

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text="🔬 Photon Cage — E-Field Intensity |E|²",
                       font=dict(size=20, color=C["cyan"])),
            xaxis_title="x (×10 nm)",
            yaxis_title="y (×10 nm)",
            height=600, width=700,
            yaxis=dict(scaleanchor="x"),
        )

        if save:
            fig.write_html(os.path.join(self.output_dir, "efield_heatmap.html"))
        return fig

    # ─── A/R/T Spectral Curves ────────────────────────────
    def plot_spectral_response(self, result, save: bool = True):
        """Absorption, Reflectance, Transmittance vs wavelength."""
        if not HAS_PLOTLY:
            return None

        from optics.granas_optics import SolarSpectrum

        wl = result.wavelengths_nm
        irr = SolarSpectrum.irradiance(wl)
        irr_norm = irr / np.max(irr)

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
            subplot_titles=("Granas Spectral Response",
                            "AM1.5G Solar Irradiance"),
            row_heights=[0.65, 0.35],
        )

        fig.add_trace(go.Scatter(
            x=wl, y=result.absorptance * 100, name="Absorption",
            line=dict(color=C["green"], width=3),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.08)",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=wl, y=result.reflectance * 100, name="Reflectance",
            line=dict(color=C["cyan"], width=2, dash="dash"),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=wl, y=result.transmittance * 100, name="Transmittance",
            line=dict(color=C["gold"], width=2, dash="dot"),
        ), row=1, col=1)
        fig.add_hline(y=95, line_dash="dash", line_color=C["red"],
                      annotation_text="95% Target", row=1, col=1)

        fig.add_trace(go.Scatter(
            x=wl, y=irr, name="AM1.5G (W/m²/nm)",
            line=dict(color=C["gold"], width=2),
            fill="tozeroy", fillcolor="rgba(251,192,45,0.08)",
        ), row=2, col=1)

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text="Granas Spectral Response — A/R/T",
                       font=dict(size=18, color=C["cyan"])),
            height=700,
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        )
        fig.update_yaxes(title_text="(%)", row=1, col=1)
        fig.update_yaxes(title_text="W/(m²·nm)", row=2, col=1)
        fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)

        if save:
            fig.write_html(os.path.join(self.output_dir, "spectral_response.html"))
        return fig

    # ─── EQE + Jsc ────────────────────────────────────────
    def plot_quantum_efficiency(self, result, save: bool = True):
        """External Quantum Efficiency and Jsc annotation."""
        if not HAS_PLOTLY:
            return None

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=result.wavelengths_nm, y=result.eqe * 100,
            name="EQE",
            line=dict(color=C["purple"], width=3),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.08)",
        ))

        fig.add_annotation(
            x=600, y=85,
            text=f"J<sub>sc</sub> = {result.jsc_mA_cm2:.2f} mA/cm²",
            font=dict(size=16, color=C["green"], family="JetBrains Mono"),
            showarrow=False,
            bgcolor="rgba(0,0,0,0.6)",
            bordercolor=C["green"],
            borderpad=8,
        )

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text="External Quantum Efficiency (EQE)",
                       font=dict(size=18, color=C["cyan"])),
            xaxis_title="Wavelength (nm)",
            yaxis_title="EQE (%)",
            height=450,
        )

        if save:
            fig.write_html(os.path.join(self.output_dir, "eqe_curve.html"))
        return fig

    # ─── Jsc Optimization Surface ─────────────────────────
    def plot_jsc_optimization(self, sweep_result, save: bool = True):
        """
        2D heatmap of Jsc vs granule radius and packing density.
        The Global Efficiency Peak.
        """
        if not HAS_PLOTLY:
            return None

        fig = go.Figure(go.Heatmap(
            z=sweep_result["jsc_map"],
            x=sweep_result["densities"],
            y=sweep_result["radii"],
            colorscale=[
                [0, C["bg"]], [0.3, "#003366"],
                [0.6, C["cyan"]], [0.8, C["green"]],
                [1, C["gold"]],
            ],
            colorbar=dict(title="Jsc (mA/cm²)"),
        ))

        # Mark the peak
        jsc = sweep_result["jsc_map"]
        peak_idx = np.unravel_index(np.argmax(jsc), jsc.shape)
        fig.add_trace(go.Scatter(
            x=[sweep_result["densities"][peak_idx[1]]],
            y=[sweep_result["radii"][peak_idx[0]]],
            mode="markers",
            marker=dict(size=18, color=C["red"], symbol="star",
                        line=dict(width=2, color="white")),
            name=f"Peak: {jsc[peak_idx]:.1f} mA/cm²",
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text="J<sub>sc</sub> Optimization Map — Global Efficiency Peak",
                       font=dict(size=18, color=C["cyan"])),
            xaxis_title="Packing Density",
            yaxis_title="Granule Radius (nm)",
            height=550,
        )

        if save:
            fig.write_html(os.path.join(self.output_dir, "jsc_optimization.html"))
        return fig

    # ─── Mie Scattering Spectrum ──────────────────────────
    def plot_mie_spectrum(self, mie_data, wavelengths_nm,
                          radius_nm, save: bool = True):
        """Q_ext, Q_sca, Q_abs vs wavelength."""
        if not HAS_PLOTLY:
            return None

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=wavelengths_nm, y=mie_data["Q_ext"], name="Q_ext",
            line=dict(color=C["cyan"], width=3),
        ))
        fig.add_trace(go.Scatter(
            x=wavelengths_nm, y=mie_data["Q_sca"], name="Q_sca",
            line=dict(color=C["green"], width=2, dash="dash"),
        ))
        fig.add_trace(go.Scatter(
            x=wavelengths_nm, y=mie_data["Q_abs"], name="Q_abs",
            line=dict(color=C["red"], width=2, dash="dot"),
            fill="tozeroy", fillcolor="rgba(255,59,92,0.06)",
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=f"Mie Scattering Efficiencies — r={radius_nm:.0f}nm",
                       font=dict(size=18, color=C["cyan"])),
            xaxis_title="Wavelength (nm)",
            yaxis_title="Efficiency Q",
            height=450,
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        )

        if save:
            fig.write_html(os.path.join(self.output_dir, "mie_spectrum.html"))
        return fig

    # ─── 3D Granule Packing ───────────────────────────────
    def plot_granule_packing(self, granules, save: bool = True):
        """3D scatter of granule positions, sized by radius."""
        if not HAS_PLOTLY or not granules:
            return None

        x = [g.x for g in granules]
        y = [g.y for g in granules]
        z = [g.z for g in granules]
        r = [g.radius_nm for g in granules]
        r_norm = np.array(r)
        sizes = (r_norm / np.max(r_norm)) * 20 + 3

        fig = go.Figure(go.Scatter3d(
            x=x, y=y, z=z,
            mode="markers",
            marker=dict(
                size=sizes,
                color=z,
                colorscale=[[0, C["cyan"]], [0.5, C["green"]], [1, C["gold"]]],
                opacity=0.7,
                line=dict(width=0.5, color="white"),
            ),
            text=[f"r={ri:.0f}nm" for ri in r],
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=f"Granular Matrix — {len(granules)} Granules (Poisson Disc)",
                       font=dict(size=18, color=C["cyan"])),
            scene=dict(
                xaxis_title="X (nm)", yaxis_title="Y (nm)", zaxis_title="Z (nm)",
                bgcolor="#050810",
            ),
            height=600,
        )

        if save:
            fig.write_html(os.path.join(self.output_dir, "granule_packing_3d.html"))
        return fig

    # ─── Generate All ─────────────────────────────────────
    def generate_all(self, result, mie_data=None,
                     wavelengths_nm=None, sweep_result=None):
        """Generate all investor-grade visualizations."""
        plots = {}
        plots["efield"] = self.plot_efield_heatmap(result)
        plots["spectral"] = self.plot_spectral_response(result)
        plots["eqe"] = self.plot_quantum_efficiency(result)
        plots["packing"] = self.plot_granule_packing(result.granule_positions)
        if mie_data is not None and wavelengths_nm is not None:
            plots["mie"] = self.plot_mie_spectrum(
                mie_data, wavelengths_nm, 250.0)
        if sweep_result is not None:
            plots["jsc_opt"] = self.plot_jsc_optimization(sweep_result)
        return plots
