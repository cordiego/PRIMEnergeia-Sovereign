import numpy as np
import pandas as pd
import time
import sys

# --- CONFIGURACIÓN DE SOBERANÍA ---
CAPITAL_INICIAL_USD = 550.0
FX_USD_MXN = 17.15  # Tasa de cambio actual
UMBRAL_REBALANCEO = 0.05 # 5% de desviación permitida (ε)

# Portafolio Eureka 1.0 (Trading USA via SIC)
# Pesos Objetivo (Target Weights)
targets = {
    'AGQ': 0.25,  # Plata 2x
    'UGL': 0.25,  # Oro 2x
    'GEV': 0.30,  # GE Vernova (Energía)
    'BIL': 0.20   # T-Bills (Cash)
}

# Precios actuales en USD (Simulados para el nodo de control)
precios_usd = {'AGQ': 34.80, 'UGL': 72.40, 'GEV': 168.20, 'BIL': 91.50}

def ejecutar_hjb_full():
    cap_total_mxn = CAPITAL_INICIAL_USD * FX_USD_MXN
    print(f"\n[⚡] FULL EUREKA 1.0 | SISTEMA DE CONTROL DE ACTIVOS")
    print(f"[🌐] NODO: GBM TRADING USA | CAPITAL: ${CAPITAL_INICIAL_USD} USD")
    print("=" * 70)
    
    ordenes = []
    
    for asset, target_w in targets.items():
        # 1. Calcular Valor Objetivo
        valor_obj_usd = CAPITAL_INICIAL_USD * target_w
        valor_obj_mxn = valor_obj_usd * FX_USD_MXN
        
        # 2. Calcular Títulos Necesarios (Enteros)
        precio_mxn = precios_usd[asset] * FX_USD_MXN
        titulos_n = int(valor_obj_mxn / precio_mxn)
        
        # 3. Detectar Desviación Estocástica
        error = np.random.normal(0, 0.02) # Simulación de movimiento de mercado
        
        status = "✅ EN RANGO"
        if abs(error) > UMBRAL_REBALANCEO:
            status = "⚠️ REBALANCEAR"
            
        print(f"{asset:<5} | Peso: {target_w*100:>2.0f}% | Obj: ${valor_obj_mxn:>8.2f} MXN | Títulos: {titulos_n:<3} | {status}")

    print("-" * 70)
    print(f"[!] Instrucción: Mantener {int(CAPITAL_INICIAL_USD * 0.2)} USD en BIL como Inercia Térmica.")

if __name__ == "__main__":
    try:
        while True:
            sys.stdout.write("\033[H\033[J")
            ejecutar_hjb_full()
            print(f"\n[Próximo escaneo de Nodo en 5 segundos...]")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[!] Standby de Soberanía activado.")
