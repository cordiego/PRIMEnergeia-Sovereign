"""
PRIMEnergeia — Granas Visualizer
=================================
Publication-quality visualization suite for Bayesian Optimization
results on perovskite fabrication parameter space.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import pandas as pd
import os
from typing import Optional, List

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ─────────────────────────────────────────────────────────────
# Color Palette (PRIMEnergeia Sovereign Theme)
# ─────────────────────────────────────────────────────────────
COLORS = {
    "bg_dark": "#0a0e17",
    "bg_card": "#111827",
    "cyan": "#00ffd5",
    "cyan_dim": "rgba(0,255,213,0.15)",
    "gold": "#fbc02d",
    "red": "#ff3b5c",
    "blue": "#3b82f6",
    "purple": "#a855f7",
    "green": "#10b981",
    "white": "#e2e8f0",
    "gray": "#4b5563",
}

GRANAS_CMAP = LinearSegmentedColormap.from_list(
    "granas", ["#0a0e17", "#0d3b66", "#00ffd5", "#fbc02d", "#ff3b5c"]
) if HAS_MPL else None


class GranasVisualizer:
    """
    Visualization suite for GranasOptimizer results.

    Generates convergence curves, parameter landscapes, parallel
    coordinates plots, GP uncertainty bands, and Pareto fronts.
    """

    def __init__(self, trials: list, output_dir: str = "granas_results"):
        """
        Parameters
        ----------
        trials : list[TrialResult]
            List of completed optimization trials.
        output_dir : str
            Directory for saving plots.
        """
        self.trials = trials
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Build DataFrame from trials
        self.df = self._trials_to_df()

    def _trials_to_df(self) -> pd.DataFrame:
        records = []
        for t in self.trials:
            records.append({
                "trial_id": t.trial_id,
                "molar_conc": t.recipe.molar_conc,
                "solvent_ratio": t.recipe.solvent_ratio,
                "spin_speed": t.recipe.spin_speed,
                "additive_pct": t.recipe.additive_pct,
                "anneal_temp": t.recipe.anneal_temp,
                "anneal_time": t.recipe.anneal_time,
                "pce": t.pce,
                "stability_score": t.stability_score,
                "grain_size_nm": t.grain_size_nm,
                "defect_density": t.defect_density,
            })
        return pd.DataFrame(records)

    # ─── Convergence Curve ──────────────────────────────────
    def plot_convergence(self, save: bool = True) -> Optional[go.Figure]:
        """Best PCE found so far vs. iteration number."""
        if not HAS_PLOTLY:
            return self._mpl_convergence(save)

        best_so_far = self.df["pce"].cummax()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df["trial_id"], y=self.df["pce"],
            mode="markers",
            marker=dict(size=8, color=self.df["pce"],
                        colorscale=[[0, COLORS["blue"]], [1, COLORS["cyan"]]],
                        opacity=0.6),
            name="Individual Trials",
        ))
        fig.add_trace(go.Scatter(
            x=self.df["trial_id"], y=best_so_far,
            mode="lines",
            line=dict(color=COLORS["cyan"], width=3),
            name="Best So Far",
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg_dark"],
            plot_bgcolor=COLORS["bg_dark"],
            title=dict(text="⚡ Granas — Convergence Curve", font=dict(size=20, color=COLORS["cyan"])),
            xaxis_title="Trial #",
            yaxis_title="PCE (%)",
            font=dict(family="Inter, sans-serif", color=COLORS["white"]),
            showlegend=True,
        )

        if save:
            path = os.path.join(self.output_dir, "convergence.html")
            fig.write_html(path)
        return fig

    def _mpl_convergence(self, save: bool) -> None:
        if not HAS_MPL:
            return
        best_so_far = self.df["pce"].cummax()
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(self.df["trial_id"], self.df["pce"], c=self.df["pce"],
                   cmap=GRANAS_CMAP, alpha=0.6, s=50, zorder=2)
        ax.plot(self.df["trial_id"], best_so_far, color=COLORS["cyan"], lw=2.5, zorder=3)
        ax.set_xlabel("Trial #")
        ax.set_ylabel("PCE (%)")
        ax.set_title("Granas — Convergence Curve", color=COLORS["cyan"], fontsize=16)
        ax.grid(alpha=0.1)
        if save:
            path = os.path.join(self.output_dir, "convergence.png")
            plt.savefig(path, dpi=200, bbox_inches="tight")
            plt.close()

    # ─── Parameter Landscape Heatmaps ───────────────────────
    def plot_parameter_landscape(self, param_x: str = "molar_conc",
                                  param_y: str = "solvent_ratio",
                                  save: bool = True) -> Optional[go.Figure]:
        """2D heatmap of PCE across two parameter dimensions."""
        if not HAS_PLOTLY:
            return None

        fig = go.Figure(go.Scatter(
            x=self.df[param_x], y=self.df[param_y],
            mode="markers",
            marker=dict(
                size=12,
                color=self.df["pce"],
                colorscale=[[0, COLORS["bg_dark"]], [0.5, COLORS["blue"]],
                            [0.8, COLORS["cyan"]], [1, COLORS["gold"]]],
                colorbar=dict(title="PCE (%)"),
                opacity=0.85,
                line=dict(width=1, color=COLORS["bg_dark"]),
            ),
            text=[f"PCE: {p:.2f}%" for p in self.df["pce"]],
            hovertemplate=f"{param_x}: %{{x}}<br>{param_y}: %{{y}}<br>%{{text}}<extra></extra>",
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg_dark"],
            plot_bgcolor=COLORS["bg_dark"],
            title=dict(text=f"Parameter Landscape: {param_x} vs {param_y}",
                       font=dict(size=18, color=COLORS["cyan"])),
            xaxis_title=param_x,
            yaxis_title=param_y,
            font=dict(family="Inter, sans-serif", color=COLORS["white"]),
        )

        if save:
            path = os.path.join(self.output_dir, f"landscape_{param_x}_vs_{param_y}.html")
            fig.write_html(path)
        return fig

    # ─── Parallel Coordinates ───────────────────────────────
    def plot_parallel_coordinates(self, save: bool = True) -> Optional[go.Figure]:
        """All trials as parallel coordinates, colored by PCE."""
        if not HAS_PLOTLY:
            return None

        dims = [
            dict(label="Molar Conc (M)", values=self.df["molar_conc"], range=[0.8, 1.5]),
            dict(label="Solvent Ratio", values=self.df["solvent_ratio"], range=[0, 1]),
            dict(label="Spin Speed (RPM)", values=self.df["spin_speed"], range=[1000, 6000]),
            dict(label="Additive (%)", values=self.df["additive_pct"], range=[0, 5]),
            dict(label="Anneal Temp (°C)", values=self.df["anneal_temp"], range=[80, 200]),
            dict(label="Anneal Time (min)", values=self.df["anneal_time"], range=[5, 60]),
            dict(label="PCE (%)", values=self.df["pce"]),
            dict(label="Stability", values=self.df["stability_score"], range=[0, 1]),
        ]

        fig = go.Figure(go.Parcoords(
            line=dict(
                color=self.df["pce"],
                colorscale=[[0, COLORS["blue"]], [0.5, COLORS["cyan"]],
                            [0.8, COLORS["gold"]], [1, COLORS["red"]]],
                showscale=True,
                cmin=self.df["pce"].min(),
                cmax=self.df["pce"].max(),
            ),
            dimensions=dims,
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg_dark"],
            plot_bgcolor=COLORS["bg_dark"],
            title=dict(text="⚡ Granas — Parallel Coordinates", font=dict(size=20, color=COLORS["cyan"])),
            font=dict(family="Inter, sans-serif", color=COLORS["white"], size=11),
        )

        if save:
            path = os.path.join(self.output_dir, "parallel_coordinates.html")
            fig.write_html(path)
        return fig

    # ─── GP Uncertainty (1D slices) ─────────────────────────
    def plot_gp_uncertainty(self, result=None, save: bool = True) -> Optional[go.Figure]:
        """
        Posterior mean ± 2σ across each parameter dimension,
        with other params fixed at their best values.
        """
        if not HAS_PLOTLY or result is None:
            return None

        best = self.df.loc[self.df["pce"].idxmax()]
        params = ["molar_conc", "solvent_ratio", "spin_speed",
                  "additive_pct", "anneal_temp", "anneal_time"]
        bounds = [(0.8, 1.5), (0.0, 1.0), (1000, 6000),
                  (0.0, 5.0), (80, 200), (5, 60)]
        labels = ["Molar Conc (M)", "Solvent Ratio", "Spin (RPM)",
                  "Additive (%)", "Anneal Temp (°C)", "Anneal Time (min)"]

        fig = make_subplots(rows=2, cols=3, subplot_titles=labels,
                            vertical_spacing=0.12, horizontal_spacing=0.08)

        gp_model = result.models[-1] if hasattr(result, "models") and result.models else None
        if gp_model is None:
            return None

        for idx, (param, (lo, hi), label) in enumerate(zip(params, bounds, labels)):
            row, col = idx // 3 + 1, idx % 3 + 1
            x_range = np.linspace(lo, hi, 100)

            # Build input matrix: vary one param, fix others at best
            X_test = np.tile([best[p] for p in params], (100, 1))
            X_test[:, idx] = x_range

            y_pred, y_std = gp_model.predict(X_test, return_std=True)
            y_mean = -y_pred  # Convert back from minimization
            y_upper = y_mean + 2 * y_std
            y_lower = y_mean - 2 * y_std

            fig.add_trace(go.Scatter(
                x=x_range, y=y_upper, mode="lines",
                line=dict(width=0), showlegend=False,
            ), row=row, col=col)
            fig.add_trace(go.Scatter(
                x=x_range, y=y_lower, mode="lines",
                line=dict(width=0), fill="tonexty",
                fillcolor=COLORS["cyan_dim"], showlegend=False,
            ), row=row, col=col)
            fig.add_trace(go.Scatter(
                x=x_range, y=y_mean, mode="lines",
                line=dict(color=COLORS["cyan"], width=2),
                showlegend=False,
            ), row=row, col=col)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg_dark"],
            plot_bgcolor=COLORS["bg_dark"],
            title=dict(text="GP Posterior — Mean ± 2σ per Parameter",
                       font=dict(size=18, color=COLORS["cyan"])),
            font=dict(family="Inter, sans-serif", color=COLORS["white"]),
            height=600,
        )

        if save:
            path = os.path.join(self.output_dir, "gp_uncertainty.html")
            fig.write_html(path)
        return fig

    # ─── Pareto Front (Multi-Objective) ─────────────────────
    def plot_pareto_front(self, save: bool = True) -> Optional[go.Figure]:
        """Pareto front: PCE vs. Stability Score."""
        if not HAS_PLOTLY:
            return None

        # Compute Pareto front
        pareto_mask = self._pareto_mask(
            self.df[["pce", "stability_score"]].values
        )

        fig = go.Figure()
        # Non-Pareto points
        non_pareto = self.df[~pareto_mask]
        fig.add_trace(go.Scatter(
            x=non_pareto["pce"], y=non_pareto["stability_score"],
            mode="markers",
            marker=dict(size=8, color=COLORS["gray"], opacity=0.4),
            name="Dominated",
        ))
        # Pareto-optimal points
        pareto_df = self.df[pareto_mask].sort_values("pce")
        fig.add_trace(go.Scatter(
            x=pareto_df["pce"], y=pareto_df["stability_score"],
            mode="markers+lines",
            marker=dict(size=12, color=COLORS["gold"],
                        line=dict(width=2, color=COLORS["cyan"])),
            line=dict(color=COLORS["gold"], width=2, dash="dot"),
            name="Pareto Front",
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg_dark"],
            plot_bgcolor=COLORS["bg_dark"],
            title=dict(text="⚡ Pareto Front — PCE vs Stability",
                       font=dict(size=20, color=COLORS["cyan"])),
            xaxis_title="PCE (%)",
            yaxis_title="Stability Score",
            font=dict(family="Inter, sans-serif", color=COLORS["white"]),
        )

        if save:
            path = os.path.join(self.output_dir, "pareto_front.html")
            fig.write_html(path)
        return fig

    @staticmethod
    def _pareto_mask(objectives: np.ndarray) -> np.ndarray:
        """Identify Pareto-optimal rows (maximizing all objectives)."""
        n = len(objectives)
        is_pareto = np.ones(n, dtype=bool)
        for i in range(n):
            for j in range(n):
                if i != j:
                    if np.all(objectives[j] >= objectives[i]) and np.any(objectives[j] > objectives[i]):
                        is_pareto[i] = False
                        break
        return is_pareto

    # ─── Generate All Plots ─────────────────────────────────
    def generate_all(self, result=None) -> dict:
        """Generate all visualization plots."""
        plots = {}
        plots["convergence"] = self.plot_convergence()
        plots["landscape_conc_solvent"] = self.plot_parameter_landscape("molar_conc", "solvent_ratio")
        plots["landscape_spin_anneal"] = self.plot_parameter_landscape("spin_speed", "anneal_temp")
        plots["landscape_additive_time"] = self.plot_parameter_landscape("additive_pct", "anneal_time")
        plots["parallel_coords"] = self.plot_parallel_coordinates()
        plots["pareto"] = self.plot_pareto_front()
        if result is not None:
            plots["gp_uncertainty"] = self.plot_gp_uncertainty(result)
        return plots
