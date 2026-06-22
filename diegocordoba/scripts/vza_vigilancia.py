import time
import json
import os

def check_sovereignty():
    print("-" * 30)
    print(f"🕒 TICK: {time.strftime('%H:%M:%S')}")
    
    # 1. Check PRIME Node
    if os.path.exists("grid_state.json"):
        with open("grid_state.json", "r") as f:
            data = json.load(f)
            freq = data['f']
            status = "ALERTA ⚠️" if freq < 59.95 or freq > 60.05 else "NOMINAL ✅"
            print(f"PRIME (VZA-400, public CENACE data): {freq} Hz | {status}")
    
    # 2. Check Eureka Node (Simulado)
    print(f"EUREKA (Capital): $550.00 USD | Sincronizado")
    print("-" * 30)

if __name__ == "__main__":
    try:
        while True:
            check_sovereignty()
            time.sleep(60) # Ejecución cada minuto
    except KeyboardInterrupt:
        print("\nSoberanía pausada.")
