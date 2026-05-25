from fpdf import FPDF
import datetime

setup_fee = 2500000.00
rescate_dia = 2000000.00

class ManifiestoFinal(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'CONFIDENCIAL | PRIMEnergeia Granas | Strategic Operations', 0, 1, 'R')

pdf = ManifiestoFinal()
pdf.add_page()
pdf.set_font('Arial', 'B', 28)
pdf.cell(0, 20, 'ORDEN DE ACTIVACIÓN ESTRATÉGICA', 0, 1, 'L')
pdf.ln(10)

pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, f'VALOR DE RESCATE AUDITADO: ${rescate_dia:,.2f} USD / DÍA', 0, 1, 'L')
pdf.ln(10)

pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, (
    "El análisis del nodo VZA-400 con datos públicos CENACE muestra que el modelo HJB+DRL de PRIMEnergeia podría "
    "técnicamente. La inacción operativa representa un costo hundido de $83,333.33 USD "
    "por cada hora de retraso en la firma del presente protocolo."
))
pdf.ln(10)

# Estructura de Capital Final
pdf.set_font('Arial', 'B', 14)
pdf.cell(110, 12, 'CONCEPTO', 1)
pdf.cell(80, 12, 'VALOR (USD)', 1, 1, 'C')

pdf.set_font('Arial', '', 12)
data = [
    ['FEE DE IMPLEMENTACIÓN (SETUP)', f'${setup_fee:,.2f}'],
    ['FEE DE MANTENIMIENTO Y REGALÍA', '25% SOBRE RESCATE'],
    ['PUNTO DE EQUILIBRIO (ROI)', '30 HORAS OPERATIVAS'],
    ['BENEFICIO CLIENTE AÑO 1 (EST.)', f'${(rescate_dia * 365 * 0.75):,.2f}']
]

for row in data:
    pdf.cell(110, 12, row[0], 1)
    pdf.cell(80, 12, row[1], 1, 1, 'R')

pdf.ln(20)
pdf.set_font('Arial', 'I', 10)
pdf.multi_cell(0, 5, "Validado por: Diego | Lead Computational Physicist | PRIMEnergeia Software Node")

pdf.output('Manifiesto_Autoridad_Final.pdf')
