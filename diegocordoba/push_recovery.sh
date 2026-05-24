#!/bin/bash
# ═══════════════════════════════════════════════════
#  One-shot recovery: push PRIMEnergeia + create missing repos
#  Run when WiFi is back: bash ~/push_recovery.sh
# ═══════════════════════════════════════════════════
set -euo pipefail

echo "🔍 Testing connectivity..."
while ! ping -c1 -t3 github.com &>/dev/null; do
    echo "⏳ Waiting for internet... (retrying in 5s)"
    sleep 5
done
echo "✅ Internet OK"

# ─── 1. Push PRIMEnergeia-Sovereign ───
echo ""
echo "═══ 1/3: PRIMEnergeia-Sovereign ═══"
cd ~/PRIMEnergeia-Sovereign
git push origin main && echo "✅ Pushed" || echo "⚠️ Failed"

# ─── 2. Install gh CLI (if needed) ───
echo ""
echo "═══ 2/3: Installing gh CLI ═══"
if ! command -v gh &>/dev/null; then
    if command -v brew &>/dev/null; then
        brew install gh
    elif command -v conda &>/dev/null; then
        conda install -y -c conda-forge gh 2>&1 | tail -3
    else
        echo "📥 Downloading gh CLI directly..."
        curl -sL https://github.com/cli/cli/releases/download/v2.62.0/gh_2.62.0_macOS_amd64.zip -o /tmp/gh.zip
        unzip -o /tmp/gh.zip -d /tmp/gh_install
        sudo cp /tmp/gh_install/gh_*/bin/gh /usr/local/bin/gh 2>/dev/null || cp /tmp/gh_install/gh_*/bin/gh ~/gh_bin
        export PATH="$HOME/gh_bin:$PATH"
        rm -rf /tmp/gh.zip /tmp/gh_install
    fi
fi

if command -v gh &>/dev/null; then
    echo "✅ gh CLI available"

    # Auth check
    if ! gh auth status &>/dev/null; then
        echo "🔐 Please login: gh auth login"
        gh auth login
    fi

    # ─── 3. Create missing repos ───
    echo ""
    echo "═══ 3/3: Creating missing repos ═══"
    MISSING_REPOS=(Granas-Metrics Granas-CFRP Granas-GHB Granas-Albedo Granas-ETFE Granas-TOPCon Granas-Blueprint Granas-Scale)

    for repo in "${MISSING_REPOS[@]}"; do
        dir="$HOME/$repo"
        if [ ! -d "$dir" ]; then
            echo "⏭️ $repo — no local directory, skipping"
            continue
        fi

        echo "📦 Creating cordiego/$repo..."
        gh repo create "cordiego/$repo" --private --source="$dir" --push 2>&1 && echo "✅ $repo created & pushed" || echo "⚠️ $repo may already exist"
    done
else
    echo "❌ Could not install gh CLI. Create repos manually at https://github.com/new"
    echo "   Repos needed: Granas-Metrics Granas-CFRP Granas-GHB Granas-Albedo Granas-ETFE Granas-TOPCon Granas-Blueprint Granas-Scale"
fi

echo ""
echo "🏁 Recovery complete! Run 'bash ~/push_all.sh' to verify all repos."
