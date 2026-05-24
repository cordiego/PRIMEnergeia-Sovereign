import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys

# Append the diegocordoba module path if needed, to import GranasModule
sys.path.append(os.path.join(os.path.dirname(__file__), 'Granas-Module'))

def run_parameter_sweep():
    print("=" * 70)
    print(" GRANAS PARAMETER SWEEP ANALYSIS")
    print("=" * 70)
    
    csv_path = "/Users/diegocordoba/diegocordoba/Granas-Metrics/metrics/granas_experiment_log.csv"
    output_dir = "/Users/diegocordoba/diegocordoba/Granas-Metrics/metrics/sweep_analysis"
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} experiment records.")
    
    # 1. Module Power / Yield calculation (using Granas blueprint)
    # Using BLUEPRINT_ACTIVE_AREA_CM2 = 624.0, Irradiance = 1000 W/m2, CF = 0.22
    AREA_M2 = 624.0 / 10000.0
    IRRADIANCE = 1000.0
    CAPACITY_FACTOR = 0.22
    HOURS_PER_YEAR = 8760
    
    # Compute P = PCE/100 * Area * Irradiance
    df['module_power_W'] = (df['pce'] / 100.0) * AREA_M2 * IRRADIANCE
    df['annual_energy_kWh'] = df['module_power_W'] * CAPACITY_FACTOR * HOURS_PER_YEAR / 1000.0
    
    print("\n▸ Computed Module Power and Annual Energy metrics based on PCE.")
    
    # 2. Correlation Matrix
    print("▸ Generating Parameter Correlation Matrix...")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    # Exclude trial_id
    features = [c for c in numeric_cols if c != 'trial_id']
    corr = df[features].corr()
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1)
    plt.title("Granas Experiment Log - Parameter Correlation Matrix", fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "correlation_matrix.png"), dpi=150)
    plt.close()
    
    # 3. 3D Scatter: Annealing Temp vs Annealing Time vs PCE
    print("▸ Generating 3D Scatter (Temp vs Time vs PCE)...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(df['anneal_temp'], df['anneal_time'], df['pce'], 
                    c=df['pce'], cmap='viridis', s=100, edgecolors='k')
    ax.set_xlabel('Annealing Temp (°C)')
    ax.set_ylabel('Annealing Time (s)')
    ax.set_zlabel('PCE (%)')
    ax.set_title('PCE Landscape: Annealing Parameters', fontsize=14)
    plt.colorbar(sc, label='PCE (%)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "3d_scatter_annealing_pce.png"), dpi=150)
    plt.close()

    # 4. 2D Scatter: Molar Conc vs Spin Speed colored by Stability Score
    print("▸ Generating 2D Scatter (Molar Conc vs Spin Speed by Stability)...")
    plt.figure(figsize=(9, 6))
    sc = plt.scatter(df['molar_conc'], df['spin_speed'], c=df['stability_score'], 
                     cmap='plasma', s=100, edgecolors='k')
    plt.xlabel('Molar Concentration (M)')
    plt.ylabel('Spin Speed (RPM)')
    plt.title('Stability Map: Precursor Concentration vs Spin Speed', fontsize=14)
    plt.colorbar(sc, label='Stability Score (0-1)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "scatter_molar_spin_stability.png"), dpi=150)
    plt.close()
    
    # 5. Export Augmented Log
    augmented_path = os.path.join(output_dir, "granas_experiment_log_augmented.csv")
    df.to_csv(augmented_path, index=False)
    print(f"\n▸ Augmented CSV exported to {augmented_path}")
    print(f"▸ Visualizations saved to {output_dir}")
    print("=" * 70)
    
    # Print the top 3 best performing configurations
    top_3 = df.nlargest(3, 'pce')
    print("\n🏆 Top 3 PCE Configurations:")
    for idx, row in top_3.iterrows():
        print(f"Trial {int(row['trial_id'])}: PCE = {row['pce']:.2f}% | "
              f"Power = {row['module_power_W']:.2f} W | "
              f"Stability = {row['stability_score']:.2f} | "
              f"Anneal = {row['anneal_temp']:.1f}°C for {row['anneal_time']:.1f}s")
        

if __name__ == "__main__":
    run_parameter_sweep()
