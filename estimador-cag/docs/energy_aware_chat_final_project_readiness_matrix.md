# Energy Aware Chat Final Project Readiness Matrix

status: readiness-matrix
branch: EACHAT
claim_boundary: production-oriented MVP candidate, not production-ready

## Summary

Energy Aware Chat is the primary final-project candidate because it naturally maps to the required AI system shape: FastAPI service, RAG evidence, agent orchestration, evaluation, and usable demo path.

This matrix is intentionally honest. PASS means implemented and evidence-backed. PARTIAL means locally useful but still missing a stronger final-project proof. GAP means not done.

| Requirement | Status | Current evidence | How to verify | Remaining gap |
| --- | --- | --- | --- | --- |
| FastAPI AI service | PASS | Energy Chat router under `/energy-chat`; health endpoint; browser demo route | `GET /health`, `GET /energy-chat/demo`, OpenAPI schema | none for local MVP |
| Browser UI | PASS | `/` redirects to `/energy-chat/demo`; same-origin UI tests the MVP path | Open forwarded port 8000 | browser HTML needs ongoing polish only |
| Streamlit UI | PASS | `energy_chat_streamlit_app.py` exposes mode, execution, Energy Card, audit, and benchmark evidence | Open forwarded port 8501 | none for local MVP |
| Project-source RAG baseline | PASS | `/energy-chat/rag/search` retrieves committed source chunks with lexical cosine baseline | Run RAG-only button or route smoke | vector DB RAG is later hardening, not current claim |
| Agent layer | PASS | Retrieval agent, live draft path, deterministic critic, decider, and repair seam exposed through `/energy-chat/chat/live` | Run live Energy Aware Chat | LangGraph or multi-agent runtime is not required for this MVP |
| Energy Card | PASS | Decision, energy, repairs, evidence, and caveats visible in browser and Streamlit | Run chat path | none for local MVP |
| Live provider path | PASS | DeepSeek primary draft path with Kimi fallback seam; local smoke script exists | `scripts/live_energy_chat_provider_smoke.py` | full live benchmark not yet done |
| Fixed deterministic benchmark | PASS | Fixed dataset, runner, JSON result, Markdown report, API routes, and UI evidence | `GET /energy-chat/benchmark/fixed` | not a live-provider quality benchmark |
| Documented evals | PARTIAL | Fixed deterministic benchmark and report exist | read benchmark report and result JSON | need live-provider benchmark dataset before improvement claims |
| Regression case | PASS | Fixed benchmark cases include known failure/repair scenarios | run fixed benchmark tests | broaden later with more cases |
| Deployment skeleton | PARTIAL | Dockerfile and compose skeleton exist | run local Docker smoke | public URL not done |
| Public deployment evidence | GAP | none claimed | not applicable yet | publish service or record 2 to 3 minute demo |
| README/final docs | PARTIAL | reviewer docs, proof packets, demo checklist, readiness matrix | inspect docs folder | final README needs consolidation before delivery |
| CI | PASS | Dedicated Energy Aware Chat CI validates branch and SHA | `scripts/check_energy_chat_ci.sh` | none for local MVP |
| Secrets hygiene | PASS | normal CI uses fake keys; live smoke is separate | inspect workflows and validation logs | continue scanning before final delivery |
| Production readiness | GAP | explicitly not claimed | claim boundary docs | requires auth/privacy/monitoring/rollback/support |

## Current allowed claim

```text
Energy Aware Chat is a browser-testable and Streamlit-testable production-oriented MVP candidate with deterministic RAG baseline, live provider path, Energy Card, visible execution audit, fixed deterministic benchmark evidence, local validation proof, and dedicated CI proof.
```

## Current forbidden claims

```text
production-ready public service
real-user production readiness
validated quality improvement over plain DeepSeek
frontier-model superiority
public deployment URL exists
```

## Next readiness upgrades

1. Public deployment or 2 to 3 minute demo video.
2. Final README consolidation.
3. Live-provider benchmark over the same fixed case IDs.
4. Broader project-source RAG dataset.
5. Deployment smoke proof for Docker compose.
