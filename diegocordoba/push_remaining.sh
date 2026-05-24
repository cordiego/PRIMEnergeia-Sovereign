#!/usr/bin/env bash
# Push remaining repos that failed due to network outage
set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; RESET='\033[0m'

printf "${CYAN}═══ Push Remaining Repos ═══${RESET}\n\n"

# Granas-Module (needs --set-upstream)
printf "  ⏳ Granas-Module...\n"
cd ~/Granas-Module && git push --set-upstream origin main 2>&1 && printf "  ${GREEN}✅ Granas-Module pushed${RESET}\n" || printf "  ${RED}❌ Granas-Module failed${RESET}\n"

# Granas-Sovereign
printf "  ⏳ Granas-Sovereign...\n"
cd ~/Granas-Sovereign && git push origin main 2>&1 && printf "  ${GREEN}✅ Granas-Sovereign pushed${RESET}\n" || printf "  ${RED}❌ Granas-Sovereign failed${RESET}\n"

echo ""
printf "${CYAN}Done.${RESET}\n"
