import multiprocessing as mp
import time
import sqlite3
import os

def regional_cluster_logic(region_name, capacity_gw, output_queue):
    """Simula el procesamiento de un clúster GKE regional"""
    print(f"[GKE] Cluster {region_name} operativo (Capacidad: {capacity_gw} GW)")
    while True:
        # Simulación de telemetría de alta frecuencia
        desviacion = 0.02 * (1 if time.time() % 2 == 0 else -1)
        # Rescate fiduciario basado en la estabilidad del nodo
        rescate_inst = abs(desviacion) * capacity_gw * 125000
        output_queue.put((region_name, rescate_inst))
        time.sleep(0.5)

def central_ledger_sync(input_queue):
    """Sincroniza los resultados de todos los nodos en el balance corporativo"""
    conn = sqlite3.connect('soberania.db', isolation_level=None)
    cursor = conn.cursor()
    
    # Aseguramos que la tabla financiera esté lista
    cursor.execute("CREATE TABLE IF NOT EXISTS finanzas_corp (id INTEGER PRIMARY KEY, utilidad_acumulada REAL, ts DATETIME)")
    cursor.execute("INSERT OR IGNORE INTO finanzas_corp VALUES (1, 0.0, datetime('now'))")

    while True:
        if not input_queue.empty():
            region, monto = input_queue.get()
            
            # Actualización del flujo de caja corporativo
            cursor.execute("UPDATE finanzas_corp SET utilidad_acumulada = utilidad_acumulada + ?, ts = datetime('now') WHERE id = 1", (monto,))
            
            cursor.execute("SELECT utilidad_acumulada FROM finanzas_corp WHERE id = 1")
            total = cursor.fetchone()[0]
            
            os.system('clear')
            print("="*60)
            print(f"      PRIMEnergeia | GLOBAL GRID ORCHESTRATOR")
            print("="*60)
            print(f" TOTAL UTILIDAD ACUMULADA:  ${total:,.2f} USD")
            print("-" * 60)
            print(f" [ESTADO] Nodos Norte/Centro/Sur: ONLINE")
            print(f" [INFO] Sincronización GCP: ACTIVA")
            print("="*60)
        time.sleep(0.1)

if __name__ == "__main__":
    q = mp.Queue()
    nodos = [("NORTE_IND", 3.8), ("CENTRO_DATA", 2.5), ("SUR_GEN", 4.0)]
    
    procesos = [mp.Process(target=regional_cluster_logic, args=(n, c, q)) for n, c in nodos]
    for p in procesos: p.start()
    
    central_ledger_sync(q)
