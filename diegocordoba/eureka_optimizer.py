import torch
import torch.nn as nn
import numpy as np
import time
import sys

# Motor de Optimización LQR para Eureka 1.0
class SovereignOptimizer(nn.Module):
    def __init__(self, n_assets=5):
        super(SovereignOptimizer, self).__init__()
        self.temp = 0.5 

    def forward(self, returns, cov_matrix):
        reg_sigma = cov_matrix + torch.eye(5) * 1e-4
        mu = returns.unsqueeze(1)
        try:
            w_raw = torch.linalg.solve(reg_sigma, mu).squeeze()
        except:
            w_raw = torch.ones(5) / 5.0
        return torch.softmax(w_raw / self.temp, dim=0)

def run():
    assets = ['AGQ', 'UGL', 'GEV', 'VGSH', 'VTIP']
    model = SovereignOptimizer()
    print("\n[+] Eureka 1.0: Sistema de Control Estocástico Iniciado.")
    
    while True:
        mu = torch.randn(5) * 0.05 + 0.02 
        A = torch.randn(5, 5)
        sigma = torch.mm(A, A.t()) + torch.eye(5) * 0.1
        
        w_opt = model(mu, sigma)
        # Operación escalar corregida para evitar RuntimeError
        risk = torch.sqrt(torch.sum(w_opt * torch.mv(sigma, w_opt))).item()
        
        w_p = w_opt.detach().numpy()
        output = " | ".join([f"{assets[i]}: {w_p[i]*100:4.1f}%" for i in range(5)])
        
        sys.stdout.write(f"\r\033[K[EUREKA] {output} | RIESGO(σ): {risk:.4f}")
        sys.stdout.flush()
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[!] Standby.")
