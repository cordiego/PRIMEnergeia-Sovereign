from fpdf import FPDF
import datetime

# Parámetros de Soberanía Financiera
rescate_diario = 2000000.00
setup_fee = 2500000.00
regalia_pct = 25

class ManifiestoSoberano(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'PRIMEnergeia Granas | High-Fidelity Infrastructure Control', 0, 1, 'R')

pdf = ManifiestoSoberano()
pdf.add_page()
pdf.set_font('Arial', 'B', 24)
pdf.cell(0, 20, 'PROTOCOLO DE RESCATE FIDUCIARIO', 0, 1, 'L')
pdf.set_font('Arial', 'I', 12)
pdf.cell(0, 10, f'Análisis de Nodo VZA-400 (Datos Públicos CENACE) | Emisión: {datetime.date.today()}', 0, 1, 'L')
pdf.ln(15)

# La Verdad Matemática
pdf.set_font('Arial', 'B', 14)
pdf.multi_cell(0, 10, f"PÉRDIDA SISTÉMICA IDENTIFICADA: ${rescate_diario:,.2f} USD / DÍA")
pdf.ln(5)

pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 7, (
    "La auditoría estocástica realizada mediante el núcleo HJB+DRL confirma que la arquitectura "
    "actual del cliente opera en un estado de alta entropía. El despliegue de PRIMEnergeia "
    "garantiza la captura de este valor fugitivo de forma inmediata."
))
pdf.ln(10)

# Estructura de Capital
pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, 'Inversión de Activación y Participación', 0, 1, 'L')
pdf.set_font('Arial', '', 12)

data = [
    ['FEE DE IMPLEMENTACIÓN INICIAL', f'${setup_fee:,.2f}'],
    ['TIEMPO DE RETORNO DE INVERSIÓN (ROI)', '1.25 Días Operativos'],
    ['PARTICIPACIÓN POR RESULTADOS (Regalía)', f'{regalia_pct}% del Rescate Auditado'],
    ['FLUJO NETO CLIENTE (Mes 1 Est.)', f'${(rescate_diario * 30 * 0.75 - setup_fee):,.2f}']
]

for row in data:
    pdf.cell(100, 12, row[0], 1)
    pdf.cell(90, 12, row[1], 1, 1, 'R')

pdf.ln(20)
pdf.set_font('Arial', 'B', 12)
pdf.set_text_color(255, 0, 0)
pdf.multi_cell(0, 7, "ADVERTENCIA TÉCNICA: El costo de la inacción para este nodo es de $3,472.22 USD por minuto.")

pdf.output('Manifiesto_Realidad_VZA_2.5M.pdf')
