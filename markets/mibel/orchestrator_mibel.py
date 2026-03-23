import multiprocessing as mp
import time
import sqlite3
import random
import sys

# ============================================================
#  PRIMEnergeia — MIBEL 20-Node Grid Orchestrator
#  Mercado Ibérico de Electricidad (Spain + Portugal)
# ============================================================

MIBEL_NODES = [
    # (ID, Location, Zone, Capacity GW)
    # — Spain: North —
    ("ES-BIL-400", "Bilbao",              "Spain North",       0.100),
    ("ES-ZAR-400", "Zaragoza",             "Spain North",       0.080),
    ("ES-BCN-400", "Barcelona",            "Spain North",       0.120),
    # — Spain: Central —
    ("ES-MAD-400", "Madrid",               "Spain Central",     0.150),
    ("ES-VAL-400", "Valencia",             "Spain Central",     0.100),
    ("ES-CLM-220", "Ciudad Real",          "Spain Central",     0.060),
    # — Spain: South —
    ("ES-SEV-400", "Sevilla",              "Spain South",       0.100),
    ("ES-MAL-400", "Málaga",               "Spain South",       0.080),
    ("ES-ALM-220", "Almería",              "Spain South",       0.060),
    ("ES-GRA-220", "Granada",              "Spain South",       0.060),
    # — Spain: Northwest —
    ("ES-COR-400", "A Coruña",             "Spain Northwest",   0.080),
    ("ES-LEO-220", "León",                 "Spain Northwest",   0.060),
    # — Spain: Islands —
    ("ES-PMI-220", "Palma de Mallorca",    "Balearic Islands",  0.040),
    ("ES-TFE-220", "Tenerife",             "Canary Islands",    0.040),
    ("ES-LPA-220", "Las Palmas",           "Canary Islands",    0.040),
    # — Portugal: North —
    ("PT-PRT-400", "Porto",                "Portugal North",    0.080),
    ("PT-BRG-220", "Braga",                "Portugal North",    0.050),
    # — Portugal: South —
    ("PT-LIS-400", "Lisboa",               "Portugal South",    0.100),
    ("PT-FAR-220", "Faro",                 "Portugal South",    0.050),
    ("PT-SET-220", "Setúbal",              "Portugal South",    0.050),
]


def motor_hjb_regional(node_id, capacity_gw, zone, q):
    """HJB motor instance for a single MIBEL node."""
    try:
        while True:
            volatility = random.uniform(0.008, 0.04)  # Lower for MIBEL
            rescue = capacity_gw * volatility * 160000
            q.put((node_id, zone, rescue))
            time.sleep(1)
    except Exception:
        pass


def coordinate_fleet(q, total_nodes):
    db = 'mibel_fleet.db'
    conn = sqlite3.connect(db, isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS fleet_mibel")
    cursor.execute("CREATE TABLE fleet_mibel (id INTEGER PRIMARY KEY, rescue_total REAL)")
    cursor.execute("INSERT INTO fleet_mibel VALUES (1, 0.0)")

    total_cap = sum(n[3] for n in MIBEL_NODES)
    print(f"\n{'='*70}")
    print(f"  PRIMEnergeia — MIBEL GRID ORCHESTRATOR")
    print(f"  {total_nodes} Nodes | {total_cap*1000:.0f} MW | Spain + Portugal")
    print(f"{'='*70}\n")

    try:
        while True:
            if not q.empty():
                node_id, zone, amount = q.get()
                cursor.execute(
                    "UPDATE fleet_mibel SET rescue_total = rescue_total + ? WHERE id = 1",
                    (amount,)
                )
                cursor.execute("SELECT rescue_total FROM fleet_mibel WHERE id = 1")
                total = cursor.fetchone()[0]

                sys.stdout.write(
                    f"\r\033[K[MIBEL] Nodes: {total_nodes} | "
                    f"Rescued: €{total:,.2f} EUR | "
                    f"Last: {node_id} ({zone})"
                )
                sys.stdout.flush()
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n\n[!] MIBEL fleet operation suspended.")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    q = mp.Queue()
    total_nodes = len(MIBEL_NODES)

    processes = []
    for node_id, location, zone, capacity in MIBEL_NODES:
        p = mp.Process(
            target=motor_hjb_regional,
            args=(node_id, capacity, zone, q)
        )
        p.daemon = True
        p.start()
        processes.append(p)
        print(f"  [DEPLOY] {node_id:<14s} | {location:<22s} | {zone:<18s} | {capacity*1000:.0f} MW")

    coordinate_fleet(q, total_nodes)
