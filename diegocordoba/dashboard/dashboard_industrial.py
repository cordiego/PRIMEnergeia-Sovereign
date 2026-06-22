import streamlit as st
import numpy as np
import time
from datetime import datetime

# Configuración de la página (apariencia industrial/terminal)
st.set_page_config(page_title="PRIMEnergeia Industrial Dashboard", layout="centered")

# CSS para recrear el entorno de terminal
st.markdown("""
<style>
    /* Fondo oscuro y fuente de terminal */
    .stApp {
        background-color: #0d1117;
        color: #00ff00;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Ocultar elementos de UI de Streamlit para mayor inmersión */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Contenedor principal de la terminal */
    .terminal-box {
        background-color: #000000;
        border: 2px solid #00d1ff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 15px rgba(0, 209, 255, 0.2);
    }
    
    /* Clases de colores ANSI simulados */
    .ansi-green { color: #00ff00; font-weight: bold; }
    .ansi-blue { color: #00d1ff; font-weight: bold; }
    .ansi-cyan { color: #00ffff; font-weight: bold; }
    .ansi-yellow { color: #ffd700; font-weight: bold; }
    .ansi-red { color: #ff0000; font-weight: bold; }
    .ansi-bold { font-weight: bold; color: #ffffff; }
    
    .divider {
        color: #00d1ff;
        font-weight: bold;
        letter-spacing: 2px;
    }
    
    /* Animación de pulso para estado en vivo */
    .blinking-text {
        animation: blinker 1.5s linear infinite;
        color: #ffd700;
        font-weight: bold;
    }
    @keyframes blinker {
        50% { opacity: 0.3; }
    }
</style>
""", unsafe_allow_html=True)

def generate_simulated_data():
    # Simula la lectura de la base de datos local
    inercia = np.random.normal(0, 0.05)
    rescate = 2540123.00 + (time.time() % 1000) * 1.5 # Crece lentamente
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return inercia, rescate, ts

def render_dashboard():
    # Usamos un placeholder para actualizar la interfaz en tiempo real
    placeholder = st.empty()
    
    while True:
        inercia, rescate, ts = generate_simulated_data()
        
        # Lógica de la barra de inercia
        bar_len = min(int(abs(inercia) * 500), 50) # Escalar para que se vea movimiento
        bar = "█" * bar_len + " " * (50 - bar_len)
        color_class = "ansi-green" if abs(inercia) < 0.05 else "ansi-yellow"
        
        with placeholder.container():
            st.markdown(f"""
            <div class="terminal-box">
                <div class="divider">======================================================================</div>
                <div align="center" class="ansi-cyan" style="font-size: 1.2em;">PRIMEnergeia Granas | SISTEMA DE CONTROL DE ESTABILIDAD ACTIVE</div>
                <div class="divider">======================================================================</div>
                <br>
                <div><span class="ansi-bold"> NODO REFERENCIA (datos públicos CENACE): </span> VZA-400 (Valle de México)</div>
                <div><span class="ansi-bold"> STATUS SENSORIAL: </span> <span class="ansi-green">SYNC OK</span> | <span class="ansi-bold">ESTADO HJB:</span> <span class="ansi-green">OPTIMIZED</span></div>
                <br>
                <div class="divider">----------------------------------------------------------------------</div>
                <div><span class="ansi-bold"> RESPUESTA DE INERCIA (MW): </span> <span class="{color_class}">[{bar}] {inercia:+.4f}</span></div>
                <div class="divider">----------------------------------------------------------------------</div>
                <br>
                <div><span class="ansi-bold ansi-yellow"> MÉTRICAS DE CUMPLIMIENTO Y AHORRO (CLIENT VIEW):</span></div>
                <div> > Capital Rescatado (CENACE):    <span class="ansi-green">${rescate:,.2f} USD</span></div>
                <div> > Mitigación de Fatiga Térmica:  <span class="ansi-cyan">14.2% (Asset Protection)</span></div>
                <div> > Estabilidad de Fase:          <span class="ansi-green">99.98% (Nominal)</span></div>
                <br>
                <div class="divider">----------------------------------------------------------------------</div>
                <div><span class="ansi-bold"> ÚLTIMA SINCRONIZACIÓN: </span> {ts}</div>
                <div class="divider">======================================================================</div>
                <br>
                <div class="blinking-text"> [!] TRANSMITIENDO TELEMETRÍA EN TIEMPO REAL A ENGIE/ENEL</div>
            </div>
            """, unsafe_allow_html=True)
            
        time.sleep(0.5)

if __name__ == "__main__":
    render_dashboard()
