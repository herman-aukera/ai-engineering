# EACHAT Final Project Architecture

Status: final-project SDD

## Context

EACHAT preserves the certified Energy-Aware graph and replaces the final-project evidence backend with a real technical-support RAG pipeline using authoritative public documentation, embeddings, PostgreSQL and pgvector.

## Runtime architecture

```text
Official public documentation
(Spring Boot / PostgreSQL / Docker)
             │
             ▼
      curated source manifest
             │
             ▼
 acquisition + HTML normalization
             │
             ▼
      section-aware chunking
             │
             ▼
      OpenAI embeddings
             │
             ▼
 PostgreSQL + pgvector
 metadata + chunks + VECTOR(1536)
             │
             ▼
 HNSW cosine top-k retrieval
             │
             ▼
       ProjectRagResult
             │
             ▼
 interpret → policy → evidence need
             │
             ▼
 candidate → critics → score → decide
             │              │
             │              ├─ repair (bounded)
             │              ├─ clarify
             │              └─ escalate/human
             ▼
 answer + citations + Energy Card + ledger
             │
             ▼
 FastAPI `/energy-chat/v2/*`
```

## Local final-project deployment topology

```text
browser / evaluator
       │
       ▼
Caddy edge :8080
       │
       ▼
EACHAT FastAPI :8000  (internal only)
       │
       ├───────────────┐
       ▼               ▼
PostgreSQL + pgvector  durable EACHAT state
(internal only)        checkpoints/conversations/ownership
       │
       ▼
RAG chunks + vectors
```

`docker-compose.final-project.yml` also includes a one-shot `ingest` service that runs only after PostgreSQL is healthy. EACHAT starts after ingestion succeeds. Only the Caddy edge publishes a host port.
The unexposed service bridge deliberately retains outbound HTTPS because live source
acquisition, embeddings and provider calls require egress.

## Architectural decisions

### Preserve the existing graph

The LangGraph already separates evidence routing, candidate generation, critic evaluation, deterministic scoring/decision, bounded repair, protected human continuation, ledger recording and final projection. Replacing it would add risk without improving rubric coverage.

### Product-local RAG boundary

Final-project retrieval stays under `app.energy_chat`. `app.energy_chat.support_pgvector` owns the native pgvector store and reuses the acquisition/chunking/embedding contracts from `app.energy_chat.support_rag`. Estimator and EACODE runtime modules are not imported.

### Native pgvector rather than JSON vector storage

The live final-project path stores embeddings in a fixed-dimension PostgreSQL `VECTOR` column and executes cosine search in PostgreSQL using `<=>`. An HNSW cosine index is created for the active corpus. This directly satisfies the vector-database/indexing intent while keeping PostgreSQL as the existing durable platform.

### No silent legacy fallback

When `EACHAT_SUPPORT_RAG_ENABLED=true`, missing PostgreSQL, extension capability, embedding configuration or corpus data is an explicit failure. The historical lexical corpus remains only for deterministic compatibility when the feature is disabled.

### Separate ingestion from serving

Acquisition/chunking/document embedding is explicit ingestion. The serving path only creates a query embedding and searches persisted chunks, reducing external calls and request latency.

### Minimal monitoring rather than a new monitoring platform

The production V2 router records safe rolling aggregates for chat requests: request/success/error counts, error rate, mean and p95 wall latency, provider calls, mean provider cost and dispositions. Protected endpoints expose JSON and a small server-rendered dashboard. Prompts, answer bodies, credentials and checkpoint contents are excluded.

## Authority boundaries

- LLM/provider: proposes answer text.
- RAG store: indexed evidence/provenance.
- deterministic critics/policy: disposition and repair budget.
- human: protected continuation/escalation authority.
- PostgreSQL: durable runtime and RAG state.

## Security and claim boundaries

Only allowlisted HTTPS sources are ingested. Credentials are runtime-only. Internal database and EACHAT ports are not published by the final-project Compose topology. Monitoring is authenticated and aggregate-only. Repository implementation is not described as live-verified until the credentialed proof workflow actually succeeds for the exact final SHA.
