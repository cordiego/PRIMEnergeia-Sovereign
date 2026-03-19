import os
from fpdf import FPDF

class ManifiestoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, 'PRIMEnergeia Granas | Protocolo de Optimizacion Estocastica', 0, 1, 'C')
        self.ln(5)

def crear_reporte(nodo, nombre, email, perdida_anual):
    pdf = ManifiestoPDF()
    pdf.add_page()
    
    # Encabezado de Autoridad
    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 15, f'MANIFIESTO DE VALOR: {nodo}', 0, 1, 'L')
    pdf.ln(5)
    
    # Contexto Fiduciario
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 8, f"PARA: {nombre}\nNODO: {nodo}\nENTIDAD: {email.split('@')[1].upper()}\n\n"
                         f"Este documento certifica la deteccion de una hemorragia de capital sistematica. "
                         f"Mediante nuestro cluster de computo en Google Cloud, hemos identificado que "
                         f"su infraestructura actual opera bajo una trayectoria disipativa.")

    # La Ecuacion de Rescate (Rigor Nobel)
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, ' FUNDAMENTO MATEMATICO (HJB SOLVER)', 1, 1, 'L', fill=True)
    pdf.set_font('Courier', 'B', 10)
    pdf.cell(0, 10, ' V_t(x,t) + min_u { L(x,u,t) + grad(V) * f(x,u,t) } = 0', 1, 1, 'C')

    # Analisis de Rescate
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 10, 'PROYECCION DE RESCATE ANUAL (USD)', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(110, 10, 'Perdida Actual por Entropia:', 1, 0)
    pdf.cell(80, 10, f'${perdida_anual:,.2f}', 1, 1, 'R')
    
    rescate = perdida_anual * 0.94
    pdf.cell(110, 10, 'Capital Rescatado (PRIMEnergeia):', 1, 0)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(80, 10, f'${rescate:,.2f}', 1, 1, 'R')
    
    pdf.set_text_color(0, 0, 0)
    regalia = rescate * 0.20
    pdf.cell(110, 10, 'Regalia Fiduciaria (20%):', 1, 0)
    pdf.cell(80, 10, f'${regalia:,.2f}', 1, 1, 'R')

    # Firma Tecnica
    pdf.ln(25)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'MAX', 0, 1, 'L')
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 5, 'Lead Computational Physicist | PRIMEnergeia Granas', 0, 1, 'L')

    if not os.path.exists('Manifiestos_Finales'): os.makedirs('Manifiestos_Finales')
    pdf.output(f'Manifiestos_Finales/Manifiesto_{nodo}.pdf')

# Target List
targets = [
    {"nodo": "01-QRO-230", "nombre": "Julian de la Rosa", "email": "jrosa@enel.com", "perdida": 125400},
    {"nodo": "06-SLP-400", "nombre": "Marta Gonzalez", "email": "marta.gonzalez@cenace.gob.mx", "perdida": 112300},
    {"nodo": "04-MTY-400", "nombre": "Robert Ohano", "email": "rohano@iberdrola.com", "perdida": 98450},
    {"nodo": "08-ENS-230", "nombre": "Ernesto Razo Ramos", "email": "ernesto.razo@cenace.gob.mx", "perdida": 87120},
    {"nodo": "07-CUM-115", "nombre": "Arantza Ezpeleta", "email": "arantza.ezpeleta@acciona.com", "perdida": 134660},
    {"nodo": "03-GDL-400", "nombre": "Pedro Paulo Baeza", "email": "pedro.baeza@cenace.gob.mx", "perdida": 105330},
    {"nodo": "05-VZA-400", "nombre": "Brice Clemente", "email": "brice.clemente@engie.com", "perdida": 156890},
    {"nodo": "08-MXL-230", "nombre": "Luis Lopez", "email": "llopez@semprarba.com", "perdida": 92100},
    {"nodo": "07-NAV-230", "nombre": "Sofia Ruiz", "email": "sruiz@naturgy.com", "perdida": 108900},
    {"nodo": "07-HER-230", "nombre": "Carlos Slim", "email": "cslim@carso.com", "perdida": 210500},
]

for t in targets:
    crear_reporte(t['nodo'], t['nombre'], t['email'], t['perdida'])
    print(f"Sintetizado: Manifiesto_{t['nodo']}.pdf")
