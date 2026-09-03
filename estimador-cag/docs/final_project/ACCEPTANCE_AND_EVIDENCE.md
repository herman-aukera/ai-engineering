# EACHAT Final Project Acceptance and Evidence Matrix

Status: live final-project gate

| Official requirement | Implementation target | Required evidence | Current status |
|---|---|---|---|
| Concrete domain | L2 Spring Boot/PostgreSQL/Docker support | Product spec + README | IMPLEMENTED |
| Real data | 16 curated official public documentation pages | Source manifest + live ingestion report | MANIFEST DONE / LIVE ACQUISITION PENDING |
| FastAPI | `app.energy_chat.production_app:app` | `/health`, `/ready`, `/version`, business-route smoke | IMPLEMENTED / EXACT-HEAD CI REQUIRED |
| RAG ingestion | `app.energy_chat.support_rag` + ingestion script | deterministic tests + live ingestion report | IMPLEMENTED / LIVE PROOF PENDING |
| Chunking | section-aware bounded support chunker | deterministic tests + live chunk counts | IMPLEMENTED / LIVE COUNTS PENDING |
| Embeddings | OpenAI embedding adapter with fake CI seam | deterministic adapter contract + bounded live proof | IMPLEMENTED / LIVE PROOF PENDING |
| Persistent/indexed storage | PostgreSQL support chunk store | store contract + live DB proof | IMPLEMENTED / LIVE DB PROOF PENDING |
| Retrieval | exact cosine top-k adapter into `ProjectRagResult` | deterministic retrieval tests + real-corpus report | IMPLEMENTED / REAL REPORT PENDING |
| Agent/orchestration | existing EACHAT LangGraph | graph tests + trace | IMPLEMENTED / EXACT-HEAD CI REQUIRED |
| Mandatory dispositions | clarify insufficient diagnostics/version conflicts; escalate L3/unsupported scope | final-project graph regression tests | IMPLEMENTED / EXACT-HEAD CI REQUIRED |
| Evals | 11-case golden set + retrieval runner | report + disposition/regression evidence | FIXTURES/RUNNER DONE / LIVE METRICS PENDING |
| README | reviewer-first final-project README | reviewer inspection | IMPLEMENTED |
| Deployment evidence | public URL OR 2–3 minute video | externally accessible link | EXTERNAL BLOCKER |
| Final branch | `finalproject-GG` | Git ref | DONE |
| No secrets | existing secret gates | exact-head CI/diff scan | EXACT-HEAD CI REQUIRED |

## Existing reusable evidence

The branch was created directly from certified EACHAT commit `c303c0d7d5c12682a88e195bd38a8d5833ded8b5`. Historical certification run `32661638856` was successful for that exact source commit. This proves the inherited repository-controlled baseline only; every final-project commit must be revalidated.

The final-project branch adds repository-controlled evidence for:

- a concrete L2 support domain and authority boundary;
- a committed allowlisted real-source manifest;
- bounded official-HTML acquisition;
- section-aware chunking;
- an injectable real embedding adapter;
- persistent PostgreSQL support-chunk storage;
- exact cosine retrieval into the existing `ProjectRagResult` contract;
- deterministic no-silent-fallback behavior when final-project RAG is enabled;
- an 11-case golden set including a version/source-conflict regression;
- mandatory clarify/escalate governance regressions;
- a reviewer-first README and executable validation commands;
- a manual exact-head live-proof workflow that ingests, persists, retrieves and performs one bounded provider call without putting paid calls in deterministic CI.

None of those repository-controlled artifacts substitutes for a successful real external ingestion run.

## Final-project GO rule

GO requires all mandatory rows to be evidenced at the final commit and at least one accessible demonstration path:

```text
real corpus
AND ingestion
AND chunking
AND embeddings
AND persistent retrieval
AND evidence reaches the graph
AND agents/critics execute
AND eval test set + metrics + regression exist
AND FastAPI works
AND README matches executable truth
AND public URL OR 2–3 minute video exists
AND TA can access finalproject-GG
```

## Live evidence still required

The final demonstration environment must produce and retain, without secrets:

1. the ingestion command and sanitized report with source/chunk counts;
2. evidence that embeddings were produced with the configured real embedding model;
3. evidence that chunks survived in PostgreSQL and were retrieved after ingestion;
4. `evals/energy_chat/final_project_retrieval_report.json` generated from that persisted corpus;
5. one bounded end-to-end support answer showing retrieved evidence plus final disposition;
6. public URL or 2–3 minute video link required by the assignment.

The repository provides `.github/workflows/final-project-live-rag.yml` and `docs/final_project/LIVE_PROOF_RUNBOOK.md` for items 1–5. The workflow is manual-only so deterministic pushes do not spend provider budget.

If any live gate fails, keep the failure visible. Do not replace it with deterministic fixtures and call the project green.

## Non-blocking post-deadline work

- pgvector/HNSW optimization;
- large-scale corpus expansion;
- reranking;
- AWS Spot-specific deployment;
- enterprise OIDC;
- real production SLOs/alerts;
- backup/restore drill;
- EACODE execution integration.

## Claim discipline

Do not claim production-scale reliability, universal hallucination prevention, ANN/pgvector retrieval, live-provider success, real-corpus metrics or public availability until corresponding evidence exists.
