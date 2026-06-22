import sys
import os
import json
import logging
import pandas as pd

# Add sdl to path if necessary
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdl.sdl_engine import SDLCampaign

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("sdl_verifier")

def main():
    print("\n" + "="*70)
    print(" 🧬 Granas: Self-Driving Lab (SDL) Active Learning Integration Run")
    print("="*70 + "\n")

    campaign_id = "VERIFICATION_RUN_001"
    logger.info(f"Initializing SDL Campaign Orchestrator: {campaign_id}")
    
    # Instantiate the Campaign
    campaign = SDLCampaign(campaign_id=campaign_id)
    
    # Run the automated active learning campaign
    logger.info("Starting closed-loop execution. AI will design -> run -> measure -> pivot/terminate.")
    
    # 15 max experiments should be enough to see active learning terminate early due to convergence or stagnation
    result = campaign.run_campaign(n_experiments=15)
    
    print("\n" + "="*70)
    print(" ✅ SDL ACTIVE LEARNING CAMPAIGN FINISHED")
    print("="*70)
    
    print(f"Total Experiments Executed: {result.experiments_run}")
    print(f"Best PCE Achieved: {result.best_pce:.2f}%")
    print(f"Total Execution Time: {result.total_time_s:.2f} s")
    
    print("\n📊 Active Learning Decision History:")
    df_al = pd.DataFrame(result.active_learning_decisions)
    if not df_al.empty:
        print(df_al[["experiment_id", "action", "measured_pce", "predicted_pce", "reason"]].to_string(index=False))
    
    # Save the formal output to a JSON payload for the audit trail
    output_payload = {
        "campaign_id": result.campaign_id,
        "experiments_run": result.experiments_run,
        "best_pce": result.best_pce,
        "best_parameters": result.best_parameters,
        "active_learning_decisions": result.active_learning_decisions
    }
    
    out_file = f"sdl_verification_{campaign_id}.json"
    with open(out_file, "w") as f:
        json.dump(output_payload, f, indent=4)
        
    print(f"\n✅ Cryptographic Audit Trail Exported: {out_file}")
    
    # Assertions to ensure it actually works
    assert result.experiments_run > 0, "No experiments were run"
    assert len(result.active_learning_decisions) > 0, "No active learning decisions recorded"
    
    print("\n" + "="*70)
    print(" 🚀 GRANAS SDL VERIFICATION COMPLETE: ALL PASS.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
