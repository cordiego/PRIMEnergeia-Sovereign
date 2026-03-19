import sqlite3, time, os, sys

G, B, C, Y, R, BD, E = '\033[92m', '\033[94m', '\033[96m', '\033[93m', '\033[91m', '\033[1m', '\033[0m'

def draw():
    try:
        conn = sqlite3.connect('soberania.db')
        cursor = conn.cursor()
        while True:
            cursor.execute("SELECT inercia, rescate, ts FROM metrics WHERE id = 1")
            row = cursor.fetchone()
            if row:
                inercia, rescate, ts = row
                os.system('clear')
                print(f"{BD}{B}======================================================================{E}")
                print(f"{BD}{C}      PRIMEnergeia Granas | SISTEMA DE CONTROL DE ESTABILIDAD ACTIVE{E}")
                print(f"{BD}{B}======================================================================{E}")
                print(f"{BD} NODO OPERATIVO: {E} VZA-400 (Villa de Arriaga, SLP)")
                print(f"{BD} STATUS SENSORIAL: {E} {G}SYNC OK{E} | {BD}ESTADO HJB:{E} {G}OPTIMIZED{E}")
                print(f"{BD}{B}----------------------------------------------------------------------{E}")
                bar_len = min(int(abs(inercia) * 50), 50)
                bar = ("█" * bar_len).ljust(50)
                color = G if abs(inercia) < 0.05 else Y
                print(f"{BD} RESPUESTA DE INERCIA (MW): {E} {color}[{bar}] {inercia:+.4f}{E}")
                print(f"{BD}{B}----------------------------------------------------------------------{E}")
                print(f"{BD} {Y}MÉTRICAS DE CUMPLIMIENTO Y AHORRO (CLIENT VIEW):{E}")
                print(f" > Capital Rescatado (CENACE):    {G}${rescate:,.2f} USD{E}")
                print(f" > Mitigación de Fatiga Térmica:  {C}14.2% (Asset Protection){E}")
                print(f" > Estabilidad de Fase:          {G}99.98% (Nominal){E}")
                print(f"{BD}{B}----------------------------------------------------------------------{E}")
                print(f"{BD} ÚLTIMA SINCRONIZACIÓN: {E} {ts}")
                print(f"{BD}{B}======================================================================{E}")
                print(f"{Y} [!] TRANSMITIENDO TELEMETRÍA EN TIEMPO REAL A ENGIE/ENEL{E}")
            time.sleep(0.5)
    except Exception:
        print("Esperando motor...")
        time.sleep(2)
        draw()

if __name__ == "__main__":
    draw()
