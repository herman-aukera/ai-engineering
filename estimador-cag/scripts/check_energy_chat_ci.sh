#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

BRANCH="${1:-EACHAT}"
SHA="${2:-$(git rev-parse HEAD)}"
WORKFLOW="${3:-Energy Aware Chat CI}"
MAX_ATTEMPTS="${ENERGY_CHAT_CI_ATTEMPTS:-36}"
SLEEP_SECONDS="${ENERGY_CHAT_CI_SLEEP_SECONDS:-5}"

echo "=== ENERGY CHAT CI PROOF ==="
echo "branch=$BRANCH"
echo "sha=${SHA:0:7}"
echo "workflow=$WORKFLOW"

RUN_ID=""
STATUS=""
CONCLUSION=""

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  RUN_ID="$(
    gh run list \
      --workflow "$WORKFLOW" \
      --branch "$BRANCH" \
      --commit "$SHA" \
      --limit 1 \
      --json databaseId \
      --jq '.[0].databaseId // ""'
  )"

  if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
    echo "No $WORKFLOW run found yet for branch=$BRANCH sha=${SHA:0:7}; attempt $attempt/$MAX_ATTEMPTS."
    sleep "$SLEEP_SECONDS"
    continue
  fi

  STATUS="$(
    gh run view "$RUN_ID" \
      --json status \
      --jq '.status'
  )"
  CONCLUSION="$(
    gh run view "$RUN_ID" \
      --json conclusion \
      --jq '.conclusion // ""'
  )"

  echo "run_id=$RUN_ID status=$STATUS conclusion=${CONCLUSION:-pending}"

  if [[ "$STATUS" == "completed" ]]; then
    break
  fi

  sleep "$SLEEP_SECONDS"
done

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "No $WORKFLOW run found for branch=$BRANCH sha=${SHA:0:7}."
  echo "Do not use the interactive gh run selector because it may show other branches."
  exit 1
fi

gh run view "$RUN_ID" \
  --json status,conclusion,displayTitle,workflowName,headBranch,headSha,url,jobs \
  --jq '{status, conclusion, title: .displayTitle, workflow: .workflowName, branch: .headBranch, sha: .headSha[0:7], url, jobs: [.jobs[] | {name, conclusion, status}]}'

if [[ "$STATUS" != "completed" ]]; then
  echo "$WORKFLOW did not complete within $((MAX_ATTEMPTS * SLEEP_SECONDS)) seconds."
  exit 1
fi

if [[ "$CONCLUSION" != "success" ]]; then
  echo "=== FAILED LOGS ==="
  gh run view "$RUN_ID" --log-failed || true
  echo "Energy Chat CI did not succeed for workflow=$WORKFLOW branch=$BRANCH sha=${SHA:0:7}."
  exit 1
fi

echo "Energy Chat CI succeeded for workflow=$WORKFLOW branch=$BRANCH sha=${SHA:0:7}."
