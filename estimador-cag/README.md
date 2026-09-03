# EACHAT Final Project — Energy-Aware AI Engineering Support Assistant ⚡

`finalproject-GG` is an evidence-grounded L2 support assistant for engineers operating Spring Boot services backed by PostgreSQL and deployed with Docker. It retrieves authoritative support evidence, generates a candidate, runs critics, applies deterministic Energy/disposition policy, repairs when justified, and clarifies or escalates when evidence or authority is insufficient.

## Problem and scope

Supported V1: Spring Boot startup/configuration/Actuator/health/runtime symptoms; PostgreSQL connections/sessions/locks/transactions/query symptoms; Docker container state/logs/networking/environment/volumes/health; and observability-driven diagnosis.

Out of scope: Santander/proprietary systems, customer/payment support, cybersecurity incident response, Kubernetes, Kafka, frontend/mobile work, arbitrary business logic and arbitrary source-code repair. Source-code remediation is an L3/EACODE/human-engineering escalation.

## Architecture

```text
support question
    ↓
request policy + evidence need
    ↓
real support RAG (OpenAI embeddings + PostgreSQL/pgvector/HNSW)
    ↓
answer candidate
    ↓
deterministic critic panel
    ↓
Energy score + deterministic disposition
    ↓
accept | repair | clarify | reject | refuse | escalate
    ↓
Energy Card + Decision Ledger + safe trace
```

Canonical application entry point: `app.energy_chat.production_app:app`. Canonical business APIs are under `/energy-chat/v2/*`; `/health`, `/ready` and `/version` are operational probes. Protected business and monitoring routes require signed actor identity.

## Real final-project RAG

The source manifest is `docs/final_project/support_source_manifest.json` and currently contains 16 curated HTTPS pages from official Spring Boot, PostgreSQL and Docker documentation.

```text
allowlisted official HTTPS acquisition
→ HTML normalization
→ section-aware bounded chunking
→ text-embedding-3-small
→ PostgreSQL VECTOR(1536)
→ HNSW cosine index
→ native pgvector top-k search
→ ProjectRagResult evidence
→ existing EACHAT graph
```

Primary implementation:

```text
app/energy_chat/support_rag.py          acquisition/chunking/embedding contracts
app/energy_chat/support_pgvector.py     native pgvector store/retrieval
scripts/ingest_eachat_support_rag.py    reproducible ingestion
evals/energy_chat/final_project_eval.py persisted retrieval evaluation
```

With `EACHAT_SUPPORT_RAG_ENABLED=true`, the graph routes to the pgvector-backed support RAG. The historical lexical project corpus remains only as an explicit deterministic compatibility path when final-project RAG is disabled.

Runtime variables:

```bash
export EACHAT_SUPPORT_RAG_DATABASE_URL='postgresql://...'
export EACHAT_SUPPORT_EMBEDDING_API_KEY='...'
export EACHAT_SUPPORT_EMBEDDING_MODEL='text-embedding-3-small'
export EACHAT_SUPPORT_EMBEDDING_DIMENSIONS='1536'
export EACHAT_SUPPORT_RAG_ENABLED=true
```

Never commit credentials.

## Golden evaluation and live system evaluation

The fixed 11-case set is `evals/energy_chat/final_project_golden.json`. It covers supported Spring Boot/PostgreSQL/Docker cases, a cross-domain incident, version/source conflict, insufficient evidence, L3 source-code escalation and unsupported Kubernetes scope.

Deterministic regressions require:

- no evidence + demand exact root cause → `clarify`;
- Spring Boot 2.7.18 against current-only evidence → `clarify`;
- request to patch Java source → `escalate`;
- Kubernetes diagnosis/mutation → `escalate`.

After real ingestion, retrieval evaluation is:

```bash
cd estimador-cag
uv run python evals/energy_chat/final_project_eval.py --k 5
```

The full real-provider golden-set evaluation is manual/live only:

```bash
cd estimador-cag
uv run python evals/energy_chat/final_project_system_eval.py \
  --live --provider openai --effort balanced
```

It records disposition/clarification/escalation accuracy, graph-retained retrieval evidence, error rate, mean/p95 latency, provider calls and cost. It does not fabricate semantic unsupported-claim scores without a fixed judge.

## Monitoring

Protected endpoints:

```text
GET /energy-chat/v2/monitoring
GET /energy-chat/v2/monitoring/dashboard
```

They expose aggregate request/success/error counts, error rate, mean/p95 wall latency, mean provider cost, provider-call count and disposition counts. Prompts, answer bodies, credentials and checkpoint contents are excluded.

## Reproducible final-project container stack

From repository root, `docker-compose.final-project.yml` provides:

```text
Caddy public edge :8080
        ↓
EACHAT FastAPI :8000 (internal)
        ↓
PostgreSQL + pgvector (internal + persistent volume)
```

A one-shot `ingest` service populates the vector corpus before EACHAT starts. Details: `docs/final_project/DEPLOYMENT_LOCAL.md`.

With a real embedding credential:

```bash
EACHAT_SUPPORT_EMBEDDING_API_KEY="$EACHAT_SUPPORT_EMBEDDING_API_KEY" \
docker compose -f docker-compose.final-project.yml up -d --build
```

Automated app-restart/RAG-persistence proof:

```bash
cd estimador-cag
EACHAT_SUPPORT_EMBEDDING_API_KEY="$EACHAT_SUPPORT_EMBEDDING_API_KEY" \
uv run python scripts/smoke_eachat_final_project_compose.py --cleanup
```

The local Compose defaults for DB password, encryption key and session-signing key are development-only and must not be reused for an internet-facing deployment.

## Deterministic validation

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test uv run pytest -q
bash scripts/validate_energy_chat.sh
```

Focused final-project contracts:

```bash
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q tests/test_eachat_final_project_*.py
```

Deterministic CI remains keyless. It validates final-project contracts, compileability, Compose syntax, production smokes, isolated production dependency lock, secret scanning and diff hygiene. A green deterministic run does not imply live acquisition/provider success.

## Manual real-data proof

GitHub Actions workflow: `Final Project - Live RAG Proof` (`.github/workflows/final-project-live-rag.yml`). It is `workflow_dispatch` only and is designed to prove, for the exact selected SHA:

```text
16 real official sources
→ real embeddings
→ PostgreSQL/pgvector persistence
→ retrieval report
→ one bounded live answer
→ full 11-case live system evaluation
→ sanitized artifacts
```

Runbook: `docs/final_project/LIVE_PROOF_RUNBOOK.md`. Recommended first run: `provider=openai`, `effort=balanced`.

## Local process-only demo

For a keyless transport demo without durable RAG:

```bash
cd estimador-cag
LANGGRAPH_STRICT_MSGPACK=true \
EACHAT_ALLOW_IN_MEMORY=true \
EACHAT_SESSION_SIGNING_KEY='local-development-signing-key-at-least-32-bytes' \
EACHAT_V2_ENABLED=true \
uv run uvicorn app.energy_chat.production_app:app --host 0.0.0.0 --port 8000
```

Then inspect `/health`, `/ready`, `/version`, and `/energy-chat/v2/demo`.

## Production-state boundaries inherited from EACHAT

EACHAT retains signed actor/tenant ownership, strict PostgreSQL-backed LangGraph checkpoints in durable mode, encrypted conversation memory, replay-safe protected human continuation, bounded provider routing/BYOK isolation, operational telemetry, and an isolated non-root production image. These are engineering controls, not claims of production-scale reliability.

## Final-project documentation

- `docs/final_project/PRODUCT_SPEC.md`
- `docs/final_project/ARCHITECTURE.md`
- `docs/final_project/DATA_AND_RAG_SPEC.md`
- `docs/final_project/EVALUATION_SPEC.md`
- `docs/final_project/EVALUATION.md`
- `docs/final_project/DEPLOYMENT_LOCAL.md`
- `docs/final_project/ACCEPTANCE_AND_EVIDENCE.md`
- `docs/final_project/LIVE_PROOF_RUNBOOK.md`
- `docs/final_project/support_source_manifest.json`

## Historical coursework compatibility

Historical Estimator coursework remains in this repository because its regression tests protect earlier course deliverables; it is not the canonical Final Project product surface.

### Session 04 Live Plus

The historical Session 04 Live Plus path used **Structured JSON output** with deterministic validation and the documented provider fallback ladder:

```text
DeepSeek flash → DeepSeek pro → Kimi 2.5 backup → Kimi 2.6 backup_pro
```

**Exact Redis cache runs before semantic cache.** **Semantic cache shadow mode** observes semantic candidates without serving them. Historical responses expose `requested_tier`, `served_tier`, `fallback_used`, `semantic_cache_mode`, and `semantic_candidate_found` for troubleshooting and class-defense evidence.

### Session 05 memory and attachments

Historical Session 05 added conversation memory and attachment support through:

```text
POST /sessions
POST /sessions/{session_id}/estimate
```

It retains `project_metadata` alongside `ConversationHistory`, uses a bounded sliding window, accepts attachments as `multipart/form-data`, parses PDF files with `pypdf`, and DOCX files with `python-docx`.

The historical Streamlit interface includes **New conversation**, **Project metadata**, PDF and DOCX controls, and supports `ESTIMADOR_BACKEND_URL` for the backend address.

These Session 04/05 contracts remain regression evidence only; they are not mounted as canonical `/energy-chat/v2/*` Final Project APIs.

## Submission claim boundary

Repository-controlled implementation covers the concrete domain, real-data manifest, ingestion/chunking/embeddings, native pgvector/index/retrieval path, governed graph, golden set, deterministic regressions, live evaluation harness, monitoring and reproducible local container topology.

Still separate external evidence until actually produced for the final SHA: live source acquisition, real embedding/vector counts, measured live reports, local/full deployment smoke, and the assignment's public URL **or** required 2–3 minute video. The correct status before those artifacts exist is **LIVE-READY**, not production-ready or submission-complete.
