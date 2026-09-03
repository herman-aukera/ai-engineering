# EACHAT Final Project Data and RAG Specification

Status: final-project SDD

## Corpus policy

The corpus uses real, public, traceable technical-support sources. V1 is deliberately curated rather than a generic web crawl. Source families are `spring_boot`, `postgresql`, `docker`, with `known_issue` reserved for selected public issues only when they improve a measured support case.

The committed `support_source_manifest.json` is the acquisition allowlist and provenance seed. Full third-party manuals are not committed merely to inflate the repository; ingestion fetches selected official pages reproducibly.

## Provenance per source/chunk

- source id and family
- title and canonical HTTPS URL
- product/framework and product version when known
- retrieval timestamp and section
- content SHA-256 and ingestion version
- embedding model

## Ingestion

```text
manifest
→ validate official host + HTTPS
→ bounded HTML fetch
→ normalize document structure
→ section-aware chunking
→ content hash
→ OpenAI embedding
→ PostgreSQL + pgvector upsert
```

Ingestion uses deterministic chunk ids derived from source id, section, ordinal and content hash. Reingesting the same content updates the active record rather than intentionally duplicating it.

## Chunking

V1 chunks by document section with a bounded word window and overlap. The purpose is to retain diagnostic context while producing focused evidence units. Corpus size is not itself a grading target; representative authoritative coverage plus measurable retrieval is preferred over an uncontrolled crawl.

## Embeddings

Canonical live embedding model: `text-embedding-3-small`, default dimensions `1536`. The implementation uses the existing OpenAI SDK. Deterministic tests inject fake embeddings and CI never requires paid embedding calls.

Runtime configuration:

```text
EACHAT_SUPPORT_EMBEDDING_API_KEY
EACHAT_SUPPORT_EMBEDDING_MODEL=text-embedding-3-small
EACHAT_SUPPORT_EMBEDDING_DIMENSIONS=1536
```

## Storage and vector index

The final-project production RAG uses PostgreSQL with the `vector` extension. `app.energy_chat.support_pgvector.PgvectorSupportRagStore` creates `eachat_support_pgvector_chunks` with provenance, chunk content and a fixed-dimension `VECTOR` column.

The store creates an HNSW cosine index:

```text
idx_eachat_support_pgvector_hnsw
USING hnsw (embedding vector_cosine_ops)
```

The local final-project topology uses the pinned `pgvector/pgvector:pg16` image. External production PostgreSQL must have permission to provision the `vector` extension or have it pre-provisioned by the database operator.

## Retrieval

```text
question
→ query embedding
→ pgvector cosine search (`<=>`)
→ top-k active chunks
→ ProjectRagResult evidence refs
→ EACHAT candidate provider
→ critics / deterministic disposition
```

Canonical live strategy name:

```text
openai_embedding_postgres_pgvector_cosine_support_rag
```

Every result maps back to a canonical source URL through its source id and committed manifest.

## Compatibility boundary

`app.energy_chat.support_rag.SupportRagService` remains as a deterministic/in-memory seam and historical exact-cosine implementation used by focused tests. The old six-summary lexical project RAG also remains available only when `EACHAT_SUPPORT_RAG_ENABLED` is disabled.

When `EACHAT_SUPPORT_RAG_ENABLED=true`, `app.energy_chat.rag.retrieve_project_context` routes to the pgvector-backed final-project service. It must not silently fall back to the historical lexical corpus.

## Version and freshness

- product version is retained when available;
- `retrieved_at` records acquisition time;
- current and versioned sources are not silently conflated;
- an explicitly version-specific question must clarify if no matching authoritative source exists;
- external/current facts outside the indexed corpus keep EACHAT's external-evidence boundary.

## Failure semantics

With final-project RAG enabled, missing database configuration, missing embedding credentials, empty corpus, source-acquisition failure or vector-dimension mismatch are explicit failures. Unsupported questions clarify/refuse/escalate according to the product policy; no missing evidence is replaced with invented diagnosis.
