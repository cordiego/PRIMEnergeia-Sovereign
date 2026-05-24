#!/usr/bin/env bash
# Push all repos with pending commits to GitHub
set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; RESET='\033[0m'
PASS=0; FAIL=0

REPOS=(
  ~/PRIMEnergeia-Sovereign
  ~/Granas-Sovereign
  ~/Granas-Module
  ~/Eureka-Sovereign
)

echo ""
printf "${CYAN}═══ Push All Repos ═══${RESET}\n\n"

for repo in "${REPOS[@]}"; do
  name=$(basename "$repo")
  if [ -d "$repo/.git" ]; then
    ahead=$(cd "$repo" && git rev-list --count @{u}..HEAD 2>/dev/null || echo "?")
    if [[ "$ahead" == "0" ]]; then
      printf "  ${GREEN}✔${RESET} %-30s already up to date\n" "$name"
      continue
    fi
    printf "  ⏳ %-30s pushing %s commit(s)...\n" "$name" "$ahead"
    if cd "$repo" && git push origin main 2>&1; then
      printf "  ${GREEN}✅${RESET} %-30s pushed\n" "$name"
      PASS=$((PASS + 1))
    else
      printf "  ${RED}❌${RESET} %-30s push failed\n" "$name"
      FAIL=$((FAIL + 1))
    fi
  fi
done

echo ""
printf "${CYAN}Done: ${GREEN}%d pushed${CYAN}, ${RED}%d failed${RESET}\n" "$PASS" "$FAIL"
