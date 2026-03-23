import numpy as np
import sqlite3
import time
import sys


class SENGridPhysics:
    """Swing Equation solver for SEN — Sistema Eléctrico Nacional (Mexico).

    60 Hz grid with moderate inertia (H=5.0s). Grid is synchronized
    across 9 CENACE regions with interconnections to ERCOT at the border.
    """

    def __init__(self):
        self.f_nom = 60.0       # Nominal frequency (Hz)
        self.H = 5.0            # Inertia constant (s)
        self.D = 2.0            # Damping coefficient
        self.dt = 0.01          # Integration step (10 ms)
        self.f_actual = 60.0
        self.p_m = 1.0          # Mechanical power (p.u.)
        self.p_e = 1.0          # Electrical load (p.u.)

    def step(self, u_inertia):
        """Solve Swing Equation with Synthetic Inertia injection u(t)."""
        M_eff = 2 * self.H + u_inertia
        self.p_e += np.random.normal(0, 0.005)
        df_dt = (self.p_m - self.p_e - self.D * (self.f_actual - self.f_nom)) / M_eff
        self.f_actual += df_dt * self.dt
        return self.f_actual, df_dt


def run_physics_engine():
    grid = SENGridPhysics()
    conn = sqlite3.connect('sen_telemetry.db', isolation_level=None)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS telemetria_sen")
    cursor.execute("""CREATE TABLE telemetria_sen (
        frecuencia REAL, df_dt REAL, inercia_u REAL, ahorro_acumulado REAL
    )""")
    cursor.execute("INSERT INTO telemetria_sen VALUES (60.0, 0.0, 0.0, 0.0)")

    ahorro_total = 0.0
    print("\n[SEN PHYSICS] Iniciando resolución de Ecuaciones de Oscilación...")

    while True:
        error = grid.f_nom - grid.f_actual
        u_control = max(0, error * 500.0)

        f, dfdt = grid.step(u_control)

        if f < 59.97:
            ahorro_total += abs(error) * 250000

        cursor.execute("""UPDATE telemetria_sen SET
                          frecuencia = ?, df_dt = ?, inercia_u = ?,
                          ahorro_acumulado = ?""", (f, dfdt, u_control, ahorro_total))

        sys.stdout.write(
            f"\r\033[K[SEN] Freq: {f:.4f} Hz | RoCoF: {dfdt:+.4f} | "
            f"Inercia: {u_control:.2f} p.u. | Rescate: ${ahorro_total:,.2f}"
        )
        sys.stdout.flush()
        time.sleep(grid.dt)


if __name__ == "__main__":
    run_physics_engine()
