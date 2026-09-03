# EACHAT Final Project Acceptance and Evidence Matrix

Status: live final-project gate

| Official requirement | Implementation target | Required evidence | Status at branch creation |
|---|---|---|---|
| Concrete domain | L2 Spring Boot/PostgreSQL/Docker support | Product spec + README | SPECIFIED |
| Real data | Official public docs in allowlisted manifest | Source manifest + ingestion report | IN PROGRESS |
| FastAPI | `app.energy_chat.production_app:app` | `/health`, `/ready`, `/version`, business route smoke | EXISTING / REVALIDATE |
| RAG ingestion | `app.energy_chat.support_rag` ingestion | deterministic tests + live ingestion report | BLOCKING |
| Chunking | support-rag section chunker | tests + chunk counts | BLOCKING |
| Embeddings | OpenAI embedding adapter with fake CI seam | deterministic adapter test + bounded live proof | BLOCKING |
| Persistent/indexed storage | PostgreSQL support chunk store | schema/store tests + live DB proof | BLOCKING |
| Retrieval | exact cosine top-k adapter into `ProjectRagResult` | retrieval golden cases | BLOCKING |
| Agent/orchestration | existing EACHAT LangGraph | graph tests + trace | EXISTING / REVALIDATE |
| Evals | final-project golden set + report | metrics + regression output | BLOCKING |
| README | final-project root README | reviewer inspection | BLOCKING |
| Deployment evidence | public URL OR 2–3 minute video | externally accessible link | EXTERNAL BLOCKER |
| Final branch | `finalproject-GG` | Git ref | DONE |
| No secrets | existing secret gates | CI/diff scan | REVALIDATE |

## Existing reusable evidence

The branch was created directly from certified EACHAT commit `c303c0d7d5c12682a88e195bd38a8d5833ded8b5`. Historical certification run `32661638856` was successful for that exact source commit. This proves the inherited repository-controlled baseline only; every final-project commit must be revalidated.

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

Do not claim production-scale reliability, universal hallucination prevention, ANN/pgvector retrieval, live-provider success or public availability until corresponding evidence exists.
