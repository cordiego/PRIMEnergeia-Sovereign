# PRIMEnergeia Granas™ — Complete Fabrication Protocol (SOP)

**Standard Operating Procedure for the Granas Photovoltaic-Ammonia Architecture**

**Version:** 1.0 — March 2026
**Author:** Diego Córdoba Urrutia — Lead Computational Physicist
**Classification:** PRIMEnergeia S.A.S. Proprietary

---

## System Overview

Granas is a **5-layer integrated energy architecture**:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: ETFE Front Encapsulation              │  Self-cleaning, anti-reflection
├─────────────────────────────────────────────────┤
│  Layer 2: Granas Perovskite Top Cell            │  Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃
│           Green Reflectance @ 535nm             │  Albedo: Tj→42°C, Voc +45mV
├─────────────────────────────────────────────────┤
│  Layer 3: TOPCon Silicon Bottom Cell            │  Enhanced NIR response (>800nm)
├─────────────────────────────────────────────────┤
│  Layer 4: PG-MoSA-BC (Haber-Bosch Back Contact)│  Mo single-site NRR catalyst
│           N₂ + 6H⁺ + 6e⁻ → 2NH₃               │  58.4% Faradaic Efficiency
├─────────────────────────────────────────────────┤
│  Layer 5: CFRP Structural Skeleton              │  17×10.5 geometric blueprint
│           89% photon recycling ridges           │  5× lighter than glass
└─────────────────────────────────────────────────┘
```

---

## Phase 1: CFRP Structural Skeleton (Layer 5)

### Materials
| Material | Spec | Supplier |
|----------|------|----------|
| Carbon fiber tow | Aerospace-grade, continuous 12K | Toray T700S |
| Epoxy resin | Cycloaliphatic, UV-resistant | Huntsman LY556 |
| Mold | CNC-machined aluminum, 17×10.5 unit pattern | Custom |

### Procedure
1. **CNC the mold** — machine the 17×10.5 geometric pattern with edge lengths 5.5, 3.5, and 3.0 units (1 unit = 10cm). Include chamfered ridges at 15° angle for photon recycling.
2. **Lay up CF tow** — wind continuous carbon fiber through multi-axis robotic arm, ensuring uninterrupted fibers across ALL internal vertices. Fiber must loop from 3.0-unit central network through 5.5-unit peripheral triangles without cutting.
3. **Resin transfer molding** — infuse cycloaliphatic epoxy at 60°C under 3 bar vacuum. Hold for 90 min.
4. **Cure** — ramp to 120°C at 2°C/min, hold 4h. Cool at 1°C/min.
5. **Demold and inspect** — max deflection < 1.8mm at 5400 Pa. Weight target: 2.5 kg/m².

### QC Checkpoints
- [ ] Fiber continuity at ALL vertices (visual + ultrasonic)
- [ ] Chamfer angle: 15° ± 1° (optical profilometry)
- [ ] Weight: 2.5 ± 0.3 kg/m²
- [ ] Rigidity: 42% improvement over flat glass (3-point bend test)

---

## Phase 2: TOPCon Silicon Bottom Cell (Layer 3)

### Materials
| Material | Spec |
|----------|------|
| n-type Si wafer | Cz, 180μm, 1-5 Ω·cm, (100) orientation |
| Tunnel oxide | SiO₂, 1.5nm, thermal growth |
| Poly-Si | n⁺ doped, 200nm, LPCVD |
| Passivation | Al₂O₃ (ALD, 10nm) + SiNₓ (PECVD, 75nm) |

### Procedure
1. **RCA clean** — SC-1 (NH₄OH:H₂O₂:H₂O = 1:1:5, 80°C, 10min) → HF dip (2%, 30s) → SC-2 (HCl:H₂O₂:H₂O = 1:1:6, 80°C, 10min).
2. **Tunnel oxide** — grow 1.5nm SiO₂ by thermal oxidation at 630°C, 10min in O₂.
3. **Poly-Si deposition** — LPCVD at 580°C, SiH₄ flow, 200nm. Phosphorus doping by ion implant (5×10¹⁵ cm⁻²).
4. **Anneal** — 850°C, N₂, 20min → activates dopants + crystallizes poly-Si.
5. **Rear passivation** — ALD Al₂O₃ (10nm, 200°C) + PECVD SiNₓ (75nm, 400°C).
6. **Front texturing** — KOH (2 wt%, 80°C, 30min) → random pyramids → SiNₓ ARC.

### QC: implied Voc > 720mV, J₀ < 5 fA/cm²

---

## Phase 3: Granas Perovskite Top Cell (Layer 2)

### 3A: Precursor Preparation

> **CRITICAL: All steps in N₂ glovebox (O₂ < 0.5 ppm, H₂O < 0.5 ppm)**

| Precursor | Amount (per 10mL batch) | Role |
|-----------|------------------------|------|
| PbI₂ | 1.20 M × 461.0 g/mol = 553.2 mg | B-site (95%) |
| CsI | 0.15 × 1.20M × 259.8 g/mol = 46.8 mg | A-site stabilizer |
| FAI (HC(NH₂)₂I) | 0.85 × 1.20M × 172.0 g/mol = 175.4 mg | A-site majority |
| MnCl₂ | 0.02 × 1.20M × 125.8 g/mol = 3.0 mg | Trap passivation |
| Ni(OH)₂ | 0.03 × 1.20M × 92.7 g/mol = 3.3 mg | Bandgap tuning |
| HI (57% aq) | 50 μL | Dissolves Ni(OH)₂ |

**Dissolution protocol:**
1. Add Ni(OH)₂ to 50μL HI in a vial. Stir until clear (Ni²⁺ + 2HI → NiI₂ + H₂O↑). **~5 min at RT.**
2. In a separate vial: dissolve PbI₂ + CsI in DMF:DMSO (**0.7:0.3 v/v**, 7.0mL DMF + 3.0mL DMSO).
3. Heat to 70°C, stir 2h until fully dissolved (yellow-clear solution).
4. Add FAI. Stir 30 min at 70°C.
5. Add MnCl₂. Stir 15 min.
6. Add the NiI₂/HI solution from step 1. Stir 30 min.
7. Cool to RT. Filter through 0.22μm PTFE syringe filter.
8. **Final ink:** 1.20M Cs₀.₁₅FA₀.₈₅Pb₀.₉₅Ni₀.₀₃Mn₀.₀₂I₃ in DMF:DMSO (7:3).

### 3B: Electron Transport Layer (SnO₂)

1. Spin-coat SnO₂ nanoparticle solution (2.5 wt% in H₂O) on TOPCon front surface.
2. **Spin:** 3000 RPM, 30s.
3. **Anneal:** 150°C, 30 min in air.
4. **UV-ozone:** 15 min immediately before perovskite deposition.

### 3C: Perovskite Deposition

> **THIS IS THE CRITICAL STEP — timing matters to the second**

1. Mount substrate on spin coater chuck. Dispense 80μL of Granas ink.
2. **Spin program:**
   - Step 1: 1000 RPM, 10s (spread)
   - Step 2: **4100 RPM**, 30s (thinning)
3. **Anti-solvent drip:** At exactly **t = 10s into Step 2** (i.e., t=20s total), rapidly dispense 200μL chlorobenzene from a height of 1cm onto the spinning substrate.
4. **Film color:** Wet film appears brown-green. The green tint confirms Ni²⁺ incorporation.
5. **Result:** Film thickness ≈ 700 nm. Wet film.

### 3D: Annealing (Green Reflectance Formation)

> **Temperature accuracy is critical: use calibrated thermocouple on hot plate surface**

1. Place film on pre-heated hot plate at **100°C, 10 min** (nucleation stage).
2. Ramp to **148°C** (2°C/min). Hold **15 min** (grain growth + green interference).
3. **NEVER exceed 150°C** — decomposition onset. The green reflection at 535nm forms from quarter-wave interference at precisely this thickness/composition.
4. Cool to RT on metal block (rapid quench preserves phase).
5. **Visual check:** Film should appear distinctly **green** under white light — NOT black, NOT yellow. Green = correct Ni²⁺/Mn²⁺ incorporation + quarter-wave condition satisfied.

### 3E: Hole Transport Layer + Top Contact

1. **Spiro-OMeTAD:** Dissolve 72.3 mg in 1mL chlorobenzene + 28.8μL t-BP + 17.5μL Li-TFSI (520mg/mL in ACN). Spin at 3000 RPM, 30s.
2. **Oxidize:** Leave in dry air box (RH < 20%) overnight.
3. **Au contact:** Thermal evaporation, 80nm, at < 1×10⁻⁶ mbar. Use shadow mask for electrode pattern.

---

## Phase 4: Haber-Bosch Back Contact PG-MoSA-BC (Layer 4)

### 4A: Mo Single-Site Catalyst Synthesis

| Material | Spec | Role |
|----------|------|------|
| Carbon black | Ketjenblack EC-600JD | Support matrix |
| MoCl₅ | 99.99%, anhydrous | Mo precursor |
| Melamine | C₃H₆N₆ | N-doping source |

1. **Create Mo-N-C precursor:** Mix 500 mg carbon black + 50 mg MoCl₅ + 200 mg melamine in 20 mL ethanol. Sonicate 2h.
2. **Dry:** Rotary evaporate at 60°C until powder.
3. **Pyrolysis:** 900°C, 2h, under Ar flow (100 sccm). Ramp 5°C/min. This creates isolated Mo-N₄ single sites in carbon lattice.
4. **Acid leach:** Wash with 0.5M H₂SO₄ (80°C, 8h) to remove Mo nanoparticles (keep only single sites). Filter, wash with DI water, dry at 80°C.
5. **Verify:** XPS for Mo³⁺/Mo⁴⁺ oxidation state. EXAFS for Mo-N bond at 2.1Å. ICP-MS for Mo loading (target: 2-3 wt%).

### 4B: Back Contact Electrode Fabrication

1. **Ink preparation:** 80 wt% Mo-N-C catalyst + 15 wt% carbon black + 5 wt% Nafion binder in IPA:H₂O (3:1). Mill 24h.
2. **Coat on gas diffusion layer:** Doctor-blade onto carbon paper (SGL 39BC). Loading: 1.0 mg_Mo/cm².
3. **Dry:** 80°C, 2h in vacuum.
4. **Hot press:** Bond to TOPCon rear surface at 130°C, 5 MPa, 5 min using conductive adhesive.

### 4C: NRR Operation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Electrolyte | 0.1M HCl, N₂-saturated | Acidic → NH₄⁺ product |
| N₂ pressure | 50 bar | Overcomes solubility limit |
| Applied potential | -0.4 V vs. RHE | Optimal for Mo-N₄ sites |
| Temperature | 25°C | Ambient, no heating needed |
| **Faradaic Efficiency** | **58.4%** | vs. 0.8% for Pt/C |
| NH₃ yield rate | Lab-scale continuous | ΔG_H = +0.45 eV (HER suppressed) |

---

## Phase 5: Albedo Enhancement (Green Reflectance System)

### How It Works

The Granas cell **intentionally reflects green light** (500-570nm) instead of absorbing it:

```
Incident AM1.5G spectrum (1000 W/m²)
        ↓
   ┌─────────────────────────┐
   │  UV + Blue (300-500nm)  │ → ABSORBED by perovskite → electricity
   │  GREEN (500-570nm)      │ → REFLECTED at 535nm → cooling
   │  Red (570-800nm)        │ → ABSORBED by perovskite → electricity
   │  NIR (800-1200nm)       │ → TRANSMITTED → absorbed by Si bottom cell
   └─────────────────────────┘
        ↓ reflected green
   Surrounding environment receives
   diffuse green light → urban cooling
```

### Thermal Benefit (from Verde-1 simulation)

| Metric | Control (MAPbI₃) | Granas | Benefit |
|--------|------------------|--------|---------|
| Junction Temp | 68°C | 42°C | **−26°C** |
| Voc | 1090 mV | 1135 mV | **+45 mV** |
| PCE initial | 22.1% | 19.8% | −2.3% (green sacrifice) |
| PCE @ 1000h | 16.4% | 19.5% | **+3.1%** (stability wins) |
| k_deg | 2.4×10⁻⁴ h⁻¹ | 1.2×10⁻⁵ h⁻¹ | **20× slower degradation** |
| T80 | 930 h (5 weeks) | 18,600 h (2.1 yr) | **20× longer life** |

### Urban Albedo Effect

Green-reflecting Granas modules installed on rooftops **reduce urban heat island effect**:
- Each m² of Granas reflects ~60 W of green light back to the atmosphere
- Building surface temperature drops ~8°C under Granas vs. black panels
- Annual HVAC energy savings: estimated 15-20% for buildings underneath

---

## Phase 6: Final Assembly

1. **Bond Layers 2-4** (perovskite/TOPCon/back contact) into monolithic stack using optical-grade silicone adhesive.
2. **Mount into CFRP skeleton** — insert monolithic stack into the green-hued polygonal fields of the 17×10.5 frame. Seal edges with CFRP-compatible gasket.
3. **ETFE front encapsulation** — thermoform macroscopic ETFE sheet onto CFRP skeleton. Heat-seal at 270°C. The ETFE provides anti-reflection + self-cleaning + UV protection.
4. **Wire bonding** — connect Au top contacts to bus bars routed through CFRP ridges.
5. **N₂ feed** — connect gas diffusion back contact to pressurized N₂ line (50 bar) via rear manifold.

---

## QC Final Test Protocol

| Test | Method | Target |
|------|--------|--------|
| PCE | Solar simulator AM1.5G, 1000 W/m² | > 20% |
| Voc | I-V curve | > 1100 mV |
| Green reflectance | Spectrophotometer, 535nm | R > 30% |
| Junction temp | IR thermography, 1h soak | < 45°C |
| Weight | Scale | < 3.0 kg/m² |
| Mechanical | 5400 Pa transverse load | Deflection < 2mm |
| NRR Faradaic eff. | Indophenol blue, N₂ at 50 bar | > 50% |
| T80 (accelerated) | 85°C/85%RH damp heat, 1000h | PCE retention > 90% |

---

**PRIMEnergeia S.A.S.** — *Soberanía Energética Global* ⚡🇲🇽

*Granas™: Solar energy + Green ammonia + Urban cooling — unified in one architecture*
