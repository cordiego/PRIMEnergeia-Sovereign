#!/usr/bin/env python3
"""
PRIME Power Electronics — DC-AC / AC-DC Conversion Models
============================================================
PRIMEnergeia S.A.S. | Power Electronics Division

Physics-based power conversion models for grid-scale energy systems:
  - InverterModel: DC→AC with parabolic loss model, temp derating, VAR support
  - RectifierModel: AC→DC for battery charging / electrolyzer coupling
  - TransformerModel: Step-up/step-down with iron + copper losses

Loss model reference:
  η(P) = P / (P + k₀ + k₁·P + k₂·P²)
  where k₀ = standby (no-load), k₁ = proportional, k₂ = switching losses

Reference: Kjaer, Pedersen & Blaabjerg, "Power Inverter Topologies
           for Photovoltaic Modules" IEEE Trans. (2005)
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Optional

# ============================================================
#  INVERTER SPECIFICATION
# ============================================================

@dataclass
class InverterSpec:
    """Grid-tied power inverter specification."""
    name: str = "PRIME-INV-100"
    rated_power_kw: float = 100.0
    rated_voltage_dc_v: float = 800.0
    rated_voltage_ac_v: float = 480.0
    topology: str = "central"            # central / string / micro
    phases: int = 3

    # Efficiency parameters (parabolic loss model)
    peak_efficiency: float = 0.984       # Max η (typically at 40-60% load)
    euro_efficiency: float = 0.978       # EU-weighted average η
    standby_power_w: float = 350.0       # k₀: fixed no-load losses (fans, controller, magnetics)
    tare_loss_pct: float = 0.004         # k₁: proportional loss coefficient (conduction)
    switching_loss_pct: float = 0.006    # k₂: quadratic switching losses (IGBT/MOSFET)

    # Thermal derating
    max_ambient_c: float = 45.0          # Derating threshold
    derating_slope_pct_per_c: float = 1.5  # Output reduction per °C above max

    # Reactive power
    apparent_power_kva: float = 110.0    # S rating (typically 1.1 × P)
    power_factor_range: Tuple[float, float] = (0.85, 0.85)  # lead, lag

    # MPPT (for PV/battery applications)
    mppt_channels: int = 2
    mppt_voltage_range_v: Tuple[float, float] = (200.0, 1000.0)
    mppt_efficiency: float = 0.998

    # Physical
    weight_kg: float = 85.0
    ip_rating: str = "IP65"
    cooling: str = "Forced air"


# Pre-configured inverter specs for each engine type
INVERTER_PRESETS = {
    "bess_100mw": InverterSpec(
        name="PRIME-INV-BESS", rated_power_kw=100000, rated_voltage_dc_v=1500,
        rated_voltage_ac_v=34500, topology="central", peak_efficiency=0.986,
        euro_efficiency=0.980, standby_power_w=5000, tare_loss_pct=0.0018,
        switching_loss_pct=0.0035, apparent_power_kva=110000, weight_kg=12000,
    ),
    "wind_15mw": InverterSpec(
        name="PRIME-CONV-WIND", rated_power_kw=15000, rated_voltage_dc_v=1100,
        rated_voltage_ac_v=690, topology="central", peak_efficiency=0.982,
        euro_efficiency=0.976, standby_power_w=800, tare_loss_pct=0.0020,
        switching_loss_pct=0.0040, apparent_power_kva=16500, weight_kg=2500,
        cooling="Liquid",
    ),
    "h2_turbine_100kw": InverterSpec(
        name="PRIME-INV-HYP", rated_power_kw=100, rated_voltage_dc_v=600,
        rated_voltage_ac_v=480, topology="central", peak_efficiency=0.980,
        euro_efficiency=0.974, standby_power_w=30, tare_loss_pct=0.0022,
        switching_loss_pct=0.0045, apparent_power_kva=110,
    ),
    "pem_50kw": InverterSpec(
        name="PRIME-INV-PEM", rated_power_kw=50, rated_voltage_dc_v=400,
        rated_voltage_ac_v=480, topology="string", peak_efficiency=0.975,
        euro_efficiency=0.968, standby_power_w=20, tare_loss_pct=0.0025,
        switching_loss_pct=0.0050, apparent_power_kva=55,
        mppt_voltage_range_v=(180.0, 500.0),
    ),
    "aice_genset_335kw": InverterSpec(
        name="PRIME-INV-AICE", rated_power_kw=335, rated_voltage_dc_v=700,
        rated_voltage_ac_v=480, topology="central", peak_efficiency=0.982,
        euro_efficiency=0.976, standby_power_w=80, tare_loss_pct=0.0020,
        switching_loss_pct=0.0038, apparent_power_kva=370,
    ),
}


# ============================================================
#  INVERTER MODEL (DC → AC)
# ============================================================

class InverterModel:
    """
    Physics-based DC→AC inverter model.

    Loss model:
        P_loss = k₀ + k₁·P + k₂·P²
        η(P) = P / (P + P_loss)

    where:
        k₀ = standby_power (W) — iron-core / control board / fan losses
        k₁ = tare_loss coefficient — conduction losses (proportional to I)
        k₂ = switching_loss coefficient — IGBT/MOSFET switching (∝ I²)

    Temperature derating:
        Above max_ambient_c, output is linearly reduced.

    Reactive power:
        Q_available = √(S² - P²), bounded by power_factor_range.
    """

    def __init__(self, spec: InverterSpec = None, preset: str = None):
        if preset and preset in INVERTER_PRESETS:
            self.spec = INVERTER_PRESETS[preset]
        else:
            self.spec = spec or InverterSpec()

    def _loss_kw(self, dc_power_kw: float) -> float:
        """Total inverter losses (kW) at given DC input power."""
        if dc_power_kw <= 0:
            return 0.0

        P = dc_power_kw
        P_rated = self.spec.rated_power_kw

        # Normalized load
        p_norm = min(P / P_rated, 1.2)  # Allow 20% transient overload

        k0 = self.spec.standby_power_w / 1000.0         # kW (fixed)
        k1 = self.spec.tare_loss_pct * P_rated           # kW/pu (proportional)
        k2 = self.spec.switching_loss_pct * P_rated      # kW/pu² (quadratic)

        loss = k0 + k1 * p_norm + k2 * p_norm ** 2
        return loss

    def efficiency(self, load_fraction: float, ambient_c: float = 25.0) -> float:
        """
        Inverter efficiency at given load fraction (0.0–1.0) and ambient temp.

        Returns float in range [0, peak_efficiency].
        At ~10% load:  ~92-94%
        At ~50% load:  ~97-98%  (near peak)
        At 100% load:  ~97-98%  (slight drop from switching losses)
        """
        if load_fraction <= 0:
            return 0.0

        load_fraction = min(load_fraction, 1.2)
        P = load_fraction * self.spec.rated_power_kw

        loss = self._loss_kw(P)
        eta = P / (P + loss) if (P + loss) > 0 else 0.0

        # Temperature correction: efficiency slightly decreases at high temp
        if ambient_c > self.spec.max_ambient_c:
            temp_penalty = 0.001 * (ambient_c - self.spec.max_ambient_c)
            eta = max(0.0, eta - temp_penalty)

        return round(min(eta, self.spec.peak_efficiency), 5)

    def temperature_derating(self, ambient_c: float) -> float:
        """
        Power derating factor (0.0–1.0) due to ambient temperature.
        Returns 1.0 below max_ambient_c, linearly reduces above.
        """
        if ambient_c <= self.spec.max_ambient_c:
            return 1.0

        delta = ambient_c - self.spec.max_ambient_c
        derating = 1.0 - (self.spec.derating_slope_pct_per_c / 100) * delta
        return round(max(0.0, derating), 4)

    def reactive_power_capability(self, active_power_kw: float) -> Dict[str, float]:
        """
        Available reactive power (kVAR) from the inverter S-curve.
        Q_max = √(S² - P²), bounded by power factor limits.
        """
        S = self.spec.apparent_power_kva
        P = min(abs(active_power_kw), S)

        q_from_s_curve = math.sqrt(max(0, S ** 2 - P ** 2))

        # Power factor limits
        pf_lead, pf_lag = self.spec.power_factor_range
        if P > 0:
            q_lead_max = P * math.tan(math.acos(pf_lead))
            q_lag_max = P * math.tan(math.acos(pf_lag))
        else:
            q_lead_max = q_lag_max = S * 0.5

        q_available = min(q_from_s_curve, max(q_lead_max, q_lag_max))

        return {
            "q_max_kvar": round(q_available, 1),
            "q_lead_max_kvar": round(min(q_from_s_curve, q_lead_max), 1),
            "q_lag_max_kvar": round(min(q_from_s_curve, q_lag_max), 1),
            "apparent_power_kva": round(S, 1),
            "power_factor_at_p": round(P / S, 4) if S > 0 else 0,
        }

    def ac_output(self, dc_power_kw: float, ambient_c: float = 25.0) -> Dict:
        """
        Top-level conversion: DC input → AC output.

        Returns dict with:
            ac_power_kw, efficiency, losses_kw, derated,
            reactive_available_kvar, derating_factor
        """
        if dc_power_kw <= 0:
            return {
                "ac_power_kw": 0.0,
                "dc_input_kw": 0.0,
                "efficiency": 0.0,
                "losses_kw": 0.0,
                "derated": False,
                "derating_factor": 1.0,
                "reactive_available_kvar": self.spec.apparent_power_kva,
            }

        # Temperature derating limits max DC input
        derating = self.temperature_derating(ambient_c)
        max_dc = self.spec.rated_power_kw * derating
        effective_dc = min(dc_power_kw, max_dc)
        derated = dc_power_kw > max_dc and derating < 1.0

        # Efficiency at this operating point
        load_frac = effective_dc / self.spec.rated_power_kw
        eta = self.efficiency(load_frac, ambient_c)

        ac_power = effective_dc * eta
        losses = effective_dc - ac_power

        # Reactive capability at this active output
        q_info = self.reactive_power_capability(ac_power)

        return {
            "ac_power_kw": round(ac_power, 3),
            "dc_input_kw": round(effective_dc, 3),
            "efficiency": round(eta, 5),
            "losses_kw": round(losses, 3),
            "derated": derated,
            "derating_factor": derating,
            "reactive_available_kvar": q_info["q_max_kvar"],
        }


# ============================================================
#  RECTIFIER MODEL (AC → DC)
# ============================================================

@dataclass
class RectifierSpec:
    """AC→DC rectifier specification (for charging / electrolyzer)."""
    name: str = "PRIME-RECT-100"
    rated_power_kw: float = 100.0
    topology: str = "active_front_end"   # active_front_end / thyristor
    peak_efficiency: float = 0.980
    standby_power_w: float = 40.0
    tare_loss_pct: float = 0.0020
    switching_loss_pct: float = 0.0042
    max_ambient_c: float = 45.0
    derating_slope_pct_per_c: float = 1.5


class RectifierModel:
    """
    AC→DC rectifier model. Same parabolic loss structure as InverterModel
    but with slightly different default coefficients for thyristor/IGBT topology.
    """

    def __init__(self, spec: RectifierSpec = None):
        self.spec = spec or RectifierSpec()

    def efficiency(self, load_fraction: float, ambient_c: float = 25.0) -> float:
        """Rectifier efficiency at given load fraction."""
        if load_fraction <= 0:
            return 0.0

        load_fraction = min(load_fraction, 1.2)
        P = load_fraction * self.spec.rated_power_kw

        k0 = self.spec.standby_power_w / 1000.0
        k1 = self.spec.tare_loss_pct * self.spec.rated_power_kw
        k2 = self.spec.switching_loss_pct * self.spec.rated_power_kw

        loss = k0 + k1 * load_fraction + k2 * load_fraction ** 2
        eta = P / (P + loss) if (P + loss) > 0 else 0.0

        if ambient_c > self.spec.max_ambient_c:
            temp_penalty = 0.001 * (ambient_c - self.spec.max_ambient_c)
            eta = max(0.0, eta - temp_penalty)

        return round(min(eta, self.spec.peak_efficiency), 5)

    def temperature_derating(self, ambient_c: float) -> float:
        """Power derating factor due to ambient temperature."""
        if ambient_c <= self.spec.max_ambient_c:
            return 1.0
        delta = ambient_c - self.spec.max_ambient_c
        return round(max(0.0, 1.0 - (self.spec.derating_slope_pct_per_c / 100) * delta), 4)

    def dc_output(self, ac_power_kw: float, ambient_c: float = 25.0) -> Dict:
        """Convert AC input to DC output."""
        if ac_power_kw <= 0:
            return {"dc_power_kw": 0.0, "ac_input_kw": 0.0, "efficiency": 0.0, "losses_kw": 0.0}

        derating = self.temperature_derating(ambient_c)
        max_ac = self.spec.rated_power_kw * derating
        effective_ac = min(ac_power_kw, max_ac)

        load_frac = effective_ac / self.spec.rated_power_kw
        eta = self.efficiency(load_frac, ambient_c)

        dc_power = effective_ac * eta
        losses = effective_ac - dc_power

        return {
            "dc_power_kw": round(dc_power, 3),
            "ac_input_kw": round(effective_ac, 3),
            "efficiency": round(eta, 5),
            "losses_kw": round(losses, 3),
            "derating_factor": derating,
        }


# ============================================================
#  TRANSFORMER MODEL
# ============================================================

@dataclass
class TransformerSpec:
    """Power transformer specification."""
    name: str = "PRIME-XFMR-100"
    rated_power_kva: float = 110.0
    primary_voltage_v: float = 480.0
    secondary_voltage_v: float = 34500.0
    iron_loss_pct: float = 0.15          # No-load / core losses (% of rated)
    copper_loss_pct: float = 0.50        # Full-load winding losses (% of rated)
    impedance_pct: float = 6.0
    cooling: str = "ONAN"                # Oil natural, air natural
    weight_kg: float = 2500.0


class TransformerModel:
    """
    Transformer efficiency model.

    Losses = P_iron (constant) + P_copper × load²
    η = P_load / (P_load + P_iron + P_copper × load²)

    Peak efficiency occurs at load = √(P_iron / P_copper)
    """

    def __init__(self, spec: TransformerSpec = None):
        self.spec = spec or TransformerSpec()

    def _iron_loss_kw(self) -> float:
        """No-load (core/iron) losses — constant regardless of load."""
        return self.spec.rated_power_kva * self.spec.iron_loss_pct / 100.0

    def _copper_loss_kw(self, load_fraction: float) -> float:
        """Load-dependent (copper/winding) losses — proportional to I²."""
        full_load_copper = self.spec.rated_power_kva * self.spec.copper_loss_pct / 100.0
        return full_load_copper * load_fraction ** 2

    def optimal_load_fraction(self) -> float:
        """Load fraction at which transformer reaches peak efficiency."""
        return round(math.sqrt(self.spec.iron_loss_pct / self.spec.copper_loss_pct), 4)

    def efficiency(self, load_fraction: float) -> float:
        """Transformer efficiency at given load fraction (0–1)."""
        if load_fraction <= 0:
            return 0.0

        load_fraction = min(load_fraction, 1.2)
        P_load = load_fraction * self.spec.rated_power_kva

        p_iron = self._iron_loss_kw()
        p_copper = self._copper_loss_kw(load_fraction)

        eta = P_load / (P_load + p_iron + p_copper)
        return round(min(eta, 0.999), 5)

    def output(self, input_power_kw: float) -> Dict:
        """Transform power with losses applied."""
        if input_power_kw <= 0:
            return {"output_kw": 0.0, "input_kw": 0.0, "efficiency": 0.0, "losses_kw": 0.0}

        load_frac = min(input_power_kw / self.spec.rated_power_kva, 1.2)
        eta = self.efficiency(load_frac)

        output_kw = input_power_kw * eta
        losses = input_power_kw - output_kw

        return {
            "output_kw": round(output_kw, 3),
            "input_kw": round(input_power_kw, 3),
            "efficiency": round(eta, 5),
            "losses_kw": round(losses, 3),
        }


# ============================================================
#  CONVENIENCE: FULL POWER CONVERSION CHAIN
# ============================================================

class PowerConversionChain:
    """
    End-to-end power conversion: DC source → Inverter → Transformer → Grid.
    Or reverse: Grid → Transformer → Rectifier → DC load.
    """

    def __init__(self, inverter: InverterModel = None,
                 transformer: TransformerModel = None,
                 rectifier: RectifierModel = None):
        self.inverter = inverter or InverterModel()
        self.transformer = transformer or TransformerModel()
        self.rectifier = rectifier or RectifierModel()

    def dc_to_grid(self, dc_power_kw: float, ambient_c: float = 25.0) -> Dict:
        """Full chain: DC → Inverter → Transformer → Grid."""
        inv = self.inverter.ac_output(dc_power_kw, ambient_c)
        xfmr = self.transformer.output(inv["ac_power_kw"])

        total_losses = inv["losses_kw"] + xfmr["losses_kw"]
        chain_eta = xfmr["output_kw"] / dc_power_kw if dc_power_kw > 0 else 0.0

        return {
            "grid_power_kw": xfmr["output_kw"],
            "dc_input_kw": round(dc_power_kw, 3),
            "inverter_output_kw": inv["ac_power_kw"],
            "inverter_efficiency": inv["efficiency"],
            "transformer_efficiency": xfmr["efficiency"],
            "chain_efficiency": round(chain_eta, 5),
            "total_losses_kw": round(total_losses, 3),
            "derated": inv["derated"],
            "reactive_available_kvar": inv["reactive_available_kvar"],
        }

    def grid_to_dc(self, grid_power_kw: float, ambient_c: float = 25.0) -> Dict:
        """Reverse chain: Grid → Transformer → Rectifier → DC load."""
        xfmr = self.transformer.output(grid_power_kw)
        rect = self.rectifier.dc_output(xfmr["output_kw"], ambient_c)

        total_losses = xfmr["losses_kw"] + rect["losses_kw"]
        chain_eta = rect["dc_power_kw"] / grid_power_kw if grid_power_kw > 0 else 0.0

        return {
            "dc_power_kw": rect["dc_power_kw"],
            "grid_input_kw": round(grid_power_kw, 3),
            "transformer_output_kw": xfmr["output_kw"],
            "rectifier_efficiency": rect["efficiency"],
            "transformer_efficiency": xfmr["efficiency"],
            "chain_efficiency": round(chain_eta, 5),
            "total_losses_kw": round(total_losses, 3),
        }


# ============================================================
#  CLI
# ============================================================

def main():
    print(f"\n{'='*65}")
    print(f"  PRIME Power Electronics — DC-AC Conversion Suite")
    print(f"  PRIMEnergeia S.A.S. | Power Electronics Division")
    print(f"{'='*65}\n")

    # ── Inverter part-load curve ──
    inv = InverterModel()
    print(f"  INVERTER: {inv.spec.name} ({inv.spec.rated_power_kw} kW)")
    print(f"  Topology:  {inv.spec.topology} | Phases: {inv.spec.phases}")
    print(f"  Peak η:    {inv.spec.peak_efficiency * 100:.1f}%")
    print(f"  Euro η:    {inv.spec.euro_efficiency * 100:.1f}%")
    print(f"  {'─'*55}")
    print(f"  {'Load%':>6} {'DC(kW)':>8} {'AC(kW)':>8} {'η(%)':>7} {'Loss(kW)':>9} {'Q(kVAR)':>8}")
    print(f"  {'─'*55}")

    for load_pct in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        dc = inv.spec.rated_power_kw * load_pct / 100
        result = inv.ac_output(dc)
        q = inv.reactive_power_capability(result["ac_power_kw"])
        print(f"  {load_pct:>5}%  {dc:>7.1f}  {result['ac_power_kw']:>7.1f}  "
              f"{result['efficiency']*100:>6.2f}  {result['losses_kw']:>8.2f}  "
              f"{q['q_max_kvar']:>7.1f}")

    # ── Temperature derating ──
    print(f"\n  TEMPERATURE DERATING (100% load)")
    print(f"  {'─'*40}")
    for temp_c in [25, 35, 45, 50, 55, 60]:
        result = inv.ac_output(inv.spec.rated_power_kw, ambient_c=temp_c)
        dera = inv.temperature_derating(temp_c)
        print(f"  {temp_c:>3}°C: {result['ac_power_kw']:>7.1f} kW  "
              f"η={result['efficiency']*100:.2f}%  "
              f"derating={dera*100:.1f}%")

    # ── Full conversion chain ──
    print(f"\n  FULL CHAIN: DC → Inverter → Transformer → Grid")
    print(f"  {'─'*55}")
    chain = PowerConversionChain()
    for load_pct in [10, 25, 50, 75, 100]:
        dc = chain.inverter.spec.rated_power_kw * load_pct / 100
        result = chain.dc_to_grid(dc)
        print(f"  {load_pct:>4}% load: DC={dc:.0f} kW → Grid={result['grid_power_kw']:.1f} kW  "
              f"chain η={result['chain_efficiency']*100:.2f}%")

    # ── Rectifier path ──
    print(f"\n  REVERSE CHAIN: Grid → Transformer → Rectifier → DC")
    print(f"  {'─'*55}")
    rect = RectifierModel()
    for load_pct in [25, 50, 75, 100]:
        ac = rect.spec.rated_power_kw * load_pct / 100
        result = chain.grid_to_dc(ac)
        print(f"  {load_pct:>4}% load: Grid={ac:.0f} kW → DC={result['dc_power_kw']:.1f} kW  "
              f"chain η={result['chain_efficiency']*100:.2f}%")

    # ── Engine presets ──
    print(f"\n  ENGINE PRESETS — Part-load η comparison")
    print(f"  {'─'*65}")
    print(f"  {'Preset':<20} {'10%':>6} {'25%':>6} {'50%':>6} {'75%':>6} {'100%':>6}")
    print(f"  {'─'*65}")
    for name, spec in INVERTER_PRESETS.items():
        m = InverterModel(spec)
        vals = [m.efficiency(l/100)*100 for l in [10, 25, 50, 75, 100]]
        print(f"  {name:<20} {vals[0]:>5.1f}% {vals[1]:>5.1f}% {vals[2]:>5.1f}% "
              f"{vals[3]:>5.1f}% {vals[4]:>5.1f}%")

    # Export
    export = {
        "inverter_spec": asdict(inv.spec),
        "part_load_curve": [],
    }
    for pct in range(0, 105, 5):
        if pct == 0:
            export["part_load_curve"].append({"load_pct": 0, "efficiency": 0})
            continue
        dc = inv.spec.rated_power_kw * pct / 100
        r = inv.ac_output(dc)
        export["part_load_curve"].append({
            "load_pct": pct,
            "efficiency": r["efficiency"],
            "ac_power_kw": r["ac_power_kw"],
            "losses_kw": r["losses_kw"],
        })
    with open("power_electronics_results.json", "w") as f:
        json.dump(export, f, indent=2)
    print(f"\n  📄 Exported to power_electronics_results.json")


if __name__ == "__main__":
    main()
