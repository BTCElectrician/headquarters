#!/usr/bin/env bash
# Run every headquarters check in one go.
#
#   ops/check_all.sh               checks this headquarters
#   ops/check_all.sh --root DIR    checks the headquarters in DIR
#
# Runs the registry, work queue, operator decisions and docs checks, then
# prints one line saying whether all of them passed. Read-only.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
failed=0

run() {
  local title="$1"
  shift
  echo "== $title"
  if ! python3 "$@"; then
    failed=$((failed + 1))
  fi
  echo ""
}

run "Registry (hq.yaml)" "$SCRIPT_DIR/validate_registry.py" "$@"
run "Work queue" "$SCRIPT_DIR/validate_work_queue.py" "$@"
run "Operator decisions" "$SCRIPT_DIR/operator_decisions.py" validate "$@"
run "Docs" "$SCRIPT_DIR/validate_docs.py" "$@"

if [ "$failed" -gt 0 ]; then
  echo "$failed check(s) found problems. Read the lines starting with '-' above."
  exit 1
fi
echo "All checks passed."
