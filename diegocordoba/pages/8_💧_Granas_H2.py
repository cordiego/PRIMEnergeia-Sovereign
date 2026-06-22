"""PRIMEnergeia — PEM Electrolysis Green Hydrogen | CEO-Grade Dashboard"""
# --- DEMO/LIVE Mode Banner ---
import sys as _sys, os as _os
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path: _sys.path.insert(0, _root)
try:
    from lib.mode_gate import show_mode_banner
    show_mode_banner()
except Exception: pass
try:
    from lib.granas_handshake import show_handshake_sidebar
    show_handshake_sidebar()
except Exception: pass
# --- End Banner ---
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ═══════════════════════════════════════════════════════════
# Physical Constants
# ═══════════════════════════════════════════════════════════
F = 96485.0
R_GAS = 8.314
MW_H2 = 2.016e-3
HHV_H2 = 39.4
STOICH_H2O = 9.0

st.header("💧 Granas H2 — PEM Electrolysis Engine")
st.caption("Nafion 212 PEM Stack | IrO₂/Pt/C Electrodes | Solar Load-Following | Zero-Carbon Green H₂")

# ─── Parameters ───
with st.expander("⚙️ Electrolyzer Parameters", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        current_density = st.slider("Current Density (A/cm²)", 0.5, 3.5, 2.0, 0.1)
        temperature = st.slider("Stack Temperature (°C)", 50, 90, 80, 5)
    with c2:
        pressure = st.slider("H₂ Pressure (bar)", 5, 50, 30, 5)
        n_cells = st.slider("Cells in Stack", 20, 200, 80, 10)
    with c3:
        solar_capacity = st.slider("Solar Capacity (MW)", 10, 200, 50, 10)
        solar_fraction = st.slider("Solar → H₂ (%)", 5, 30, 15, 1)

# ═══════════════════════════════════════════════════════════
# Electrolysis Physics
# ═══════════════════════════════════════════════════════════
T_K = temperature + 273.15
active_area = 500.0  # cm² per cell

# Reversible voltage (Nernst)
E0 = 1.229
delta_s = -163.0
e_rev = E0 - (delta_s / (2 * F)) * (T_K - 298.15) + (R_GAS * T_K / (2 * F)) * np.log(pressure * np.sqrt(1.0))

# Thermoneutral voltage
delta_h = 286e3 - 10.0 * (T_K - 298.15)
e_tn = delta_h / (2 * F)

# Activation overpotential (Tafel)
j = current_density
eta_act_a = 0.060 * np.log10(max(j, 1e-10) / 1e-7)  # IrO₂ OER
eta_act_c = 0.030 * np.log10(max(j, 1e-10) / 1e-3)   # Pt/C HER
eta_act = max(0, eta_act_a) + max(0, eta_act_c)

# Ohmic overpotential
r_mem = (50e-4) / 0.10  # 50μm Nafion / 0.10 S/cm
r_contact = 0.02
eta_ohm = j * (r_mem + r_contact)

# Mass transport
j_lim = 4.0
eta_mt = (R_GAS * T_K / (2 * F)) * np.log(j_lim / max(j_lim - j, 0.04)) if j < j_lim * 0.99 else 0.5

# Cell voltage
v_cell = e_rev + eta_act + eta_ohm + eta_mt

# Efficiency
cell_eff = min(100, e_tn / v_cell * 100) if v_cell > 0 else 0
sys_eff = cell_eff * 0.92  # -8% BoP

# Production rate (Faraday's law)
I_total = j * active_area * n_cells  # Amperes
mol_h2_s = I_total / (2 * F)
h2_kg_h = mol_h2_s * MW_H2 * 3600
h2_kg_day = h2_kg_h * 24
power_kw = v_cell * I_total / 1000
kwh_per_kg = power_kw / max(h2_kg_h, 1e-10)
h2o_kg_h = h2_kg_h * STOICH_H2O

# Solar coupling
h2_power_mw = solar_capacity * solar_fraction / 100
annual_mwh = h2_power_mw * 0.22 * 8760
h2_annual_kg = annual_mwh * 1000 / (HHV_H2 / 0.70)
h2_annual_t = h2_annual_kg / 1000
revenue_annual = h2_annual_kg * 4.50

# LCOH
crf = (0.08 * 1.08**10) / (1.08**10 - 1)
capex_total = 810 * h2_power_mw * 1000
annual_capex = capex_total * crf
annual_opex = capex_total * 0.03
annual_elec = annual_mwh * 1000 * 30 / 1000  # $30/MWh
lcoh = (annual_capex + annual_opex + annual_elec) / max(h2_annual_kg, 1)

# ─── KPI Row 1 ───
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⚡ Cell Voltage", f"{v_cell:.3f} V")
k2.metric("🔋 Cell Efficiency", f"{cell_eff:.1f}%")
k3.metric("🏭 System Efficiency", f"{sys_eff:.1f}%")
k4.metric("💧 H₂ Rate", f"{h2_kg_h:.2f} kg/h")
k5.metric("⚡ Power", f"{power_kw:.0f} kW")

# ─── KPI Row 2 ───
k6, k7, k8, k9, k10 = st.columns(5)
k6.metric("📊 Energy", f"{kwh_per_kg:.1f} kWh/kg")
k7.metric("🏢 H₂/day", f"{h2_kg_day:.0f} kg")
k8.metric("💧 H₂O/h", f"{h2o_kg_h:.1f} kg")
k9.metric("💰 LCOH", f"${lcoh:.2f}/kg")
k10.metric("🌍 CO₂", "0 kg/kg H₂", "-9.3 vs SMR")

# ─── KPI Row 3: solar coupling ───
k11, k12, k13, k14, k15 = st.columns(5)
k11.metric("☀️ Solar → H₂", f"{h2_power_mw:.1f} MW")
k12.metric("📅 Annual H₂", f"{h2_annual_t:.0f} tonnes")
k13.metric("💵 Revenue", f"${revenue_annual/1e6:.1f}M/yr")
k14.metric("⏱️ Stack Life", "80,000 h")
k15.metric("📉 Degradation", "4 μV/h")

st.divider()

# ═══════════════════════════════════════════════════════════
# Charts
# ═══════════════════════════════════════════════════════════
c1, c2 = st.columns(2)

with c1:
    # Polarization curve
    j_arr = np.linspace(0.05, 3.5, 60)
    v_arr = []
    eff_arr = []
    for jj in j_arr:
        ea = max(0, 0.060 * np.log10(max(jj, 1e-10)/1e-7)) + max(0, 0.030 * np.log10(max(jj, 1e-10)/1e-3))
        eo = jj * (r_mem + r_contact)
        em = (R_GAS * T_K / (2*F)) * np.log(j_lim / max(j_lim - jj, 0.04)) if jj < j_lim*0.99 else 0.5
        vv = e_rev + ea + eo + em
        v_arr.append(vv)
        eff_arr.append(min(100, e_tn / vv * 100) if vv > 0 else 0)

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=j_arr, y=v_arr, name="V_cell",
        line=dict(color="#00d1ff", width=3)), secondary_y=False)
    fig1.add_trace(go.Scatter(x=j_arr, y=eff_arr, name="η_cell (%)",
        line=dict(color="#00ff64", width=2, dash="dot")), secondary_y=True)
    fig1.add_vline(x=current_density, line_dash="dash", line_color="gold",
        annotation_text=f"Operating: {current_density} A/cm²")
    fig1.add_hline(y=e_rev, line_dash="dot", line_color="rgba(255,255,255,0.3)",
        annotation_text="E_rev", secondary_y=False)
    fig1.update_layout(title="Polarization Curve & Efficiency", height=380,
        xaxis_title="Current Density (A/cm²)",
        margin=dict(t=40, b=40), legend=dict(x=0.02, y=0.98),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)', title="V_cell (V)"),
        yaxis2=dict(title="Efficiency (%)"))
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    # LCOH sensitivity
    elec_prices = np.arange(10, 110, 5)
    lcohs = []
    for ep in elec_prices:
        ae = annual_mwh * 1000 * ep / 1000
        ll = (annual_capex + annual_opex + ae) / max(h2_annual_kg, 1)
        lcohs.append(ll)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=elec_prices, y=lcohs, name="LCOH",
        line=dict(color="#00d1ff", width=3), fill="tozeroy",
        fillcolor="rgba(0,209,255,0.08)"))
    fig2.add_hline(y=4.50, line_dash="dash", line_color="#00ff64",
        annotation_text="Green H₂ Market ($4.50)")
    fig2.add_hline(y=1.50, line_dash="dash", line_color="#ff4444",
        annotation_text="Grey H₂ SMR ($1.50)")
    fig2.update_layout(title="LCOH vs Electricity Price", height=380,
        xaxis_title="Electricity ($/MWh)", yaxis_title="LCOH ($/kg H₂)",
        margin=dict(t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig2, use_container_width=True)

# ─── Technology Comparison ───
st.subheader("📊 PEM Electrolysis vs Alternatives")
t1, t2 = st.columns(2)
with t1:
    techs = ["PEM\n(Granas)", "Alkaline", "SMR\n(Grey)", "SOEC"]
    effs = [sys_eff, 62, 76, 82]
    co2s = [0, 0, 9.3, 0]
    colors = ['rgba(0,209,255,0.7)', 'rgba(100,200,100,0.6)',
              'rgba(200,80,80,0.7)', 'rgba(180,130,255,0.6)']

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=techs, y=effs, name='Efficiency (%)',
        marker_color=colors))
    fig3.update_layout(title="System Efficiency Comparison", height=300,
        margin=dict(t=40, b=40), yaxis_title="Efficiency (%)",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'))
    st.plotly_chart(fig3, use_container_width=True)

with t2:
    st.markdown(f"""
**PEM Electrolysis Reaction:**
```
2H₂O(l) → 2H₂(g) + O₂(g)
E° = 1.229 V | ΔG° = +237.2 kJ/mol
```

**Granas H₂ Advantages:**
- ⚡ **Load-following** — ramps in seconds (solar-coupled)
- 🌡️ Low temp (80°C) vs SOEC (800°C) or SMR (850°C)
- 🌍 **Zero carbon** — 9.3 kg CO₂/kg H₂ avoided vs SMR
- 💧 Pure H₂O feedstock (9 kg/kg H₂)
- 🔗 Feeds downstream: **fuel cells**, **turbines**, **Haber-Bosch**

**Downstream Chain:**
```
Granas Solar → PEM Stack → H₂ Storage
                                │
                    ├→ PEM Fuel Cells (PEM-PB-50)
                    ├→ H₂ Turbines (HY-P100)
                    └→ Haber-Bosch → NH₃ → A-ICE
```
    """)
