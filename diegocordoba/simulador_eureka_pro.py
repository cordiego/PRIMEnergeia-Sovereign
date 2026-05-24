import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. CONFIGURACIÓN DEL NODO EUREKA
capital_inicial = 550.0
dias_proyeccion = 252 # Un año bursátil
escenarios = 1000

# Retornos y Volatilidades Estimadas (Triada Eureka)
# AGQ (Plata 2x), UGL (Oro 2x), GEV (Energía), Cash/Bonds
mu = np.array([0.0008, 0.0006, 0.0005, 0.0001]) # Retorno diario esperado
sigma = np.array([0.025, 0.018, 0.015, 0.002])  # Volatilidad diaria
pesos = np.array([0.25, 0.25, 0.30, 0.20])      # Tu distribución Eureka

# 2. MOTOR DE MONTE CARLO (Generación de Caminos)
retorno_portafolio = np.sum(mu * pesos)
vol_portafolio = np.sqrt(np.dot(pesos**2, sigma**2))

# Generar caminatas aleatorias (Brownian Motion)
cambios_diarios = np.random.normal(retorno_portafolio, vol_portafolio, (dias_proyeccion, escenarios))
trayectorias = capital_inicial * np.exp(np.cumsum(cambios_diarios, axis=0))

# 3. VISUALIZACIÓN DE SOBERANÍA PROYECTADA
plt.style.use('dark_background')
plt.figure(figsize=(12, 7))

# Dibujar todos los escenarios con transparencia
plt.plot(trayectorias, color='white', alpha=0.05)

# Resaltar la Mediana (El camino más probable)
mediana = np.median(trayectorias, axis=1)
plt.plot(mediana, color='#00d1ff', linewidth=3, label='Trayectoria Eureka (Mediana)')

# Resaltar el Escenario Optimista (Percentil 95)
plt.plot(np.percentile(trayectorias, 95, axis=1), color='#2ecc71', linestyle='--', label='Escenario Optimista (95%)')

# Resaltar el Escenario de Estrés (Percentil 5)
plt.plot(np.percentile(trayectorias, 5, axis=1), color='#ff4b5c', linestyle='--', label='Escenario de Estrés (Risk-Off)')

plt.axhline(y=capital_inicial, color='yellow', linestyle=':', label='Capital Semilla ($550)')
plt.title(f'SIMULACIÓN DE MONTE CARLO: EUREKA 1.0 (Capital: ${capital_inicial})', fontsize=14)
plt.xlabel('Días de Operación (Ciclos HJB)')
plt.ylabel('Valor del Patrimonio (USD)')
plt.legend(loc='upper left')
plt.grid(alpha=0.1)

plt.savefig('simulacion_montecarlo_eureka.png', dpi=300)
final_avg = mediana[-1]
print(f"\n[+] Simulación Completada.")
print(f"[+] Valor Mediano Proyectado a 1 año: ${final_avg:.2f} USD")
print(f"[+] Probabilidad de Retorno Positivo: {np.mean(trayectorias[-1] > capital_inicial)*100:.1f}%")
