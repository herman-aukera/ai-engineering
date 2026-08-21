# Energy-Aware Estimator ⚡

The canonical `main` product is an Energy-Aware AI project estimator: it turns a project request into a governed estimate through typed evidence, specialist proposals, deterministic policy, bounded recovery and persistent human review.

This is the primary evolutionary product line from LIDR Sessions 13/14, with the Session 15 production envelope applied around it.

## Production entry point

```text
app.estimator.production_app:app
```

The historical `app.main` application remains available for coursework and compatibility, but production does **not** deploy it.

Canonical production API:

```text
GET  /api/v1/estimate/graph/unified/readiness
POST /api/v1/estimate/graph/unified
POST /api/v1/estimate/graph/unified/control
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

Operational probes are `/startup`, `/health`, `/ready`, `/version` and are intentionally excluded from the business OpenAPI contract.

## Energy-Aware decision loop

```text
request
-> reformulate / classify
-> structure + retrieval evidence
-> estimate candidates
-> competition + reliability + critics
-> deterministic review/Boss policy
-> bounded selective recovery when justified
-> independent coherence validation
-> persistent human authorization when protected
-> final proposal + evidence
```

Models and specialists may propose and provide evidence. They may not waive hard constraints, own arithmetic/budgets, authorize protected transitions or decide their own acceptance. The supervisor and deterministic policy own machine routing/decision authority; the human gate owns protected human authority.

The portfolio-neutral vocabulary is defined in `docs/ENERGY_AWARE_PROTOCOL_V1.md`.

## Durable state

Authoritative LangGraph checkpoints, replay/HITL state and revisions use PostgreSQL. Production compute is designed to be replaceable; authoritative workflow state must not depend on EC2/Spot-local disk.

Redis is runtime infrastructure and must not silently become authoritative state.

## Local deterministic validation

```bash
cd estimador-cag
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q -m "not live_provider"
uv run ruff check app tests scripts
```

Production-surface smoke:

```bash
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test \
uv run pytest -q tests/smoke/test_session15_http_smoke.py
uv run python scripts/session15_production_contract.py
uv run python scripts/verify_repo_split_readiness.py
```

Normal blocking CI never performs a real model call. Credentialed provider quality/cost/latency evaluation is isolated in `.github/workflows/provider-evaluation.yml`.

## Production model

```text
Internet
-> Caddy :80/:443
-> private estimator container :8000
-> durable external PostgreSQL
-> runtime Redis
-> outbound HTTPS to selected model providers
```

The production image is non-root, built once, identified by Git SHA/OCI digest, deployed by immutable digest and rolled back by a previous digest. See `deploy/session15/README.md` and `docs/RELEASE.md`.

## Current claim boundary

Repository evidence supports a production-oriented estimator architecture with isolated production surface, deterministic CI contract, durable graph state, non-root container, single ingress and immutable deployment/rollback design.

It is **not yet truthful to call this live production-ready** without real staging/production evidence for EC2/RDS, TLS/DNS, backup/restore, load/SLO/alerting, multi-tenant identity/ownership and operational telemetry.

## Canonical documentation

- `docs/ARCHITECTURE.md`
- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`

Historical session evidence remains in Git and the history index; it is no longer the product README.
