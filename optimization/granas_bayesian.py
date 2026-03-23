"""
PRIMEnergeia — Granas Bayesian Optimizer
========================================
Physics-informed Bayesian Optimization for perovskite solar cell
ink-recipe fabrication. Uses Gaussian Process surrogate models to
intelligently explore the 6D parameter space and maximize Power
Conversion Efficiency (PCE).

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import pandas as pd
import json
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple, Callable

from skopt import gp_minimize, Optimizer
from skopt.space import Real, Integer
from skopt.utils import use_named_args

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [Granas BO] - %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Physical Constants & Band-Gap Parameters
# ─────────────────────────────────────────────────────────────
# MAPbI3 perovskite — Shockley-Queisser optimal band gap ~1.34 eV
# Practical MAPbI3 Eg ≈ 1.55 eV, tunable by composition
BOLTZMANN_EV = 8.617333e-5   # eV/K
CELL_TEMP_K = 300.0           # Standard test conditions (K)
SQ_LIMIT_EG_155 = 0.306       # Theoretical SQ efficiency at Eg=1.55 eV (~30.6%)
PRACTICAL_CAP = 0.258         # Lab-champion single-junction perovskite PCE ~25.8%


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class GranasRecipe:
    """A single perovskite ink recipe."""
    molar_conc: float      # Precursor molar concentration (M)
    solvent_ratio: float   # DMSO : DMF volume ratio (0 = pure DMF)
    spin_speed: int        # Spin-coating RPM
    additive_pct: float    # Additive concentration (mol%)
    anneal_temp: float     # Annealing temperature (°C)
    anneal_time: float     # Annealing time (min)


@dataclass
class TrialResult:
    """Result of a single optimization trial."""
    trial_id: int
    recipe: GranasRecipe
    pce: float                  # Power conversion efficiency (%)
    stability_score: float      # 0–1 (T80 lifetime proxy)
    grain_size_nm: float        # Estimated grain diameter (nm)
    defect_density: float       # Relative defect density (a.u.)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─────────────────────────────────────────────────────────────
# Physics-Informed Objective
# ─────────────────────────────────────────────────────────────
class PerovskitePhysics:
    """
    Physics-informed model for perovskite grain formation and
    photovoltaic performance. Combines:
      1. Crystallization kinetics (LaMer nucleation)
      2. Scherrer grain-size estimation
      3. Defect-density model (Urbach tail)
      4. Shockley-Queisser-bounded PCE
    """

    # Optimal parameter basins (empirical, literature-calibrated)
    OPT_CONC = 1.2        # Optimal molar concentration
    OPT_SOLVENT = 0.70    # Optimal DMSO fraction
    OPT_SPIN = 4000       # Optimal spin speed (RPM)
    OPT_ADDITIVE = 2.5    # Optimal additive %
    OPT_ANNEAL_T = 140.0  # Optimal annealing temperature (°C)
    OPT_ANNEAL_M = 20.0   # Optimal annealing time (min)

    @staticmethod
    def grain_size(conc: float, solvent_ratio: float, spin_speed: int,
                   anneal_temp: float, anneal_time: float) -> float:
        """
        Estimate average grain diameter (nm) via Scherrer-inspired model.
        Larger grains → fewer grain boundaries → higher efficiency.
        """
        # Nucleation density: higher concentration = more nuclei = smaller grains
        nucleation = np.exp(-0.8 * (conc - 1.0) ** 2)

        # DMSO as Lewis-base retarder: optimal ratio slows crystallization
        retardation = np.exp(-2.0 * (solvent_ratio - 0.70) ** 2)

        # Spin speed thins the film; moderate speed = better coverage
        spin_factor = np.exp(-((spin_speed - 4000) / 2000) ** 2)

        # Annealing promotes Ostwald ripening — grain growth
        # But too high → decomposition; too low → amorphous
        anneal_growth = np.exp(-((anneal_temp - 140) / 40) ** 2)
        time_growth = 1.0 - np.exp(-anneal_time / 15.0)  # Saturating kinetics

        # Base grain size 50–800 nm
        grain_nm = 50.0 + 750.0 * nucleation * retardation * spin_factor * anneal_growth * time_growth
        return float(np.clip(grain_nm, 30.0, 900.0))

    @staticmethod
    def defect_density(conc: float, additive_pct: float, solvent_ratio: float,
                       anneal_temp: float, anneal_time: float) -> float:
        """
        Relative trap/defect density (a.u., 0 = perfect crystal).
        Additives passivate defects; optimal annealing minimizes residual strain.
        """
        # Additive passivation (e.g., Cl⁻, GuaBr, MACl)
        passivation = np.exp(-0.6 * (additive_pct - 2.5) ** 2)

        # Stoichiometry deviations increase defects
        stoich_penalty = (conc - 1.2) ** 2

        # Anti-solvent window: DMSO ratio affects intermediate phase
        solvent_penalty = (solvent_ratio - 0.70) ** 2

        # Over-annealing causes Pb⁰ defects; under-annealing leaves organics
        anneal_penalty = ((anneal_temp - 140) / 50) ** 2
        time_penalty = ((anneal_time - 20) / 20) ** 2

        defects = 0.05 + 0.95 * (1.0 - passivation) + 0.3 * stoich_penalty \
                  + 0.2 * solvent_penalty + 0.25 * anneal_penalty + 0.15 * time_penalty

        return float(np.clip(defects, 0.02, 3.0))

    @staticmethod
    def efficiency(grain_nm: float, defects: float, spin_speed: int) -> float:
        """
        Power Conversion Efficiency (%) bounded by Shockley-Queisser.
        Large grains + low defects → high Voc and Jsc → high PCE.
        """
        # Grain contribution: logarithmic (diminishing returns above 500 nm)
        grain_factor = np.log1p(grain_nm / 100.0) / np.log1p(8.0)  # normalized 0–1

        # Defect loss: exponential penalty
        defect_factor = np.exp(-0.5 * defects)

        # Film uniformity from spin speed (affects Jsc)
        uniformity = np.exp(-((spin_speed - 4000) / 3000) ** 2)

        # Raw PCE capped by practical champion
        raw_pce = PRACTICAL_CAP * grain_factor * defect_factor * uniformity

        # Add small stochastic noise (measurement uncertainty, ±0.3%)
        noise = np.random.normal(0, 0.3)
        return float(np.clip(raw_pce + noise, 0.5, PRACTICAL_CAP))

    @staticmethod
    def stability_score(anneal_temp: float, anneal_time: float,
                        additive_pct: float, defects: float) -> float:
        """
        Proxy for T80 operational stability (0–1 scale).
        Proper annealing + additive passivation → stable films.
        """
        thermal = np.exp(-((anneal_temp - 140) / 35) ** 2)
        temporal = np.exp(-((anneal_time - 25) / 15) ** 2)
        additive_stab = np.exp(-0.4 * (additive_pct - 3.0) ** 2)
        defect_stab = np.exp(-0.3 * defects)

        score = 0.25 * thermal + 0.20 * temporal + 0.30 * additive_stab + 0.25 * defect_stab
        return float(np.clip(score, 0.0, 1.0))


# ─────────────────────────────────────────────────────────────
# Main Optimizer Class
# ─────────────────────────────────────────────────────────────
class GranasOptimizer:
    """
    Bayesian Optimization engine for perovskite ink recipes.

    Parameters
    ----------
    n_calls : int
        Total number of optimization evaluations.
    n_initial : int
        Number of random initial explorations.
    acq_func : str
        Acquisition function: 'EI', 'PI', or 'LCB'.
    multi_objective : bool
        If True, optimize PCE + stability jointly.
    random_state : int or None
        Random seed for reproducibility.
    output_dir : str
        Directory for experiment logs.
    """

    # 6D Search Space
    SPACE = [
        Real(0.8, 1.5, name="molar_conc", prior="uniform"),
        Real(0.0, 1.0, name="solvent_ratio", prior="uniform"),
        Integer(1000, 6000, name="spin_speed"),
        Real(0.0, 5.0, name="additive_pct", prior="uniform"),
        Real(80.0, 200.0, name="anneal_temp", prior="uniform"),
        Real(5.0, 60.0, name="anneal_time", prior="uniform"),
    ]

    PARAM_NAMES = [s.name for s in SPACE]

    def __init__(
        self,
        n_calls: int = 50,
        n_initial: int = 8,
        acq_func: str = "EI",
        multi_objective: bool = False,
        random_state: Optional[int] = 42,
        output_dir: str = "granas_results",
    ):
        self.n_calls = n_calls
        self.n_initial = n_initial
        self.acq_func = acq_func
        self.multi_objective = multi_objective
        self.random_state = random_state
        self.output_dir = output_dir
        self.physics = PerovskitePhysics()

        # Trial history
        self.trials: List[TrialResult] = []
        self.result = None  # skopt OptimizeResult

        # Ensure output directory
        os.makedirs(self.output_dir, exist_ok=True)

    # ─── Objective ──────────────────────────────────────────
    def _evaluate(self, molar_conc, solvent_ratio, spin_speed,
                  additive_pct, anneal_temp, anneal_time) -> TrialResult:
        """Run the physics model for a single recipe and return a TrialResult."""
        recipe = GranasRecipe(
            molar_conc=molar_conc,
            solvent_ratio=solvent_ratio,
            spin_speed=int(spin_speed),
            additive_pct=additive_pct,
            anneal_temp=anneal_temp,
            anneal_time=anneal_time,
        )

        grain = self.physics.grain_size(
            molar_conc, solvent_ratio, spin_speed, anneal_temp, anneal_time
        )
        defects = self.physics.defect_density(
            molar_conc, additive_pct, solvent_ratio, anneal_temp, anneal_time
        )
        pce = self.physics.efficiency(grain, defects, spin_speed)
        stab = self.physics.stability_score(anneal_temp, anneal_time, additive_pct, defects)

        trial = TrialResult(
            trial_id=len(self.trials) + 1,
            recipe=recipe,
            pce=pce,
            stability_score=stab,
            grain_size_nm=grain,
            defect_density=defects,
        )
        self.trials.append(trial)

        logger.info(
            f"Trial {trial.trial_id:>3d} | PCE={pce:5.2f}% | "
            f"Grain={grain:6.1f}nm | Defects={defects:.3f} | "
            f"Stability={stab:.3f}"
        )
        return trial

    def _objective_fn(self, params: list) -> float:
        """skopt-compatible objective (minimization target)."""
        conc, ratio, speed, additive, temp, time_ = params
        trial = self._evaluate(conc, ratio, speed, additive, temp, time_)

        if self.multi_objective:
            # Scalarized multi-objective: 70% PCE + 30% stability
            score = 0.70 * trial.pce + 0.30 * (trial.stability_score * PRACTICAL_CAP)
            return -score
        return -trial.pce

    # ─── Run Full Optimization ──────────────────────────────
    def run(self, warm_start_csv: Optional[str] = None) -> "GranasOptimizer":
        """
        Execute the full Bayesian Optimization loop.

        Parameters
        ----------
        warm_start_csv : str, optional
            Path to CSV with prior experiments (columns must match PARAM_NAMES + 'pce').

        Returns
        -------
        self : GranasOptimizer
            Returns self for chaining.
        """
        logger.info("=" * 65)
        logger.info(" GRANAS — Bayesian Optimization for Perovskite Fabrication")
        logger.info(f" Search dimensions: {len(self.SPACE)}")
        logger.info(f" Total evaluations: {self.n_calls}")
        logger.info(f" Acquisition func:  {self.acq_func}")
        logger.info(f" Multi-objective:   {self.multi_objective}")
        logger.info("=" * 65)

        x0, y0 = None, None
        if warm_start_csv and os.path.exists(warm_start_csv):
            x0, y0 = self._load_warm_start(warm_start_csv)
            logger.info(f"Warm-started with {len(x0)} prior experiments")

        self.result = gp_minimize(
            func=self._objective_fn,
            dimensions=self.SPACE,
            n_calls=self.n_calls,
            n_initial_points=self.n_initial,
            acq_func=self.acq_func,
            random_state=self.random_state,
            x0=x0,
            y0=y0,
            verbose=False,
        )

        self._log_summary()
        self.export_results()
        return self

    # ─── Warm Start ─────────────────────────────────────────
    def _load_warm_start(self, csv_path: str) -> Tuple[list, list]:
        """Load prior experiments from CSV."""
        df = pd.read_csv(csv_path)
        required = self.PARAM_NAMES + ["pce"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Warm-start CSV missing columns: {missing}")

        x0 = df[self.PARAM_NAMES].values.tolist()
        # Convert PCE to negative (minimization)
        y0 = (-df["pce"]).values.tolist()
        return x0, y0

    # ─── Suggest Next Experiment ────────────────────────────
    def suggest_next(self) -> Dict[str, float]:
        """
        Suggest the next most promising experiment based on
        the current GP surrogate. Useful for human-in-the-loop.
        """
        if not self.trials:
            # No data yet — return center of space
            return {s.name: (s.low + s.high) / 2 for s in self.SPACE}

        opt = Optimizer(
            dimensions=self.SPACE,
            acq_func=self.acq_func,
            random_state=self.random_state,
        )
        # Feed existing data
        X = [[getattr(t.recipe, n) for n in self.PARAM_NAMES] for t in self.trials]
        Y = [-t.pce for t in self.trials]
        opt.tell(X, Y)

        next_point = opt.ask()
        return dict(zip(self.PARAM_NAMES, next_point))

    # ─── Report External Result ─────────────────────────────
    def report_result(self, recipe_dict: Dict[str, float], pce: float,
                      stability: Optional[float] = None) -> TrialResult:
        """
        Manually report an experimental result (human-in-the-loop).
        """
        trial = self._evaluate(**recipe_dict)
        # Override with actual measured values
        trial.pce = pce
        if stability is not None:
            trial.stability_score = stability
        return trial

    # ─── Best Result ────────────────────────────────────────
    def get_best(self) -> Optional[TrialResult]:
        """Return the trial with the highest PCE."""
        if not self.trials:
            return None
        return max(self.trials, key=lambda t: t.pce)

    # ─── Export ──────────────────────────────────────────────
    def export_results(self, fmt: str = "both") -> Dict[str, str]:
        """Export all trials to CSV and/or JSON."""
        paths = {}

        records = []
        for t in self.trials:
            rec = asdict(t.recipe)
            rec.update({
                "trial_id": t.trial_id,
                "pce": t.pce,
                "stability_score": t.stability_score,
                "grain_size_nm": t.grain_size_nm,
                "defect_density": t.defect_density,
                "timestamp": t.timestamp,
            })
            records.append(rec)

        if fmt in ("csv", "both"):
            csv_path = os.path.join(self.output_dir, "granas_experiment_log.csv")
            pd.DataFrame(records).to_csv(csv_path, index=False)
            paths["csv"] = csv_path
            logger.info(f"Exported CSV → {csv_path}")

        if fmt in ("json", "both"):
            json_path = os.path.join(self.output_dir, "granas_experiment_log.json")
            with open(json_path, "w") as f:
                json.dump(records, f, indent=2, default=str)
            paths["json"] = json_path
            logger.info(f"Exported JSON → {json_path}")

        # Export best recipe separately
        best = self.get_best()
        if best:
            best_path = os.path.join(self.output_dir, "best_recipe.json")
            best_data = {
                "optimal_recipe": asdict(best.recipe),
                "predicted_pce_pct": round(best.pce, 3),
                "stability_score": round(best.stability_score, 3),
                "grain_size_nm": round(best.grain_size_nm, 1),
                "defect_density": round(best.defect_density, 4),
                "trial_id": best.trial_id,
                "optimization_config": {
                    "n_calls": self.n_calls,
                    "acq_func": self.acq_func,
                    "multi_objective": self.multi_objective,
                },
            }
            with open(best_path, "w") as f:
                json.dump(best_data, f, indent=2)
            paths["best_recipe"] = best_path

        return paths

    # ─── Summary ────────────────────────────────────────────
    def _log_summary(self):
        best = self.get_best()
        if not best:
            return
        logger.info("=" * 65)
        logger.info(" ⚡ GRANAS OPTIMIZATION COMPLETE")
        logger.info("-" * 65)
        logger.info(f" Best PCE:           {best.pce:.2f}%")
        logger.info(f" Grain Size:         {best.grain_size_nm:.1f} nm")
        logger.info(f" Defect Density:     {best.defect_density:.4f}")
        logger.info(f" Stability Score:    {best.stability_score:.3f}")
        logger.info("-" * 65)
        logger.info(f" Molar Conc:         {best.recipe.molar_conc:.3f} M")
        logger.info(f" Solvent Ratio:      {best.recipe.solvent_ratio:.3f} (DMSO:DMF)")
        logger.info(f" Spin Speed:         {best.recipe.spin_speed} RPM")
        logger.info(f" Additive:           {best.recipe.additive_pct:.2f}%")
        logger.info(f" Annealing Temp:     {best.recipe.anneal_temp:.1f} °C")
        logger.info(f" Annealing Time:     {best.recipe.anneal_time:.1f} min")
        logger.info("=" * 65)


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    optimizer = GranasOptimizer(
        n_calls=50,
        n_initial=8,
        acq_func="EI",
        multi_objective=False,
        random_state=42,
    )
    optimizer.run()

    best = optimizer.get_best()
    print(f"\n{'='*55}")
    print(f" 🏆 BEST INK RECIPE FOUND")
    print(f"{'─'*55}")
    print(f" Molar Concentration:  {best.recipe.molar_conc:.3f} M")
    print(f" Solvent Ratio (DMSO): {best.recipe.solvent_ratio:.3f}")
    print(f" Spin Speed:           {best.recipe.spin_speed} RPM")
    print(f" Additive:             {best.recipe.additive_pct:.2f}%")
    print(f" Annealing Temp:       {best.recipe.anneal_temp:.1f} °C")
    print(f" Annealing Time:       {best.recipe.anneal_time:.1f} min")
    print(f"{'─'*55}")
    print(f" Predicted PCE:        {best.pce:.2f}%")
    print(f" Grain Size:           {best.grain_size_nm:.1f} nm")
    print(f" Stability Score:      {best.stability_score:.3f}")
    print(f"{'='*55}")

    # Suggest next experiment for the lab
    next_exp = optimizer.suggest_next()
    print(f"\n 🔬 NEXT SUGGESTED EXPERIMENT:")
    for k, v in next_exp.items():
        print(f"   {k}: {v}")
