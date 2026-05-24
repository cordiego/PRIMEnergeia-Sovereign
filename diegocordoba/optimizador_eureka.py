import numpy as np
import pandas as pd
from scipy.optimize import minimize

# --- CONFIGURACIÓN DEL NODO EUREKA 1.0 ---
tickers = ['AGQ', 'UGL', 'GEV', 'VTIP', 'VGSH']
precios_actuales = np.array([35.20, 72.10, 165.40, 48.15, 58.90]) # Simulación cierre
capital_total = 550.0

# Matriz de Covarianza Estimada (Volatilidad y Correlación)
# AGQ/UGL tienen alta volatilidad (Leverage 2x), VGSH es el ancla.
returns = np.array([0.08, 0.06, 0.12, 0.02, 0.01]) # Retornos esperados anuales
cov_matrix = np.array([
    [0.090, 0.045, 0.020, 0.001, 0.000], # AGQ
    [0.045, 0.050, 0.015, 0.001, 0.000], # UGL
    [0.020, 0.015, 0.070, 0.002, 0.000], # GEV
    [0.001, 0.001, 0.002, 0.002, 0.000], # VTIP
    [0.000, 0.000, 0.000, 0.000, 0.001]  # VGSH
])

def objetivo_sharpe(weights):
    port_return = np.dot(weights, returns)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return - (port_return / port_vol) # Maximizamos Sharpe (negativo para minimize)

# Restricciones: Suma de pesos = 1, límites por activo (0% a 40%)
cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
bounds = tuple((0.05, 0.40) for x in range(len(tickers))) # Mínimo 5% por seguridad
init_guess = [0.2, 0.2, 0.2, 0.2, 0.2]

# Optimización HJB de Capital
res = minimize(objetivo_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
pesos_optimos = res.x

print("-" * 40)
print("🎯 OPTIMIZACIÓN DE SOBERANÍA: EUREKA 1.0")
print("-" * 40)
for i, t in enumerate(tickers):
    monto = pesos_optimos[i] * capital_total
    print(f"{t}: {pesos_optimos[i]*100:.2f}% | Inversión: ${monto:.2f}")

vol_opt = np.sqrt(np.dot(pesos_optimos.T, np.dot(cov_matrix, pesos_optimos)))
print("-" * 40)
print(f"Sharpe Ratio Estimado: {-res.fun:.2f}")
print(f"Volatilidad del Nodo: {vol_opt*100:.2f}%")
print("-" * 40)
