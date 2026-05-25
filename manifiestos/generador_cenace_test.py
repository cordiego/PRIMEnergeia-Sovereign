import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def materializar_datos_cliente(filename="client_data.csv"):
    print(f"--- Iniciando Emulación de Telemetría Nodal: 07-HER-230 ---")
    
    # 1. Horizonte Temporal: 30 días con resolución de 15 min
    start_date = datetime(2026, 2, 1)
    periods = 30 * 96 
    t = pd.date_range(start=start_date, periods=periods, freq='15min')
    
    # 2. Trayectoria Óptima (Theoretical_MW)
    # Basado en la Ley de Stefan-Boltzmann para irradiancia máxima (100 MW Cap)
    hr = t.hour + t.minute / 60.0
    base_solar = np.maximum(0, np.sin((hr - 6) * np.pi / 12)) * 100.0
    # Ruido atmosférico estocástico (nubes transitorias)
    theo = np.clip(base_solar * np.random.normal(1.0, 0.08, periods), 0, 100)
    
    # 3. Dinámica de Mercado (PML_USD)
    # Reflejando congestión real en Sonora: Precios base + picos de volatilidad
    pml_base = 35 + 15 * np.sin((hr - 10) * np.pi / 12)
    picos = np.where((hr > 11) & (hr < 16) & (np.random.rand(periods) > 0.94), 
                     np.random.uniform(250, 550, periods), 0)
    pml = np.clip(pml_base + picos, 20, 600)
    
    # 4. Modelado del Fallo Determinista (Actual_MW)
    # Los inversores actuales pierden eficiencia durante transitorios de alta frecuencia
    # Ineficiencia inducida por latencia algorítmica (12-28% de pérdida en picos)
    factor_falla = np.where(pml > 180, 0.76, 0.91)
    act = theo * factor_falla * np.random.uniform(0.96, 1.0, periods)
    
    # Consolidación de la Matriz Fiduciaria
    df = pd.DataFrame({
        'timestamp': t,
        'Actual_MW': np.round(act, 2),
        'Theoretical_MW': np.round(theo, 2),
        'PML_USD': np.round(pml, 2)
    })
    
    df.to_csv(filename, index=False)
    print(f"ÉXITO: Archivo '{filename}' generado para auditoría.")

if __name__ == "__main__":
    materializar_datos_cliente()
