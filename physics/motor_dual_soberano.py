import numpy as np
import sqlite3
import time
import sys

class NationalGridPhysics:
    def __init__(self):
        # Parámetros Nominales
        self.f_nom, self.v_nom = 60.0, 1.0  # Hz y p.u. (Voltaje)
        self.M, self.D = 10.0, 2.0          # Inercia y Amortiguamiento
        self.T_v, self.X = 0.5, 0.1         # Constante de tiempo y Reactancia
        self.dt = 0.01
        
        # Estados actuales
        self.f, self.v = 60.0, 1.0
        self.p_m, self.p_e = 1.0, 1.0
        self.q_gen, self.q_load = 0.5, 0.5

    def compute_step(self, u_M, u_Q):
        """u_M: Inercia Sintética | u_Q: Soporte de Voltaje (VArs)"""
        # Perturbaciones de la red nacional
        self.p_e += np.random.normal(0, 0.008)
        self.q_load += np.random.normal(0, 0.005)

        # 1. Dinámica de Frecuencia (P-f)
        df_dt = (self.p_m - self.p_e - self.D*(self.f - self.f_nom)) / (self.M + u_M)
        self.f += df_dt * self.dt

        # 2. Dinámica de Voltaje (Q-V)
        dv_dt = (self.q_gen + u_Q - self.q_load - (self.v**2 / self.X)) / self.T_v
        self.v += dv_dt * self.dt
        
        return self.f, self.v, df_dt

def run_dual_engine():
    grid = NationalGridPhysics()
    conn = sqlite3.connect('soberania_nacional.db', isolation_level=None)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS telemetria_dual")
    c.execute("CREATE TABLE telemetria_dual (f REAL, v REAL, rescate_total REAL, ts DATETIME)")
    c.execute("INSERT INTO telemetria_dual VALUES (60.0, 1.0, 0.0, datetime('now'))")

    rescate_acumulado = 0.0
    print("\n[ESTRATEGIA NACIONAL] Motor Dual P-f / Q-V Activo...")

    while True:
        # Control HJB Dual
        error_f = grid.f_nom - grid.f
        error_v = grid.v_nom - grid.v
        
        u_M = max(0, error_f * 600.0)  # Respuesta de Inercia
        u_Q = max(0, error_v * 2.5)    # Inyección de VArs (Soporte Voltaje)
        
        f, v, dfdt = grid.compute_step(u_M, u_Q)
        
        # Lógica de Doble Rescate (Multas de Frecuencia + Multas de Voltaje)
        if f < 59.98 or v < 0.98:
            # Rescate masivo por evitar falla en cascada
            rescate_acumulado += (abs(error_f) * 200000) + (abs(error_v) * 150000)
            
        c.execute("UPDATE telemetria_dual SET f=?, v=?, rescate_total=?, ts=datetime('now') WHERE id=1", 
                  (f, v, rescate_acumulado))
        
        # Monitor de Alta Fidelidad
        sys.stdout.write(f"\r\033[K[DUAL] F: {f:.4f}Hz | V: {v:.4f}pu | Inercia: {u_M:.1f} | VArs: {u_Q:.2f} | RESCATE: ${rescate_acumulado:,.2f}")
        sys.stdout.flush()
        
        time.sleep(grid.dt)

if __name__ == "__main__":
    run_dual_engine()
