#!/bin/bash
# Push all Granas PCE updates to GitHub
# Run: bash ~/push_granas.sh

set -e

REPOS=(
  PRIMEnergeia-Sovereign
  Granas-Metrics
  Granas-Sovereign
  Granas-Scale
)

echo "🚀 Pushing PCE 33.5% updates to all repos..."
echo ""

for repo in "${REPOS[@]}"; do
  echo "=== $repo ==="
  cd "$HOME/$repo"
  git push origin main && echo "✅ $repo pushed" || echo "❌ $repo failed"
  echo ""
done

echo "🏁 Done. Check Streamlit Cloud for live deployment."
