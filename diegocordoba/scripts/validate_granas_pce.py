#!/usr/bin/env python3
"""
Granas PCE 30.3% Physical Model Validation Script
=================================================
Executes the thermodynamic and structural model for the Granas
tandem architecture, asserting that it meets the physical
metrics defined in the validation protocol.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from granas_module.pce_physics import GranasPCEValidator, TargetMetrics

def run_validation():
    print("=" * 60)
    print(" GRANAS TANDEM ARCHITECTURE - PHYSICAL MODEL VALIDATION")
    print("=" * 60)
    
    validator = GranasPCEValidator()
    results = validator.evaluate_model()
    targets = TargetMetrics()
    
    # Validation checks
    passed = True
    checks = [
        ("Power Conversion Efficiency (PCE)", results["pce_pct"], targets.pce_target, "%"),
        ("Open Circuit Voltage (Voc)", results["voc_mv"], targets.voc_target_mv, "mV"),
        ("Grain Size", results["grain_size_nm"], targets.grain_size_nm, "nm"),
        ("Defect Density (N_def)", results["defect_density"], targets.defect_density, "a.u."),
        ("Stability Score", results["stability_score"], targets.stability_score, "")
    ]
    
    print(f"{'Metric':<35} | {'Measured':<10} | {'Target':<10}")
    print("-" * 60)
    for name, measured, target, unit in checks:
        status = "✅ PASS" if abs(measured - target) < 0.1 else "❌ FAIL"
        if "FAIL" in status:
            passed = False
        print(f"{name:<35} | {measured:<6} {unit:<3} | {target:<6} {unit:<3} {status}")
        
    print("-" * 60)
    if passed:
        print(" VALIDATION STATUS: ALL TARGET METRICS ACHIEVED.")
        print(" Physical thermodynamic apportionment supports the 30.3% PCE.")
    else:
        print(" VALIDATION STATUS: DEVIATION DETECTED.")
        print(" Review perovskite fabrication parameters (Ni:Mn co-doping).")
        sys.exit(1)
        
    print("=" * 60)

if __name__ == "__main__":
    run_validation()
