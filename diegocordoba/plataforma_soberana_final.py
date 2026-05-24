import torch
import torch.nn as nn
import numpy as np
import multiprocessing as mp
import sqlite3
import time
from fastapi import FastAPI
import uvicorn
import os

# --- 1. MOTOR DE CÁLCULO HJB ---
class AutoHealing_Actor(nn.Module):
    def __init__(self):
        super(AutoHealing_Actor, self).__init__()
        self.fc = nn.Sequential(nn.Linear(4, 128), nn.ReLU(), nn.Linear(128, 1), nn.Tanh())
    def forward(self, x): return self.fc(x)

def engine_worker():
    """Este proceso es el corazón físico. No depende de la API."""
    print(f"[ENGINE] Proceso de cálculo activo (PID: {os.getpid()})")
    model = AutoHealing_Actor()
    model.eval()
    
    # Conexión local al archivo de base de datos
    conn = sqlite3.connect('soberania.db', isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, inercia REAL, rescate REAL, ts DATETIME)")
    cursor.execute("INSERT OR IGNORE INTO metrics (id, inercia, rescate, ts) VALUES (1, 0.0, 0.0, datetime('now'))")
    
    total_rescate = 0.0
    while True:
        # Simulación de sensor
        state = np.array([59.98, 230.0, 450.0, 450.0], dtype=np.float32)
        with torch.no_grad():
            action = model(torch.from_numpy(state)).item()
        
        # Lógica de Rescate Fiduciario
        if state[0] < 59.99:
            total_rescate += 128.12
            
        # Actualizamos la DB (el puente de comunicación)
        cursor.execute("UPDATE metrics SET inercia = ?, rescate = ?, ts = datetime('now') WHERE id = 1", (action, total_rescate))
        time.sleep(0.1)

# --- 2. SERVIDOR API (FASTAPI) ---
app = FastAPI()

@app.get("/")
def get_metrics():
    try:
        conn = sqlite3.connect('soberania.db')
        cursor = conn.cursor()
        cursor.execute("SELECT inercia, rescate, ts FROM metrics WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return {
            "status": "ONLINE",
            "node": "VZA-400",
            "data": {
                "inertia_mw": f"{row[0]:+.4f}",
                "fiduciary_rescue_usd": f"${row[1]:,.2f}",
                "last_update": row[2]
            }
        }
    except Exception as e:
        return {"status": "SYNCING", "error": str(e)}

if __name__ == "__main__":
    print("\n[SISTEMA] Desplegando Arquitectura de Soberanía Distribuida...")
    
    # 1. Limpiamos base de datos previa para evitar bloqueos
    if os.path.exists('soberania.db'): os.remove('soberania.db')
    
    # 2. Lanzamos el motor de física como un proceso independiente
    p_engine = mp.Process(target=engine_worker)
    p_engine.daemon = True
    p_engine.start()
    
    print("[INFO] Motor de física corriendo en segundo plano.")
    print("[INFO] Dashboard disponible en: http://127.0.0.1:8000")
    
    # 3. Lanzamos la API en el hilo principal
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
