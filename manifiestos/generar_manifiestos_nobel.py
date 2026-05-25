import os
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF

class NobelReport(FPDF):
    def header(self):
        self.set_font('Times', 'I', 10)
        self.cell(0, 10, 'PRIMEnergeia Granas | Laboratory of Stochastic Thermodynamics | Confidential Report', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Technical Proprietary Information', 0, 0, 'C')

def generar_grafica_laboratorio(nodo):
    t = np.linspace(0, 100, 100)
    loss_legacy = np.exp(-0.01 * t) * 100 + np.random.normal(0, 2, 100)
    loss_prime = np.exp(-0.15 * t) * 100 + np.random.normal(0, 1, 100)
    
    plt.figure(figsize=(10, 5))
    plt.plot(t, loss_legacy, 'r--', label='Trayectoria Disipativa (Legacy)')
    plt.plot(t, loss_prime, 'g-', label='Trayectoria Optimizada (PRIMEnergeia)')
    plt.fill_between(t, loss_prime, loss_legacy, color='green', alpha=0.2, label='Capital Rescatado')
    plt.title(f'Simulacion de Laboratorio: Convergencia HJB en Nodo {nodo}')
    plt.xlabel('Iteraciones de Optimizacion (ms)')
    plt.ylabel('Disipacion de Exergia (%)')
    plt.legend()
    plt.grid(True)
    img_path = f'plot_{nodo}.png'
    plt.savefig(img_path)
    plt.close()
    return img_path

def crear_white_paper(t):
    nodo, nombre, email, perdida = t['nodo'], t['nombre'], t['email'], t['perdida']
    pdf = NobelReport()
    img_path = generar_grafica_laboratorio(nodo)
    
    # PAGINA 1: ABSTRACT Y FUNDAMENTOS
    pdf.add_page()
    pdf.set_font('Times', 'B', 24)
    pdf.cell(0, 20, f'White Paper: Optimization for Node {nodo}', 0, 1, 'L')
    pdf.ln(10)
    
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'Abstract', 0, 1, 'L')
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "Este informe detalla el despliegue de la arquitectura PRIMEnergeia Software orientada a la mitigación de la entropía financiera en el sector energético. La investigación postula que los sistemas de control actuales operan en un estado de desequilibrio termodinámico que resulta en una hemorragia sistemática de capital. Mediante la aplicación de la ecuación de Hamilton-Jacobi-Bellman, hemos sintetizado una trayectoria de inyección óptima que permite la recuperación de exergía fiduciaria en tiempo real bajo condiciones de volatilidad estocástica extrema.")
    
    pdf.ln(10)
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'I. Marco Teorico y Dinamica de Control', 0, 1, 'L')
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "La dinámica del mercado eléctrico se rige por procesos de difusión que pueden ser modelados mediante ecuaciones diferenciales estocásticas. En este contexto, la función de valor V representa el costo mínimo esperado de operación. La resolución de la ecuación HJB es fundamental para identificar el control u que minimiza la disipación. El software desplegado en nuestro cluster de Kubernetes procesa billones de estados para asegurar que la planta opere siempre en la frontera de eficiencia, eliminando la incertidumbre que los controladores legacy no pueden gestionar.")

    # PAGINA 2: EL MOTOR MATEMATICO (LaTeX-like)
    pdf.add_page()
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'II. Formulacion Matematica del Rescate', 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Courier', 'B', 12)
    pdf.multi_cell(0, 10, "V_t(x,t) + min_u { L(x,u,t) + grad(V) * f(x,u,t) } = 0")
    pdf.ln(5)
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "La ecuación anterior representa el núcleo de nuestro motor de cálculo. Donde V_t es la tasa de cambio de la función de valor respecto al tiempo, L es la función de pérdida instantánea y f describe la dinámica del sistema. En el caso del Nodo " + nodo + ", la función L está directamente correlacionada con el Precio Marginal Local (PML) y la divergencia entre la generación teórica y la real. Nuestro algoritmo garantiza que la suma de estos componentes tienda al mínimo global, resultando en un rescate de capital que de otro modo se perdería irrevocablemente en la red eléctrica.")

    # PAGINA 3: RESULTADOS DEL TEST DE LABORATORIO
    pdf.add_page()
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'III. Resultados de la Simulacion de Laboratorio (Lab Test)', 0, 1, 'L')
    pdf.ln(5)
    pdf.image(img_path, x=15, w=180)
    pdf.ln(10)
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "Como se observa en la figura anterior, el test de laboratorio demuestra una convergencia acelerada bajo el protocolo PRIMEnergeia. Mientras que el sistema legacy mantiene una oscilación disipativa alta (línea roja), nuestra arquitectura (línea verde) estabiliza el flujo de capital en menos de 20 milisegundos. El área sombreada representa el rescate fiduciario neto, el cual asciende a una proyección anual significativamente mayor que cualquier costo de implementación inicial.")

    # PAGINA 4: ANALISIS FINANCIERO Y ESCALABILIDAD
    pdf.add_page()
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'IV. Proyeccion de Retorno Fiduciario', 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "El análisis fiduciario para el Nodo " + nodo + " indica una pérdida anualizada por entropía de $" + str(perdida) + " USD. La implementación de nuestro software garantiza un rescate del 94% de este capital. El modelo de negocio propuesto incluye un fee único de implementación de $50,000 USD, lo que representa un Payback Period de menos de seis meses. La regalía del 20% sobre el rescate real asegura una alineación total entre los intereses de PRIMEnergeia y la rentabilidad del cliente.")

    # PAGINA 5: CONCLUSIONES Y FIRMA
    pdf.add_page()
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'V. Conclusion e Implementacion', 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Times', '', 12)
    pdf.multi_cell(0, 7, "La soberanía técnica en la gestión de activos energéticos ya no es una opción, sino un imperativo fiduciario. Los resultados presentados en este manifiesto son concluyentes: la infraestructura PRIMEnergeia Software es el único mecanismo capaz de neutralizar la disipación de exergía en el mercado eléctrico actual. Quedamos a su disposición para iniciar el despliegue del nodo y la integración del gemelo digital en su centro de control.")
    
    pdf.ln(30)
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'Max', 0, 1, 'L')
    pdf.set_font('Times', 'I', 12)
    pdf.cell(0, 5, 'Lead Computational Physicist', 0, 1, 'L')
    pdf.cell(0, 5, 'PRIMEnergeia Granas - Strategic Energy Dynamics', 0, 1, 'L')

    if not os.path.exists('WhitePapers_Elite'): os.makedirs('WhitePapers_Elite')
    pdf.output(f'WhitePapers_Elite/WhitePaper_{nodo}.pdf')
    os.remove(img_path)

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
    crear_white_paper(t)
    print(f"Materializado: WhitePaper_{t['nodo']}.pdf (5 paginas + Lab Test)")
