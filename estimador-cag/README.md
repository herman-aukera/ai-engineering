# Energy-Aware Estimator ⚡

The canonical `main` product is an Energy-Aware AI project estimator: it turns a project request into a governed estimate through typed evidence, specialist proposals, deterministic policy, bounded recovery and persistent human review.

## Production entry point

`app.estimator.production_app:app`

Production does **not** deploy the historical coursework `app.main`. The canonical business API is `/api/v1/estimate/graph/unified*`; operational probes are `/startup`, `/health`, `/ready` and `/version`. Business routes require a backend-signed bearer session.

## Energy-Aware authority loop

```text
request -> structure/retrieval -> candidates -> critics/reliability
-> deterministic decision -> bounded selective recovery
-> coherence verification -> protected human authorization -> record
```

Models and specialists may propose and provide evidence. They may not waive hard constraints, own arithmetic/budgets, authorize protected transitions or decide their own acceptance. The deterministic supervisor/review policy owns machine authority; the human gate owns protected human authority.

## Identity and durable state

Production requires `ESTIMATOR_SESSION_SIGNING_KEY`. Signed sessions carry actor and tenant identity; each persisted `estimation_id` is bound to that owner in PostgreSQL. Cross-owner resume/control fails closed, and the public HITL `actor` field is replaced by the authenticated server-side actor before reaching the graph.

This is an application identity boundary, not a claim of live OIDC integration. Authoritative LangGraph checkpoints, replay/HITL state, revisions and estimation ownership use PostgreSQL; replaceable compute does not own authoritative state.

`/health` is deliberately cheap and provider/database independent. `/ready` separately performs a bounded authority-store availability check and fails with 503 when PostgreSQL authority is unavailable, so a live process with a dead authoritative database is removed from service without calling an LLM.

## Isolated production artifact

The deployable dependency closure is frozen independently of coursework dependencies:

```text
deploy/estimator/pyproject.toml
deploy/estimator/uv.lock
deploy/estimator/uv.lock.sha256
```

`scripts/estimator_export_production_requirements.py` verifies the lock digest and rejects notebook/UI/local-model/document-processing dependencies. The Dockerfile consumes this isolated lock directly and installs hashed requirements.

The product mapping is machine-readable in `docs/energy_aware_product_manifest.json`. `scripts/verify_energy_aware_protocol.py` proves shared authority invariants and `scripts/product_split_dry_run.py` traces the production import closure, rejects peer-product imports and materializes a compile-checked product-only tree.

## Observability

Production emits the neutral `energy-aware.event.v1` envelope through `app/energy_aware_observability.py`. Events contain safe correlation, outcome, stable reason code and duration. Prompts, transcripts, authorization values, API keys and secrets are prohibited event attributes.

## Deterministic validation

```bash
cd estimador-cag
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q -m "not live_provider"
python scripts/estimator_export_production_requirements.py
python scripts/verify_energy_aware_protocol.py
python scripts/product_split_dry_run.py
uv run python scripts/session15_production_contract.py
```

Normal blocking CI never performs a real model call. Credentialed provider quality/cost/latency evaluation remains isolated in `.github/workflows/provider-evaluation.yml`.

## Production topology and release

```text
Internet -> Caddy :80/:443 -> private estimator :8000
         -> signed actor + tenant ownership
         -> durable PostgreSQL
         -> provider HTTPS when explicitly selected
```

The image is non-root, SHA/digest identified, immutable at release and rolled back by prior digest. Release builds attach BuildKit SBOM and provenance attestations; the portfolio final gate separately audits the isolated Python dependency closure.

## Remaining external production gates

Repository evidence covers the isolated production surface, signed tenant ownership, durable graph state, product-only dependency lock, neutral telemetry contract, single ingress and immutable deployment design.

It is **not yet truthful to call this live production-ready** without real staging/production evidence for EC2/RDS, external identity/OIDC, DNS/TLS, backup/restore, load/SLO/alerting and collected production telemetry.

## Canonical documentation

- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/energy_aware_product_manifest.json`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
