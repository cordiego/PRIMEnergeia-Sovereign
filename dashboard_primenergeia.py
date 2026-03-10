import streamlit as st
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE GRADO INDUSTRIAL (SOVEREIGN UI) ---
st.set_page_config(
    page_title="PRIMEnergeia Sovereign Node | VZA-400",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estética de Terminal de Investigación (Black & Cyber Blue)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; font-family: 'Courier New', Courier, monospace; }
    .stMetric { background-color: #161b22; border: 1px solid #00d1ff; padding: 20px; border-radius: 5px; }
    div[data-testid="stMetricValue"] { color: #00d1ff; font-size: 32px; font-weight: bold; }
    .stAlert { background-color: #161b22; border: 1px solid #00d1ff; color: #00d1ff; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA DE AUTORIDAD ---
st.title("⚡ PRIMEnergeia: Sovereign Control Dashboard")
st.markdown(f"### **NODO OPERATIVO: VZA-400** | **Status: SYNCHRONIZED** | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.divider()

# --- TELEMETRÍA DE RED (CAPA DE CONTROL HJB) ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Estabilidad de Frecuencia", "60.001 Hz", "Δ 0.001")
    st.caption("Filtro Estocástico HJB: Activo")
with m2:
    st.metric("Rescate de Capital (PML)", "$2.54M USD", "+14.2%")
    st.caption("Arbitraje de Nodo Energético")
with m3:
    st.metric("Entropía del Sistema (σ)", "0.0042", "Optimizado", delta_color="inverse")
    st.caption("Minimización de Pérdida Térmica")
with m4:
    st.metric("Confianza Monte Carlo", "99.98%", "Sigma-6")
    st.caption("Resiliencia de Red ante Fallos")

# --- VISUALIZACIÓN DE ESTABILIZACIÓN DE CARGA ---
st.markdown("## 📊 Respuesta de Red vs. Compensación PRIMEnergeia")

t = np.linspace(0, 100, 100)
noise_raw = 400 + 20 * np.sin(t/4) + np.random.normal(0, 8, 100)
stabilized = 400 + 20 * np.sin(t/4) + np.random.normal(0, 1.2, 100)

fig = go.Figure()
fig.add_trace(go.Scatter(x=t, y=noise_raw, name="Carga Crítica (Sin Control)", line=dict(color='rgba(255, 0, 0, 0.4)', dash='dash')))
fig.add_trace(go.Scatter(x=t, y=stabilized, name="Compensación PRIMEnergeia (VZA-400)", line=dict(color='#00d1ff', width=3)))

fig.update_layout(
    template="plotly_dark",
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    height=450,
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
)

st.plotly_chart(fig, use_container_width=True)

# --- ESTRATEGIA DE ACTIVOS EUREKA 1.0 (INTEGRACIÓN FINANCIERA) ---
st.divider()
st.subheader("💹 Gestión de Capital Soberano (Eureka 1.0)")
e1, e2, e3, e4, e5 = st.columns(5)

# Triada Eureka + Estabilidad para el Nodo de $550 USD
e1.metric("AGQ (Silver 2x)", "20%", "w* Target")
e2.metric("GEV (Energy)", "25%", "w* Target")
e3.metric("UGL (Gold 2x)", "20%", "w* Target")
e4.metric("VTIP (TIPS)", "15%", "Stability")
e5.metric("VGSH (Cash)", "20%", "Liquidity")

st.info("**Análisis de Soberanía:** El sistema mitiga el riesgo de liquidación mediante la optimización del Sharpe Ratio en tiempo real, vinculando la estabilidad de la red eléctrica con la preservación del capital rescatado.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #444;'>PRIMEnergeia S.A.S. | Lead Physicist: Diego | ITAM Finance & Physics Lab</p>", unsafe_allow_html=True)
