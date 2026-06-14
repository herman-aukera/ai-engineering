#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

BRANCH="${1:-gg-finalproject-energy-aware-chat}"
SHA="${2:-$(git rev-parse HEAD)}"

echo "=== ENERGY CHAT CI PROOF ==="
echo "branch=$BRANCH"
echo "sha=${SHA:0:7}"

RUN_ID="$(
  gh run list \
    --branch "$BRANCH" \
    --commit "$SHA" \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId'
)"

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "No GitHub Actions run found for branch=$BRANCH sha=${SHA:0:7}."
  exit 1
fi

echo "run_id=$RUN_ID"

gh run view "$RUN_ID" \
  --json status,conclusion,displayTitle,workflowName,headBranch,headSha,url,jobs \
  --jq '{status, conclusion, title: .displayTitle, workflow: .workflowName, branch: .headBranch, sha: .headSha[0:7], url, jobs: [.jobs[] | {name, conclusion, status}]}'

CONCLUSION="$(
  gh run view "$RUN_ID" \
    --json conclusion \
    --jq '.conclusion'
)"

if [[ "$CONCLUSION" != "success" ]]; then
  echo "=== FAILED LOGS ==="
  gh run view "$RUN_ID" --log-failed || true
  echo "Energy Chat CI did not succeed for branch=$BRANCH sha=${SHA:0:7}."
  exit 1
fi

echo "Energy Chat CI succeeded for branch=$BRANCH sha=${SHA:0:7}."
