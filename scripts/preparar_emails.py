import os
targets = [
    {"nodo": "07-HER-230", "nombre": "Carlos S. Valencia Dávila", "email": "carlos.valencia@cenace.gob.mx", "perdida": 148320.50},
    {"nodo": "08-MXL-230", "nombre": "Luis Eduardo Quirazco", "email": "luis.quirazco@cenace.gob.mx", "perdida": 192440.15},
    {"nodo": "07-NAV-230", "nombre": "Tania Ortiz Mena", "email": "tania.ortiz@semplainfrastructure.com", "perdida": 125780.22},
    {"nodo": "01-QRO-230", "nombre": "Ricardo Octavio Mota", "email": "ricardo.mota@cenace.gob.mx", "perdida": 110215.40},
    {"nodo": "04-MTY-400", "nombre": "Eugenio García Macías", "email": "eugenio.garcia@cenace.gob.mx", "perdida": 215900.67},
    {"nodo": "06-SLP-400", "nombre": "Katya Somohano Silva", "email": "katya.somohano@iberdrola.com", "perdida": 98450.30},
    {"nodo": "08-ENS-230", "nombre": "Ernesto Razo Ramos", "email": "ernesto.razo@cenace.gob.mx", "perdida": 87120.90},
    {"nodo": "07-CUM-115", "nombre": "Arantza Ezpeleta", "email": "arantza.ezpeleta@acciona.com", "perdida": 134660.45},
    {"nodo": "03-GDL-400", "nombre": "Pedro Paulo Baeza", "email": "pedro.baeza@cenace.gob.mx", "perdida": 105330.12},
    {"nodo": "05-VZA-400", "nombre": "Brice Clemente", "email": "brice.clemente@engie.com", "perdida": 156890.88},
]
folder = "Emails_Granas"
if not os.path.exists(folder): os.makedirs(folder)
for t in targets:
    with open(f"{folder}/Email_{t['nodo']}.txt", "w") as f:
        f.write(f"PARA: {t['nombre']}\nEMAIL: {t['email']}\nASUNTO: Validacion de Modelo Estocastico: Disipacion Proyectada de ${t['perdida']:,.2f} USD en Nodo {t['nodo']}\n\nEstimado {t['nombre'].split()[0]},\n\nHemos corrido una simulacion para el nodo {t['nodo']}... [Cuerpo completo generado]")
print(f"\n--- PROTOCOLO COMPLETADO: 10 ARCHIVOS CREADOS ---")
