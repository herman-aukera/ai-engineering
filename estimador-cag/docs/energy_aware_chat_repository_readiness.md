# Energy Aware Chat repository readiness

Status: final-project staging branch, not a coursework merge branch.

Branch: `gg-finalproject-energy-aware-chat`

## Repository strategy

Energy Aware Chat is currently developed inside `herman-aukera/ai-engineering` because the final project must keep absorbing class material until Session 17.

This branch is not intended to be merged into the coursework `main` branch as a normal session task. It is a staging branch for a product that should later move to its own repository.

Target future repository:

    herman-aukera/energy-aware-chat

## Why it stays here for now

1. The LIDR course repository already has the shared FastAPI, Streamlit, provider, validation, and CI scaffolding.
2. Sessions after the current checkpoint may still add useful patterns for RAG, agents, deployment, evals, and documentation.
3. Keeping the branch here preserves comparability with previous coursework artifacts while the final project is still evolving.
4. Extracting too early would duplicate infrastructure and make class-inspired improvements harder to port.

## Extraction trigger

Extract to the standalone repository only after one of these gates is true:

1. Session 17 is completed and no more class material needs to be absorbed into the final project.
2. The Energy Aware Chat boundary is stable enough that most future work is product-specific rather than coursework-specific.
3. The final project needs public-facing issue tracking, releases, deployment docs, or a clean portfolio README independent from `estimador-cag`.

## Package boundary

Initial standalone export boundary:

    estimador-cag/app/energy_chat/
    estimador-cag/energy_chat_streamlit_app.py
    estimador-cag/demo_payloads/energy_chat/
    estimador-cag/docs/energy_aware_chat_demo.md
    estimador-cag/docs/energy_aware_chat_repository_readiness.md
    estimador-cag/docs/energy_aware_chat_final_project_delivery_plan.md
    estimador-cag/docs/energy_aware_chat_demo_walkthrough.md
    estimador-cag/docs/energy_aware_chat_live_demo_readiness.md
    estimador-cag/docs/energy_aware_chat_standalone_export_readme.md
    estimador-cag/docs/energy_aware_chat_session17_backlog.md
    estimador-cag/scripts/validate_energy_chat.sh
    estimador-cag/scripts/check_energy_chat_ci.sh
    estimador-cag/scripts/export_energy_chat_manifest.sh
    estimador-cag/tests/test_energy_chat_*.py
    .github/workflows/energy-chat-ci.yml
    .github/workflows/ci.yml

Expected future standalone layout:

    energy-aware-chat/
      app/energy_chat/
      apps/streamlit/energy_chat_streamlit_app.py
      demo_payloads/energy_chat/
      docs/
      scripts/
      tests/
      .github/workflows/ci.yml
      README.md
      pyproject.toml

## Delivery artifacts

The current staging branch includes these final-project handoff artifacts:

1. `docs/energy_aware_chat_final_project_delivery_plan.md`
2. `docs/energy_aware_chat_demo_walkthrough.md`
3. `docs/energy_aware_chat_live_demo_readiness.md`
4. `docs/energy_aware_chat_standalone_export_readme.md`
5. `docs/energy_aware_chat_session17_backlog.md`
6. `demo_payloads/energy_chat/`
7. `scripts/export_energy_chat_manifest.sh`
8. `app/energy_chat/release_snapshot.py`

These files keep delivery, demo, backlog, snapshot, and future extraction decisions explicit.

## Release snapshot helper

`app/energy_chat/release_snapshot.py` provides a small pure-Python helper for recording a branch and commit checkpoint from already observed local and remote validation facts.

The helper is not a runtime dependency for the evaluator. It is a reviewer-support artifact for summarizing a known-good checkpoint.

## Do not merge policy

Do not open a merge PR from `gg-finalproject-energy-aware-chat` into `main` just because GitHub reports the branch as mergeable.

Correct branch interpretation:

    unmerged = expected
    mergeable = mechanically possible
    merge target = not main
    product target = future standalone repository

## CI proof policy

Energy Aware Chat now has a dedicated workflow:

    Energy Aware Chat CI

Use that workflow as the proof target. The shared `CI - Estimador CAG` workflow may still run as a repository backstop, but it is not the primary product proof because it also covers other branches and can be visually confused with Energy Aware Code runs.

Use non-interactive GitHub CLI commands scoped to the exact workflow, branch, and commit. Do not use the interactive `gh run view --log-failed` selector without a run id, because it can show failed workflow runs from other branches such as Energy Aware Code.

From repository root, prefer:

    bash estimador-cag/scripts/check_energy_chat_ci.sh

The helper checks:

    workflow = Energy Aware Chat CI
    branch = gg-finalproject-energy-aware-chat
    sha = current HEAD
    conclusion = success

Manual equivalent:

    CURRENT_SHA="$(git rev-parse HEAD)"

    gh run list \
      --workflow "Energy Aware Chat CI" \
      --branch gg-finalproject-energy-aware-chat \
      --commit "$CURRENT_SHA" \
      --limit 5 \
      --json databaseId,status,conclusion,displayTitle,workflowName,headBranch,headSha,url \
      --jq '.[] | {id: .databaseId, status, conclusion, title: .displayTitle, workflow: .workflowName, branch: .headBranch, sha: .headSha[0:7], url}'

Acceptance condition:

    workflow = Energy Aware Chat CI
    branch = gg-finalproject-energy-aware-chat
    sha = current HEAD
    conclusion = success

## Local proof policy

From `estimador-cag`:

    bash scripts/validate_energy_chat.sh

The local validation gate must pass before using a commit as a demo checkpoint.

The gate must include:

1. Ruff auto-fix.
2. Ruff check.
3. Python compilation.
4. Dynamic focused discovery of `tests/test_energy_chat_*.py`.
5. Focused Energy Chat tests.
6. Full test suite.
7. Root diff check.
8. Dirty-tree failure.

## Current no-claim boundary

Do not claim any of the following until later proof exists:

1. Production readiness.
2. RAG grounding.
3. Agent orchestration.
4. DeepSeek quality improvement.
5. Frontier-model superiority.
6. Deployment readiness.

The correct benchmark status remains:

    measurement_only_no_quality_claim
