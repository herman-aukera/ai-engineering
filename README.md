# EACHAT Final Project — Energy-Aware AI Engineering Support Assistant ⚡

This branch is the LIDR AI Engineering **Final Project** submission.

- Final branch: `finalproject-GG`
- Product: **EACHAT**
- Domain: evidence-grounded L2 support for **Spring Boot + PostgreSQL + Docker**
- Canonical implementation: `estimador-cag/`
- Production entry point: `app.energy_chat.production_app:app`
- Business API: `/energy-chat/v2/*`

> Reviewer entry point: [`estimador-cag/README.md`](estimador-cag/README.md) contains the complete problem statement, architecture, real-RAG design, orchestration, evaluation, monitoring, deployment instructions, limitations and claim boundaries.

## Product flow

```text
support question
    ↓
request policy + evidence need
    ↓
real technical-support RAG
    ↓
answer candidate
    ↓
deterministic critics
    ↓
Energy score + disposition
    ↓
accept | repair | clarify | reject | refuse | escalate
    ↓
Energy Card + Decision Ledger + safe trace
```

## Real RAG

The final-project corpus is an allowlisted set of 16 official Spring Boot, PostgreSQL and Docker documentation pages. The live path performs:

```text
official HTTPS acquisition
→ section-aware chunking
→ text-embedding-3-small
→ PostgreSQL VECTOR(1536)
→ HNSW cosine index
→ native pgvector top-k retrieval
→ ProjectRagResult evidence
→ governed EACHAT graph
```

The historical six-summary lexical project RAG remains only as a deterministic compatibility path when final-project support RAG is disabled.

## Production/container topology

`docker-compose.final-project.yml` adapts the teacher's Dockerization intent to the actual EACHAT product without adding an artificial Rails layer:

```text
browser / evaluator
       ↓
Caddy :8080              public edge
       ↓
EACHAT FastAPI :8000     internal only
       ↓
PostgreSQL + pgvector    internal + persistent
```

A one-shot ingestion container populates the real vector corpus after PostgreSQL becomes healthy and before EACHAT starts. `scripts/smoke_eachat_final_project_compose.py` is the explicit live end-to-end/restart-persistence proof path.

## Golden set and evaluation

The fixed evaluation set contains **11 cases** covering supported Spring Boot/PostgreSQL/Docker support, cross-domain diagnosis, insufficient-evidence clarification, version/source conflict, L3 source-code escalation and unsupported Kubernetes escalation.

Evaluation is intentionally split:

- deterministic CI: contracts, RAG seams, dispositions, regressions, monitoring and Compose syntax;
- persisted retrieval: `estimador-cag/evals/energy_chat/final_project_eval.py`;
- full live system: `estimador-cag/evals/energy_chat/final_project_system_eval.py`;
- bounded one-answer proof: `estimador-cag/scripts/smoke_eachat_final_project_live.py`.

The live system report measures disposition/clarification/escalation accuracy, retrieval/evidence presence, error rate, mean/p95 latency, provider calls and cost. Semantic unsupported-claim rate is not invented without a fixed judge.

## Monitoring

Authenticated reviewer endpoints:

```text
GET /energy-chat/v2/monitoring
GET /energy-chat/v2/monitoring/dashboard
```

They expose safe rolling aggregates: request/success/error counts, error rate, mean/p95 latency, mean provider cost, provider-call count and disposition counts. Prompts, answer bodies, credentials and checkpoint contents are excluded.

## Evidence map

Primary reviewer files:

```text
estimador-cag/README.md
estimador-cag/docs/final_project/PRODUCT_SPEC.md
estimador-cag/docs/final_project/ARCHITECTURE.md
estimador-cag/docs/final_project/DATA_AND_RAG_SPEC.md
estimador-cag/docs/final_project/EVALUATION_SPEC.md
estimador-cag/docs/final_project/EVALUATION.md
estimador-cag/docs/final_project/DEPLOYMENT_LOCAL.md
estimador-cag/docs/final_project/ACCEPTANCE_AND_EVIDENCE.md
estimador-cag/docs/final_project/LIVE_PROOF_RUNBOOK.md
estimador-cag/docs/final_project/support_source_manifest.json
estimador-cag/evals/energy_chat/final_project_golden.json
```

## Deterministic validation

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test uv run pytest -q
bash scripts/validate_energy_chat.sh
```

Focused final-project contracts:

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q tests/test_eachat_final_project_*.py
```

Green deterministic CI proves repository-controlled contracts only. It does not prove paid-provider success, current real-source acquisition or public deployment.

## Manual real-data/live proof

Run GitHub Actions workflow:

```text
Final Project - Live RAG Proof
```

For the exact selected SHA it is designed to prove:

```text
16 real official sources
→ real embeddings
→ PostgreSQL/pgvector persistence
→ retrieval evaluation
→ one bounded live answer
→ full 11-case live evaluation
→ sanitized evidence artifacts
```

The workflow is manual-only so normal pushes never spend provider budget.

## Claim boundary and final external requirement

Repository-controlled implementation is now designed to cover FastAPI, real-data ingestion, embeddings, pgvector/indexed retrieval, LangGraph/critics, golden-set evaluation, monitoring and reproducible container deployment. Those features remain **LIVE-READY rather than LIVE-VERIFIED** until the corresponding external commands/workflow actually succeed for the final SHA.

The assignment separately requires an accessible demonstration path: **public URL or the required 2–3 minute video**. That external evidence is not inferred from CI.

## Historical coursework

Earlier Estimator/LIDR coursework remains in the repository for regression and learning continuity but is not the canonical Final Project surface.
