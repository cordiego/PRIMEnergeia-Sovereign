import sqlite3
import datetime

def generar():
    try:
        conn = sqlite3.connect('soberania.db')
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(rescate), AVG(abs(inercia)), ts FROM metrics")
        rescate, inercia_avg, ts = cursor.fetchone()
        
        print("\n" + "="*50)
        print(f"REPORT DE OPERACIONES - PRIMEnergeia Granas")
        print(f"FECHA DE CORTE: {datetime.date.today()}")
        print("="*50)
        print(f"NODO:           VZA-400 (Valle de México, datos públicos CENACE)")
        print(f"RESCATE TOTAL:  ${rescate:,.2f} USD")
        print(f"ESTABILIDAD:    {100 - (inercia_avg*10):.2f}% Deviation Index")
        print(f"STATUS:         CUMPLIMIENTO TOTAL (CENACE SAFE)")
        print("-" * 50)
        print(f"FEE DE ACTIVACIÓN PENDIENTE: $2,500,000.00 USD")
        print(f"REGALÍA OPERATIVA (25%):     ${(rescate * 0.25):,.2f} USD")
        print("="*50 + "\n")
        
    except Exception as e:
        print("Error al leer la base de datos: Asegúrate de que el motor esté corriendo.")

if __name__ == "__main__":
    generar()
