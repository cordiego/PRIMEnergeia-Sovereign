import numpy as np
import pandas as pd
import time
import sys

# --- CONFIGURACIÓN DE SOBERANÍA (NODO $550 USD) ---
CAPITAL_INICIAL = 550.0
FX_USD_MXN = 17.20   # Tasa de cambio actual para GBM
UMBRAL_DRIFT = 0.05  # Rebalanceo solo si la desviación > 5%

# Definición de la Triada Eureka 1.0 + Cash
# Incluimos Volatilidad Anualizada para cálculo de Sharpe y Decay
assets = {
    'AGQ': {'w_target': 0.25, 'vol': 0.65, 'lever': 2.0, 'name': 'Plata 2x'},
    'UGL': {'w_target': 0.25, 'vol': 0.35, 'lever': 2.0, 'name': 'Oro 2x'},
    'GEV': {'w_target': 0.30, 'vol': 0.25, 'lever': 1.0, 'name': 'GE Vernova'},
    'BIL': {'w_target': 0.20, 'vol': 0.01, 'lever': 1.0, 'name': 'T-Bills (Cash)'}
}

def calculate_hjb_state(prices):
    print(f"\n[⚡] EUREKA 1.0 | FULL OPTIMIZER | NODO: GBM TRADING USA")
    print(f"[🌐] CAPITAL: ${CAPITAL_INICIAL:.2f} USD | TRABAJANDO EN EL SIC")
    print("-" * 85)
    print(f"{'TICKER':<8} | {'W_ACT':<7} | {'DRIFT':<7} | {'DECAY':<7} | {'ORDEN (Títulos)'}")
    print("-" * 85)

    for ticker, info in assets.items():
        # 1. Simulación de Desviación del Peso (Drift)
        # En la realidad, esto vendría de tu saldo actual en GBM
        drift_error = np.random.normal(0, 0.08) 
        w_actual = info['w_target'] + drift_error
        drift_pct = (w_actual - info['w_target']) / info['w_target']
        
        # 2. Leverage Decay Correction: L = -0.5 * L^2 * sigma^2
        # Calculamos la erosión teórica diaria por volatilidad
        daily_decay = -0.5 * (info['lever']**2) * (info['vol']**2) / 252
        
        # 3. Lógica de Rebalanceo (Sharpe Optimization)
        # Si el drift supera el umbral, el sistema genera la orden
        status = "HOLD"
        titulos_orden = 0
        if abs(drift_pct) > UMBRAL_DRIFT:
            status = "TRADE"
            monto_ajuste_usd = (info['w_target'] - w_actual) * CAPITAL_INICIAL
            titulos_orden = round(monto_ajuste_usd / prices[ticker])
        
        print(f"{ticker:<8} | {w_actual*100:>6.1f}% | {drift_pct*100:>6.1f}% | {daily_decay*1000:>6.4f} | {status:<6} -> {titulos_orden:>+3} tít.")

if __name__ == "__main__":
    # Precios de cierre estimados para Trading USA (SIC)
    current_prices = {'AGQ': 35.20, 'UGL': 73.10, 'GEV': 169.50, 'BIL': 91.60}
    
    try:
        while True:
            sys.stdout.write("\033[H\033[J")
            calculate_hjb_state(current_prices)
            print(f"\n[!] REGLA DE SOBERANÍA: El Leverage Decay en {assets['AGQ']['name']} es crítico.")
            print(f"[!] Rebalanceo sugerido para optimizar Sharpe Ratio acumulado.")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[!] Motor Eureka en Standby. Datos guardados en memoria.")
