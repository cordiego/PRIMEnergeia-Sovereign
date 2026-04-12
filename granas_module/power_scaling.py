"""
Granas Power Scaling — Home to Continent
==========================================
How many 2.1m × 3.4m Granas modules to power every scale
from a single home to an entire continent.

Scale Levels:
  🏠 Home           10,000 kWh/yr
  🏘️ Neighborhood   1,000,000 kWh/yr   (100 homes)
  🏙️ City           5,000 GWh/yr       (~500k homes)
  🗺️ State          50 TWh/yr          (Jalisco-scale)
  🇲🇽 Country        300 TWh/yr         (Mexico total)
  🌎 Continent      6,500 TWh/yr       (Latin America)

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
from dataclasses import dataclass
from typing import List
from granas_module.module_spec import GranasProductionModule


@dataclass
class ScaleLevel:
    """A consumption scale level."""
    name: str
    emoji: str
    annual_kWh: float
    description: str
    reference: str

    @property
    def annual_GWh(self) -> float:
        return self.annual_kWh / 1e6

    @property
    def annual_TWh(self) -> float:
        return self.annual_kWh / 1e9


# ─────────────────────────────────────────────────────────────
# Standard Scale Levels
# ─────────────────────────────────────────────────────────────
SCALE_LEVELS = [
    ScaleLevel(
        name="Home",
        emoji="🏠",
        annual_kWh=10_000,
        description="Average residential household",
        reference="US/Mexico avg ~10 MWh/yr",
    ),
    ScaleLevel(
        name="Neighborhood",
        emoji="🏘️",
        annual_kWh=1_000_000,
        description="100 homes, residential block",
        reference="100 × 10 MWh = 1 GWh/yr",
    ),
    ScaleLevel(
        name="City",
        emoji="🏙️",
        annual_kWh=5_000_000_000,
        description="Mid-size city (~500k households)",
        reference="~5 TWh/yr (Guadalajara-scale)",
    ),
    ScaleLevel(
        name="State",
        emoji="🗺️",
        annual_kWh=50_000_000_000,
        description="Mexican state (Jalisco-scale)",
        reference="~50 TWh/yr",
    ),
    ScaleLevel(
        name="Country",
        emoji="🇲🇽",
        annual_kWh=300_000_000_000,
        description="Mexico total electricity consumption",
        reference="~300 TWh/yr",
    ),
    ScaleLevel(
        name="Continent",
        emoji="🌎",
        annual_kWh=6_500_000_000_000,
        description="Latin America total electricity",
        reference="~6,500 TWh/yr",
    ),
]


# ─────────────────────────────────────────────────────────────
# Scaling Result
# ─────────────────────────────────────────────────────────────
@dataclass
class ScalingResult:
    """Result of a power scaling calculation."""
    scale: ScaleLevel
    module: GranasProductionModule
    modules_needed: int
    total_area_m2: float
    total_area_km2: float
    total_power_MW: float
    total_power_GW: float
    total_weight_tonnes: float
    annual_energy_GWh: float

    @property
    def total_area_ha(self) -> float:
        return self.total_area_m2 / 10000

    @property
    def football_fields(self) -> float:
        """Area in standard football fields (7,140 m²)."""
        return self.total_area_m2 / 7140

    def summary_line(self) -> str:
        if self.modules_needed < 1000:
            n_str = f"{self.modules_needed:,}"
        elif self.modules_needed < 1_000_000:
            n_str = f"{self.modules_needed/1000:.1f}K"
        elif self.modules_needed < 1_000_000_000:
            n_str = f"{self.modules_needed/1_000_000:.1f}M"
        else:
            n_str = f"{self.modules_needed/1_000_000_000:.2f}B"

        return (
            f"{self.scale.emoji} {self.scale.name:14s} │ "
            f"{n_str:>10s} modules │ "
            f"{self.total_power_MW:>12,.1f} MW │ "
            f"{self.scale.annual_kWh/1e9:>10,.1f} TWh/yr"
        )


# ─────────────────────────────────────────────────────────────
# Power Scaling Calculator
# ─────────────────────────────────────────────────────────────
class PowerScaling:
    """
    Calculate how many Granas 2.1m × 3.4m modules are needed
    to power consumption at each scale level.
    """

    def __init__(self, module: GranasProductionModule = None):
        self.module = module or GranasProductionModule()

    def compute(self, scale: ScaleLevel) -> ScalingResult:
        """Compute modules needed for a given consumption scale."""
        if self.module.annual_energy_kWh <= 0:
            raise ValueError("Module annual energy must be > 0")

        n_modules = int(
            np.ceil(scale.annual_kWh / self.module.annual_energy_kWh)
        )

        total_area = n_modules * self.module.total_area_m2
        total_power = n_modules * self.module.peak_power_W / 1e6  # MW

        return ScalingResult(
            scale=scale,
            module=self.module,
            modules_needed=n_modules,
            total_area_m2=total_area,
            total_area_km2=total_area / 1e6,
            total_power_MW=total_power,
            total_power_GW=total_power / 1000,
            total_weight_tonnes=n_modules * self.module.weight_kg / 1000,
            annual_energy_GWh=n_modules * self.module.annual_energy_kWh / 1e6,
        )

    def compute_all(self) -> List[ScalingResult]:
        """Compute scaling for all standard levels."""
        return [self.compute(level) for level in SCALE_LEVELS]
