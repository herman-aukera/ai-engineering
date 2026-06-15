#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

BRANCH="${1:-EACHAT}"
SHA="${2:-$(git rev-parse HEAD)}"
PRIMARY_WORKFLOW="${3:-Energy Aware Chat CI}"
FALLBACK_WORKFLOW="${ENERGY_CHAT_CI_FALLBACK_WORKFLOW:-CI - Estimador CAG}"
MAX_ATTEMPTS="${ENERGY_CHAT_CI_ATTEMPTS:-36}"
SLEEP_SECONDS="${ENERGY_CHAT_CI_SLEEP_SECONDS:-5}"
REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq '.nameWithOwner')}"

if [[ -z "$REPO" || "$REPO" == "null" ]]; then
  echo "Could not resolve GitHub repository name."
  exit 1
fi

echo "=== ENERGY CHAT CI PROOF ==="
echo "repo=$REPO"
echo "branch=$BRANCH"
echo "sha=${SHA:0:7}"
echo "primary_workflow=$PRIMARY_WORKFLOW"
echo "fallback_workflow=$FALLBACK_WORKFLOW"

find_run_id_for_workflow() {
  local workflow_name="$1"

  gh api \
    -H "Accept: application/vnd.github+json" \
    "/repos/$REPO/actions/runs?per_page=100" \
    --paginate \
    --jq ".workflow_runs[] | select(.head_branch == \"$BRANCH\" and .head_sha == \"$SHA\" and .name == \"$workflow_name\") | .id" \
    | head -n 1
}

RUN_ID=""
STATUS=""
CONCLUSION=""
WORKFLOW="$PRIMARY_WORKFLOW"

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  RUN_ID="$(find_run_id_for_workflow "$PRIMARY_WORKFLOW")"
  WORKFLOW="$PRIMARY_WORKFLOW"

  if [[ -z "$RUN_ID" && -n "$FALLBACK_WORKFLOW" && "$FALLBACK_WORKFLOW" != "$PRIMARY_WORKFLOW" ]]; then
    RUN_ID="$(find_run_id_for_workflow "$FALLBACK_WORKFLOW")"
    WORKFLOW="$FALLBACK_WORKFLOW"
  fi

  if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
    echo "No proof run found yet for repo=$REPO branch=$BRANCH sha=${SHA:0:7}; attempt $attempt/$MAX_ATTEMPTS."
    echo "Checked workflow name=$PRIMARY_WORKFLOW and fallback=$FALLBACK_WORKFLOW via GitHub Actions API."
    sleep "$SLEEP_SECONDS"
    continue
  fi

  STATUS="$(
    gh run view "$RUN_ID" \
      --repo "$REPO" \
      --json status \
      --jq '.status'
  )"
  CONCLUSION="$(
    gh run view "$RUN_ID" \
      --repo "$REPO" \
      --json conclusion \
      --jq '.conclusion // ""'
  )"

  echo "run_id=$RUN_ID status=$STATUS conclusion=${CONCLUSION:-pending} workflow=$WORKFLOW"

  if [[ "$STATUS" == "completed" ]]; then
    break
  fi

  sleep "$SLEEP_SECONDS"
done

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "No proof run found for repo=$REPO branch=$BRANCH sha=${SHA:0:7}."
  echo "Do not use the interactive gh run selector because it may show other branches."
  echo "This script lists Actions runs by exact branch and commit, then filters workflow name from JSON."
  exit 1
fi

gh run view "$RUN_ID" \
  --repo "$REPO" \
  --json status,conclusion,displayTitle,workflowName,headBranch,headSha,url,jobs \
  --jq '{status, conclusion, title: .displayTitle, workflow: .workflowName, branch: .headBranch, sha: .headSha[0:7], url, jobs: [.jobs[] | {name, conclusion, status}]}'

if [[ "$STATUS" != "completed" ]]; then
  echo "$WORKFLOW did not complete within $((MAX_ATTEMPTS * SLEEP_SECONDS)) seconds."
  exit 1
fi

if [[ "$CONCLUSION" != "success" ]]; then
  echo "=== FAILED LOGS ==="
  gh run view "$RUN_ID" --repo "$REPO" --log-failed || true
  echo "Energy Chat CI did not succeed for workflow=$WORKFLOW branch=$BRANCH sha=${SHA:0:7}."
  exit 1
fi

echo "Energy Chat CI succeeded for workflow=$WORKFLOW branch=$BRANCH sha=${SHA:0:7}."
