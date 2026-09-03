# EACHAT Final Project Architecture

Status: final-project SDD

## Context

EACHAT preserves the certified Energy-Aware graph and changes the evidence backend from a six-summary lexical baseline into a real, reproducible technical-support RAG pipeline.

## System architecture

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
 PostgreSQL support-rag chunk store
 (content + provenance + vectors)
             │
             ▼
 exact cosine vector retrieval
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
 FastAPI `/energy-chat/v2/*` + browser tester
```

## Architectural decisions

### Preserve the existing graph

The existing LangGraph already separates evidence routing, candidate generation, critic evaluation, deterministic scoring/decision, bounded repair, protected human continuation, ledger recording and final projection. Replacing it would increase deadline risk without improving rubric coverage.

### Product-local RAG boundary

Final-project retrieval is implemented under `app.energy_chat.support_rag`. It must not import Estimator or EACODE runtime modules. The existing `ProjectRagRequest`, `ProjectRagChunk` and `ProjectRagResult` contracts remain the adapter boundary into the graph.

### Persistent exact vector search first

The deadline implementation persists embeddings and provenance in PostgreSQL and computes exact cosine similarity over the bounded corpus. This satisfies a real embeddings + persistent retrieval pipeline without introducing a new production dependency or changing the certified EACHAT lock. Approximate-nearest-neighbour/pgvector indexing is a documented optimization, not a claim.

### No silent legacy fallback

When `EACHAT_SUPPORT_RAG_ENABLED=true`, missing PostgreSQL or embedding configuration is an explicit RAG-unavailable error. The old lexical project corpus remains only for deterministic compatibility when the final-project RAG feature is disabled; it must never masquerade as the final-project production RAG.

### Separate ingestion from serving

Network acquisition and embedding are an explicit ingestion operation. The production request path only embeds the query and searches already-persisted chunks. This reduces latency, cost and external failure modes.

## Authority boundaries

- LLM/provider: proposes answer text only.
- RAG store: authoritative for indexed support evidence and provenance.
- deterministic critics/policy: authoritative for disposition and repair budget.
- human: authoritative for protected continuation/escalation decisions.
- PostgreSQL: authoritative durable state for EACHAT runtime and support corpus.

## Security and claim boundaries

- Only HTTPS sources on allowlisted official hosts are ingested.
- API keys are read from environment/request-scoped BYOK infrastructure and never persisted in corpus records.
- Retrieved evidence exposes provenance but not hidden model reasoning.
- No claim of production-scale support, universal correctness or ANN performance is allowed without evidence.
