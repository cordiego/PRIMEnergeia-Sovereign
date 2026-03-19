import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [PRIMEnergeia] - %(message)s')

class GranasValueEngine:
    def __init__(self, capacity_mw=100.0, node="07-HER-230"):
        self.capacity = capacity_mw
        self.node = node
        self.deployment_fee = 50000  # Fee inicial de ingeniería
        self.alpha_royalty = 0.20    # 20% del capital rescatado
        self.client_file = "client_data.csv"
        self.output_pdf = f"Manifiesto_Valor_{node}.pdf"

    def resolver(self):
        if os.path.exists(self.client_file):
            logging.info("MODO AUDITORÍA: Procesando telemetría real...")
            df = pd.read_csv(self.client_file, parse_dates=['timestamp'])
        else:
            logging.info("MODO PROSPECCIÓN: Simulando dinámica de Sonora...")
            t = pd.date_range(start="2026-02-01", periods=30*96, freq='15min')
            hr = t.hour + t.minute / 60.0
            theo = np.maximum(0, np.sin((hr - 6) * np.pi / 12)) * self.capacity
            pml = 45 + 30 * np.sin((hr - 10) * np.pi / 12) + np.where(np.random.rand(len(t)) > 0.95, 450, 0)
            act = theo * np.where(pml > 180, 0.75, 0.92)
            df = pd.DataFrame({'timestamp': t, 'Actual_MW': act, 'Theoretical_MW': theo, 'PML_USD': pml})

        # Cálculo de la Integral de Rescate Fiduciario
        df['Loss_USD'] = (df['Theoretical_MW'] - df['Actual_MW']) * df['PML_USD'] * 0.25
        total_rescate = df['Loss_USD'].sum()
        
        # Estructura de Captura de Valor
        performance_fee = total_rescate * self.alpha_royalty
        net_client_gain = total_rescate - performance_fee

        self.generar_pdf(df, total_rescate, performance_fee, net_client_gain)

    def generar_pdf(self, df, rescate, fee_perf, neto_cliente):
        # Gráfica de Hemorragia
        plt.style.use('dark_background')
        plt.figure(figsize=(12, 5))
        df_p = df.tail(192)
        plt.plot(df_p['timestamp'], df_p['Theoretical_MW'], color='#00ffcc', label='Trayectoria Óptima', lw=2)
        plt.fill_between(df_p['timestamp'], df_p['Actual_MW'], df_p['Theoretical_MW'], color='#ff3333', alpha=0.3)
        plt.plot(df_p['timestamp'], df_p['Actual_MW'], color='#ff3333', label='Fallo Cliente', alpha=0.7)
        plt.savefig('evidencia.png', dpi=150, bbox_inches='tight')
        plt.close()

        # PDF con Tabla de Reparto de Valor
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(0, 255, 204)
        pdf.cell(0, 15, f"PRIMEnergeia: Manifiesto de Valor - Nodo {self.node}", 0, 1, 'C')
        pdf.ln(5)
        
        pdf.set_font("Arial", '', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 10, f"Tras la resolucion estocastica del nodo, se ha identificado un potencial de rescate de capital de ${rescate:,.2f} USD mensuales.")
        
        pdf.ln(5)
        # TABLA DE REPARTO
        pdf.set_fill_color(30, 30, 30)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(95, 10, "CONCEPTO", 1, 0, 'C', True)
        pdf.cell(95, 10, "VALOR (USD)", 1, 1, 'C', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 12)
        pdf.cell(95, 10, "Rescate Fiduciario Total", 1, 0, 'L')
        pdf.cell(95, 10, f"${rescate:,.2f}", 1, 1, 'R')
        
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(255, 51, 51)
        pdf.cell(95, 10, f"Performance Fee PRIMEnergeia ({int(self.alpha_royalty*100)}%)", 1, 0, 'L')
        pdf.cell(95, 10, f"- ${fee_perf:,.2f}", 1, 1, 'R')
        
        pdf.set_text_color(0, 153, 76)
        pdf.cell(95, 10, "BENEFICIO NETO CLIENTE (Mensual)", 1, 0, 'L')
        pdf.cell(95, 10, f"${neto_cliente:,.2f}", 1, 1, 'R')
        
        pdf.ln(10)
        pdf.image('evidencia.png', x=10, w=190)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'I', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 8, f"* Fee de Despliegue Unico: ${self.deployment_fee:,.2f} USD. El modelo de performance asegura que nuestra compensacion esta vinculada directamente a la captura de exergia real.")
        
        pdf.output(self.output_pdf)
        logging.info(f"ÉXITO: Manifiesto de Valor generado en {self.output_pdf}")

if __name__ == "__main__":
    GranasValueEngine().resolver()
