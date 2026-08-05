# Spec 0012 — Production Hardening Slice: Acceptance

## Deterministic gates

From `estimador-cag/`:

```text
uv run ruff check app/routers/eacode.py energy_core/beta_demo.py energy_core/beta_store.py energy_core/beta_evaluation.py tests/test_energy_core_beta_demo.py tests/test_energy_core_beta_store.py tests/test_energy_core_beta_evaluation.py tests/test_eacode_beta_api.py
uv run pytest -q tests/test_energy_core_beta_demo.py tests/test_energy_core_beta_store.py tests/test_energy_core_beta_evaluation.py tests/test_eacode_beta_api.py
uv run pytest -q
```

Expected:

- client `human_authorization` field returns 422;
- unsigned authorization returns 401;
- viewer authorization returns 403;
- signed operator authorization returns one receipt;
- first exact receipt consumption succeeds;
- replay returns conflict;
- persisted result survives a new store instance;
- record tampering raises an integrity error;
- poisoned expected label does not alter the calculated actual decision;
- final benchmark mode classifies all twelve cases correctly.

## Container gate

From repository root:

```text
docker compose --profile demo config --quiet
docker compose --profile demo up -d --build --wait db redis api
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/eacode/status
docker compose restart api
curl --fail http://127.0.0.1:8000/health
docker compose --profile demo run --rm --no-deps runner
docker compose --profile demo down --volumes --remove-orphans
```

Expected:

- API runs as UID 10001;
- runner runs as UID 10002;
- runtime image does not contain `pytest`;
- prepared demo state survives API restart;
- no real process or provider is invoked.

## Release verdict

A successful gate permits describing the slice as:

> durable, signed-session, replay-safe simulated beta with container-runtime proof

It does not permit describing EACODE as production-ready.
