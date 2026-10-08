#!/usr/bin/env bash
# Open Claude Code in career-ops, with access to your data in me/.
set -euo pipefail
cd "$(dirname "$0")/career-ops"
exec claude --add-dir ../me "$@"
