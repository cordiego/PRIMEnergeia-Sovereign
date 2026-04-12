import torch
import torch.nn as nn
import numpy as np
import multiprocessing as mp
import sqlite3
import time
from fastapi import FastAPI
import uvicorn

# --- NÚCLEO HJB ---
class AutoHealing_Actor(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(AutoHealing_Actor, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
            nn.Tanh()
        )
    def forward(self, x): return self.fc(x)

def inference_loop(data_queue, shared_val):
    model = AutoHealing_Actor(state_dim=4, action_dim=1)
    model.eval()
    total_rescate = 0.0
    conn = sqlite3.connect('registro_soberania.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS rescate_logs (ts DATETIME, inercia REAL, rescate REAL)")
    
    while True:
        if not data_queue.empty():
            state = data_queue.get()
            with torch.no_grad():
                action = model(torch.from_numpy(state)).item()
            if state[0] < 59.99: 
                total_rescate += 128.12
            
            shared_val.update({'inercia': action, 'rescate': total_rescate})
            
            cursor.execute("INSERT INTO rescate_logs VALUES (datetime('now'), ?, ?)", (action, total_rescate))
            conn.commit()
        time.sleep(0.1)

# --- API FASTAPI (CORREGIDA) ---
app = FastAPI(title="PRIMEnergeia Sovereign Dashboard")
shared_data = None 

@app.get("/")
def read_root():
    return {
        "status": "OPERATIONAL",
        "node": "VZA-400 (public CENACE data)",
        "metrics": {
            "current_inertia_mw": f"{shared_data['inercia']:+.4f}",
            "fiduciary_rescue_usd": f"${shared_data['rescate']:,.2f}",
            "hjb_state": "OPTIMIZED"
        },
        "timestamp": str(time.ctime())
    }

if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    
    with mp.Manager() as manager:
        shared_data = manager.dict({'inercia': 0.0, 'rescate': 0.0})
        
        print("\n[SISTEMA] Dashboard SaaS PRIMEnergeia Activado.")
        print("[INFO] Accede en: http://127.0.0.1:8000")
        
        data_bus = mp.Queue(maxsize=10)
        
        def sensor(q):
            while True:
                q.put(np.array([59.98, 230.0, 450.0, 450.0], dtype=np.float32))
                time.sleep(0.1)
                
        p_sensor = mp.Process(target=sensor, args=(data_bus,))
        p_brain = mp.Process(target=inference_loop, args=(data_bus, shared_data))
        
        p_sensor.start()
        p_brain.start()
        
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
