import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json, os, time
from datetime import datetime

st.set_page_config(page_title="PRIMEnergeia S.A.S. Control", layout="wide")
st.markdown("<style>.main { background-color: #0b1016; color: #ffffff; }</style>", unsafe_allow_html=True)

def get_live_data():
    if os.path.exists("grid_state.json"):
        with open("grid_state.json", "r") as f: return json.load(f)
    return {"f": 60.0, "v": 115.0, "status": "SYNCING", "timestamp": time.time()}

data = get_live_data()
f_actual = data['f']
is_alert = f_actual < 59.95 or f_actual > 60.05

st.title("⚡ PRIMEnergeia S.A.S. - Sovereign Node VZA-400")
st.write(f"ENTIDAD LEGAL AUTORIZADA | STATUS: {'⚠️ ALERTA' if is_alert else '● NOMINAL'}")

m1, m2, m3 = st.columns(3)
m1.metric("FRECUENCIA", f"{f_actual:.3f} Hz", f"{round(f_actual-60, 4)}")
m2.metric("TENSIÓN", f"{data['v']} kV")
m3.metric("RESCATE ESTIMADO", "$2.54M USD")

t_sim = np.linspace(0, 0.05, 500)
shift = 2 * np.pi * f_actual * (data.get('timestamp', 0) % 1)
wave = np.sin(2 * np.pi * f_actual * t_sim + shift)
fig = go.Figure(go.Scatter(x=t_sim, y=wave, line=dict(color='#ff4b4b' if is_alert else '#00d1ff', width=4)))
fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0))
st.plotly_chart(fig, use_container_width=True)

time.sleep(0.2)
st.rerun()
