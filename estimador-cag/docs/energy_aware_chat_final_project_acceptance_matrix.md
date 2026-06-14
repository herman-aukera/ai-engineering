# Energy Aware Chat final project acceptance matrix

Status: final-project MVP checkpoint document.
Branch: `EACHAT`.
Rollback checkpoint: `checkpoint-eachat-20260614`.
Canonical delivery mirror: `finalproject-GGC`.

## Purpose

This document maps the final-project expectations to concrete Energy Aware Chat evidence.
It prevents the project from being described as an MVP only because the deterministic evaluator works.
A final-project MVP candidate must also show RAG grounding, agent orchestration, deployment path, evals, and safe provider handling.

## Acceptance matrix

| Final-project requirement | Current Energy Aware Chat evidence | Status | Remaining proof |
| --- | --- | --- | --- |
| User-facing AI service | FastAPI Energy Chat API and Streamlit demo | implemented | run local API and UI smoke in Codespaces |
| RAG pipeline | deterministic project-source RAG baseline through `/energy-chat/rag/search` | implemented baseline | vector database RAG is not claimed |
| Agent layer | local retrieval, draft, critic, decider, repair path through `/energy-chat/chat` | implemented baseline | live provider-assisted agent flow is future work |
| Documented evals | deterministic tests, measurement-only benchmark request, report helpers | implemented baseline | no quality improvement claim before benchmark data |
| Deployment evidence | Dockerfile, compose file, start script, manual deploy/run path | implemented skeleton | public URL or video evidence still required |
| Provider resilience | DeepSeek baseline seam with fallback ladder to Kimi backup tiers | implemented seam | live smoke must pass before claiming live fallback proof |
| CI and validation | `scripts/validate_energy_chat.sh` and dedicated CI proof helper | implemented | run from fresh Codespace tomorrow |
| README and reviewer docs | reviewer index, quickstart, PR body, proof packet, demo docs | implemented | final README polish before delivery |
| Claim boundaries | explicit non-claims and `measurement_only_no_quality_claim` token | implemented | keep wording unchanged until evidence exists |

## Five middle milestones for the sleep checkpoint

1. Preserve rollback and delivery branches.
2. Add final-project acceptance matrix.
3. Add deployment readiness runbook.
4. Add live provider smoke evidence template.
5. Add demo recording checklist for the upgraded MVP.
6. Update reviewer index, export manifest, artifact registry, and PR handoff.

## Decision boundary

Allowed wording after local and CI proof:

```text
production-oriented MVP candidate with deterministic RAG grounding baseline, deterministic agent orchestration, DeepSeek-to-Kimi fallback seam, and deployment skeleton
```

Blocked wording:

```text
production-ready
public deployment is live
quality improvement over DeepSeek
live fallback proof without smoke evidence
vector database RAG grounding for Energy Aware Chat
```

## Morning acceptance gate

Run from a fresh Codespace:

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git pull --ff-only

git rev-parse --short HEAD
git status --short

cd estimador-cag
bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

Accept only if the local gate and the exact CI proof are green for the same `EACHAT` head.
