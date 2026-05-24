#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Granas-H2 — Full Push Script
# Creates GitHub repo, pushes Granas-H2, commits & pushes
# all README updates across the Granas ecosystem.
# ═══════════════════════════════════════════════════════════
set -e

echo "💧 Granas-H2 — Full Ecosystem Push"
echo "======================================"

# ─── 0. Wait for DNS ─────────────────────────────────────
echo ""
echo "🔄 Checking DNS..."
for i in {1..30}; do
    if ping -c1 -t2 github.com &>/dev/null; then
        echo "✅ DNS OK"
        break
    fi
    echo "  attempt $i/30 — retrying in 3s..."
    sleep 3
done

# ─── 1. Create Granas-H2 repo on GitHub ──────────────────
echo ""
echo "🆕 Creating Granas-H2 on GitHub..."
curl -s -u "cordiego" https://api.github.com/user/repos \
  -d '{"name":"Granas-H2","description":"💧 PEM Electrolysis — Solar to Green Hydrogen Engine | PRIMEnergeia S.A.S.","public":true}' \
  | grep -o '"html_url": "[^"]*"' | head -1

# ─── 2. Push Granas-H2 ───────────────────────────────────
echo ""
echo "📦 Pushing Granas-H2..."
cd /Users/diegocordoba/Granas-H2
git remote add origin https://github.com/cordiego/Granas-H2.git 2>/dev/null || true
git branch -M main
git push -u origin main
echo "✓ Granas-H2 pushed"

# ─── 3. Push Granas-Metrics (H2Metrics + dashboard) ──────
echo ""
echo "📦 Pushing Granas-Metrics (H2Metrics + 💧 H2 tab)..."
cd /Users/diegocordoba/Granas-Metrics
git add -A
git commit -m "feat: add H2Metrics dataclass + 💧 H2 dashboard tab

- H2Metrics: 22-field PEM electrolysis model (efficiency, LCOH, production)
- Dashboard: new 💧 H2 tab with 12 KPIs + LCOH sensitivity chart
- README: add Granas-H2 to sub-products table
- HolisticGranas: wire h2 field into compute()

PRIMEnergeia S.A.S. — Diego Córdoba Urrutia" 2>/dev/null || echo "(already committed)"
git push --force origin main
echo "✓ Granas-Metrics pushed"

# ─── 4. Push README updates for all Granas repos ─────────
for repo in Granas-SDL Granas-Albedo Granas-ETFE Granas-TOPCon Granas-Blueprint Granas-Sovereign Granas-Optics; do
    echo ""
    echo "📦 Pushing $repo (README: +H2 row)..."
    cd "/Users/diegocordoba/$repo"
    git add README.md
    git commit -m "docs: add Granas-H2 to product suite table" 2>/dev/null || echo "(already committed)"
    git push origin main
    echo "✓ $repo pushed"
done

# ─── Done ─────────────────────────────────────────────────
echo ""
echo "======================================"
echo "✅ All pushed! Granas-H2 is live:"
echo "   https://github.com/cordiego/Granas-H2"
echo ""
echo "Updated repos:"
echo "   Granas-Metrics  (H2Metrics + dashboard tab)"
echo "   Granas-SDL      (README)"
echo "   Granas-Albedo   (README)"
echo "   Granas-ETFE     (README)"
echo "   Granas-TOPCon   (README)"
echo "   Granas-Blueprint(README)"
echo "   Granas-Sovereign(README)"
echo "   Granas-Optics   (README)"
echo "======================================"
