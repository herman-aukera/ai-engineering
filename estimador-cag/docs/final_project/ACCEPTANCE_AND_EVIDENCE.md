# EACHAT Final Project Acceptance and Evidence Matrix

Status: final-project closure gate

| Requirement | Implementation | Current evidence/status |
|---|---|---|
| Concrete domain | L2 Spring Boot/PostgreSQL/Docker support | IMPLEMENTED |
| Real data | 16 curated official public pages | MANIFEST IMPLEMENTED / LIVE ACQUISITION PENDING |
| FastAPI | `app.energy_chat.production_app:app` | IMPLEMENTED / FINAL EXACT-HEAD CI PENDING |
| Ingestion + chunking | allowlisted acquisition + section chunking | IMPLEMENTED / LIVE COUNTS PENDING |
| Embeddings | `text-embedding-3-small`, fake CI seam | IMPLEMENTED / LIVE PROOF PENDING |
| Vector DB/index | PostgreSQL `vector` + HNSW cosine index | IMPLEMENTED / LIVE DB PROOF PENDING |
| Retrieval | native pgvector cosine top-k into `ProjectRagResult` | IMPLEMENTED / REAL REPORT PENDING |
| Agent/orchestration | EACHAT LangGraph + critics + deterministic disposition | IMPLEMENTED / FINAL CI PENDING |
| Governance regressions | clarify version/insufficient evidence; escalate L3/unsupported | IMPLEMENTED / FINAL CI PENDING |
| Golden set | 11 fixed domain cases | IMPLEMENTED |
| Retrieval eval | persisted pgvector runner | IMPLEMENTED / LIVE REPORT PENDING |
| Full-system eval | 11-case real-provider runner | IMPLEMENTED / LIVE REPORT PENDING |
| Monitoring | authenticated JSON + HTML dashboard | IMPLEMENTED / FINAL CI + BROWSER PROOF PENDING |
| Local deployment | Caddy → EACHAT → PostgreSQL/pgvector + one-shot ingest | IMPLEMENTED / LIVE COMPOSE SMOKE PENDING |
| Restart persistence proof | compose smoke restarts EACHAT then re-queries RAG | IMPLEMENTED / EXECUTION PENDING |
| README/docs | reviewer-first final-project package | IMPLEMENTED / FINAL DOC REVIEW PENDING |
| No secrets | deterministic secret/diff gates | FINAL EXACT-HEAD CI PENDING |
| Deployment evidence | public URL OR 2–3 minute video | EXTERNAL BLOCKER |
| Final branch | `finalproject-GG` | DONE |

## Repository-controlled additions

The final-project branch now contains the concrete domain, allowlisted corpus, real ingestion/chunking/embedding path, native pgvector persistence/index/retrieval, evidence integration into the existing graph, 11-case golden set, deterministic governance regressions, full-system live evaluator, safe monitoring dashboard and reproducible local Compose topology.

The local topology intentionally adapts the teacher's Docker exercise to EACHAT rather than adding a fake Rails layer. Only the Caddy edge exposes a host port; EACHAT and PostgreSQL/pgvector remain internal. The same PostgreSQL instance holds durable EACHAT state and RAG vectors for this bounded final-project deployment.

## Live evidence required before GO

A GO claim still requires external execution evidence for the final SHA:

1. live ingestion of all allowlisted sources;
2. real embedding generation;
3. pgvector persistence and retrieval report;
4. bounded live answer with retrieved evidence retained by the graph;
5. full 11-case live system-evaluation report;
6. local Compose/restart proof or equivalent deployment evidence;
7. public URL or required 2–3 minute video.

The repository provides the manual `Final Project - Live RAG Proof` workflow for items 1–5 and `scripts/smoke_eachat_final_project_compose.py` for the local full-stack/restart proof. These are LIVE-READY until actually executed.

## Final-project GO rule

```text
real corpus + embeddings + pgvector retrieval
AND evidence reaches the governed graph
AND golden set + metrics + regressions
AND FastAPI + monitoring
AND reproducible container topology
AND exact-head deterministic CI green
AND public URL OR 2–3 minute video
```

Do not convert a missing live artifact into a deterministic claim. Failures remain visible.

## Post-deadline only

Large-scale corpus expansion, reranking, AWS Spot, enterprise OIDC, production SLO/alert infrastructure, backup/restore drills and EACODE integration are intentionally outside the submission-critical slice.
