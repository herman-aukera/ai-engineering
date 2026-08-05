# Spec 0012 — Production Hardening Slice: Acceptance

## Deterministic code gate

From `estimador-cag/`:

```text
uv run ruff check app/eacode_main.py app/main.py app/routers/eacode.py energy_core/beta_demo.py energy_core/beta_store.py energy_core/beta_evaluation.py tests/test_energy_core_beta_demo.py tests/test_energy_core_beta_store.py tests/test_energy_core_beta_evaluation.py tests/test_eacode_beta_api.py tests/test_eacode_cors.py tests/test_eacode_runtime_app.py
uv run pytest -q tests/test_energy_core_beta_demo.py tests/test_energy_core_beta_store.py tests/test_energy_core_beta_evaluation.py tests/test_eacode_beta_api.py tests/test_eacode_cors.py tests/test_eacode_runtime_app.py
uv run pytest -q
```

Expected:

- unsigned preparation and inspection return 401;
- client `human_authorization` returns 422;
- viewer can prepare/inspect its own proposal but authorization returns 403;
- another tenant receives 404 for read and authorization attempts;
- admin can inspect across the tenant boundary;
- signed operator receives one exact-scope receipt;
- first exact receipt consumption reserves the transition and succeeds;
- receipt replay and a second independently issued receipt fail closed;
- persisted result survives a new store instance;
- record tampering raises an integrity error;
- poisoned expected label does not alter the calculated actual decision;
- final benchmark mode classifies all twelve cases correctly;
- wildcard CORS is absent;
- the dedicated composition root contains EACODE routes and excludes estimator/session routes.

## Product-container gate

From repository root:

```text
docker compose --profile demo config --quiet
docker compose --profile demo up -d --build --wait eacode-api
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/eacode/status
docker compose restart eacode-api
curl --fail http://127.0.0.1:8000/health
docker compose --profile demo run --rm --no-deps runner
docker compose --profile demo down --volumes --remove-orphans
```

Expected:

- EACODE API runs as UID 10001;
- runner runs as UID 10002;
- runtime image does not contain `pytest`, Torch, or Jupyter;
- unsigned proposal preparation returns 401;
- signed tenant proposal state survives API restart;
- fixed high/critical vulnerabilities fail the workflow;
- an SPDX SBOM is uploaded as workflow evidence;
- no PostgreSQL, Redis, live provider, or real process is required by the EACODE beta product path.

## Publication gate

- Pull requests and non-canonical branches MUST NOT publish images.
- Only a push to canonical `EACODE` MAY publish.
- The tag MUST be the immutable commit SHA.
- BuildKit SBOM and maximum provenance MUST be enabled.

## Release verdict

A successful gate permits describing the slice as:

> tenant-scoped, signed-session, replay-safe simulated beta with minimal product-image and restart proof

It does not permit describing EACODE as production-ready.
