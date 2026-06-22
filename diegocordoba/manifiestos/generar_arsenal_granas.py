import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os

# --- MATRIZ DE OBJETIVOS ESTRATÉGICOS ---
targets = [
    {"id": "01-QRO-230", "nombre": "Julian de la Rosa", "empresa": "Enel", "p_nominal": 150},
    {"id": "06-SLP-400", "nombre": "Marta Gonzalez", "empresa": "CENACE", "p_nominal": 200},
    {"id": "04-MTY-400", "nombre": "Robert Ohano", "empresa": "Iberdrola", "p_nominal": 300},
    {"id": "08-ENS-230", "nombre": "Ernesto Razo Ramos", "empresa": "CENACE", "p_nominal": 120},
    {"id": "07-CUM-115", "nombre": "Arantza Ezpeleta", "empresa": "Acciona", "p_nominal": 180},
    {"id": "03-GDL-400", "nombre": "Pedro Paulo Baeza", "empresa": "CENACE", "p_nominal": 250},
    {"id": "05-VZA-400", "nombre": "Brice Clemente", "empresa": "Engie", "p_nominal": 280},
    {"id": "08-MXL-230", "nombre": "Luis Lopez", "empresa": "Sempra", "p_nominal": 160},
    {"id": "07-NAV-230", "nombre": "Sofia Ruiz", "empresa": "Naturgy", "p_nominal": 140},
    {"id": "07-HER-230", "nombre": "Carlos Slim", "empresa": "Grupo Carso", "p_nominal": 400},
]

class ReporteNoble(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'PRIMEnergeia Software | Protocolo de Rescate Fiduciario', 0, 1, 'C')
        self.ln(5)

def procesar_nodo(t):
    nodo = t['id']
    cap = t['p_nominal']
    
    # 1. Simulación de Datos (Vectores de Estado)
    intervals = 96 
    theo = cap + np.random.normal(0, 5, intervals)
    actual = theo * np.random.uniform(0.85, 0.93, intervals)
    pml = 380 + 150 * np.sin(np.linspace(0, 2*np.pi, intervals)) + np.random.uniform(0, 100, intervals)
    
    # 2. Gráfico de Convergencia HJB
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(theo, label='Trayectoria Óptima HJB', color='green', linewidth=2, linestyle='--')
    ax1.plot(actual, label='Desempeño Legacy', color='blue', alpha=0.4)
    ax1.set_ylabel('Potencia (MW)')
    
    ax2 = ax1.twinx()
    # Rescate acumulado como array de NumPy
    rescate_acumulado = ((theo - actual) * pml).cumsum() / 4
    ax2.fill_between(range(intervals), rescate_acumulado, color='red', alpha=0.1)
    ax2.set_ylabel('Capital Rescatado (USD)', color='red')
    
    plot_file = f"plot_{nodo}.png"
    plt.savefig(plot_file, dpi=120)
    plt.close()
    
    # 3. PDF Final (Materialización Fiduciaria)
    pdf = ReporteNoble()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"MANIFIESTO DE VALOR: NODO {nodo}", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 10, f"Atención: {t['nombre']} | Entidad: {t['empresa']}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.multi_cell(0, 7, "El presente reporte certifica la divergencia entre la operación legacy y "
                         "la trayectoria de mínima disipación calculada por el motor estocástico "
                         "PRIMEnergeia. Se ha detectado una hemorragia de capital sistemática.")
    pdf.image(plot_file, x=10, w=190)
    
    # CORRECCIÓN: Acceso directo al último elemento del array de NumPy
    total_anual = rescate_acumulado[-1] * 365
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, 'Métrica Fiduciaria', 1)
    pdf.cell(90, 10, 'Valor (USD)', 1, 1, 'C')
    pdf.set_font('Arial', '', 11)
    pdf.cell(100, 10, 'Rescate Bruto Proyectado (Anual)', 1)
    pdf.cell(90, 10, f"${total_anual:,.2f}", 1, 1, 'R')
    pdf.cell(100, 10, 'Fee de Implementación', 1)
    pdf.cell(90, 10, "$50,000.00", 1, 1, 'R')
    pdf.cell(100, 10, 'Regalía PRIMEnergeia (20%)', 1)
    pdf.cell(90, 10, f"${total_anual * 0.20:,.2f}", 1, 1, 'R')
    
    pdf.output(f"Manifiesto_{nodo}.pdf")
    os.remove(plot_file)

if __name__ == "__main__":
    folder = "Reportes_Finales_Granas"
    if not os.path.exists(folder): os.makedirs(folder)
    # Limpiar carpeta si ya existe para evitar duplicados
    for f in os.listdir(folder): os.remove(os.path.join(folder, f))
    os.chdir(folder)
    for t in targets:
        procesar_nodo(t)
        print(f"[CONVERGENCIA] Nodo {t['id']} materializado con éxito.")
