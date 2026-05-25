import torch
import torch.nn as nn
import numpy as np
import sqlite3
import time
import os

class PrimeCorporativo(nn.Module):
    def __init__(self):
        super(PrimeCorporativo, self).__init__()
        self.fc = nn.Sequential(nn.Linear(4, 128), nn.ReLU(), nn.Linear(128, 1), nn.Tanh())
    def forward(self, x): return self.fc(x)

def run_engine():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = PrimeCorporativo().to(device).half()
    model.eval()
    
    conn = sqlite3.connect('soberania.db', isolation_level=None)
    cursor = conn.cursor()
    # Estructura enfocada en Utilidades y Dividendos
    cursor.execute("""CREATE TABLE IF NOT EXISTS finanzas_corp 
                      (id INTEGER PRIMARY KEY, inercia REAL, utilidad_acumulada REAL, 
                       dividendos_invertidos REAL, ts DATETIME)""")
    cursor.execute("INSERT OR IGNORE INTO finanzas_corp VALUES (1, 0.0, 0.0, 0.0, datetime('now'))")
    
    utilidad_total = 0.0
    dividendos_totales = 0.0

    print("[SISTEMA] Motor Corporativo v9.0 Activo. Enfoque: Maximización de Utilidad.")

    while True:
        state = np.array([59.98, 230.0, 450.0, 450.0], dtype=np.float32)
        state_t = torch.from_numpy(state).to(device).half().unsqueeze(0)
        
        with torch.no_grad():
            action = model(state_t).item()
        
        if state[0] < 59.99:
            # El ahorro se registra como utilidad bruta de la empresa
            utilidad_total += 145.20 
            
            # Lógica de Dividendos: Se reinvierte el excedente operacional
            if utilidad_total % 10000 < 145.20:
                dividendos_totales += (utilidad_total * 0.20) # 20% a reinversión estratégica

        cursor.execute("""UPDATE finanzas_corp SET inercia = ?, utilidad_acumulada = ?, 
                          dividendos_invertidos = ?, ts = datetime('now') WHERE id = 1""", 
                       (action, utilidad_total, dividendos_totales))
        time.sleep(0.01)

if __name__ == "__main__":
    try: run_engine()
    except KeyboardInterrupt: print("\n[!] Shutdown corporativo.")
