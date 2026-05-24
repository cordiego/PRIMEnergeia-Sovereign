import numpy as np
import sqlite3
import time
import sys

class GridPhysics:
    def __init__(self):
        self.f_nom = 60.0       # Frecuencia Nominal (Hz)
        self.H = 5.0            # Constante de Inercia Base (s)
        self.D = 2.0            # Amortiguamiento
        self.dt = 0.01          # Paso de integración (10ms)
        self.f_actual = 60.0
        self.p_m = 1.0          # Potencia Mecánica (p.u.)
        self.p_e = 1.0          # Carga Eléctrica (p.u.)

    def step(self, u_inercia):
        """Resuelve la Swing Equation con Inercia Sintética (u_inercia)"""
        # El control u_inercia modifica la inercia efectiva M = 2H + u
        M_efectiva = 2 * self.H + u_inercia
        
        # Simulación de un disturbio aleatorio en la carga (Ruido de la Grid)
        self.p_e += np.random.normal(0, 0.005)
        
        # Derivada de la frecuencia (Swing Equation)
        df_dt = (self.p_m - self.p_e - self.D * (self.f_actual - self.f_nom)) / M_efectiva
        
        # Integración de Euler
        self.f_actual += df_dt * self.dt
        return self.f_actual, df_dt

def run_physics_engine():
    grid = GridPhysics()
    conn = sqlite3.connect('soberania_nacional.db', isolation_level=None)
    cursor = conn.cursor()
    
    # Asegurar tabla para auditoría física
    cursor.execute("DROP TABLE IF EXISTS telemetria_fisica")
    cursor.execute("CREATE TABLE telemetria_fisica (frecuencia REAL, df_dt REAL, inercia_u REAL, ahorro_acumulado REAL)")
    cursor.execute("INSERT INTO telemetria_fisica VALUES (60.0, 0.0, 0.0, 0.0)")

    ahorro_total = 0.0
    print("\n[NÚCLEO FÍSICO] Iniciando resolución de Ecuaciones de Oscilación...")

    while True:
        # Lógica HJB: Si la frecuencia cae, inyectamos inercia proporcional al gradiente
        error = grid.f_nom - grid.f_actual
        u_control = max(0, error * 500.0) # Inercia Sintética Proporcional
        
        f, dfdt = grid.step(u_control)
        
        # El ahorro se calcula por la 'Mitigación de Excursión'
        # Si evitamos que f baje de 59.95Hz, rescatamos capital de penalización
        if f < 59.97:
            ahorro_total += abs(error) * 250000 # Valor físico del rescate
            
        cursor.execute("""UPDATE telemetria_fisica SET 
                          frecuencia = ?, df_dt = ?, inercia_u = ?, 
                          ahorro_acumulado = ?""", (f, dfdt, u_control, ahorro_total))
        
        # Visualización de la física en tiempo real
        sys.stdout.write(f"\r\033[K[PHYSICS] Freq: {f:.4f} Hz | RoCoF: {dfdt:+.4f} | Inercia Inyectada: {u_control:.2f} p.u. | Rescate: ${ahorro_total:,.2f}")
        sys.stdout.flush()
        
        time.sleep(grid.dt)

if __name__ == "__main__":
    run_physics_engine()
