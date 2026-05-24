import torch
import torch.nn as nn
import numpy as np
import time
import sys

class SovereignOptimizer(nn.Module):
    def __init__(self, n_assets=5):
        super(SovereignOptimizer, self).__init__()
        # Red de retroalimentación para calcular el gradiente de Sharpe
        self.layer = nn.Linear(n_assets, n_assets)
        self.temp = 0.5 # Factor de amortiguación (Temperatura)

    def forward(self, returns, cov_matrix):
        # Calculamos el ratio de eficiencia estocástica
        # w_opt = inv(Sigma) * mu
        mu = returns.unsqueeze(1)
        sigma_inv = torch.inverse(cov_matrix + torch.eye(5) * 1e-4)
        raw_weights = torch.mm(sigma_inv, mu).squeeze()
        
        # Softmax con temperatura para estabilidad de la red
        return torch.softmax(raw_weights / self.temp, dim=0)

def run_optimization():
    assets = ['SNDK', 'SNXX', 'CASH']
    model = SovereignOptimizer()
    
    print("\n[+] Iniciando Optimizador LQR para Eureka 1.0...")
    
    while True:
        # 1. Ingesta de Datos (Simulando Drift y Volatilidad Real)
        mu = torch.randn(5) * 0.05 + 0.02 # Retornos esperados
        # Generar matriz de covarianza definida positiva
        A = torch.randn(5, 5)
        sigma = torch.mm(A, A.t()) + torch.eye(5) * 0.1
        
        # 2. Resolución del Hamiltoniano
        w_opt = model(mu, sigma)
        
        # 3. Output de Soberanía
        w_p = w_opt.detach().numpy()
        output = " | ".join([f"{assets[i]}: {w_p[i]*100:4.1f}%" for i in range(5)])
        
        # Métrica de Estabilidad (Varianza del Portafolio)
        risk = torch.sqrt(torch.mv(torch.mv(sigma, w_opt), w_opt)).item()
        
        sys.stdout.write(f"\r\033[K[EUREKA OPT] {output} | RIESGO(σ): {risk:.4f}")
        sys.stdout.flush()
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        run_optimization()
    except KeyboardInterrupt:
        print("\n[!] Optimizador pausado. Pesos guardados en memoria.")
