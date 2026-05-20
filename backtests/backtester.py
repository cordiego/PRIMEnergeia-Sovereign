"""
PRIMEnergeia — Savings Backtester
====================================
Runs HJB, DRL, PID, and no-control strategies against historical
or synthetic market data. Generates auditable ROI reports.

Usage:
    python -m backtests.backtester --market ERCOT --days 30
    python -m backtests.backtester --market SEN --days 7 --report

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
import logging
import os
import json
import io
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("prime.backtester")

# Safe matplotlib import
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

# Safe PDF import
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# Import sibling modules
import sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from core.grid_stabilizer import (
    GridStabilizer, HJBController, PIDController, SimulationResult,
    MARKET_PARAMS, PriceGenerator, DisturbanceGenerator,
)
from core.bess_controller import BESSController, MODE_LABELS


# ─────────────────────────────────────────────────────────────
# Backtest Data Structures
# ─────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    """Backtest configuration."""
    market: str = "ERCOT"
    duration_days: int = 7
    dt_s: float = 1.0            # 1-second resolution
    bess_capacity_mwh: float = 400.0
    bess_max_power_mw: float = 100.0
    strategies: List[str] = field(default_factory=lambda: ["HJB", "PID", "NONE"])
    seed: int = 42
    severity: float = 1.0
    royalty_rate: float = 0.25
    output_dir: str = ""

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(_root, "backtests", "results")
        os.makedirs(self.output_dir, exist_ok=True)


@dataclass
class StrategyResult:
    """Results for a single strategy."""
    name: str = ""
    market: str = ""
    duration_days: int = 0

    # Revenue metrics
    total_revenue_usd: float = 0.0
    freq_response_usd: float = 0.0
    arbitrage_usd: float = 0.0
    penalty_avoidance_usd: float = 0.0
    penalties_usd: float = 0.0
    net_revenue_usd: float = 0.0

    # Performance metrics
    stability_pct: float = 0.0
    max_freq_dev_hz: float = 0.0
    avg_freq_dev_hz: float = 0.0
    total_violations: int = 0
    violation_minutes: float = 0.0

    # BESS metrics
    final_soc_pct: float = 0.0
    total_cycles: float = 0.0
    battery_health_pct: float = 100.0
    utilization_pct: float = 0.0

    # Time series (subsampled for plotting)
    times: List[float] = field(default_factory=list)
    freq_devs: List[float] = field(default_factory=list)
    prices: List[float] = field(default_factory=list)
    powers: List[float] = field(default_factory=list)
    socs: List[float] = field(default_factory=list)
    revenues: List[float] = field(default_factory=list)

    def annualized_revenue(self) -> float:
        if self.duration_days > 0:
            return self.net_revenue_usd * 365.0 / self.duration_days
        return 0.0


@dataclass
class BacktestReport:
    """Complete backtest output."""
    config: BacktestConfig
    results: Dict[str, StrategyResult]
    generated_at: str = ""
    summary: str = ""


# ─────────────────────────────────────────────────────────────
# Synthetic Market Data Generator
# ─────────────────────────────────────────────────────────────

class MarketDataGenerator:
    """Generate realistic multi-day market data for backtesting."""

    def __init__(self, market: str = "ERCOT", seed: int = 42):
        self.market = market
        self.params = MARKET_PARAMS.get(market, MARKET_PARAMS["ERCOT"])
        self.rng = np.random.RandomState(seed)

    def generate_prices(self, n_steps: int, dt_s: float) -> np.ndarray:
        """Generate LMP price trajectory."""
        prices = np.zeros(n_steps)
        price = self.params["base_price"]

        for i in range(n_steps):
            hour = (i * dt_s / 3600) % 24

            # Diurnal pattern
            solar = max(0, np.sin(np.pi * (hour - 6) / 12)) ** 2
            demand = 0.6 + 0.4 * np.sin(np.pi * (hour - 8) / 14) ** 2

            target = self.params["base_price"] * (0.7 + 0.6 * demand - 0.2 * solar)

            # Mean reversion + noise
            price += 0.001 * (target - price) + self.rng.normal(0, 0.5)

            # Spike events
            if self.rng.random() < 0.0005:
                price += self.rng.uniform(100, 1000)
            if self.rng.random() < 0.001:
                price -= self.rng.uniform(20, 50)

            # Negative prices (duck curve for CAISO)
            if self.market == "CAISO" and 10 <= hour <= 14 and self.rng.random() < 0.05:
                price = self.rng.uniform(-30, 0)

            prices[i] = np.clip(price, -50, self.params["price_cap"])

        return prices

    def generate_disturbances(self, n_steps: int, dt_s: float,
                              severity: float = 1.0) -> np.ndarray:
        """Generate frequency disturbance trajectory."""
        disturbances = np.zeros(n_steps)
        gen = DisturbanceGenerator(seed=self.rng.randint(0, 10000), severity=severity)

        for i in range(n_steps):
            t = i * dt_s
            disturbances[i] = gen.get_disturbance(t % 600)  # Wrap every 10 min
        return disturbances


# ─────────────────────────────────────────────────────────────
# Backtester Engine
# ─────────────────────────────────────────────────────────────

class Backtester:
    """Multi-strategy backtesting engine."""

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def run(self) -> BacktestReport:
        """Run full backtest across all strategies."""
        cfg = self.config
        duration_s = cfg.duration_days * 86400
        n_steps = int(duration_s / cfg.dt_s)

        logger.info("=" * 70)
        logger.info(" PRIMEnergeia Savings Backtester")
        logger.info(f" Market: {cfg.market} | Duration: {cfg.duration_days} days")
        logger.info(f" BESS: {cfg.bess_capacity_mwh} MWh / {cfg.bess_max_power_mw} MW")
        logger.info(f" Strategies: {', '.join(cfg.strategies)}")
        logger.info("=" * 70)

        # Generate shared market data
        data_gen = MarketDataGenerator(cfg.market, cfg.seed)
        prices = data_gen.generate_prices(n_steps, cfg.dt_s)
        disturbances = data_gen.generate_disturbances(n_steps, cfg.dt_s, cfg.severity)

        # Run each strategy
        results = {}
        for strategy in cfg.strategies:
            logger.info(f"\n  Running strategy: {strategy}")
            result = self._run_strategy(strategy, prices, disturbances)
            results[strategy] = result
            logger.info(f"  [{strategy}] Net revenue: ${result.net_revenue_usd:,.2f} | "
                        f"Stability: {result.stability_pct:.2f}% | "
                        f"Annualized: ${result.annualized_revenue():,.0f}")

        report = BacktestReport(
            config=cfg,
            results=results,
            generated_at=datetime.now().isoformat(),
        )
        report.summary = self._generate_summary(results)

        # Save results
        self._save_results(report)

        return report

    def _run_strategy(self, strategy: str, prices: np.ndarray,
                      disturbances: np.ndarray) -> StrategyResult:
        """Run a single strategy against market data."""
        cfg = self.config
        params = MARKET_PARAMS.get(cfg.market, MARKET_PARAMS["ERCOT"])
        n_steps = len(prices)

        # Controllers
        hjb = HJBController(market=cfg.market, max_injection_mw=cfg.bess_max_power_mw) if strategy == "HJB" else None
        pid = PIDController(max_output=cfg.bess_max_power_mw) if strategy == "PID" else None
        bess = BESSController(
            capacity_mwh=cfg.bess_capacity_mwh,
            max_power_mw=cfg.bess_max_power_mw,
            market=cfg.market,
        )

        # Physics state
        freq_dev = 0.0
        injection = 0.0
        H = params["H"]
        D = params["D"]
        threshold = params["penalty_threshold_hz"]

        # Tracking
        result = StrategyResult(name=strategy, market=cfg.market, duration_days=cfg.duration_days)
        violations = 0
        total_nominal = 0
        cumulative_revenue = 0.0

        sample_interval = max(1, int(60 / cfg.dt_s))  # Sample every 60s for output

        for step in range(n_steps):
            t = step * cfg.dt_s
            price = prices[step]
            disturbance = disturbances[step]

            # Control
            if strategy == "HJB":
                control = hjb.compute(freq_dev, injection, price)
            elif strategy == "PID":
                control = pid.compute(freq_dev, cfg.dt_s)
            else:
                control = 0.0

            # BESS dispatch (applies safety constraints)
            actual_power, bat_state = bess.dispatch(
                freq_dev, price, control, cfg.dt_s, t
            )
            injection = actual_power

            # Physics (swing equation)
            ddf = (injection - D * freq_dev - disturbance) / (2 * H)
            freq_dev += ddf * cfg.dt_s
            freq_dev = np.clip(freq_dev, -3.0, 3.0)

            # Track violations
            if abs(freq_dev) > threshold:
                violations += 1
            else:
                total_nominal += 1

            result.max_freq_dev_hz = max(result.max_freq_dev_hz, abs(freq_dev))

            # Subsample for time series
            if step % sample_interval == 0:
                cumulative_revenue = bess.revenue.net_revenue
                result.times.append(t / 3600)  # Hours
                result.freq_devs.append(freq_dev)
                result.prices.append(price)
                result.powers.append(actual_power)
                result.socs.append(bat_state.soc_pct)
                result.revenues.append(cumulative_revenue)

        # Final metrics
        rev = bess.revenue.summary()
        result.total_revenue_usd = rev["total_revenue_usd"]
        result.penalties_usd = rev["total_penalties_usd"]
        result.net_revenue_usd = rev["net_revenue_usd"]
        result.freq_response_usd = rev["freq_response_usd"]
        result.arbitrage_usd = rev["arbitrage_usd"]
        result.penalty_avoidance_usd = rev.get("penalty_avoidance_usd", 0)

        result.stability_pct = 100.0 * total_nominal / max(total_nominal + violations, 1)
        result.total_violations = violations
        result.violation_minutes = violations * cfg.dt_s / 60

        result.avg_freq_dev_hz = np.mean([abs(f) for f in result.freq_devs]) if result.freq_devs else 0
        result.final_soc_pct = bat_state.soc_pct
        result.total_cycles = bat_state.cycle_count
        result.battery_health_pct = bat_state.health_pct
        active_steps = sum(1 for p in result.powers if abs(p) > 1.0)
        result.utilization_pct = 100.0 * active_steps / max(len(result.powers), 1)

        return result

    def _generate_summary(self, results: Dict[str, StrategyResult]) -> str:
        """Generate text summary."""
        lines = [
            "",
            "=" * 80,
            " PRIMEnergeia Savings Backtester — Results",
            "=" * 80,
            f"{'Strategy':<12} {'Net Revenue':>14} {'Annualized':>14} "
            f"{'Stability':>10} {'Max Δf':>10} {'Cycles':>8} {'Health':>8}",
            "-" * 80,
        ]
        for name, r in results.items():
            lines.append(
                f"{name:<12} ${r.net_revenue_usd:>13,.2f} "
                f"${r.annualized_revenue():>13,.0f} "
                f"{r.stability_pct:>9.2f}% "
                f"{r.max_freq_dev_hz:>9.4f} "
                f"{r.total_cycles:>7.1f} "
                f"{r.battery_health_pct:>7.2f}%"
            )
        lines.append("=" * 80)

        if "HJB" in results and "NONE" in results:
            hjb = results["HJB"]
            none = results["NONE"]
            incremental = hjb.net_revenue_usd - none.net_revenue_usd
            client_share = incremental * (1 - self.config.royalty_rate)
            prime_share = incremental * self.config.royalty_rate
            lines.extend([
                "",
                f"  HJB Incremental Revenue:     ${incremental:>12,.2f}",
                f"  Client Net ({int((1-self.config.royalty_rate)*100)}%):          ${client_share:>12,.2f}",
                f"  PRIMEnergeia Fee ({int(self.config.royalty_rate*100)}%):      ${prime_share:>12,.2f}",
                f"  Annualized Client Savings:   ${client_share * 365 / max(self.config.duration_days, 1):>12,.0f}",
            ])

        summary = "\n".join(lines)
        print(summary)
        return summary

    def _save_results(self, report: BacktestReport):
        """Save results to JSON."""
        path = os.path.join(
            report.config.output_dir,
            f"backtest_{report.config.market}_{report.config.duration_days}d.json"
        )
        data = {
            "config": {
                "market": report.config.market,
                "duration_days": report.config.duration_days,
                "bess_mwh": report.config.bess_capacity_mwh,
                "bess_mw": report.config.bess_max_power_mw,
            },
            "generated_at": report.generated_at,
            "results": {},
        }
        for name, r in report.results.items():
            data["results"][name] = {
                "net_revenue_usd": round(r.net_revenue_usd, 2),
                "annualized_usd": round(r.annualized_revenue(), 2),
                "stability_pct": round(r.stability_pct, 2),
                "max_freq_dev_hz": round(r.max_freq_dev_hz, 4),
                "total_cycles": round(r.total_cycles, 1),
                "battery_health_pct": round(r.battery_health_pct, 2),
            }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Results saved: {path}")

    def generate_pdf_report(self, report: BacktestReport) -> Optional[str]:
        """Generate PDF backtest report."""
        if not MPL_AVAILABLE or not FPDF_AVAILABLE:
            logger.warning("matplotlib or fpdf not available — skipping PDF")
            return None

        # Generate comparison chart
        chart_path = self._generate_chart(report)
        if not chart_path:
            return None

        pdf_path = os.path.join(
            report.config.output_dir,
            f"PRIMEnergeia_Backtest_{report.config.market}_{report.config.duration_days}d.pdf"
        )

        pdf = FPDF()
        pdf.add_page()

        # Header
        pdf.set_font("Arial", "B", 22)
        pdf.set_text_color(0, 255, 204)
        pdf.cell(0, 15, "PRIMEnergeia Savings Backtest", 0, 1, "L")

        pdf.set_font("Arial", "I", 10)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, (
            f"Market: {report.config.market} | "
            f"Duration: {report.config.duration_days} days | "
            f"BESS: {report.config.bess_capacity_mwh} MWh | "
            f"Generated: {report.generated_at[:19]}"
        ), 0, 1, "L")
        pdf.ln(8)

        # Results table
        pdf.set_fill_color(20, 20, 20)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 11)
        headers = ["Strategy", "Net Revenue", "Annualized", "Stability", "Max Δf"]
        widths = [30, 40, 40, 35, 35]
        for h, w in zip(headers, widths):
            pdf.cell(w, 10, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        for name, r in report.results.items():
            pdf.cell(30, 10, name, 1, 0, "L")
            pdf.cell(40, 10, f"${r.net_revenue_usd:,.2f}", 1, 0, "R")
            pdf.cell(40, 10, f"${r.annualized_revenue():,.0f}", 1, 0, "R")
            pdf.cell(35, 10, f"{r.stability_pct:.2f}%", 1, 0, "R")
            pdf.cell(35, 10, f"{r.max_freq_dev_hz:.4f} Hz", 1, 0, "R")
            pdf.ln()

        pdf.ln(5)

        # Chart
        if os.path.exists(chart_path):
            pdf.image(chart_path, x=10, w=190)

        # Footer
        pdf.ln(5)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "HJB Control Law: V_t + min_u { L(x,u) + Grad(V) * f(x,u) } = 0", 0, 1, "C")

        pdf.output(pdf_path)

        # Cleanup temp chart
        if os.path.exists(chart_path):
            os.unlink(chart_path)

        logger.info(f"PDF report: {pdf_path}")
        return pdf_path

    def _generate_chart(self, report: BacktestReport) -> Optional[str]:
        """Generate comparison charts."""
        if not MPL_AVAILABLE:
            return None

        import tempfile
        plt.style.use("dark_background")
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

        colors = {"HJB": "#00ffcc", "PID": "#ff9800", "NONE": "#ff3333"}

        for name, r in report.results.items():
            c = colors.get(name, "#888888")
            axes[0].plot(r.times, r.freq_devs, label=name, color=c, alpha=0.8, lw=1)
            axes[1].plot(r.times, r.socs, label=name, color=c, alpha=0.8, lw=1)
            axes[2].plot(r.times, r.revenues, label=name, color=c, alpha=0.8, lw=1.5)

        axes[0].set_ylabel("Freq Deviation (Hz)")
        axes[0].set_title(f"PRIMEnergeia Backtest — {report.config.market} "
                          f"({report.config.duration_days} days)", fontsize=14)
        axes[0].axhline(0, color="white", alpha=0.2, lw=0.5)
        axes[0].legend(loc="upper right", frameon=False)
        axes[0].grid(alpha=0.1)

        axes[1].set_ylabel("Battery SoC (%)")
        axes[1].axhline(10, color="red", alpha=0.3, ls="--", lw=0.5)
        axes[1].axhline(90, color="red", alpha=0.3, ls="--", lw=0.5)
        axes[1].grid(alpha=0.1)

        axes[2].set_ylabel("Cumulative Revenue ($)")
        axes[2].set_xlabel("Time (hours)")
        axes[2].grid(alpha=0.1)

        plt.tight_layout()

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return tmp.name


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="PRIMEnergeia Savings Backtester")
    parser.add_argument("--market", default="ERCOT",
                        choices=["ERCOT", "SEN", "MIBEL", "NEM", "CAISO"])
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--bess-mwh", type=float, default=400)
    parser.add_argument("--bess-mw", type=float, default=100)
    parser.add_argument("--report", action="store_true", help="Generate PDF report")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = BacktestConfig(
        market=args.market,
        duration_days=args.days,
        bess_capacity_mwh=args.bess_mwh,
        bess_max_power_mw=args.bess_mw,
        seed=args.seed,
    )

    backtester = Backtester(config)
    report = backtester.run()

    if args.report:
        pdf_path = backtester.generate_pdf_report(report)
        if pdf_path:
            print(f"\n  📄 PDF Report: {pdf_path}")
