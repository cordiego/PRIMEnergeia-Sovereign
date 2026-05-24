import numpy as np

def carnot_efficiency(th, tc):
    """
    Calculates maximum theoretical efficiency.
    th: Hot source temperature (K)
    tc: Cold sink temperature (K) - can be a NumPy array
    """
    th = np.asarray(th)
    tc = np.asarray(tc)
    
    if np.any(th <= 0) or np.any(tc <= 0):
        raise ValueError("Temperatures must be in Kelvin (positive).")
    
    # Efficiency calculation
    efficiency = 1 - (tc / th)
    
    # Logic check: Efficiency cannot be negative in this model
    return np.maximum(efficiency, 0)

if __name__ == "__main__":
    # Example: Solar substrate at 800K, varying ambient cooling from 270K to 350K
    T_hot = 800
    T_cold_range = np.array([273, 298, 323, 348]) # 0C, 25C, 50C, 75C
    
    efficiencies = carnot_efficiency(T_hot, T_cold_range)
    
    print(f"Hot Source: {T_hot}K")
    for tc, eff in zip(T_cold_range, efficiencies):
        print(f"Sink Temp: {tc}K | Max Efficiency: {eff:.2%}")
