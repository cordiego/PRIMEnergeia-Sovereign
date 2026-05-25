import time
import json
import random
from google.cloud import pubsub_v1

# Configuración de Soberanía Técnica
project_id = "primenergeia-saas-prod"
topic_id = "energy-telemetry-ingestion"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

print(f"Iniciando inyección de telemetría en {topic_path}...")

try:
    for i in range(100):
        # Simulación de vectores de estado: Generación y Precio
        p_theo = 150.0 + random.uniform(-5, 5)
        p_act = p_theo * random.uniform(0.85, 0.95)
        pml = 450.0 + random.uniform(-50, 50)
        
        data = {
            "timestamp": time.time(),
            "node_id": "01-QRO-230",
            "actual_mw": round(p_act, 2),
            "theoretical_mw": round(p_theo, 2),
            "pml_usd": round(pml, 2)
        }
        
        message = json.dumps(data).encode("utf-8")
        future = publisher.publish(topic_path, message)
        print(f"Enviado paquete {i+1}: {data['actual_mw']} MW | PML: ${data['pml_usd']}")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nInyección interrumpida por el usuario.")

print("Protocolo de inyección finalizado.")
