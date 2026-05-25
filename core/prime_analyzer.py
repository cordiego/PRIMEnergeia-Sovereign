import pandas as pd
import numpy as np

def analizar_datos_engie(file_path):
    print(f"[🔍] ANALIZANDO NODO VZA-400 (datos públicos CENACE): {file_path}")
    try:
        # Cargar datos (ajusta el nombre de columnas según el archivo)
        df = pd.read_csv(file_path)
        
        # 1. Detección de Violación de Código de Red
        violations = df[df['frecuencia'] < 59.95].count()
        print(f"[⚠️] Violaciones de Frecuencia Detectadas: {violations.iloc[0]}")
        
        # 2. Cálculo de Pérdida por Entropía (Estimado)
        thd_mean = df['thd'].mean()
        print(f"[🔥] THD Promedio (Estrés Térmico): {thd_mean:.2f}%")
        
        # 3. Alpha de Arbitraje Potencial
        # Si el PML > 100 USD/MWh, PRIME optimiza
        pml_high = df[df['pml'] > 100].count()
        print(f"[💹] Oportunidades de Arbitraje PML: {pml_high.iloc[0]}")
        
    except Exception as e:
        print(f"[❌] Error en formato: {e}. Asegúrate de que las columnas coincidan.")

if __name__ == "__main__":
    print("Esperando 'telemetria_engie.csv'...")
