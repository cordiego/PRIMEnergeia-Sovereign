#!/bin/bash
# ============================================================
#  One-shot: Set PRIME Platform link everywhere & push
# ============================================================
set -e

echo "🔗 Setting GitHub profile website link..."
gh api -X PATCH /user -f blog="https://cordiego.github.io/PRIME-Platform/" --silent && \
  echo "  ✅ Profile website → https://cordiego.github.io/PRIME-Platform/" || \
  echo "  ⚠️  Failed — run: gh auth refresh -h github.com -s user"

echo ""
echo "📦 Pushing PRIMEnergeia-Sovereign (dashboard)..."
cd /Users/diegocordoba/PRIMEnergeia-Sovereign
git add -A
git diff --cached --quiet || git commit -m "Link dashboard to PRIME Platform"
git push

echo ""
echo "📦 Pushing cordiego profile README..."
cd /Users/diegocordoba/cordiego
git add -A
git diff --cached --quiet || git commit -m "Add PRIME Platform link to profile"
git push

echo ""
echo "✅ All done — profile link + dashboard + README updated."
