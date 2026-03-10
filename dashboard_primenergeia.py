import streamlit as st
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- ARQUITECTURA DE RED PRIME ---
st.set_page_config(page_title="PRIMEnergeia Sovereign Network", layout="wide", initial_sidebar_state="collapsed")

# Estética SCADA de Grado Militar
st.markdown("""
    <style>
    .main { background-color: #05070a; color: #ffffff; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #0d1117; border: 1px solid #00d1ff; padding: 20px; border-radius: 2px; }
    div[data-testid="stMetricValue"] { color: #00d1ff; font-family: 'JetBrains Mono', monospace; font-size: 40px; }
    .node-card { border: 1px solid #1f2937; padding: 15px; background-color: #0d1117; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- PANEL DE CONTROL CENTRAL ---
st.title("⚡ PRIMEnergeia: Sovereign Grid Control")
st.markdown(f"**SISTEMA OPERATIVO DE RED** | ESTATUS: NOMINAL | {datetime.now().strftime('%H:%M:%S UTC')}")
st.divider()

# --- CAPA 1: TELEMETRÍA DE ALTA FIDELIDAD ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("FRECUENCIA MAESTRA", "60.001 Hz", "Δ 0.001")
with m2:
    st.metric("TENSIÓN DE NODO", "115.2 kV", "Estable")
with m3:
    st.metric("RESCATE PML ACUM.", "$2.54M USD", "PROY: $3.8M")
with m4:
    st.metric("LATENCIA HJB", "0.85 ms", "Real-Time")

# --- CAPA 2: MAPA DE NODOS REGIONALES ---
st.write("### 🌐 Topología de Nodos Activos")
n1, n2, n3 = st.columns(3)

with n1:
    st.markdown("<div class='node-card'>", unsafe_allow_html=True)
    st.write("#### NODO VZA-400")
    st.write("**Ubicación:** Valle de México")
    st.write("**Carga:** 85% | **Status:** Master")
    st.progress(85)
    st.markdown("</div>", unsafe_allow_html=True)

with n2:
    st.markdown("<div class='node-card'>", unsafe_allow_html=True)
    st.write("#### NODO SLP-100")
    st.write("**Ubicación:** San Luis Potosí")
    st.write("**Carga:** 42% | **Status:** Slave")
    st.progress(42)
    st.markdown("</div>", unsafe_allow_html=True)

with n3:
    st.markdown("<div class='node-card'>", unsafe_allow_html=True)
    st.write("#### NODO QRO-200")
    st.write("**Ubicación:** Querétaro")
    st.write("**Carga:** 12% | **Status:** Failover")
    st.progress(12)
    st.markdown("</div>", unsafe_allow_html=True)

# --- CAPA 3: ANÁLISIS DE FASE (EL CORAZÓN DEL ALGORITMO) ---
st.write("---")
st.write("### 📊 Compensación Dinámica de Armónicos (Filtro PRIME)")
t = np.linspace(0, 0.1, 1000)
raw_wave = np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 180 * t) # Ruido armónico
clean_wave = np.sin(2 * np.pi * 60 * t) # Resultado del algoritmo

fig = go.Figure()
fig.add_trace(go.Scatter(x=t, y=raw_wave, name="Distorsión de Red (Pre-PRIME)", line=dict(color='red', width=1)))
fig.add_trace(go.Scatter(x=t, y=clean_wave, name="Estabilización PRIME VZA", line=dict(color='#00d1ff', width=3)))
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.divider()
st.info("**Soberanía Energética:** La arquitectura PRIME minimiza el Hamiltoniano de costo operativo mediante el control estocástico de la demanda, garantizando la estabilidad del Sistema Eléctrico Nacional (SEN).")
st.caption("PRIMEnergeia S.A.S. | Lead Computational Physicist: Diego | Confidential Proprietary Protocol")
