import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Extracción de Datos de Soberanía
conn = sqlite3.connect('eureka_patrimonio.db')
df = pd.read_sql_query("SELECT * FROM historial ORDER BY timestamp ASC", conn)
conn.close()

# 2. Arquitectura de la Gráfica
plt.style.use('dark_background')
fig, ax1 = plt.subplots(figsize=(12, 6))

# Eje de Saldo (Soberanía Financiera)
color_saldo = '#00d1ff' # Azul Neón PRIMEnergeia
ax1.set_xlabel('Tiempo (Ciclos de Control)')
ax1.set_ylabel('Saldo Eureka (USD)', color=color_saldo, fontsize=12, fontweight='bold')
ax1.plot(df['saldo'], color=color_saldo, linewidth=2, label='Trayectoria de Capital')
ax1.tick_params(axis='y', labelcolor=color_saldo)
ax1.grid(alpha=0.2)

# Eje de Riesgo (Entropía del Sistema)
ax2 = ax1.twinx()
color_riesgo = '#ff4b5c' # Rojo Alerta
ax2.set_ylabel('Riesgo Estocástico (σ)', color=color_riesgo, fontsize=12, fontweight='bold')
ax2.fill_between(range(len(df)), df['riesgo'], color=color_riesgo, alpha=0.1)
ax2.plot(df['riesgo'], color=color_riesgo, linestyle='--', linewidth=1, label='Entropía (σ)')
ax2.tick_params(axis='y', labelcolor=color_riesgo)

# 3. Finalización del Reporte
plt.title('CONVERGENCIA DE SOBERANÍA: EUREKA 1.0 (NODO $550)', fontsize=14, pad=20)
fig.tight_layout()
plt.savefig('soberania_progression.png', dpi=300)
print("\n[+] Visualización generada: soberania_progression.png")
