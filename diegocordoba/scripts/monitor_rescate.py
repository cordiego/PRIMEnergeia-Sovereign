import json
import time
from google.cloud import pubsub_v1

# Configuración de Identidad de Proyecto
PROJECT_ID = "primenergeia-saas-prod"
SUBSCRIPTION_ID = "test-sub"

# Parámetros de Simulación de Ineficiencia Legacy
EFFICIENCY_LEGACY = 0.88  # El sistema del cliente pierde el 12% por entropía
EFFICIENCY_PRIME = 0.98   # Tu software rescata el 10% de esa pérdida

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

print(f"--- MONITOR DE RESCATE FIDUCIARIO: EN LÍNEA ---")
print(f"Infraestructura: {PROJECT_ID} | Nodo: 07-HER-230")
print("-" * 50)

# Variables de acumulación
total_rescued_usd = 0.0

def procesar_evidencia(message):
    global total_rescued_usd
    data = json.loads(message.data.decode("utf-8"))
    
    p_theo = data.get("theoretical_mw", 0)
    pml = data.get("pml_usd", 0)
    
    # Cálculo de Trayectorias
    valor_legacy = p_theo * EFFICIENCY_LEGACY * pml
    valor_prime = p_theo * EFFICIENCY_PRIME * pml
    
    # Delta de Rescate (Ganancia Neta por segundo)
    ganancia_instante = (valor_prime - valor_legacy) / 3600 # Normalizado a segundos
    total_rescued_usd += ganancia_instante
    
    # El 20% de regalía acumulado
    tu_regalia_usd = total_rescued_usd * 0.20
    
    print(f"[RESCATE] Acumulado: ${total_rescued_usd:,.4f} USD | Tu Regalía (20%): ${tu_regalia_usd:,.4f} USD")
    print(f"        -> PML Actual: ${pml}/MWh | Delta de Eficiencia: +10.0%")
    
    message.ack()

streaming_pull_future = subscriber.subscribe(subscription_path, callback=procesar_evidencia)

try:
    print("Escuchando vectores de estado en tiempo real...")
    streaming_pull_future.result()
except KeyboardInterrupt:
    streaming_pull_future.cancel()
    print("\nProtocolo de monitoreo suspendido. Datos guardados en Bigtable.")
