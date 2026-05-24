#!/bin/bash
# ============================================================
# set_github_topics.sh — Tag all PRIMEnergeia repos with topics
# ============================================================
# Usage: GH_TOKEN=ghp_xxx bash set_github_topics.sh
# Requires: curl, GitHub Personal Access Token with repo scope
# ============================================================

OWNER="cordiego"

# Check for token
if [ -z "$GH_TOKEN" ]; then
    # Try gh CLI auth
    GH_TOKEN=$(gh auth token 2>/dev/null)
    if [ -z "$GH_TOKEN" ]; then
        echo "❌ No GitHub token found. Set GH_TOKEN or login with 'gh auth login'"
        exit 1
    fi
fi

set_repo() {
    local repo="$1"
    local desc="$2"
    shift 2
    local topics=("$@")

    # Build topics JSON array
    local topics_json=$(printf '"%s",' "${topics[@]}")
    topics_json="[${topics_json%,}]"

    echo "→ $repo"

    # Set description
    curl -s -X PATCH \
        -H "Authorization: token $GH_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$OWNER/$repo" \
        -d "{\"description\": \"$desc\"}" > /dev/null

    # Set topics
    curl -s -X PUT \
        -H "Authorization: token $GH_TOKEN" \
        -H "Accept: application/vnd.github.mercy-preview+json" \
        "https://api.github.com/repos/$OWNER/$repo/topics" \
        -d "{\"names\": $topics_json}" > /dev/null

    echo "  ✅ topics: ${topics[*]}"
}

echo "🏷️  Setting GitHub topics & descriptions for all repos..."
echo ""

# ── SBU 1: PRIMEnergeia (Energy Core) ──
set_repo "PRIMEnergeia-Sovereign" \
    "⚡ Sovereign Command Center — HJB-optimal energy dispatch dashboard" \
    "energy" "streamlit" "hjb-control" "solar" "hydrogen" "dashboard" "optimization" "python"

set_repo "PRIMEnergeia-Battery" \
    "🔋 Grid-scale BESS simulator — LFP/NMC dispatch + degradation + revenue stack" \
    "energy-storage" "battery" "bess" "dispatch" "degradation" "python" "simulation"

set_repo "PRIM-Wind" \
    "🌬️ H₂-ready wind farm simulator — IEC power curves, wake effects, green H₂ coupling" \
    "wind-energy" "wind-turbine" "hydrogen" "weibull" "wake-model" "python" "simulation"

set_repo "PRIMEcycle" \
    "♻️ Perovskite solar module recycling simulator — circular economy + Pb capture" \
    "recycling" "circular-economy" "perovskite" "solar" "materials" "python" "simulation"

# ── SBU 2: PRIMEngines ──
set_repo "PRIMEngines-AICE" \
    "🧊 Advanced Ice-Cooled Engine simulator — HJB optimal control + BOM" \
    "engine" "hjb-control" "thermodynamics" "manufacturing" "python" "simulation"

set_repo "PRIMEngines-HYP" \
    "🔥 HY-P100 H₂ gas turbine simulator — Brayton cycle + CHP + grid peaking" \
    "hydrogen" "gas-turbine" "brayton-cycle" "chp" "thermodynamics" "python" "simulation"

set_repo "PRIMEngines-PEM" \
    "⚡ PEM-PB-50 fuel cell simulator — Nernst + polarization + degradation" \
    "fuel-cell" "pem" "hydrogen" "electrochemistry" "python" "simulation"

# ── SBU 3: Granas (Materials) ──
set_repo "Granas-Sovereign" \
    "🔬 Granas Materials Command Center — Unified perovskite-silicon tandem dashboard" \
    "materials-science" "perovskite" "silicon" "tandem-solar" "streamlit" "dashboard" "python"

set_repo "Granas-Optics" \
    "🌈 Optical multilayer engine — TMM/RCWA for Granas tandem stack" \
    "optics" "thin-film" "tmm" "perovskite" "materials-science" "python" "simulation"

set_repo "Granas-SDL" \
    "🤖 Self-driving lab engine — Bayesian optimization for Granas fabrication" \
    "self-driving-lab" "bayesian-optimization" "perovskite" "automation" "python"

set_repo "Granas-Metrics" \
    "📊 Holistic performance twin — Unified analytics for all Granas engines" \
    "analytics" "digital-twin" "perovskite" "performance" "python"

set_repo "Granas-Albedo" \
    "🌿 Green reflectance & thermal engine for Granas tandem modules" \
    "albedo" "thermal" "reflectance" "perovskite" "python" "simulation"

set_repo "Granas-Blueprint" \
    "📐 Master geometric engine for Granas module design" \
    "cad" "geometry" "blueprint" "perovskite" "python"

set_repo "Granas-CFRP" \
    "🏗️ Carbon fiber structural engine for Granas lightweight frames" \
    "cfrp" "carbon-fiber" "structural" "materials-science" "python"

set_repo "Granas-ETFE" \
    "🛡️ ETFE front encapsulation engine for Granas modules" \
    "etfe" "encapsulation" "polymer" "materials-science" "python"

set_repo "Granas-GHB" \
    "⚗️ Green Haber-Bosch — Electrochemical NRR catalyst engine" \
    "green-ammonia" "haber-bosch" "electrochemistry" "catalyst" "python"

set_repo "Granas-Scale" \
    "⚡ Industrial perovskite manufacturing — Lab to GW scale-up" \
    "manufacturing" "scale-up" "perovskite" "gigawatt" "python"

set_repo "Granas-TOPCon" \
    "🔬 TOPCon silicon bottom cell engine for Granas tandem" \
    "topcon" "silicon" "solar-cell" "passivation" "python"

# ── SBU 4: Eureka (Trading) ──
set_repo "Eureka-Sovereign" \
    "📈 Eureka Trading System — Algorithmic equity strategy with Telegram signals" \
    "trading" "algorithmic-trading" "telegram-bot" "github-actions" "python" "finance"

# ── SBU 5: Platform ──
set_repo "PRIME-Kernel" \
    "🧠 Shared IP core — HJB solver, physics constants, telemetry for all PRIMEnergeia" \
    "kernel" "hjb-control" "physics" "telemetry" "shared-library" "python"

set_repo "PRIME-Dashboard" \
    "🖥️ CEO executive dashboard — Fleet-wide monitoring for PRIMEnergeia" \
    "dashboard" "executive" "monitoring" "github-pages" "javascript"

set_repo "PRIMStack" \
    "🏭 Unified plant integrator — Multi-timescale HJB dispatch across all subsystems" \
    "plant-control" "hjb-control" "energy" "integration" "dispatch" "python"

echo ""
echo "🎉 Done! All 23 repos tagged."
