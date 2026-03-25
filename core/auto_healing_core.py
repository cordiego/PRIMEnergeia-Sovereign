import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.distributions import Normal
import time

# ⚠ [SIMULATION MODE] — DRL networks are NOT trained on real data.
# Outputs are synthetic demonstrations of the auto-healing architecture.
SIMULATION_MODE = True

class HJB_Critic(nn.Module):
    def __init__(self, state_dim):
        super(HJB_Critic, self).__init__()
        self.fc1 = nn.Linear(state_dim, 256)
        self.fc2 = nn.Linear(256, 256)
        self.value_head = nn.Linear(256, 1)
    def forward(self, state):
        x = torch.relu(self.fc1(state))
        x = torch.relu(self.fc2(x))
        return self.value_head(x)

class AutoHealing_Actor(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(AutoHealing_Actor, self).__init__()
        self.fc1 = nn.Linear(state_dim, 256)
        self.fc2 = nn.Linear(256, 256)
        self.mu_head = nn.Linear(256, action_dim)
        self.sigma_head = nn.Linear(256, action_dim)
    def forward(self, state):
        x = torch.relu(self.fc1(state))
        x = torch.relu(self.fc2(x))
        mu = torch.tanh(self.mu_head(x))
        sigma = torch.nn.functional.softplus(self.sigma_head(x)) + 1e-5
        return mu, sigma

class PRIMEnergeia_DRL_Core:
    def __init__(self, state_dim, action_dim):
        self.actor = AutoHealing_Actor(state_dim, action_dim)
        self.critic = HJB_Critic(state_dim)

if __name__ == "__main__":
    mode_tag = " [SIMULATION]" if SIMULATION_MODE else ""
    print(f"\n[+] Inicializando PRIMEnergeia Auto-Healing Core v2.0{mode_tag}...")
    if SIMULATION_MODE:
        print("    ⚠  Networks are NOT trained — output is synthetic demonstration.")
        print("    ⚠  Connect real SCADA/frequency data for production use.")
    agent = PRIMEnergeia_DRL_Core(state_dim=4, action_dim=1)
    
    np.random.seed(42)
    time_steps = 1000
    base_freq = 60.0 + np.random.normal(0, 0.3, time_steps)
    base_freq[400:450] -= 0.8
    base_freq[800:850] -= 1.2
    
    hjb_freq = 60.0 + np.random.normal(0, 0.05, time_steps)
    hjb_freq[400:450] -= 0.1
    hjb_freq[800:850] -= 0.15
    
    capital_rescued = sum(15000.0 for f in base_freq if f < 59.5)
    
    print("="*55)
    print(f" FRECUENCIA MÍNIMA (LEGACY):      {np.min(base_freq):.4f} Hz")
    print(f" FRECUENCIA MÍNIMA (AUTO-HEALING): {np.min(hjb_freq):.4f} Hz")
    print("-" * 55)
    print(f" RESCATE FIDUCIARIO PROYECTADO:    ${capital_rescued:,.2f} USD")
    print("="*55)
