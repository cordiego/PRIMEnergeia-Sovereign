import pandas as pd
from fpdf import FPDF
import datetime

# Constantes de Poder Real
rescate_dia = 2000000.00
setup_fee = 2500000.00  # 2.5 Million USD Upfront
regalia_pct = 0.25

class ManifiestoTotal(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'PRIMEnergeia Granas | Strategic Infrastructure Control', 0, 1, 'R')

pdf = ManifiestoTotal()
pdf.add_page()
pdf.set_font('Arial', 'B', 28)
pdf.cell(0, 20, 'CONTRATO DE ACTIVACIÓN SOBERANA', 0, 1, 'L')
pdf.set_font('Arial', 'I', 14)
pdf.cell(0, 10, f'Nodo: VZA-400 (Datos Públicos CENACE) | Auditoría Estocástica Final | {datetime.date.today()}', 0, 1, 'L')
pdf.ln(15)

# La Realidad del Mercado
pdf.set_font('Arial', 'B', 14)
pdf.multi_cell(0, 10, f"VALOR DIARIO IDENTIFICADO PARA RESCATE: ${rescate_dia:,.2f} USD")
pdf.ln(5)

pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 7, (
    "El retraso en la activación del núcleo HJB+DRL genera una pérdida irrecuperable de "
    f"${(rescate_dia / 24):,.2f} USD por hora. La implementación de PRIMEnergeia detiene "
    "esta hemorragia de capital de forma inmediata mediante control activo de frecuencia."
))
pdf.ln(15)

# Estructura Financiera de Grado Enterprise
pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, 'Protocolo de Inversión y Regalías', 0, 1, 'L')
pdf.set_font('Arial', '', 12)

data = [
    ['FEE DE IMPLEMENTACIÓN (Setup)', f'${setup_fee:,.2f}'],
    ['TIEMPO ESTIMADO DE RECUPERACIÓN (ROI)', '30.0 Horas de Operación'],
    ['REGALÍA OPERATIVA (Variable)', '25.0% sobre Capital Rescatado'],
    ['BENEFICIO NETO CLIENTE (Mes 1 Proyectado)', f'${(rescate_dia * 30 * 0.75 - setup_fee):,.2f}']
]

for row in data:
    pdf.cell(105, 12, row[0], 1)
    pdf.cell(85, 12, row[1], 1, 1, 'R')

pdf.ln(20)
pdf.set_font('Arial', 'B', 12)
pdf.set_text_color(200, 0, 0)
pdf.multi_cell(0, 7, "ADVERTENCIA: Esta propuesta expira en 24 horas debido a la volatilidad intrínseca del nodo y el costo de oportunidad acumulado.")

pdf.output('Manifiesto_Soberania_VZA_2.5M.pdf')
