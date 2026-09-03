# EACHAT Final Project — Energy-Aware AI Engineering Support Assistant ⚡

`finalproject-GG` turns the existing EACHAT governance architecture into a concrete AI Engineering final project: an evidence-grounded L2 support assistant for engineers operating Spring Boot services backed by PostgreSQL and deployed with Docker.

The product does not try to guess an incident root cause from thin air. It retrieves bounded official technical evidence, generates an answer candidate, critiques that candidate, applies deterministic Energy/disposition policy, repairs once when justified, and clarifies or escalates when evidence or authority is insufficient.

## Final-project problem

L2 support engineers routinely receive incomplete incident descriptions such as connection failures, unhealthy Spring Boot services, containers that exit after startup, or suspected database contention. A generic LLM can produce plausible but unsupported certainty. EACHAT instead treats support as a governed evidence workflow.

Supported V1 domain:

- Spring Boot startup, external configuration, profiles, Actuator, health/readiness, REST/runtime symptoms;
- PostgreSQL connections, sessions, locks, transactions, slow-query symptoms and monitoring;
- Docker container state, logs, ports/networking, environment configuration, volumes and health checks;
- diagnostic use of logs, Actuator endpoints, health/readiness, metrics and PostgreSQL monitoring views.

Explicitly out of scope include Santander/proprietary systems, customer or payment support, cybersecurity incident response, Kubernetes, Kafka, frontend/mobile work, arbitrary business-domain logic and arbitrary source-code repair. Source-code remediation is an L3/EACODE/human-engineering escalation, not an EACHAT execution claim.

## Architecture

```text
support question
    ↓
request policy + evidence need
    ↓
real support RAG
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

The provider is a proposal mechanism, never the authority boundary. Deterministic code owns hard constraints, evidence requirements, retry budgets and final machine disposition. Protected continuation remains bound to authenticated human authority.

Canonical application entry point:

```text
app.energy_chat.production_app:app
```

Canonical production business APIs are under `/energy-chat/v2/*`. Representative routes include:

```text
POST /energy-chat/v2/chat
POST /energy-chat/v2/chat/live
GET  /energy-chat/v2/threads/{thread_id}/state
GET  /energy-chat/v2/demo
```

`/health`, `/ready` and `/version` are keyless operational probes. Protected business APIs require signed actor identity.

## Real final-project RAG

The final-project RAG is separate from the historical deterministic lexical project-RAG compatibility path.

Source authority is committed in:

```text
docs/final_project/support_source_manifest.json
```

The manifest currently contains 16 curated HTTPS pages from official Spring Boot, PostgreSQL and Docker documentation. The ingestion path performs:

```text
allowlisted official HTTPS acquisition
→ HTML normalization
→ section-aware bounded chunking
→ OpenAI embedding adapter
→ PostgreSQL persistence
→ exact cosine top-k retrieval
→ ProjectRagResult evidence
→ existing EACHAT graph
```

Implementation:

```text
app/energy_chat/support_rag.py
scripts/ingest_eachat_support_rag.py
```

The current implementation deliberately uses exact cosine retrieval over persisted vectors rather than claiming pgvector/HNSW or ANN optimization. That optimization is not required for this bounded final-project corpus.

### RAG runtime configuration

Real ingestion/retrieval requires a PostgreSQL database and a real embedding credential:

```bash
export EACHAT_SUPPORT_RAG_DATABASE_URL='postgresql://...'
export EACHAT_SUPPORT_EMBEDDING_API_KEY='...'
export EACHAT_SUPPORT_RAG_ENABLED=true
```

`EACHAT_POSTGRES_URL` may be used as the database fallback and `OPENAI_API_KEY` as the embedding-key fallback. The default embedding model is `text-embedding-3-small` unless `EACHAT_SUPPORT_EMBEDDING_MODEL` is explicitly set.

Never commit credentials. Use runtime secret injection.

### Ingest the curated corpus

```bash
cd estimador-cag
uv run python scripts/ingest_eachat_support_rag.py
```

This command fetches the allowlisted source pages, chunks them, creates embeddings and persists the active chunks. A successful command is live evidence only for the environment in which it was actually executed; deterministic CI does not substitute for it.

### Evaluate real retrieval

```bash
cd estimador-cag
uv run python evals/energy_chat/final_project_eval.py
```

The default report is written to:

```text
evals/energy_chat/final_project_retrieval_report.json
```

The current evaluator measures retrieval hit-at-k only. It intentionally does not pretend that expected disposition fixtures were executed or that unsupported-claim quality was measured by the retrieval script.

## Golden evaluation set

The fixed final-project cases are in:

```text
evals/energy_chat/final_project_golden.json
```

They cover Spring Boot health/configuration, PostgreSQL connections/locks, Docker runtime/networking, a cross-domain health/database incident, insufficient diagnostic evidence, the L3 source-code boundary and unsupported Kubernetes scope.

Mandatory deterministic regressions include:

- a request for the exact PostgreSQL root cause while explicitly providing no logs/error message must `clarify`, not fabricate certainty;
- a request to patch Java source must `escalate` beyond L2 authority;
- Kubernetes diagnosis/mutation must `escalate` as unsupported final-project scope.

These governance regressions are executable in:

```text
tests/test_eachat_final_project_dispositions.py
```

## Deterministic validation

CI must remain keyless and reproducible. Run locally with sentinel provider credentials:

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test uv run pytest -q
```

Focused final-project contracts:

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q tests/test_eachat_final_project_*.py
```

Full EACHAT deterministic gate:

```bash
cd estimador-cag
bash scripts/validate_energy_chat.sh
```

Production-contract checks:

```bash
cd estimador-cag
uv run pytest -q \
  tests/test_eachat_session15_production_contract.py \
  tests/test_eachat_ci_contract.py \
  tests/smoke/test_eachat_production_smoke.py
uv run python scripts/session15_eachat_production_contract.py
```

GitHub Actions additionally verifies the isolated production dependency lock, secret scanning and `git diff --check`. Deterministic green CI proves repository-controlled contracts; it does not prove paid-provider success, public deployment or live corpus ingestion.

## Local API and browser shell

A keyless development composition can start the production transport with process-local state:

```bash
cd estimador-cag
LANGGRAPH_STRICT_MSGPACK=true \
EACHAT_ALLOW_IN_MEMORY=true \
EACHAT_SESSION_SIGNING_KEY='local-development-signing-key-at-least-32-bytes' \
EACHAT_V2_ENABLED=true \
uv run uvicorn app.energy_chat.production_app:app --host 0.0.0.0 --port 8000
```

Then inspect:

```text
http://localhost:8000/health
http://localhost:8000/ready
http://localhost:8000/version
http://localhost:8000/energy-chat/v2/demo
```

The browser shell does not fake a production login/OIDC system. Protected business calls require signed identity. Durable production composition additionally requires PostgreSQL-backed ownership/checkpoints and encrypted conversation memory.

## Production-state boundaries inherited from EACHAT

EACHAT retains the certified architecture on which the final project was based:

- signed actor and tenant ownership;
- PostgreSQL-backed strict LangGraph checkpoints in durable mode;
- encrypted conversation memory;
- replay-safe protected human continuation;
- bounded provider routing and BYOK isolation;
- neutral `energy-aware.event.v1` operational telemetry;
- isolated production dependency lock and non-root image contract.

Those controls are valuable engineering evidence, but they do not turn this educational final-project branch into a claim of real-world production readiness.

## Historical coursework compatibility

The repository still carries historical LIDR coursework and regression tests. These contracts are retained as compatibility evidence; they are not the canonical final-project production surface.

### Session 04 Live Plus

The historical Session 04 Live Plus estimator used a typed product request and Structured JSON output with deterministic validation. Its documented provider fallback ladder was:

```text
DeepSeek flash → DeepSeek pro → Kimi 2.5 backup → Kimi 2.6 backup_pro
```

Historical cache semantics were explicit: Exact Redis cache runs before semantic cache. Semantic cache shadow mode observed candidates without serving them. Responses exposed `requested_tier`, `served_tier`, `fallback_used`, `semantic_cache_mode`, and `semantic_candidate_found` as troubleshooting evidence.

### Session 05 memory and attachments

Session 05 added conversational memory and document attachment support to the historical coursework application through:

```text
POST /sessions
POST /sessions/{session_id}/estimate
```

It retained `project_metadata` beside `ConversationHistory`, used a bounded sliding window, accepted attachment requests through `multipart/form-data`, parsed PDF content with `pypdf`, and parsed DOCX with `python-docx`.

The historical Streamlit path exposed **New conversation**, **Project metadata**, PDF and DOCX attachment controls, and supported `ESTIMADOR_BACKEND_URL` for the backend address.

These Session 04 and Session 05 contracts remain regression-tested coursework evidence and are not mounted as canonical `/energy-chat/v2/*` final-project APIs.

## Submission evidence and claim boundary

Repository-controlled implementation now covers the final-project SDD, curated source manifest, ingestion/chunking/embedding/storage/retrieval code, golden set, deterministic RAG contracts and deterministic L2 disposition regressions.

The following remain separate live/external evidence classes and must not be inferred from CI:

- successful acquisition of the current 16-source corpus in the final demonstration environment;
- real embedding generation and persisted PostgreSQL chunk counts;
- the measured real-corpus retrieval report;
- a bounded live answer path using real external services where required;
- a public URL or the required 2–3 minute demonstration video.

Until those artifacts exist, the correct status is **implementation complete for the repository-controlled slice, final submission evidence still pending** rather than “production-ready”.

## Final-project SDD

- `docs/final_project/PRODUCT_SPEC.md`
- `docs/final_project/ARCHITECTURE.md`
- `docs/final_project/DATA_AND_RAG_SPEC.md`
- `docs/final_project/EVALUATION_SPEC.md`
- `docs/final_project/ACCEPTANCE_AND_EVIDENCE.md`
- `docs/final_project/support_source_manifest.json`

Shared inherited architecture references remain under `docs/`, including `ENERGY_AWARE_PROTOCOL_V1.md`, security/operations/release documentation and the product manifest.
