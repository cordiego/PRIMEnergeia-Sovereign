"""
Granas-Module — Production-Scale Perovskite/TOPCon Tandem Module
================================================================
2.1m × 3.4m master module with 100 sub-cells (10×10 tessellation).

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

from granas_module.module_spec import GranasProductionModule
from granas_module.power_scaling import PowerScaling, ScaleLevel

__version__ = "1.0.0"
__all__ = ["GranasProductionModule", "PowerScaling", "ScaleLevel"]
