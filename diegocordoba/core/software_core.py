"""
PRIMEnergeia — Report Engine (Hardened)
=========================================
Generates savings reports from real or synthetic market data.
Decoupled from data generation — accepts MarketDataset objects.

Uses tempfiles for images, BytesIO for in-memory passing.
Supports real data with proper baseline methodology.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import os
import io
import tempfile
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for safety
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PRIMEnergeia Report] - %(message)s',
)
logger = logging.getLogger(__name__)


class PRIMEnergeiaSoftware:
    """
    Report engine for PRIMEnergeia savings analysis.

    Can operate in two modes:
      1. REAL DATA: accepts a MarketDataset from data_loader.py
      2. DEMO MODE: generates synthetic data (clearly labelled)
    """

    def __init__(self, capacity: float = 100.0, node: str = "07-HER-230",
                 output_dir: str = None, royalty_rate: float = 0.20):
        self.capacity = capacity
        self.node = node
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="prime_reports_")
        self.output_pdf = os.path.join(self.output_dir, "PRIMEnergeia_Savings_Report.pdf")
        self.royalty_rate = royalty_rate
        self._demo_mode = False

    # ─── Real Data Adapter ──────────────────────────────────
    def load_from_dataset(self, dataset) -> pd.DataFrame:
        """
        Convert a MarketDataset into the internal DataFrame format.

        Handles both:
          - SEN nodo format (Actual_MW, Theoretical_MW, PML_USD)
          - ERCOT DA/RT format (da_prices, rt_prices)
        """
        self._demo_mode = False

        if dataset.actual_mw is not None and dataset.theoretical_mw is not None:
            # SEN nodo format — direct mapping
            timestamps = dataset.timestamps or [
                f"t_{i}" for i in range(dataset.hours)
            ]
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps, errors='coerce'),
                'Actual_MW': dataset.actual_mw,
                'Theoretical_MW': dataset.theoretical_mw,
                'PML_USD': dataset.da_prices,
            })
            logger.info(f"Loaded real SEN data: {len(df)} intervals from {dataset.source_file}")

        elif dataset.da_prices is not None and dataset.rt_prices is not None:
            # ERCOT/MIBEL format — construct theoretical from optimal dispatch
            timestamps = dataset.timestamps or dataset.dates or [
                f"t_{i}" for i in range(dataset.hours)
            ]
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps, errors='coerce'),
                'Actual_MW': np.zeros(dataset.hours),  # Will be filled by client
                'Theoretical_MW': np.zeros(dataset.hours),
                'PML_USD': dataset.da_prices,
            })
            # For ERCOT: use price spread as proxy for savings opportunity
            df['DA_Price'] = dataset.da_prices
            df['RT_Price'] = dataset.rt_prices
            logger.info(f"Loaded real {dataset.market.upper()} data: {len(df)} intervals")

        else:
            raise ValueError("Dataset has neither actual/theoretical MW nor DA/RT prices.")

        return df

    # ─── Demo Data Generator (clearly labelled) ────────────
    def generate_demo_data(self) -> pd.DataFrame:
        """
        Generate synthetic demo data. Clearly labelled as [DEMO MODE].
        """
        self._demo_mode = True
        logger.info("[DEMO MODE] Generating synthetic market data...")

        t = pd.date_range(start="2026-03-01", periods=96 * 7, freq='15min')
        hr = t.hour + t.minute / 60.0

        # Optimal Trajectory P*(t)
        theo = np.maximum(0, np.sin((hr - 6) * np.pi / 12)) * self.capacity

        # Market Price
        pml = 42 + 22 * np.sin((hr - 10) * np.pi / 12)
        pml += np.cumsum(np.random.normal(0, 4, len(t))) * 0.12
        pml = np.clip(pml + np.where(np.random.rand(len(t)) > 0.96, 480, 0), 28, 750)

        # Suboptimal actual performance
        act = theo * np.where(pml > 190, 0.74, 0.93)
        act = np.clip(act * np.random.normal(1.0, 0.015, len(t)), 0, self.capacity)

        df = pd.DataFrame({
            'timestamp': t,
            'Actual_MW': act,
            'Theoretical_MW': theo,
            'PML_USD': pml,
        })
        return df

    # ─── Savings Calculation (rigorous baseline) ────────────
    def calculate_savings(self, df: pd.DataFrame, interval_hours: float = 0.25) -> dict:
        """
        Calculate savings with rigorous baseline methodology.

        Methodology:
          savings = Σ (Theoretical_MW - Actual_MW) × PML × interval_hours
          This represents the revenue difference between optimal and actual dispatch.

        For real data, Theoretical_MW should be the PRIMEnergeia-optimized setpoint.
        For demo data, it's the physics-based optimal trajectory.
        """
        # Filter to intervals where there's generation (avoid nighttime zeros)
        mask = (df['Theoretical_MW'] > 0) | (df['Actual_MW'] > 0)
        active = df[mask]

        if len(active) == 0:
            return {
                'loss_total': 0.0,
                'royalty_value': 0.0,
                'client_net': 0.0,
                'active_hours': 0,
                'total_hours': len(df),
                'avg_loss_per_hour': 0.0,
                'avg_price': 0.0,
                'total_mwh_gap': 0.0,
            }

        loss_per_interval = (
            (active['Theoretical_MW'] - active['Actual_MW'])
            * active['PML_USD']
            * interval_hours
        )
        loss_total = float(loss_per_interval.sum())
        royalty_value = loss_total * self.royalty_rate
        client_net = loss_total - royalty_value

        return {
            'loss_total': loss_total,
            'royalty_value': royalty_value,
            'client_net': client_net,
            'active_hours': int(len(active) * interval_hours),
            'total_hours': int(len(df) * interval_hours),
            'avg_loss_per_hour': loss_total / max(len(active) * interval_hours, 1),
            'avg_price': float(active['PML_USD'].mean()),
            'total_mwh_gap': float(
                ((active['Theoretical_MW'] - active['Actual_MW']) * interval_hours).sum()
            ),
        }

    # ─── Dashboard Chart ────────────────────────────────────
    def create_dashboard(self, df: pd.DataFrame, window_hours: int = 48) -> bytes:
        """
        Create dashboard chart. Returns PNG as bytes (no file dependency).
        """
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(14, 10),
            gridspec_kw={'height_ratios': [2, 1]},
        )

        # Sample window
        intervals = window_hours * 4  # 15-min intervals
        sample = df.tail(min(intervals, len(df)))

        mode_label = " [DEMO]" if self._demo_mode else ""

        ax1.plot(sample['timestamp'], sample['Theoretical_MW'],
                 color='#00ffcc', label=f'Optimal Trajectory (PRIMEnergeia){mode_label}', lw=2.5)
        ax1.fill_between(sample['timestamp'], sample['Actual_MW'],
                         sample['Theoretical_MW'], color='#ff3333', alpha=0.2,
                         label='Exergy Dissipation')
        ax1.plot(sample['timestamp'], sample['Actual_MW'],
                 color='#ff3333', label='Sub-optimal Injection (Current)',
                 alpha=0.8, ls='--')
        ax1.set_title(
            f"Stochastic Convergence Diagnostics - Node {self.node}{mode_label}",
            fontsize=16, color='white', pad=20,
        )
        ax1.set_ylabel("Active Power (MW)")
        ax1.legend(loc='upper right', frameon=False)
        ax1.grid(alpha=0.1)

        ax2.fill_between(sample['timestamp'], 0, sample['PML_USD'],
                         color='#fbc02d', alpha=0.1)
        ax2.plot(sample['timestamp'], sample['PML_USD'],
                 color='#fbc02d', label='Market Price (USD/MWh)', lw=1.5)
        ax2.set_ylabel("Market Price (USD)")
        ax2.legend(loc='upper left', frameon=False)
        ax2.grid(alpha=0.1)

        plt.tight_layout()

        # Save to BytesIO (no file dependency)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=200, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    # ─── PDF Report ─────────────────────────────────────────
    def generate_report(self, df: pd.DataFrame,
                        output_path: str = None) -> str:
        """
        Generate the full PDF savings report.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with columns: timestamp, Actual_MW, Theoretical_MW, PML_USD
        output_path : str, optional
            Output PDF path. Defaults to self.output_pdf.

        Returns
        -------
        str : path to generated PDF
        """
        output_path = output_path or self.output_pdf
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Calculate savings
        savings = self.calculate_savings(df)
        mode_label = "[DEMO MODE] " if self._demo_mode else ""

        # Generate chart as PNG bytes
        chart_png = self.create_dashboard(df)

        # Write chart to temp file for FPDF
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(chart_png)
            chart_path = tmp.name

        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font("Arial", 'B', 26)
            pdf.set_text_color(0, 255, 204)
            pdf.cell(0, 20, f"{mode_label}PRIMEnergeia Software", 0, 1, 'L')

            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, (
                f"Protocol: Fiduciary Recovery Engine | Node: {self.node} | "
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ), 0, 1, 'L')
            pdf.ln(10)

            # Data quality summary (if available)
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 7, (
                f"Analysis period: {savings['active_hours']} active hours "
                f"({savings['total_hours']} total hours). "
                f"Average market price: ${savings['avg_price']:.2f}/MWh. "
                f"Total energy gap: {savings['total_mwh_gap']:.1f} MWh."
            ))
            pdf.ln(5)

            # Methodology narrative
            pdf.set_font("Arial", '', 12)
            if self._demo_mode:
                pdf.multi_cell(0, 8, (
                    "[!] DEMO MODE: This report uses synthetic data to demonstrate "
                    "PRIMEnergeia's analytical capabilities. Numbers shown are illustrative. "
                    "For accurate savings analysis, connect your actual operational data."
                ))
            else:
                pdf.multi_cell(0, 8, (
                    "This report quantifies the fiduciary gap between your asset's actual "
                    "injection profile and the PRIMEnergeia HJB-optimal trajectory. "
                    "Savings represent the additional revenue achievable through "
                    "real-time optimal dispatch control."
                ))
            pdf.ln(5)

            # Savings table
            pdf.set_fill_color(20, 20, 20)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(100, 12, "Fiduciary Metric", 1, 0, 'C', True)
            pdf.cell(90, 12, "Value (USD)", 1, 1, 'C', True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 12)
            pdf.cell(100, 12, "Total Capital Recovery Potential", 1, 0, 'L')
            pdf.cell(90, 12, f"${savings['loss_total']:,.2f}", 1, 1, 'R')

            pdf.set_text_color(255, 51, 51)
            pdf.cell(100, 12, f"PRIMEnergeia Royalty ({int(self.royalty_rate * 100)}%)", 1, 0, 'L')
            pdf.cell(90, 12, f"- ${savings['royalty_value']:,.2f}", 1, 1, 'R')

            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 153, 76)
            pdf.cell(100, 12, "NET CLIENT RECOVERY", 1, 0, 'L')
            pdf.cell(90, 12, f"${savings['client_net']:,.2f}", 1, 1, 'R')
            pdf.ln(10)

            # Dashboard image
            if os.path.exists(chart_path):
                pdf.image(chart_path, x=10, w=190)

            # Footer
            pdf.ln(5)
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "HJB Control Law: V_t + min_u { L(x,u) + Grad(V) * f(x,u) } = 0", 0, 1, 'C')

            pdf.output(output_path)
            logger.info(f"Report generated: {output_path}")

        finally:
            # Clean up temp file
            if os.path.exists(chart_path):
                os.unlink(chart_path)

        return output_path

    # ─── High-Level Convenience Methods ─────────────────────
    def run_from_dataset(self, dataset, output_path: str = None) -> str:
        """One-call pipeline: dataset → report PDF."""
        df = self.load_from_dataset(dataset)
        return self.generate_report(df, output_path)

    def run_demo(self, output_path: str = None) -> str:
        """One-call demo pipeline: synthetic data → report PDF."""
        df = self.generate_demo_data()
        return self.generate_report(df, output_path)


if __name__ == "__main__":
    engine = PRIMEnergeiaSoftware()

    # Try real data first
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data.data_loader import load_sen_csv
        dataset = load_sen_csv()
        path = engine.run_from_dataset(dataset)
        print(f"\n✅ Real data report: {path}")
    except Exception as e:
        print(f"\n⚠  Real data failed ({e}), running demo...")
        path = engine.run_demo()
        print(f"✅ Demo report: {path}")
"""
PRIMEnergeia — Report Engine (Hardened)
=========================================
Generates savings reports from real or synthetic market data.
Decoupled from data generation — accepts MarketDataset objects.

Uses tempfiles for images, BytesIO for in-memory passing.
Supports real data with proper baseline methodology.

PRIMEnergeia S.A.S. — Grid Optimization Division
"""
