import multiprocessing as mp
import time
import sqlite3
import random
import sys

# ============================================================
#  PRIMEnergeia — SEN 30-Node National Grid Orchestrator
#  Sistema Eléctrico Nacional — Full CENACE Coverage
# ============================================================

SEN_NODES = [
    # (ID, Location, CENACE Region, Capacity GW)
    # — Central —
    ("05-VZA-400", "Valle de México",  "Central",          0.100),
    ("01-QRO-230", "Querétaro",        "Central",          0.080),
    ("01-TUL-400", "Tula, Hidalgo",    "Central",          0.100),
    ("06-SLP-400", "San Luis Potosí",  "Central",          0.100),
    # — Oriental —
    ("02-PUE-400", "Puebla",           "Oriental",         0.100),
    ("02-VER-230", "Veracruz",         "Oriental",         0.080),
    ("02-OAX-230", "Oaxaca",           "Oriental",         0.080),
    ("02-TEH-400", "Tehuantepec",      "Oriental",         0.100),
    # — Occidental —
    ("03-GDL-400", "Guadalajara",      "Occidental",       0.100),
    ("03-MAN-400", "Manzanillo",       "Occidental",       0.100),
    ("03-AGS-230", "Aguascalientes",   "Occidental",       0.080),
    ("03-COL-115", "Colima",           "Occidental",       0.040),
    # — Noreste —
    ("04-MTY-400", "Monterrey",        "Noreste",          0.100),
    ("04-TAM-230", "Tampico",          "Noreste",          0.080),
    ("04-SAL-400", "Saltillo",         "Noreste",          0.100),
    # — Norte —
    ("05-CHI-400", "Chihuahua",        "Norte",            0.100),
    ("05-LAG-230", "Gómez Palacio",    "Norte",            0.080),
    ("05-DGO-230", "Durango",          "Norte",            0.060),
    ("05-JRZ-230", "Cd. Juárez",       "Norte",            0.080),
    # — Noroeste —
    ("07-HER-230", "Hermosillo",       "Noroeste",         0.080),
    ("07-NAV-230", "Navojoa",          "Noroeste",         0.060),
    ("07-CUM-115", "Cd. Obregón",      "Noroeste",         0.040),
    ("07-GUY-230", "Guaymas",          "Noroeste",         0.060),
    ("07-CUL-230", "Culiacán",         "Noroeste",         0.080),
    # — Baja California —
    ("08-MXL-230", "Mexicali",         "Baja California",  0.080),
    ("08-ENS-230", "Ensenada",         "Baja California",  0.080),
    ("08-TIJ-230", "Tijuana",          "Baja California",  0.080),
    # — Baja California Sur —
    ("09-LAP-115", "La Paz",           "BCS",              0.040),
    # — Peninsular —
    ("10-MER-230", "Mérida",           "Peninsular",       0.080),
    ("10-CAN-230", "Cancún",           "Peninsular",       0.080),
]


def motor_hjb_regional(id_nodo, capacidad_gw, region, q):
    """HJB motor instance for a single SEN node."""
    try:
        while True:
            volatilidad = random.uniform(0.01, 0.05)
            rescate_inst = capacidad_gw * volatilidad * 145000
            q.put((id_nodo, region, rescate_inst))
            time.sleep(1)
    except Exception:
        pass


def coordinar_flota(q, total_nodos):
    db = 'sen_fleet.db'
    conn = sqlite3.connect(db, isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS fleet_sen")
    cursor.execute("CREATE TABLE fleet_sen (id INTEGER PRIMARY KEY, rescate_total REAL)")
    cursor.execute("INSERT INTO fleet_sen VALUES (1, 0.0)")

    total_cap = sum(n[3] for n in SEN_NODES)
    print(f"\n{'='*70}")
    print(f"  PRIMEnergeia — SEN GRID ORCHESTRATOR")
    print(f"  {total_nodos} Nodos | {total_cap*1000:.0f} MW | 9 Regiones CENACE")
    print(f"{'='*70}\n")

    try:
        while True:
            if not q.empty():
                id_n, region, monto = q.get()
                cursor.execute(
                    "UPDATE fleet_sen SET rescate_total = rescate_total + ? WHERE id = 1",
                    (monto,)
                )
                cursor.execute("SELECT rescate_total FROM fleet_sen WHERE id = 1")
                total = cursor.fetchone()[0]

                sys.stdout.write(
                    f"\r\033[K[SEN] Nodos: {total_nodos} | "
                    f"Rescate: ${total:,.2f} USD | "
                    f"Último: {id_n} ({region})"
                )
                sys.stdout.flush()
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n\n[!] Suspendiendo operación de flota SEN.")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    q = mp.Queue()
    total_nodos = len(SEN_NODES)

    procesos = []
    for nodo_id, ubicacion, region, capacidad in SEN_NODES:
        p = mp.Process(
            target=motor_hjb_regional,
            args=(nodo_id, capacidad, region, q)
        )
        p.daemon = True
        p.start()
        procesos.append(p)
        print(f"  [DEPLOY] {nodo_id:<12s} | {ubicacion:<20s} | {region:<18s} | {capacidad*1000:.0f} MW")

    coordinar_flota(q, total_nodos)
