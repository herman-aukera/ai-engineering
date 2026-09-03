# EACHAT Final Project — Local Deployment

Status: LIVE-READY; execution evidence must be captured separately.

## Topology

`docker-compose.final-project.yml` adapts the teacher's production-container intent to EACHAT without adding a fake Rails layer:

```text
host :8080
   ↓
Caddy edge
   ↓
EACHAT FastAPI :8000     internal only
   ↓
PostgreSQL + pgvector    internal only + persistent volume
```

A one-shot `ingest` container runs after PostgreSQL becomes healthy, fetches the curated official corpus, creates real embeddings and persists chunks/vectors. EACHAT starts only after ingestion succeeds.

“Internal only” means the database, ingestion worker and application publish no host
ports. Their shared bridge network still permits the outbound HTTPS required to fetch
the allowlisted corpus and call the embedding/provider APIs.

## Required live input

Set a real embedding credential in your shell or secret manager:

```bash
export EACHAT_SUPPORT_EMBEDDING_API_KEY='...'
```

Optional provider keys are required only for live-provider calls. The Compose file contains clearly development-only defaults for the local database password, memory-encryption key and signed-session key; do not reuse them for an internet-facing deployment.

## Start the full stack

From repository root:

```bash
EACHAT_SUPPORT_EMBEDDING_API_KEY="$EACHAT_SUPPORT_EMBEDDING_API_KEY" \
docker compose -f docker-compose.final-project.yml up -d --build
```

Inspect service state:

```bash
docker compose -f docker-compose.final-project.yml ps
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/ready
```

Only Caddy publishes a host port. PostgreSQL and EACHAT are reachable only on the internal Compose network.

## Automated end-to-end + restart proof

From `estimador-cag/`:

```bash
EACHAT_SUPPORT_EMBEDDING_API_KEY="$EACHAT_SUPPORT_EMBEDDING_API_KEY" \
uv run python scripts/smoke_eachat_final_project_compose.py --cleanup
```

The smoke script:

1. builds/starts the stack;
2. waits for `/ready`;
3. creates a signed local reviewer session;
4. sends a project-mode PostgreSQL support request;
5. requires `source:*` RAG evidence;
6. restarts only the EACHAT container;
7. waits for readiness again;
8. sends a Docker support request;
9. requires persisted RAG evidence after restart;
10. prints sanitized proof only.

Do not claim this proof passed until the command has actually succeeded in the target environment.

## Monitoring

Protected reviewer endpoints:

```text
GET /energy-chat/v2/monitoring
GET /energy-chat/v2/monitoring/dashboard
```

They expose aggregate latency, p95 latency, cost/request, provider calls, error rate and disposition counts without exposing prompts, answer bodies, credentials or checkpoint contents.

## Stop

```bash
docker compose -f docker-compose.final-project.yml down
```

Omit `-v` unless you intentionally want to destroy the local persistent database volume.
