import numpy as np
import sqlite3
import time
import sys


class MIBELGridPhysics:
    """Swing Equation solver for MIBEL — Mercado Ibérico de Electricidad.

    50 Hz grid (ENTSO-E Continental European synchronous area).
    Higher inertia (H=6.0s) due to large conventional thermal and
    hydro fleet in Spain/Portugal. Lower volatility than ERCOT.
    """

    def __init__(self):
        self.f_nom = 50.0       # European nominal frequency (Hz)
        self.H = 6.0            # Higher inertia constant (s)
        self.D = 2.5            # Damping coefficient
        self.dt = 0.01          # Integration step (10 ms)
        self.f_actual = 50.0
        self.p_m = 1.0          # Mechanical power (p.u.)
        self.p_e = 1.0          # Electrical load (p.u.)

    def step(self, u_inertia):
        """Solve Swing Equation with Synthetic Inertia injection u(t)."""
        M_eff = 2 * self.H + u_inertia

        # MIBEL: lower volatility (large interconnected grid)
        self.p_e += np.random.normal(0, 0.004)

        df_dt = (self.p_m - self.p_e - self.D * (self.f_actual - self.f_nom)) / M_eff
        self.f_actual += df_dt * self.dt
        return self.f_actual, df_dt


def run_physics_engine():
    grid = MIBELGridPhysics()
    conn = sqlite3.connect('mibel_telemetry.db', isolation_level=None)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS telemetria_mibel")
    cursor.execute("""CREATE TABLE telemetria_mibel (
        frecuencia REAL, df_dt REAL, inercia_u REAL, ahorro_acumulado REAL
    )""")
    cursor.execute("INSERT INTO telemetria_mibel VALUES (50.0, 0.0, 0.0, 0.0)")

    savings_total = 0.0
    print("\n[MIBEL PHYSICS] Starting Swing Equation solver (50 Hz)...")

    while True:
        error = grid.f_nom - grid.f_actual
        u_control = max(0, error * 500.0)

        f, dfdt = grid.step(u_control)

        # ENTSO-E penalty: frequency below 49.96 Hz
        if f < 49.96:
            savings_total += abs(error) * 280000

        cursor.execute("""UPDATE telemetria_mibel SET
                          frecuencia = ?, df_dt = ?, inercia_u = ?,
                          ahorro_acumulado = ?""", (f, dfdt, u_control, savings_total))

        sys.stdout.write(
            f"\r\033[K[MIBEL] Freq: {f:.4f} Hz | RoCoF: {dfdt:+.4f} | "
            f"Inertia: {u_control:.2f} p.u. | Rescued: €{savings_total:,.2f}"
        )
        sys.stdout.flush()
        time.sleep(grid.dt)


if __name__ == "__main__":
    run_physics_engine()
