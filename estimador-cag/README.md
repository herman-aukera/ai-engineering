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

The production app exposes V2 chat, bounded live chat, thread state/replay, multi-turn conversations, HITL start/resume and the same-origin V2 demo. Historical evaluation, benchmark, draft and legacy MVP routes remain compatibility/coursework code and are not imported by the production V2 transport.

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

## Durable state

Production requires PostgreSQL-backed strict LangGraph checkpointing plus encrypted conversation storage. `EACHAT_ALLOW_IN_MEMORY=true` is a development/test override only and is absent from production Compose.

Existing container canary evidence destroys and recreates the application against the same PostgreSQL database and verifies conversation recovery.

## Deterministic validation

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q
bash scripts/validate_energy_chat.sh
uv run python scripts/session15_eachat_production_contract.py
uv run python scripts/verify_repo_split_readiness.py
```

Normal CI uses fake/deterministic providers. Credentialed provider evidence runs separately in `.github/workflows/eachat-live-provider-smoke.yml`.

## Production topology

```text
Internet
-> Caddy :80/:443
-> private EACHAT container :8000
-> durable PostgreSQL
-> outbound HTTPS to explicitly selected providers
```

Images are non-root, released by immutable digest, deployed by exact digest and rolled back by previous digest.

## Current claim boundary

EACHAT is a production-oriented, restart-persistent conversational product candidate with deterministic governance, V2-only production API, encrypted durable conversation state and Session 15 release/deploy contracts.

It is **not yet live production-ready**. Major remaining gates are authenticated tenant/thread ownership, real staging on EC2/RDS, backup/restore, abuse/rate controls, external identity integration, load/SLO/alerting and real production telemetry.

## Canonical documentation

- `docs/ARCHITECTURE.md`
- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
