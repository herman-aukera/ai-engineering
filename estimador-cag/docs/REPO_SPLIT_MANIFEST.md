# Repository Split Manifest — EACHAT

Future repository candidate: `energy-aware-chat`.

## Retain

- `app/energy_chat/` current V2 domain/runtime/persistence/production surface;
- production Docker/deploy files under `deploy/eachat/`;
- V2 browser artifact and current product docs;
- current EACHAT unit/contract/browser/Postgres/container/security tests;
- production lock/dependency surface;
- `.env.example`;
- `energy-chat-ci.yml`, container canary, live-provider smoke and image-release workflows;
- relevant evaluation corpus separate from public production transport.

## Retire/exclude after dependency proof

- estimator application/runtime modules;
- EACODE modules;
- old `/energy-chat/evaluate`, benchmark and legacy MVP HTTP transport from the future production repo unless retained as an offline eval package;
- old coursework session docs and unrelated demos;
- stale branch/PR instructions.

## Production entry point

`app.energy_chat.production_app:app`

## External state

Durable PostgreSQL + encrypted conversation memory are authoritative. Model credentials and encryption keys are runtime secrets.

## Remaining split blockers

Production V2 code still shares some repository-wide base dependencies and historical test infrastructure. Authenticated tenant/thread ownership must be designed before public multi-user deployment but is not required merely to copy the repository.

Run `python scripts/verify_repo_split_readiness.py` before physical extraction.
