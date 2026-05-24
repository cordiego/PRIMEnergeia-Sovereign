#!/bin/bash
# PRIMEnergeia — Push All Pending Commits
# Run this when your network is back: ./push_all.sh

echo "⚡ Checking network..."
ping -c 1 -t 3 github.com > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ No network. Try restarting Wi-Fi or your router."
    exit 1
fi

echo "✅ Network is up! Pushing..."

echo ""
echo "📦 Pushing PRIMEnergeia-Sovereign (3 commits)..."
cd ~/PRIMEnergeia-Sovereign && git push origin main
echo ""
echo "📦 Pushing PRIME-Platform (1 commit)..."
cd ~/PRIME-Platform && git push origin main

echo ""
echo "🎉 Done! All changes are live on GitHub."
echo "   → https://github.com/cordiego/PRIMEnergeia-Sovereign"
echo "   → https://cordiego.github.io/PRIME-Platform/"
