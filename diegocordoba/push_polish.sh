#!/bin/bash
# push_polish.sh — Push all polish changes when network is back
# Run: bash push_polish.sh

echo "🚀 Pushing polish changes to all repos..."
for repo in Eureka-Sovereign Granas-Albedo Granas-Blueprint Granas-CFRP Granas-ETFE Granas-GHB Granas-Metrics Granas-Scale Granas-SDL Granas-TOPCon PRIM-Wind PRIME-Dashboard PRIME-Kernel PRIMEcycle PRIMEnergeia-Battery PRIMEnergeia-Sovereign PRIMEngines-AICE PRIMEngines-HYP PRIMEngines-PEM PRIMStack; do
  cd /Users/diegocordoba/$repo
  result=$(git push --set-upstream origin main 2>&1)
  if [ $? -eq 0 ]; then
    echo "✅ $repo"
  else
    echo "❌ $repo"
  fi
done
echo "🎉 Done!"
