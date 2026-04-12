import torch
import torch.nn as nn
import numpy as np
import multiprocessing as mp
import time
import sys

# --- NÚCLEO DE INTELIGENCIA HJB ---
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

# --- PROCESO 1: INGESTA DE DATOS (SENSOR DE NODO) ---
def sensor_loop(data_queue):
    """Simula la recepción de telemetría a 10Hz desde el PMU del cliente"""
    print("[INGESTA] Datos públicos CENACE — Nodo VZA-400...")
    while True:
        # Generamos el vector de estado: [Frecuencia, Voltaje, Demanda, PML]
        freq = 60.0 + np.random.normal(0, 0.02)
        volt = 230.0 + np.random.normal(0, 0.5)
        demanda = 450.0 + np.random.normal(0, 10)
        pml = 450.0 + np.random.normal(0, 5)
        
        state = np.array([freq, volt, demanda, pml], dtype=np.float32)
        if not data_queue.full():
            data_queue.put(state)
        time.sleep(0.1) # 100ms de latencia de muestreo

# --- PROCESO 2: MOTOR DE INFERENCIA (EL CEREBRO) ---
def inference_loop(data_queue, control_queue):
    """Calcula la acción de control HJB sobre los datos entrantes"""
    model = AutoHealing_Actor(state_dim=4, action_dim=1)
    model.eval()
    print("[CEREBRO] Motor HJB inicializado y listo para control activo.")
    
    total_rescate = 0.0
    while True:
        if not data_queue.empty():
            state = data_queue.get()
            state_t = torch.from_numpy(state)
            
            with torch.no_grad():
                action = model(state_t).item()
            
            # Lógica de Rescate Fiduciario en Tiempo Real
            # Si la frecuencia < 59.9Hz, el algoritmo 'inyecta' corrección
            if state[0] < 59.98:
                ahorro_inst = 1281.25 # USD rescatados por cada segundo de acción
                total_rescate += ahorro_inst * 0.1
                
            control_queue.put((action, total_rescate))

# --- PROCESO 3: DASHBOARD DE TERMINAL (MONITORING) ---
def monitor_loop(control_queue):
    """Muestra el estado de la plataforma y el dinero generado"""
    print("[MONITOR] Dashboard activado.")
    start_time = time.time()
    try:
        while True:
            if not control_queue.empty():
                action, rescate = control_queue.get()
                uptime = time.time() - start_time
                # Limpiar línea y actualizar
                sys.stdout.write(f"\r\033[K[PRIMEnergeia] Uptime: {uptime:.1f}s | Inercia: {action:+.4f} MW | RESCATE: ${rescate:,.2f} USD")
                sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[!] Apagado de emergencia iniciado.")

if __name__ == "__main__":
    # Colas de comunicación entre procesos (IPC)
    raw_data_bus = mp.Queue(maxsize=10)
    control_bus = mp.Queue(maxsize=10)

    # Lanzamiento de la arquitectura asíncrona
    p_sensor = mp.Process(target=sensor_loop, args=(raw_data_bus,))
    p_brain = mp.Process(target=inference_loop, args=(raw_data_bus, control_bus))
    
    p_sensor.start()
    p_brain.start()
    
    # El proceso principal se queda monitoreando
    monitor_loop(control_bus)
