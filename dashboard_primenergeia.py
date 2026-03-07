import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE MARCA ---
st.set_page_config(page_title="PRIMEnergeia Sovereign Console", layout="wide")

st.title("🛡️ PRIMEnergeia | Sovereign Grid Control")
st.sidebar.header("Parámetros del Nodo: VZA-400")
st.sidebar.write("Estado: **ACTIVO (HJB-CORE)**")
st.sidebar.divider()

# --- MÉTRICAS DE PODER (KPIs) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Rescate Fiduciario (USD)", value="$1,845,000.00", delta="+$125,400.00 hoy")
with col2:
    st.metric(label="Estabilidad de Frecuencia", value="59.98 Hz", delta="Optimizado", delta_color="normal")
with col3:
    st.metric(label="Eficiencia de Activos", value="98.4%", delta="0.5% vs Legacy")

st.divider()

# --- SIMULACIÓN DE DATOS EN TIEMPO REAL ---
st.subheader("Visualización de Telemetría Estocástica")

# Generar datos para el gráfico
t = np.linspace(0, 24, 100)
freq_legacy = 60 + 0.3 * np.random.randn(100)
freq_legacy[40:55] -= 0.8  # Simulación de falla legacy
freq_hjb = 60 + 0.05 * np.random.randn(100)

chart_data = pd.DataFrame({
    'Tiempo (Horas)': t,
    'Frecuencia Legacy (Riesgo)': freq_legacy,
    'Frecuencia PRIMEnergeia (Auto-Healing)': freq_hjb
}).set_index('Tiempo (Horas)')

st.line_chart(chart_data, color=["#ff4b5c", "#00d1ff"])

# --- CONTROLES DE ACTUACIÓN ---
st.subheader("Controles de Actuación del Lead Physicist")
col_ctrl1, col_ctrl2 = st.columns(2)

with col_ctrl1:
    agresividad = st.slider("Agresividad del Control HJB", 0.0, 1.0, 0.85)
    st.info(f"Nivel de control calibrado a {agresividad * 100}% de inercia sintética.")

with col_ctrl2:
    if st.button("DESPLEGAR MANIFIESTO DE RESCATE (PDF)"):
        st.success("Generando reporte para el Director de Operaciones... Enviado.")

# --- LOG DE EVENTOS ---
st.divider()
st.subheader("Eventos de Red")
st.table(pd.DataFrame({
    'Evento': ['Inyección de Inercia', 'Compensación de Fase', 'Estabilización de PML'],
    'Impacto Económico': ['$12,500.00', '$45,000.00', '$67,900.00'],
    'Estado': ['Completado', 'Completado', 'Completado']
}))
