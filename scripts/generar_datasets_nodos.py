import pandas as pd
import numpy as np
import os
from datetime import datetime

def materializar_datasets():
    folder = "Datasets_Nodos"
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Configuración de Nodos: {Nombre: (Capacidad, Precio Promedio, Volatilidad)}
    nodos_config = {
        "07-HER-230": (100, 45, 0.95),
        "08-MXL-230": (120, 52, 0.98),
        "07-NAV-230": (80, 42, 0.92),
        "01-QRO-230": (150, 38, 0.85),
        "04-MTY-400": (200, 48, 0.88),
        "06-SLP-400": (100, 40, 0.87),
        "08-ENS-230": (60, 55, 0.93),
        "07-CUM-115": (110, 44, 0.96),
        "03-GDL-400": (130, 41, 0.86),
        "05-VZA-400": (140, 39, 0.89)
    }

    t = pd.date_range(start="2026-02-01", periods=96*30, freq='15min')
    hr = t.hour + t.minute / 60.0

    for nodo, (cap, p_base, vol) in nodos_config.items():
        # Trayectoria Óptima P*(t)
        theo = np.maximum(0, np.sin((hr - 6) * np.pi / 12)) * cap
        theo *= np.random.normal(1.0, 0.05, len(t)) # Ruido de irradiancia
        
        # Dinámica de Precios Nodal (PML)
        pml = p_base + 20 * np.sin((hr - 10) * np.pi / 12)
        pml += np.where(np.random.rand(len(t)) > vol, np.random.uniform(200, 600), 0)
        
        # Ineficiencia Actual (Hemorragia de Capital)
        act = theo * np.where(pml > 180, 0.73, 0.92)
        act = np.clip(act * np.random.normal(1.0, 0.02, len(t)), 0, cap)
        
        df = pd.DataFrame({
            'timestamp': t,
            'Actual_MW': np.round(act, 2),
            'Theoretical_MW': np.round(theo, 2),
            'PML_USD': np.round(pml, 2)
        })
        
        df.to_csv(f"{folder}/data_{nodo}.csv", index=False)
    
    print(f"--- PROTOCOLO COMPLETADO: 10 DATASETS GENERADOS EN {folder} ---")

if __name__ == "__main__":
    materializar_datasets()
