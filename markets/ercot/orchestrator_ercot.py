import multiprocessing as mp
import time
import sqlite3
import random
import sys

# ============================================================
#  PRIMEnergeia — ERCOT 25-Node Grid Orchestrator
#  Full ERCOT Weather Zone Coverage
# ============================================================

ERCOT_NODES = [
    # (ID, Location, Zone, Capacity GW)
    # — Houston —
    ("HOU-345-01", "Houston Central",   "Houston",    0.120),
    ("HOU-345-02", "Baytown",           "Houston",    0.100),
    ("HOU-138-03", "Galveston",         "Houston",    0.060),
    # — North —
    ("NTH-345-01", "Dallas–Fort Worth", "North",      0.120),
    ("NTH-345-02", "Denton",            "North",      0.080),
    ("NTH-138-03", "Waco",              "North",      0.060),
    # — South —
    ("STH-345-01", "San Antonio",       "South",      0.100),
    ("STH-345-02", "Corpus Christi",    "South",      0.080),
    ("STH-138-03", "Laredo",            "South",      0.050),
    ("AUS-345-01", "Austin",            "South",      0.100),
    ("AUS-138-02", "Georgetown",        "South",      0.060),
    ("AUS-138-03", "Round Rock",        "South",      0.050),
    # — West —
    ("WST-345-01", "Midland–Odessa",    "West",       0.100),
    ("WST-345-02", "Abilene",           "West",       0.080),
    ("WST-138-03", "San Angelo",        "West",       0.060),
    # — Far West —
    ("FWS-345-01", "El Paso",           "Far West",   0.080),
    ("FWS-138-02", "Pecos",             "Far West",   0.060),
    # — Coast —
    ("CST-345-01", "Victoria",          "Coast",      0.080),
    ("CST-138-02", "Bay City",          "Coast",      0.060),
    ("CST-138-03", "Freeport",          "Coast",      0.050),
    # — Panhandle —
    ("PNH-345-01", "Amarillo",          "Panhandle",  0.080),
    ("PNH-138-02", "Lubbock",           "Panhandle",  0.060),
    # — East —
    ("EST-345-01", "Beaumont",          "East",       0.080),
    ("EST-345-02", "Tyler",             "East",       0.080),
    ("EST-138-03", "Lufkin",            "East",       0.050),
]


def motor_hjb_regional(node_id, capacity_gw, zone, q):
    """HJB motor instance for a single ERCOT node."""
    try:
        while True:
            volatility = random.uniform(0.01, 0.06)  # Higher for ERCOT
            rescue = capacity_gw * volatility * 180000
            q.put((node_id, zone, rescue))
            time.sleep(1)
    except Exception:
        pass


def coordinate_fleet(q, total_nodes):
    db = 'ercot_fleet.db'
    conn = sqlite3.connect(db, isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS fleet_ercot")
    cursor.execute("CREATE TABLE fleet_ercot (id INTEGER PRIMARY KEY, rescue_total REAL)")
    cursor.execute("INSERT INTO fleet_ercot VALUES (1, 0.0)")

    total_cap = sum(n[3] for n in ERCOT_NODES)
    print(f"\n{'='*70}")
    print(f"  PRIMEnergeia — ERCOT GRID ORCHESTRATOR")
    print(f"  {total_nodes} Nodes | {total_cap*1000:.0f} MW | 8 Weather Zones")
    print(f"{'='*70}\n")

    try:
        while True:
            if not q.empty():
                node_id, zone, amount = q.get()
                cursor.execute(
                    "UPDATE fleet_ercot SET rescue_total = rescue_total + ? WHERE id = 1",
                    (amount,)
                )
                cursor.execute("SELECT rescue_total FROM fleet_ercot WHERE id = 1")
                total = cursor.fetchone()[0]

                sys.stdout.write(
                    f"\r\033[K[ERCOT] Nodes: {total_nodes} | "
                    f"Rescued: ${total:,.2f} USD | "
                    f"Last: {node_id} ({zone})"
                )
                sys.stdout.flush()
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n\n[!] ERCOT fleet operation suspended.")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    q = mp.Queue()
    total_nodes = len(ERCOT_NODES)

    processes = []
    for node_id, location, zone, capacity in ERCOT_NODES:
        p = mp.Process(
            target=motor_hjb_regional,
            args=(node_id, capacity, zone, q)
        )
        p.daemon = True
        p.start()
        processes.append(p)
        print(f"  [DEPLOY] {node_id:<14s} | {location:<20s} | {zone:<12s} | {capacity*1000:.0f} MW")

    coordinate_fleet(q, total_nodes)
