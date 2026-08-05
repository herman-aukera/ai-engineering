# Energy Aware Chat deployment readiness runbook

Status: deployment skeleton runbook.
Branch: `EACHAT`.
Scope: low-friction deployment preparation without claiming public production readiness.

## Purpose

This runbook explains how to test the Energy Aware Chat API locally, through Docker Compose, and later through a public deployment target.
It is intentionally conservative: a successful local run proves the app starts, not that the service is production-ready.

## Local API path

From `estimador-cag`:

```bash
bash scripts/start_energy_chat.sh
```

Expected behavior:

1. FastAPI starts.
2. `/health` responds.
3. `/energy-chat/evaluate` accepts deterministic payloads.
4. `/energy-chat/rag/search` returns deterministic project-source hits.
5. `/energy-chat/chat` returns a final answer plus Energy Card.

## Docker Compose path

From `estimador-cag`:

```bash
docker compose -f docker-compose.energy-chat.yml up --build
```

Expected behavior:

1. Container builds without real provider keys.
2. API exposes the same deterministic endpoints.
3. Secrets are provided only through environment variables when live provider smoke is intentional.
4. No `.env` file is committed.

## Public deployment candidate rules

A public deployment is acceptable only after these are true:

1. Local validation passes.
2. Dedicated Energy Chat CI proof passes.
3. Container starts from a clean environment.
4. Secret values are injected through the deployment platform.
5. Health check is public or reviewer-accessible.
6. At least one deterministic API smoke succeeds.
7. Claim boundary remains visible in README or deployment notes.

## Low-friction GitHub deployment strategy

Recommended safe path:

1. Keep `EACHAT` as development branch.
2. Keep `finalproject-GGC` as delivery mirror branch.
3. Use PR #5 as the control surface.
4. Add real provider keys only as GitHub Actions or deployment environment secrets.
5. Use manual `workflow_dispatch` for live smoke and deployment.
6. Never deploy automatically from an unreviewed commit.

## Required GitHub secrets for live provider smoke

```text
DEEPSEEK_API_KEY
KIMI_API_KEY
```

Do not commit these values. Do not paste them in docs, screenshots, logs, or PR comments.

## Non-claims

This runbook does not claim:

1. public deployment is already live,
2. production readiness,
3. production-grade auth,
4. rate limiting,
5. persistent telemetry,
6. live DeepSeek-to-Kimi fallback proof before manual smoke passes.

## Morning deployment smoke

After local validation, start the API and run the deterministic demo payloads manually or through the API smoke guide.
If anything fails, use the latest green checkpoint before adding deployment features.
