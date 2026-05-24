import multiprocessing as mp
import time
import sqlite3
import sys

def logic(name, cap, q):
    try:
        while True:
            # Simulación de Inercia HJB a 10GW
            v = abs(0.02 * (1 if time.time() % 2 == 0 else -1)) * cap * 125000
            q.put((name, v))
            time.sleep(0.5)
    except: pass

def sync(q):
    db = 'soberania_nacional.db'
    conn = sqlite3.connect(db, isolation_level=None)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS finanzas')
    c.execute('CREATE TABLE finanzas (id INTEGER PRIMARY KEY, total REAL)')
    c.execute('INSERT INTO finanzas VALUES (1, 0.0)')
    print(f'\n[SISTEMA] GRID NACIONAL ACTIVA EN {db}')
    while True:
        if not q.empty():
            n, m = q.get()
            c.execute('UPDATE finanzas SET total = total + ? WHERE id = 1', (m,))
            c.execute('SELECT total FROM finanzas WHERE id = 1')
            t = c.fetchone()[0]
            sys.stdout.write(f'\r\033[K[GRID] Utilidad Acumulada: ${t:,.2f} USD | Nodo: {n}')
            sys.stdout.flush()
        time.sleep(0.1)

if __name__ == '__main__':
    mp.set_start_method('spawn', force=True)
    q = mp.Queue()
    nodos = [('NORTE', 3.8), ('CENTRO', 2.5), ('SUR', 4.0)]
    for n, c in nodos:
        p = mp.Process(target=logic, args=(n, c, q))
        p.daemon = True
        p.start()
    sync(q)
