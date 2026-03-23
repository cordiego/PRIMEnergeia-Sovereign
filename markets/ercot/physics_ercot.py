import numpy as np
import sqlite3
import time
import sys


class ERCOTGridPhysics:
    """Swing Equation solver tuned for ERCOT (islanded 60 Hz grid).

    ERCOT has lower system inertia than SEN due to high wind/solar
    penetration in West Texas, making frequency more volatile.
    """

    def __init__(self):
        self.f_nom = 60.0       # Nominal frequency (Hz)
        self.H = 4.5            # Lower inertia constant (s) — high renewables
        self.D = 1.8            # Damping coefficient
        self.dt = 0.01          # Integration step (10 ms)
        self.f_actual = 60.0
        self.p_m = 1.0          # Mechanical power (p.u.)
        self.p_e = 1.0          # Electrical load (p.u.)

    def step(self, u_inertia):
        """Solve Swing Equation with Synthetic Inertia injection u(t)."""
        M_eff = 2 * self.H + u_inertia

        # ERCOT-specific: higher load volatility (extreme weather events)
        self.p_e += np.random.normal(0, 0.007)

        df_dt = (self.p_m - self.p_e - self.D * (self.f_actual - self.f_nom)) / M_eff
        self.f_actual += df_dt * self.dt
        return self.f_actual, df_dt


def run_physics_engine():
    grid = ERCOTGridPhysics()
    conn = sqlite3.connect('ercot_telemetry.db', isolation_level=None)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS telemetria_ercot")
    cursor.execute("""CREATE TABLE telemetria_ercot (
        frecuencia REAL, df_dt REAL, inercia_u REAL, ahorro_acumulado REAL
    )""")
    cursor.execute("INSERT INTO telemetria_ercot VALUES (60.0, 0.0, 0.0, 0.0)")

    savings_total = 0.0
    print("\n[ERCOT PHYSICS] Starting Swing Equation solver...")

    while True:
        error = grid.f_nom - grid.f_actual
        u_control = max(0, error * 500.0)

        f, dfdt = grid.step(u_control)

        # ERCOT penalty: frequency below 59.97 Hz triggers NERC enforcement
        if f < 59.97:
            savings_total += abs(error) * 300000  # Higher ERCOT penalties

        cursor.execute("""UPDATE telemetria_ercot SET
                          frecuencia = ?, df_dt = ?, inercia_u = ?,
                          ahorro_acumulado = ?""", (f, dfdt, u_control, savings_total))

        sys.stdout.write(
            f"\r\033[K[ERCOT] Freq: {f:.4f} Hz | RoCoF: {dfdt:+.4f} | "
            f"Inertia: {u_control:.2f} p.u. | Rescued: ${savings_total:,.2f}"
        )
        sys.stdout.flush()
        time.sleep(grid.dt)


if __name__ == "__main__":
    run_physics_engine()
