import multiprocessing as mp
import time
import sqlite3
import os
import sys

# --- LÓGICA DE NODO REGIONAL ---
def regional_cluster_logic(region_name, capacity_gw, output_queue):
    """Procesamiento GKE por región"""
    try:
        while True:
            # Simulación de telemetría de alta frecuencia
            desviacion = 0.02 * (1 if time.time() % 2 == 0 else -1)
            # Rescate fiduciario basado en la estabilidad del nodo
            rescate_inst = abs(desviacion) * capacity_gw * 125000
            output_queue.put((region_name, rescate_inst))
            time.sleep(0.5)
    except Exception as e:
        pass

# --- SINCRONIZADOR CENTRAL ---
def central_ledger_sync(input_queue):
    # Forzamos una base de datos limpia para evitar conflictos de columnas
    db_name = 'soberania_nacional.db'
    conn = sqlite3.connect(db_name, isolation_level=None)
    cursor = conn.cursor()
    
    # Esquema robusto para 10 GW
    cursor.execute("DROP TABLE IF EXISTS finanzas_nacionales")
    cursor.execute("""CREATE TABLE finanzas_nacionales 
                      (id INTEGER PRIMARY KEY, utilidad_acumulada REAL, ts DATETIME)""")
    cursor.execute("INSERT INTO finanzas_nacionales VALUES (1, 0.0, datetime('now'))")

    print(f"\n[SISTEMA] Sincronización Nacional Iniciada en {db_name}")
    
    try:
        while True:
            if not input_queue.empty():
                region, monto = input_queue.get()
                
                cursor.execute("UPDATE finanzas_nacionales SET utilidad_acumulada = utilidad_acumulada + ?, ts = datetime('now') WHERE id = 1", (monto,))
                
                cursor.execute("SELECT utilidad_acumulada FROM finanzas_nacionales WHERE id = 1")
                total = cursor.fetchone()[0]
                
                sys.stdout.write(f"\r\033[K[GRID NACIONAL] Utilidad: ${total:,.2f} USD | Región: {region}")
                sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[!] Deteniendo Orquestador.")

if __name__ == "__main__":
    # Configuración de multiprocesamiento para Apple Silicon
    mp.set_start_method('spawn', force=True)
    
    q = mp.Queue()
    nodos_config = [("NORTE_IND", 3.8), ("CENTRO_DATA", 2.5), ("SUR_GEN", 4.0)]
    
    procesos = []
    for n, c in nodos_config:
        p = mp.Process(target=regional_cluster_logic, args=(n, c, q))
        p.daemon = True
        p.start()
        procesos.append(p)
    
    central_ledger_sync(q)
