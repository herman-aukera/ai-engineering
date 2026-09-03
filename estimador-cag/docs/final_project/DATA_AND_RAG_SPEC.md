# EACHAT Final Project Data and RAG Specification

Status: final-project SDD

## Corpus policy

The corpus uses real, public, traceable technical-support sources. V1 is deliberately curated rather than a generic web crawl.

Source families:

- `spring_boot`: official Spring Boot reference documentation.
- `postgresql`: official PostgreSQL current documentation.
- `docker`: official Docker documentation.
- `known_issue`: selected resolved Spring Boot GitHub issues may be added only when they improve a measured support case.

The committed `support_source_manifest.json` is the acquisition allowlist and provenance seed. Full third-party manuals are not committed merely to inflate the repository; ingestion fetches the selected pages reproducibly.

## Required provenance per source/chunk

- source id
- source family
- title
- canonical HTTPS URL
- product/framework
- product version when known
- retrieval timestamp
- section
- content SHA-256
- ingestion version
- embedding model

## Ingestion

```text
manifest
→ validate official host + HTTPS
→ fetch HTML with bounded size/time
→ remove scripts/styles/navigation noise
→ preserve heading/paragraph structure
→ normalize whitespace
→ section-aware chunking
→ content hash
→ OpenAI embedding
→ PostgreSQL upsert
```

Ingestion is idempotent by deterministic chunk id. Reingesting the same content updates metadata without creating duplicate chunks.

## Chunking

V1 chunks by document section and bounded text size. A chunk must remain large enough to preserve diagnostic context but small enough to retrieve a focused procedure. Chunk ids are stable hashes of source id + section + ordinal + content hash.

Target corpus guidance: roughly 50–150 source pages and 300–2,000 chunks when time permits. The deadline acceptance criterion is representative coverage and measurable retrieval quality, not a vanity count.

## Embeddings

Canonical production embedding model for this branch: `text-embedding-3-small`, using the already-supported OpenAI SDK. Tests inject deterministic fake embeddings; deterministic CI must not make paid provider calls.

## Storage

PostgreSQL table `eachat_support_rag_chunks` stores chunk text, provenance metadata and embedding JSON. Metadata indexes cover active status, source family and source id. V1 retrieval loads the bounded active candidate set and computes exact cosine similarity in Python.

This is intentionally not described as pgvector/ANN retrieval. Adding pgvector/HNSW is a post-deadline performance optimization after measured need.

## Retrieval

```text
question
→ query embedding
→ active persisted chunks
→ exact cosine score
→ deterministic tie-break by chunk id
→ top-k chunks
→ ProjectRagResult
→ EACHAT candidate provider
```

Every result maps back to an official canonical URL through the source manifest/provenance record.

## Version and freshness

- Source version is retained when the documentation exposes it.
- `retrieved_at` records acquisition time.
- The manifest distinguishes versioned/current URLs.
- Conflicting versions must not be silently fused; when the user gives a version, retrieval/evaluation should prefer matching metadata where available.
- Questions requiring facts newer than the indexed corpus keep EACHAT's `external_required` boundary and must not be answered as if the index were live web search.

## Failure semantics

With final-project RAG enabled:

- missing DB URL → explicit configuration error;
- missing embedding credential → explicit configuration/provider error;
- empty corpus → explicit evidence-unavailable result/error;
- acquisition failure → source-level ingestion failure with no fabricated content;
- unsupported/out-of-scope question → clarification/escalation, not invented diagnosis.
