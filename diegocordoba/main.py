import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class EurekaTerminal:
    def __init__(self):
        self.assets = ["SNDK", "SNXX", "CASH"]
        self.weights = {"SNDK": 0.40, "SNXX": 0.40, "CASH": 0.20}
        self.milestones = [
            ("2026-02-27", "Eureka 1.0 Initial Concept", "V1.0"),
            ("2026-03-04", "Cross-Entropy Arbitrage Logic", "V1.1"),
            ("2026-03-14", "Real Yield Optimizer Implementation", "V1.2"),
            ("2026-03-15", "AGQ Component Deletion / Re-Weighting", "V1.3")
        ]

    def display_dashboard(self):
        console.print(Panel("[bold cyan]EUREKA 1.0 | QUANTITATIVE TERMINAL v1.3[/bold cyan]\n[italic]Status: Operational | AGQ: DELETED[/italic]", expand=False))

        work_table = Table(title="Eureka Development History", style="dim")
        work_table.add_column("Date", style="magenta")
        work_table.add_column("Milestone", style="white")
        work_table.add_column("Build", style="green")
        for date, task, build in self.milestones:
            work_table.add_row(date, task, build)
        console.print(work_table)

        metrics_table = Table(title="Live Portfolio Targets")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Target Value", justify="right")
        metrics_table.add_row("Target CAGR", "14.0% - 18.0%")
        metrics_table.add_row("Max Drawdown", "< 15.0%")
        metrics_table.add_row("Sortino Ratio", "> 1.5")
        console.print(metrics_table)

        alloc_table = Table(title="Optimized Allocations (No AGQ)")
        alloc_table.add_column("Ticker", style="bold yellow")
        alloc_table.add_column("Weight (%)", justify="right")
        for asset, weight in self.weights.items():
            alloc_table.add_row(asset, f"{weight*100:.1f}%")
        console.print(alloc_table)

if __name__ == "__main__":
    terminal = EurekaTerminal()
    terminal.display_dashboard()
