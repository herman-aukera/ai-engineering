# EACHAT Final Project — Energy-Aware AI Engineering Support Assistant ⚡

This branch is the LIDR AI Engineering **Final Project** submission.

- Final branch: `finalproject-GG`
- Product: **EACHAT**
- Domain: evidence-grounded L2 support for **Spring Boot + PostgreSQL + Docker**
- Canonical implementation: `estimador-cag/`
- Canonical application entry point: `app.energy_chat.production_app:app`
- Canonical business API surface: `/energy-chat/v2/*`

> Reviewer entry point: read [`estimador-cag/README.md`](estimador-cag/README.md). It contains the complete problem statement, architecture, real-RAG design, agent/orchestration flow, evaluation strategy, run commands, limitations, and evidence boundaries.

## What the final project does

EACHAT is a governed AI support assistant. It does not treat an LLM answer as authority. The final-project path:

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

The final-project corpus is an allowlisted set of official Spring Boot, PostgreSQL, and Docker documentation. The implemented RAG path performs official HTTPS acquisition, HTML normalization, bounded section-aware chunking, embeddings, PostgreSQL persistence, exact cosine top-k retrieval, and injection of retrieved evidence into the existing EACHAT graph.

## Final-project evidence map

Primary reviewer files:

```text
estimador-cag/README.md
estimador-cag/docs/final_project/PRODUCT_SPEC.md
estimador-cag/docs/final_project/ARCHITECTURE.md
estimador-cag/docs/final_project/DATA_AND_RAG_SPEC.md
estimador-cag/docs/final_project/EVALUATION_SPEC.md
estimador-cag/docs/final_project/ACCEPTANCE_AND_EVIDENCE.md
estimador-cag/docs/final_project/LIVE_PROOF_RUNBOOK.md
estimador-cag/docs/final_project/support_source_manifest.json
estimador-cag/evals/energy_chat/final_project_golden.json
estimador-cag/evals/energy_chat/final_project_eval.py
estimador-cag/scripts/ingest_eachat_support_rag.py
estimador-cag/scripts/smoke_eachat_final_project_live.py
```

The fixed evaluation set currently contains **11 cases**, including supported Spring/PostgreSQL/Docker questions, insufficient-evidence clarification, L3 source-code escalation, unsupported Kubernetes escalation, and a current-versus-version-specific source conflict.

## Deterministic validation

From the active project directory:

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

GitHub Actions also checks the production contract, final-project RAG/disposition contracts, keyless HTTP smoke tests, isolated production dependency lock, secret gates, diff hygiene, and immutable supply-chain policy.

## Local FastAPI / browser demonstration

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

## Real RAG / live proof

Real ingestion and retrieval require a PostgreSQL database plus a real embedding credential. The manual GitHub Actions workflow is:

```text
Final Project - Live RAG Proof
```

It is designed to prove, separately from deterministic CI:

```text
real official-source acquisition
→ real embeddings
→ PostgreSQL persistence
→ cross-process retrieval evaluation
→ one bounded live provider answer
→ sanitized evidence artifacts
```

The live run is intentionally not inferred from green deterministic CI.

## Claim boundary

Repository-controlled implementation and deterministic validation are separate from external evidence. Do **not** infer real-corpus ingestion, paid-provider success, public deployment, or production-scale reliability unless the corresponding live artifact exists.

The final submission still requires an externally accessible demonstration path: **public URL or the required 2–3 minute video**, according to the assignment evidence route.

## Historical coursework

This repository also contains earlier LIDR coursework and estimator history. Those materials remain for regression and learning continuity, but they are **not the canonical Final Project surface**. For this branch, the reviewer should start with `estimador-cag/README.md` and `estimador-cag/docs/final_project/`.
