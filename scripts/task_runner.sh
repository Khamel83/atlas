#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/task_runner.sh <TASK_ID> "<TASK_SLUG>"
TASK_ID="${1:-"":}"; TASK_SLUG="${2:-"":}"
if [[ -z "${TASK_ID}" || -z "${TASK_SLUG}" ]]; then
  echo "Usage: $0 <TASK_ID> \"<TASK_SLUG>\"" >&2; exit 2
fi

BRANCH="task/${TASK_ID}-${TASK_SLUG}"

# Preflight
git fetch origin
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree not clean; commit or stash first." >&2; exit 3
fi
git checkout main
git pull --rebase origin main

# Branch
git checkout -b "${BRANCH}"

echo "==> Implement the task now per agents.md (manual or agent-driven)."
echo "==> Commit in small steps with messages like: task(${TASK_ID}): <change>"

# Verify gates are expected to be run by the agent (tests, lint, etc.)
# Add project-specific invocations here, e.g.:
#   ./scripts/run_tests.sh
#   ./scripts/lint.sh

read -p "Mark task as successful and merge to main? (y/N) " yn
if [[ "${yn}" =~ ^[Yy]$ ]]; then
  git checkout main
  git pull --rebase origin main
  git merge --no-ff "${BRANCH}" -m "merge: task(${TASK_ID}) ${TASK_SLUG}"
  git push origin main
  echo "Merged ${BRANCH} -> main"
else
  echo "Left branch ${BRANCH} unmerged."
fi
