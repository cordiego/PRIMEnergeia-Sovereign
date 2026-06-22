import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_sen_real import fetch_sen_data, SEN_NODES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Grid-Ingest] - %(message)s')

def ingest_node(node_id):
    try:
        logging.info(f"Ingestando datos para {node_id} ({SEN_NODES[node_id]})...")
        path = fetch_sen_data(node_id=node_id, days=7)
        return f"OK: {node_id} -> {path}"
    except Exception as e:
        return f"ERROR: {node_id} -> {e}"

def mass_ingestion():
    logging.info(f"Iniciando ingesta masiva de {len(SEN_NODES)} nodos del Sistema Interconectado Nacional (SIN)...")
    
    # We use ThreadPoolExecutor to speed up API fetches
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(ingest_node, node) for node in SEN_NODES.keys()]
        for future in futures:
            results.append(future.result())
            
    for res in results:
        logging.info(res)
        
    logging.info("--- PROTOCOLO COMPLETADO: TODOS LOS NODOS DEL SIN INTEGRADOS ---")

if __name__ == "__main__":
    mass_ingestion()
