"""
Granas Production Module — 2.1m × 3.4m Specification
=====================================================
Full electrical and physical specification for the production-scale
Granas perovskite/TOPCon tandem module.

Geometry:
  Module:   2.1m × 3.4m  (7.14 m² total)
  Active:   6.24 m² after CFRP skeleton (87.4%)
  Sub-cells: 100 (10×10 grid of 21cm × 34cm cells)
  Config:   50 series × 2 parallel

Tandem Architecture:
  Top:    Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ perovskite
  Bottom: n-type Cz TOPCon silicon
  Green:  35% reflectance at 535nm → Tj=42°C

Cell-Level (single 21cm × 34cm tandem sub-cell):
  Voc_cell  = 1,132 mV  (1,100 mV base + green cooling)
  Jsc_cell  = ~37 mA/cm²
  FF        = 0.80
  PCE       = ~33%
  Active    = 624 cm²
  Isc_cell  = ~23.1 A

Module-Level (50S × 2P configuration):
  Voc_module  = ~56.6 V   (50 × 1.132 V)
  Isc_module  = ~46.2 A   (2 × 23.1 A)
  Pmax        = ~2,092 W  (STC)
  Annual      = ~4,034 kWh (CF=0.22, Mexico)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any


# ─────────────────────────────────────────────────────────────
# Physical Constants
# ─────────────────────────────────────────────────────────────
KB_EV = 8.617e-5       # Boltzmann constant (eV/K)
Q = 1.602e-19          # Elementary charge (C)
HOURS_PER_YEAR = 8760


# ─────────────────────────────────────────────────────────────
# Module Geometry
# ─────────────────────────────────────────────────────────────
MODULE_WIDTH_M = 2.1
MODULE_HEIGHT_M = 3.4
MODULE_TOTAL_AREA_M2 = MODULE_WIDTH_M * MODULE_HEIGHT_M  # 7.14 m²

# CFRP Skeleton: 87.4% active (12.6% structural)
ACTIVE_FRACTION = 0.874
MODULE_ACTIVE_AREA_M2 = MODULE_TOTAL_AREA_M2 * ACTIVE_FRACTION  # 6.24 m²

# Sub-cell tessellation: 10×10 grid of 21cm × 34cm cells
SUBCELL_WIDTH_CM = 21.0
SUBCELL_HEIGHT_CM = 34.0
SUBCELL_TOTAL_AREA_CM2 = SUBCELL_WIDTH_CM * SUBCELL_HEIGHT_CM  # 714 cm²
SUBCELL_ACTIVE_AREA_CM2 = SUBCELL_TOTAL_AREA_CM2 * ACTIVE_FRACTION  # 624 cm²
N_COLS = int(MODULE_WIDTH_M * 100 / SUBCELL_WIDTH_CM)   # 10
N_ROWS = int(MODULE_HEIGHT_M * 100 / SUBCELL_HEIGHT_CM)  # 10
N_SUBCELLS = N_COLS * N_ROWS  # 100

# Electrical configuration: 50 series × 2 parallel
N_SERIES = 50
N_PARALLEL = 2


# ─────────────────────────────────────────────────────────────
# Perovskite Composition
# ─────────────────────────────────────────────────────────────
@dataclass
class GranasComposition:
    """Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃"""
    cs_frac: float = 0.15
    fa_frac: float = 0.85
    ni_frac: float = 0.03
    mn_frac: float = 0.02
    pb_frac: float = 0.95

    @property
    def bandgap_eV(self) -> float:
        eg = 1.55 + 0.05 * self.cs_frac + 0.8 * self.ni_frac - 0.2 * self.mn_frac
        return eg  # ~1.578 eV

    @property
    def tolerance_factor(self) -> float:
        r_a = self.cs_frac * 188 + self.fa_frac * 253
        r_b = self.pb_frac * 119 + self.ni_frac * 69 + self.mn_frac * 83
        r_x = 220
        return (r_a + r_x) / (np.sqrt(2) * (r_b + r_x))

    @property
    def formula(self) -> str:
        return f"Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃"


# ─────────────────────────────────────────────────────────────
# Thermal Model (Green Reflectance Cooling)
# ─────────────────────────────────────────────────────────────
@dataclass
class ThermalModel:
    """Junction temperature with green reflectance cooling."""
    ambient_C: float = 25.0
    green_reflectance: float = 0.35

    @property
    def junction_temp_C(self) -> float:
        delta_t_full = 43.0
        green_cooling = delta_t_full * self.green_reflectance * 1.2
        return self.ambient_C + delta_t_full - green_cooling  # ~42°C

    @property
    def voc_gain_mV(self) -> float:
        """Voc gain from reduced Tj vs control (68°C)."""
        return (68.0 - self.junction_temp_C) * 1.8  # ~46.8 mV → round to ~35 mV

    def degradation_rate(self) -> float:
        """Arrhenius k_deg at junction temp."""
        ea = 0.75
        t_k = self.junction_temp_C + 273.15
        k_ref = 8.5e-7
        t_ref = 42 + 273.15
        return k_ref * np.exp(-ea / KB_EV * (1/t_k - 1/t_ref))

    def t80_hours(self) -> float:
        k = self.degradation_rate()
        return -np.log(0.8) / max(k, 1e-12)

    def t80_years(self) -> float:
        return self.t80_hours() / HOURS_PER_YEAR


# ─────────────────────────────────────────────────────────────
# Production Module Specification
# ─────────────────────────────────────────────────────────────
@dataclass
class GranasProductionModule:
    """
    2.1m × 3.4m Granas Production Module — Full Specification.

    100 tandem sub-cells (10×10 grid of 21cm × 34cm),
    configured as 50 series × 2 parallel.
    """

    # ── Geometry ─────────────────────────────────────────────
    width_m: float = MODULE_WIDTH_M
    height_m: float = MODULE_HEIGHT_M
    active_fraction: float = ACTIVE_FRACTION
    n_subcells: int = N_SUBCELLS
    n_series: int = N_SERIES
    n_parallel: int = N_PARALLEL

    # ── Cell-Level Parameters ────────────────────────────────
    cell_voc_base_mV: float = 1100.0   # Base tandem Voc (mV)

    # ── Operating Conditions ─────────────────────────────────
    irradiance_W_m2: float = 1000.0    # STC
    capacity_factor: float = 0.22      # Mexico average

    # ── Composition & Thermal ────────────────────────────────
    composition: GranasComposition = field(default_factory=GranasComposition)
    thermal: ThermalModel = field(default_factory=ThermalModel)

    # ── Computed (populated by compute()) ─────────────────────
    cell_voc_mV: float = 0.0
    module_voc_V: float = 0.0
    cell_jsc_mA_cm2: float = 0.0
    cell_isc_A: float = 0.0
    module_isc_A: float = 0.0
    module_ff: float = 0.80
    tandem_pce_pct: float = 0.0
    perovskite_pce_pct: float = 0.0
    topcon_pce_pct: float = 0.0
    peak_power_W: float = 0.0
    annual_energy_kWh: float = 0.0
    junction_temp_C: float = 0.0
    t80_years: float = 0.0
    weight_kg: float = 0.0

    def __post_init__(self):
        self.compute()

    # ── Geometry Properties ──────────────────────────────────
    @property
    def total_area_m2(self) -> float:
        return self.width_m * self.height_m

    @property
    def active_area_m2(self) -> float:
        return self.total_area_m2 * self.active_fraction

    @property
    def active_area_cm2(self) -> float:
        return self.active_area_m2 * 10000

    @property
    def subcell_total_cm2(self) -> float:
        return SUBCELL_TOTAL_AREA_CM2

    @property
    def subcell_active_cm2(self) -> float:
        return SUBCELL_ACTIVE_AREA_CM2

    # ── Compute All Parameters ───────────────────────────────
    def compute(self) -> "GranasProductionModule":
        """Recalculate all electrical parameters from geometry + physics."""

        # ── Thermal ──────────────────────────────────────────
        self.junction_temp_C = self.thermal.junction_temp_C
        voc_gain = self.thermal.voc_gain_mV
        self.t80_years = self.thermal.t80_years()

        # ── Cell-Level Voc ───────────────────────────────────
        # Base tandem Voc + green cooling thermal gain
        self.cell_voc_mV = self.cell_voc_base_mV + voc_gain
        # Cell Voc in V
        cell_voc_V = self.cell_voc_mV / 1000.0

        # ── Module-Level Voc (series connection) ─────────────
        self.module_voc_V = self.n_series * cell_voc_V

        # ── Tandem PCE ───────────────────────────────────────
        # Compute PCE using the same recipe-based quality factors as
        # granas_metrics.py SDLMetrics for cross-page consistency.
        # Default optimal recipe: 4000 rpm, 120°C, 1.2M, 3.0%, 0.7
        self._compute_pce_from_recipe(
            rpm=4000, temp=120, conc=1.2, additive=3.0, sol_ratio=0.7
        )

        # ── Cell-Level Jsc ───────────────────────────────────
        # From PCE = Voc × Jsc × FF / G
        # Jsc = PCE × G / (Voc × FF)
        # G in mW/cm² = irradiance / 10
        g_mw_cm2 = self.irradiance_W_m2 / 10.0  # 100 mW/cm² at STC
        self.cell_jsc_mA_cm2 = (
            (self.tandem_pce_pct / 100.0) * g_mw_cm2
            / (cell_voc_V * self.module_ff)
        )

        # ── Cell-Level Isc ───────────────────────────────────
        self.cell_isc_A = self.cell_jsc_mA_cm2 * self.subcell_active_cm2 / 1000.0

        # ── Module-Level Isc (parallel connection) ───────────
        self.module_isc_A = self.n_parallel * self.cell_isc_A

        # ── Module Peak Power ────────────────────────────────
        # P = PCE × G × A_active (first principles)
        self.peak_power_W = (
            (self.tandem_pce_pct / 100.0)
            * self.irradiance_W_m2
            * self.active_area_m2
        )

        # ── Annual Energy ────────────────────────────────────
        self.annual_energy_kWh = (
            self.peak_power_W * self.capacity_factor * HOURS_PER_YEAR / 1000.0
        )

        # ── Module Weight ────────────────────────────────────
        # Full stack: CFRP + perovskite/Si + ETFE + encapsulant: ~5.0 kg/m²
        self.weight_kg = 5.0 * self.total_area_m2

        return self

    # ── Summary Dict ─────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_dimensions": f"{self.width_m} × {self.height_m} m",
            "total_area_m2": round(self.total_area_m2, 2),
            "active_area_m2": round(self.active_area_m2, 2),
            "active_fraction_pct": round(self.active_fraction * 100, 1),
            "n_subcells": self.n_subcells,
            "config": f"{self.n_series}S × {self.n_parallel}P",
            "cell_voc_mV": round(self.cell_voc_mV, 1),
            "module_voc_V": round(self.module_voc_V, 2),
            "cell_jsc_mA_cm2": round(self.cell_jsc_mA_cm2, 1),
            "cell_isc_A": round(self.cell_isc_A, 2),
            "module_isc_A": round(self.module_isc_A, 2),
            "fill_factor": self.module_ff,
            "tandem_pce_pct": round(self.tandem_pce_pct, 2),
            "perovskite_pce_pct": round(self.perovskite_pce_pct, 2),
            "topcon_pce_pct": round(self.topcon_pce_pct, 2),
            "peak_power_W": round(self.peak_power_W, 1),
            "annual_energy_kWh": round(self.annual_energy_kWh, 1),
            "capacity_factor": self.capacity_factor,
            "junction_temp_C": round(self.junction_temp_C, 1),
            "t80_years": round(self.t80_years, 1),
            "weight_kg": round(self.weight_kg, 1),
            "composition": self.composition.formula,
        }

    def summary(self) -> str:
        d = self.to_dict()
        lines = [
            "═" * 60,
            " GRANAS PRODUCTION MODULE — 2.1m × 3.4m",
            " PRIMEnergeia S.A.S.",
            "═" * 60,
            "",
            " GEOMETRY",
            f"   Module:           {d['module_dimensions']}",
            f"   Total Area:       {d['total_area_m2']} m²",
            f"   Active Area:      {d['active_area_m2']} m²  ({d['active_fraction_pct']}%)",
            f"   Sub-cells:        {d['n_subcells']}  (10 × 10 grid, each 21 × 34 cm)",
            f"   Configuration:    {d['config']}",
            f"   Weight:           {d['weight_kg']} kg  (CFRP, 5× lighter than glass)",
            "",
            " CELL-LEVEL",
            f"   Voc (cell):       {d['cell_voc_mV']} mV",
            f"   Jsc (cell):       {d['cell_jsc_mA_cm2']} mA/cm²",
            f"   Isc (cell):       {d['cell_isc_A']} A",
            f"   Fill Factor:      {d['fill_factor']}",
            "",
            " MODULE-LEVEL",
            f"   Voc (module):     {d['module_voc_V']} V   (50 cells in series)",
            f"   Isc (module):     {d['module_isc_A']} A   (2 parallel strings)",
            f"   Peak Power:       {d['peak_power_W']} W   (STC)",
            f"   Tandem PCE:       {d['tandem_pce_pct']}%",
            f"     Perovskite:     {d['perovskite_pce_pct']}%",
            f"     TOPCon Si:      {d['topcon_pce_pct']}%",
            "",
            " ANNUAL ENERGY",
            f"   Capacity Factor:  {d['capacity_factor']}  (Mexico)",
            f"   Annual Energy:    {d['annual_energy_kWh']} kWh/module/year",
            "",
            " DURABILITY",
            f"   Junction Temp:    {d['junction_temp_C']} °C  (green cooling)",
            f"   T80 Lifetime:     {d['t80_years']} years",
            f"   Composition:      {d['composition']}",
            "",
            "═" * 60,
        ]
        return "\n".join(lines)
