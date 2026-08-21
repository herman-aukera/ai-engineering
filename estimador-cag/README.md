# EACHAT — Energy-Aware Chat ⚡

EACHAT is the conversational specialization of the Energy-Aware architecture. It turns a user request into a governed answer through evidence routing, candidate generation, deterministic critics/Energy policy, bounded repair, durable replay and protected human continuation.

Canonical branch: `EACHAT`; it is a peer product to estimator `main` and `EACODE`, not a feature branch for `main`.

## Production entry point

`app.energy_chat.production_app:app`

Canonical business APIs are explicitly major-versioned under `/energy-chat/v2/*`. Historical evaluation, benchmark, draft and legacy MVP routes are compatibility/coursework code and are not mounted by the production V2 transport.

The bundled HTML is a browser shell only. Protected API calls require signed identity; a real browser login/OIDC adapter is deliberately not faked.

## Energy-Aware authority loop

```text
request -> evidence need/retrieval -> answer candidate -> critic panel
-> deterministic Energy/disposition -> bounded repair
-> durable protected human continuation -> Energy Card + Decision Ledger
```

Providers may draft and return evidence. Deterministic policy owns hard constraints, budgets, repair bounds and disposition. Planned provider behavior is never served evidence, and a provider cannot authorize itself.

## Identity, ownership and durable state

Production requires `EACHAT_SESSION_SIGNING_KEY`. Backend-signed sessions carry actor and tenant identity. Conversations and graph threads are bound to the authenticated owner; cross-tenant history/replay/resume fails closed, and client-supplied HITL actor identity is replaced by the authenticated server actor.

Production also requires PostgreSQL-backed strict LangGraph checkpoints and encrypted conversation memory. Ownership is persisted in PostgreSQL, so application replacement cannot erase the access boundary. `EACHAT_ALLOW_IN_MEMORY=true` is test/development-only.

`/health` remains a cheap local liveness probe. `/ready` performs a bounded authority-store availability check and returns 503 if the PostgreSQL ownership authority is unreachable; this removes a live-but-unsafe process from service without making an LLM/provider call.

## Isolated production artifact

EACHAT carries a dedicated production lock:

```text
deploy/eachat/pyproject.toml
deploy/eachat/uv.lock
deploy/eachat/uv.lock.sha256
```

`scripts/eachat_export_production_requirements.py` verifies its digest and refuses coursework-only dependency families. The production Dockerfile consumes the isolated lock directly.

The machine-readable mapping is `docs/energy_aware_product_manifest.json`. `scripts/verify_energy_aware_protocol.py` checks portfolio authority invariants; `scripts/product_split_dry_run.py` traces the production import closure, rejects peer-product imports and materializes a compile-checked product-only tree.

## Observability

Production emits the neutral `energy-aware.event.v1` operational envelope from `app/energy_aware_observability.py`: safe request correlation, outcome, stable reason code and duration only. Prompts, transcripts, authorization values and secrets are rejected as event attributes.

## Deterministic validation

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test uv run pytest -q
python scripts/eachat_export_production_requirements.py
python scripts/verify_energy_aware_protocol.py
python scripts/product_split_dry_run.py
uv run python scripts/session15_eachat_production_contract.py
```

The container canary destroys and recreates the app against the same PostgreSQL database and verifies conversation and ownership recovery. Credentialed provider evidence remains isolated in `.github/workflows/eachat-live-provider-smoke.yml`.

A sanitized bounded DeepSeek smoke from 2026-08-05 is retained at `evals/energy_chat/live_provider_smoke_deepseek_2026-08-05.json`. It proves one historical balanced-profile live call only; it is **not** current-head provider proof and does not support provider superiority, fallback reliability or production-readiness claims.

## Production topology and release

```text
Internet -> Caddy :80/:443 -> private EACHAT :8000
         -> signed actor + tenant ownership
         -> durable PostgreSQL
         -> explicitly selected provider HTTPS
```

Images are non-root, immutable and digest-addressed; deploy is readiness-gated and rollback uses a prior digest. Release builds attach BuildKit SBOM and provenance attestations; the portfolio final gate separately audits the isolated Python dependency closure.

## Remaining external production gates

Repository evidence covers deterministic governance, V2-only production API, signed tenant/resource ownership, encrypted durable state, isolated dependencies, neutral telemetry, restart evidence and immutable release/deploy contracts.

It is **not yet live production-ready** without real external identity/OIDC, EC2/RDS staging, backup/restore, abuse/rate controls, load/SLO/alerting and collected production telemetry.

## Canonical documentation

- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/energy_aware_product_manifest.json`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
