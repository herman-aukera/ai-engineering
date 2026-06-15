# Energy Aware Chat Evaluator Landing Page

status: demo-ready-evidence-index
branch: EACHAT
last_accepted_checkpoint: 7376718
claim_status: measurement_only_no_quality_claim

## Purpose

This page is the fastest route for a reviewer, teacher, or future maintainer to test Energy Aware Chat without reading the whole repository history.

Energy Aware Chat is a constraint-governed assistant for AI project and release-readiness questions. It retrieves project evidence, asks a provider for a draft in live mode, evaluates that candidate with deterministic critics, computes energy, applies one deterministic repair when appropriate, and returns a visible Energy Card.

## What to open first

Start FastAPI:

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the forwarded Codespaces port 8000. The root path redirects to:

```text
/energy-chat/demo
```

Primary browser path:

```text
https://<codespace-8000-url>/energy-chat/demo
```

Swagger path:

```text
https://<codespace-8000-url>/docs
```

## Streamlit product UI

Start Streamlit in another terminal:

```bash
cd /workspaces/ai-engineering/estimador-cag
ESTIMADOR_BACKEND_URL=https://<codespace-8000-url> \
UV_HTTP_TIMEOUT=600 \
uv run streamlit run energy_chat_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

Open the forwarded Codespaces port 8501.

Use Streamlit when you want the clearest reviewer-friendly product UI with mode selector, execution selector, Energy Card, evidence, provider metadata, visible execution audit, and fixed benchmark evidence.

## Main reviewer flow

1. Open `/energy-chat/demo`.
2. Select `Execution mode = live provider draft, DeepSeek primary, Kimi fallback`.
3. Select a mode: `chat_lite`, `research`, `project`, or `tutor`.
4. Ask a project-governance or release-readiness question.
5. Inspect:
   1. Energy Card
   2. final answer
   3. visible execution audit
   4. retrieved evidence
   5. provider metadata
   6. fixed benchmark evidence
6. Open Streamlit if a cleaner product walkthrough is needed.

## Main API paths

```text
GET  /health
GET  /metrics
GET  /energy-chat/demo
POST /energy-chat/rag/search
POST /energy-chat/chat
POST /energy-chat/chat/live
POST /energy-chat/evaluate
POST /energy-chat/evaluate/repair-once
GET  /energy-chat/benchmark/fixed
GET  /energy-chat/benchmark/fixed/report
POST /energy-chat/benchmark/deepseek-energy-aware
```

## Execution modes

| Mode | Calls provider? | Purpose | Claim boundary |
| --- | ---: | --- | --- |
| deterministic `/energy-chat/chat` | no | CI-safe proof path with deterministic draft, critics, scoring, repair, and Energy Card | local evaluator proof only |
| live `/energy-chat/chat/live` | yes | human demo path using DeepSeek primary and Kimi fallback seam | live smoke and product demo, not benchmark superiority |
| fixed benchmark `/energy-chat/benchmark/fixed` | no | committed deterministic benchmark evidence over fixed cases | `measurement_only_no_quality_claim` |
| measurement benchmark `/energy-chat/benchmark/deepseek-energy-aware` | yes | bounded measurement harness for provider outputs | no quality claim without fixed live benchmark review |

## Visible execution audit

The app must show external execution evidence, not hidden chain of thought.

For the current MVP, live mode is expected to show:

```text
provider_draft_calls = 1
critic_llm_calls = 0
repair_llm_calls = 0
```

The system does not run six hidden model calls per question. It uses one provider draft call, deterministic RAG, deterministic critics, deterministic scoring, deterministic decider, and optional deterministic repair.

## Fixed benchmark evidence

Committed evidence files:

```text
evals/energy_chat/fixed_benchmark_cases.jsonl
evals/energy_chat/fixed_benchmark_result.json
docs/energy_aware_chat_fixed_benchmark_report.md
```

Routes exposing that evidence:

```text
GET /energy-chat/benchmark/fixed
GET /energy-chat/benchmark/fixed/report
```

Known local result from the accepted evidence checkpoint:

```json
{
  "run_id": "energy-chat-fixed-benchmark-local",
  "cases_total": 5,
  "accepted_baseline": 0,
  "accepted_after_repair": 4,
  "claim_status": "measurement_only_no_quality_claim"
}
```

This demonstrates deterministic repair behavior on fixed cases. It does not prove that the live provider version improves over plain DeepSeek.

## Validation commands

Run the Energy Chat gate:

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh
```

Check exact CI proof:

```bash
cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

Current accepted proof before this landing page was added:

```text
branch=EACHAT
sha=7376718
browser demo fixed benchmark visible=true
Energy Chat validation gate=success
claim_status=measurement_only_no_quality_claim
```

## Allowed claims

Allowed:

```text
Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.
```

Allowed:

```text
Energy Aware Chat has deterministic benchmark evidence, visible Energy Card decisions, live DeepSeek draft path, Kimi fallback seam, and CI-proven validation gates.
```

Forbidden:

```text
Energy Aware Chat is production ready.
```

Forbidden:

```text
Energy Aware Chat has proven quality improvement over plain DeepSeek.
```

Forbidden:

```text
Energy Aware Chat beats frontier models.
```

## Final-project readiness summary

| Requirement | Current status | Evidence |
| --- | --- | --- |
| FastAPI AI service | pass | `/energy-chat/*`, `/health`, `/docs` |
| frontend/client | pass | `/energy-chat/demo`, `energy_chat_streamlit_app.py` |
| RAG pipeline | partial-pass | deterministic project-source RAG; persistent vector search remains future hardening |
| agent layer | pass for MVP | retrieval agent, live draft agent, critic, decider, repair trace |
| documented evals | pass for deterministic benchmark | fixed benchmark JSONL, result JSON, Markdown report |
| deployment evidence | partial | local deployment smoke docs; public URL or final video still needed |
| CI/CD | pass for branch validation | Energy Aware Chat CI |
| benchmark claim | measurement only | `measurement_only_no_quality_claim` |

## Next best improvements

1. Record the 2 to 3 minute final-project demo video.
2. Add public deployment evidence or preserve the video as the official deployment artifact.
3. Build a fixed live benchmark comparing plain DeepSeek, structured prompt DeepSeek, and energy-aware DeepSeek before any improvement claim.
4. Migrate the Energy Aware Chat landing content into the main README during a careful README cleanup slice.
