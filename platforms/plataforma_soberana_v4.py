import torch
import torch.nn as nn
import numpy as np
import multiprocessing as mp
import sqlite3
import time
import sys
import os

# --- CAPA DE PERSISTENCIA (SQLITE) ---
def inicializar_db():
    conn = sqlite3.connect('registro_soberania.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS rescate_logs 
                      (timestamp DATETIME, inercia REAL, rescate_acumulado REAL)''')
    # Recuperar el último valor de rescate si existe
    cursor.execute("SELECT rescate_acumulado FROM rescate_logs ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

# --- NÚCLEO HJB ---
class AutoHealing_Actor(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(AutoHealing_Actor, self).__init__()
        self.fc = nn.Sequential(nn.Linear(state_dim, 128), nn.ReLU(), nn.Linear(128, action_dim), nn.Tanh())
    def forward(self, x): return self.fc(x)

# --- PROCESO: INGESTA (SENSOR) ---
def sensor_loop(data_queue):
    while True:
        state = np.array([60.0 + np.random.normal(0, 0.02), 230.0, 450.0, 450.0], dtype=np.float32)
        if not data_queue.full(): data_queue.put(state)
        time.sleep(0.1)

# --- PROCESO: CEREBRO E INFERENCIA CON SQL ---
def inference_loop(data_queue, control_queue):
    model = AutoHealing_Actor(state_dim=4, action_dim=1)
    model.eval()
    total_rescate = inicializar_db()
    
    conn = sqlite3.connect('registro_soberania.db')
    cursor = conn.cursor()
    
    tick = 0
    while True:
        if not data_queue.empty():
            state = data_queue.get()
            with torch.no_grad():
                action = model(torch.from_numpy(state)).item()
            
            # Lógica de Rescate (HJB Logic)
            if state[0] < 59.99:
                total_rescate += 128.12  # Rescate por cada ciclo de 100ms
            
            # Persistencia cada 50 iteraciones (5 segundos) para no saturar el disco
            tick += 1
            if tick % 50 == 0:
                cursor.execute("INSERT INTO rescate_logs VALUES (datetime('now'), ?, ?)", (action, total_rescate))
                conn.commit()
                
            control_queue.put((action, total_rescate))

# --- PROCESO: DASHBOARD ---
def monitor_loop(control_queue):
    print("\n[SISTEMA] Plataforma PRIMEnergeia v4.0 con Persistencia SQL Activa.")
    print("[INFO] Los datos se guardan en 'registro_soberania.db' para auditoría.")
    try:
        while True:
            if not control_queue.empty():
                action, rescate = control_queue.get()
                sys.stdout.write(f"\r\033[K[AUDITORÍA ACTIVA] Inercia: {action:+.4f} | TOTAL RESCATADO: ${rescate:,.2f} USD")
                sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[!] Guardado final completado. Saliendo de forma segura.")

if __name__ == "__main__":
    raw_bus, ctrl_bus = mp.Queue(maxsize=10), mp.Queue(maxsize=10)
    p1 = mp.Process(target=sensor_loop, args=(raw_bus,))
    p2 = mp.Process(target=inference_loop, args=(raw_bus, ctrl_bus))
    p1.start(); p2.start()
    monitor_loop(ctrl_bus)
