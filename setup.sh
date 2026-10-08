#!/usr/bin/env bash
# Install career-ops at a pinned commit and point it at your data in me/. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

# career-ops v1.35.0. To upgrade, see "Updating career-ops" in README.md.
CAREER_OPS_COMMIT=e8332a8ba88c8da1e21eeeeec90bac517807b475
PLAYWRIGHT_MCP=@playwright/mcp@0.0.83

for tool in git node npm claude; do
  command -v "$tool" >/dev/null || { echo "setup.sh: '$tool' is required" >&2; exit 1; }
done

# Fetch exactly the pinned commit (git verifies object hashes). -f only resets
# career-ops' own files; your data lives in me/.
[ -d career-ops/.git ] || git init -q career-ops
git -C career-ops fetch -q --depth 1 https://github.com/career-ops-hq/career-ops.git "$CAREER_OPS_COMMIT"
git -C career-ops checkout -q -f --detach FETCH_HEAD

cd career-ops
# career-ops reads and writes user data in the folder this marker names.
echo ../me > .career-ops-data
# Locked dependencies. postinstall downloads Playwright's Chromium, used for PDFs.
cp ../career-ops.package-lock.json package-lock.json
npm ci --no-fund --no-audit
# Playwright MCP is the browser Claude Code uses to read and fill application forms.
# Project scope (.mcp.json) is what this career-ops version's doctor detects.
[ -f .mcp.json ] || claude mcp add --scope project playwright -- npx -y "$PLAYWRIGHT_MCP"
# Keep the files setup.sh adds out of career-ops' git status.
for f in .career-ops-data .mcp.json; do
  grep -qx "$f" .git/info/exclude || echo "$f" >> .git/info/exclude
done

node doctor.mjs || true
echo
echo "Done. Run ./start.sh to open Claude Code."
