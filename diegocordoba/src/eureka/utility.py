import numpy as np
import json
import os

def load_config():
    """Reads project settings from the terminal-generated config."""
    config_path = os.path.join('config', 'settings.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def crra_utility(c, rho=None):
    """
    Calculates CRRA utility for a consumption vector c.
    Vectorized via NumPy for Monte Carlo efficiency.
    """
    if rho is None:
        rho = load_config().get('default_rho', 2.0)
    
    c = np.asarray(c)
    
    # Handle the Logarithmic case (rho = 1)
    if np.isclose(rho, 1.0):
        return np.log(c)
    
    # Standard CRRA formula
    return (c**(1 - rho) - 1) / (1 - rho)

if __name__ == "__main__":
    # Test with a stochastic endowment sample
    endowments = np.array([0.8, 1.0, 1.2, 1.5])
    u_values = crra_utility(endowments)
    print(f"Endowments: {endowments}")
    print(f"CRRA Utility (rho=2.0): {u_values}")
