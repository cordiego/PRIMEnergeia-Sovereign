import torch
import torch.nn as nn
import numpy as np
import multiprocessing as mp
import sqlite3
import time
from fastapi import FastAPI
import uvicorn
import os

# --- 1. MOTOR DE CÁLCULO HJB + EUREKA ---
class AutoHealing_Actor(nn.Module):
    def __init__(self):
        super(AutoHealing_Actor, self).__init__()
        self.fc = nn.Sequential(nn.Linear(4, 128), nn.ReLU(), nn.Linear(128, 1), nn.Tanh())
    def forward(self, x): return self.fc(x)

def engine_worker():
    model = AutoHealing_Actor()
    model.eval()
    
    conn = sqlite3.connect('soberania.db', isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, inercia REAL, rescate REAL, ugl_units REAL, agq_units REAL, ts DATETIME)")
    cursor.execute("INSERT OR IGNORE INTO metrics (id, inercia, rescate, ugl_units, agq_units, ts) VALUES (1, 0.0, 0.0, 0.0, 0.0, datetime('now'))")
    
    total_rescate = 0.0
    ugl_units, agq_units = 0.0, 0.0
    last_investment_milestone = 0.0
    
    # Precios simulados (Eureka 1.0)
    UGL_PRICE, AGQ_PRICE = 75.0, 35.0

    while True:
        state = np.array([59.98, 230.0, 450.0, 450.0], dtype=np.float32)
        with torch.no_grad():
            action = model(torch.from_numpy(state)).item()
        
        if state[0] < 59.99:
            total_rescate += 128.12 # Rescate bruto
            
        # --- LÓGICA DE INVERSIÓN EUREKA 1.0 ---
        # Cada vez que el rescate acumulado sube $5,000 USD (tu regalía de ~25%)
        # Invertimos automáticamente en metales
        if total_rescate - last_investment_milestone >= 5000:
            inversion = 5000 * 0.50 # Solo invertimos el 50% de las regalías
            ugl_units += (inversion * 0.5) / UGL_PRICE
            agq_units += (inversion * 0.5) / AGQ_PRICE
            last_investment_milestone = total_rescate
            
        cursor.execute("""UPDATE metrics SET inercia = ?, rescate = ?, ugl_units = ?, agq_units = ?, ts = datetime('now') 
                          WHERE id = 1""", (action, total_rescate, ugl_units, agq_units))
        time.sleep(0.1)

# --- 2. SERVIDOR API (DASHBOARD PATRIMONIAL) ---
app = FastAPI()

@app.get("/")
def get_metrics():
    conn = sqlite3.connect('soberania.db')
    cursor = conn.cursor()
    cursor.execute("SELECT inercia, rescate, ugl_units, agq_units, ts FROM metrics WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    # Precios actuales simulados
    UGL_PRICE, AGQ_PRICE = 75.0, 35.0
    val_patrimonio = (row[2] * UGL_PRICE) + (row[3] * AGQ_PRICE)
    
    return {
        "node_status": "OPTIMIZED_BY_PRIMEnergeia",
        "realtime_metrics": {
            "fiduciary_rescue_usd": f"${row[1]:,.2f}",
            "grid_inertia_mw": f"{row[0]:+.4f}"
        },
        "eureka_1.0_portfolio": {
            "total_value_usd": f"${val_patrimonio:,.2f}",
            "assets": {
                "UGL_Gold_2x_units": f"{row[2]:.2f}",
                "AGQ_Silver_2x_units": f"{row[3]:.2f}"
            },
            "strategy": "Eureka 1.0 Multi-Asset Allocation"
        },
        "timestamp": row[4]
    }

if __name__ == "__main__":
    if os.path.exists('soberania.db'): os.remove('soberania.db')
    p_engine = mp.Process(target=engine_worker)
    p_engine.daemon = True
    p_engine.start()
    print("\n[EUREKA] Motor de Inversión y Control Activo.")
    print("[INFO] Dashboard Patrimonial: http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
