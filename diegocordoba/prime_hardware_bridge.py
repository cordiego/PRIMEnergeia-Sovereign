import time
import numpy as np
import json

print("[🛰️] NODO VZA-400: GENERANDO FÍSICA DE RED")

def simular_red():
    try:
        while True:
            # Física estocástica de red
            f = 60.0 + np.random.normal(0, 0.01)
            v = 115.0 + np.random.normal(0, 0.2)
            
            estado = {
                "f": round(f, 3), 
                "v": round(v, 2), 
                "status": "NOMINAL", 
                "timestamp": time.time()
            }
            
            # Escritura de estado para el Dashboard
            with open("grid_state.json", "w") as f_out:
                json.dump(estado, f_out)
                
            print(f"[📡] LIVE: {f:.3f} Hz | {v:.2f} kV", end="\r")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[🛑] Nodo OFF.")

if __name__ == "__main__":
    simular_red()
