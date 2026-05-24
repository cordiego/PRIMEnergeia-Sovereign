import torch
import numpy as np
import sqlite3
import time
import sys

# --- BASE DE DATOS DE SOBERANÍA ---
def init_db():
    conn = sqlite3.connect('eureka_patrimonio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (timestamp TEXT, saldo REAL, riesgo REAL)''')
    conn.commit()
    return conn

# --- MOTOR DE OPTIMIZACIÓN ---
def run_eureka_lite(saldo_inicial):
    conn = init_db()
    c = conn.cursor()
    assets = ['SNDK', 'SNXX', 'CASH']
    saldo_actual = saldo_inicial
    
    print(f"\n[+] Eureka Lite Activado. Capital Semilla: ${saldo_inicial:.2f} USD")
    
    try:
        while True:
            # Simulación de mercado (Drift + Ruido)
            mu = torch.randn(5) * 0.02 + 0.005 # Retornos más conservadores
            A = torch.randn(5, 5)
            sigma = torch.mm(A, A.t()) + torch.eye(5) * 0.1
            
            # Cálculo de pesos (Equipartición optimizada por riesgo)
            w_opt = torch.softmax(mu / 0.5, dim=0)
            risk = torch.sqrt(torch.sum(w_opt * torch.mv(sigma, w_opt))).item()
            
            # Simulación de rendimiento diario (0.1% - 0.5%)
            rendimiento_diario = (torch.mean(mu).item())
            saldo_actual *= (1 + rendimiento_diario)
            
            # Persistencia en SQLite
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO historial VALUES (?, ?, ?)", (ts, saldo_actual, risk))
            conn.commit()
            
            # Output en terminal
            output = " | ".join([f"{assets[i]}: {w_opt[i]*100:2.0f}%" for i in range(5)])
            sys.stdout.write(f"\r\033[K[EUREKA] {output} | SALDO: ${saldo_actual:,.2f} | σ: {risk:.4f}")
            sys.stdout.flush()
            time.sleep(1)
            
    except KeyboardInterrupt:
        conn.close()
        print(f"\n[!] Sesión guardada. Saldo Final: ${saldo_actual:.2f}")

if __name__ == "__main__":
    run_eureka_lite(550.00)
