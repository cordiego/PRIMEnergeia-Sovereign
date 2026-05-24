import numpy as np
from datetime import datetime

# --- EUREKA 1.0 | MAX RETURN CONFIG ---
CAPITAL = 550.0
SIMULACIONES = 1000

# Ajuste de Pesos para MAX RETURN (Más peso en GEV y AGQ)
ASSETS = {
    'SNDK':  {'w_opt': 0.40, 'vol': 0.35, 'l': 1.0, 'mu': 0.15},
    'SNXX':  {'w_opt': 0.40, 'vol': 0.35, 'l': 1.0, 'mu': 0.15},
    'CASH':  {'w_opt': 0.20, 'vol': 0.02, 'l': 1.0, 'mu': 0.05}
}

def run_max_return_sim():
    # Cálculo de Retorno Esperado del Portafolio (Mu_p)
    mu_p = sum([i['w_opt'] * i['mu'] for i in ASSETS.values()])
    vol_p = np.sqrt(sum([(i['w_opt']**2) * (i['vol']**2) for i in ASSETS.values()]))
    
    # Monte Carlo para proyectar la Soberanía Financiera
    returns = np.random.normal(mu_p/252, vol_p/np.sqrt(252), (252, SIMULACIONES))
    price_paths = CAPITAL * np.exp(np.cumsum(returns, axis=0))
    
    p95 = np.percentile(price_paths[-1], 95) # Escenario de éxito masivo
    
    print(f"\n[🚀] EUREKA 1.0 | MODO: MAX RETURN | {datetime.now().strftime('%H:%M')}")
    print(f"{'TICKER':<7} | {'W_OPT':<7} | {'EXPECTED':<8} | {'ORDEN'}")
    print("-" * 55)

    for ticker, info in ASSETS.items():
        drift = np.random.normal(0, 0.05)
        status = "HOLD"
        if abs(drift) > 0.04: # Sensibilidad aumentada para capturar momentum
            status = "AJUSTAR"
        print(f"{ticker:<7} | {info['w_opt']*100:>6.1f}% | {info['mu']*100:>7.1f}% | {status}")

    print("-" * 55)
    print(f"📈 PROYECCIÓN MAX RETURN (12 Meses):")
    print(f"    Potencial Máximo (P95):   ${p95:.2f} USD")
    print(f"    Sharpe Ratio Estimado:    {mu_p/vol_p:.2f}")
    print("-" * 55)

if __name__ == "__main__":
    run_max_return_sim()
