# EACHAT — Energy-Aware Chat ⚡

EACHAT is the conversational specialization of the Energy-Aware architecture. It turns a user request into a governed answer through evidence routing, candidate generation, deterministic critics/Energy policy, bounded repair, durable replay and protected human continuation.

Canonical branch: `EACHAT`. The branch is a peer product to the estimator `main` and `EACODE`; it is not intended to merge into `main`.

## Production entry point

```text
app.energy_chat.production_app:app
```

Canonical public business API is explicitly versioned under:

```text
/energy-chat/v2/*
```

The production app exposes V2 chat, bounded live chat, thread state/replay, multi-turn conversations and HITL start/resume. Historical evaluation, benchmark, draft and legacy MVP routes remain compatibility/coursework code and are not imported by the production V2 transport.

The bundled V2 HTML remains a browser shell, but protected API calls now require authenticated identity. A real browser login/OIDC adapter is deliberately **not faked**; it remains a staging integration task.

## Energy-Aware decision loop

```text
user request
-> interpret + policy/constraints
-> evidence need + retrieval/citation validation
-> answer candidate
-> critic panel
-> deterministic Energy score + disposition
-> bounded repair when justified
-> durable human interrupt when protected
-> final answer + Energy Card + Decision Ledger
```

Models/providers can draft and return evidence. Deterministic policy owns hard constraints, budgets, repair bounds and disposition. A provider cannot authorize itself or turn a planned route into served evidence. Human resume is explicit and revision/idempotency guarded.

Common portfolio terminology is defined in `docs/ENERGY_AWARE_PROTOCOL_V1.md`.

## Identity, ownership and durable state

Production requires `EACHAT_SESSION_SIGNING_KEY`. Backend-signed sessions carry actor and tenant identity. Conversations and graph threads are bound to their authenticated owner; cross-tenant history/replay/resume attempts fail closed with stable reason codes. The client-supplied HITL `actor` is replaced by the authenticated server actor before authority reaches the runtime.

Ownership itself is persisted in PostgreSQL, so destroying/replacing the application cannot silently erase the access boundary.

Production also requires PostgreSQL-backed strict LangGraph checkpointing plus encrypted conversation storage. `EACHAT_ALLOW_IN_MEMORY=true` is a development/test override only and is absent from production Compose.

The container canary is configured to destroy and recreate the application against the same PostgreSQL database and verify conversation **and ownership** recovery.

## Deterministic validation

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q
bash scripts/validate_energy_chat.sh
uv run pytest -q tests/test_eachat_identity_ownership.py tests/test_eachat_production_ownership.py
uv run python scripts/session15_eachat_production_contract.py
uv run python scripts/verify_repo_split_readiness.py
```

Normal CI uses fake/deterministic providers. Credentialed provider evidence runs separately in `.github/workflows/eachat-live-provider-smoke.yml`.

## Production topology

```text
Internet
-> Caddy :80/:443
-> private EACHAT container :8000
-> signed actor + tenant ownership
-> durable PostgreSQL
-> outbound HTTPS to explicitly selected providers
```

Images are non-root, released by immutable digest, deployed by exact digest and rolled back by previous digest.

## Current claim boundary

Repository implementation supports a production-oriented conversational product candidate with deterministic governance, V2-only production API, signed tenant/resource ownership, encrypted durable conversation state and immutable release/deploy contracts.

It is **not yet live production-ready**. Remaining gates include exact-head hosted validation of the current ownership slice, real external identity/OIDC, EC2/RDS staging, backup/restore, abuse/rate controls, load/SLO/alerting and real production telemetry.

## Canonical documentation

- `docs/ARCHITECTURE.md`
- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
