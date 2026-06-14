# Tasks

spec_id: 0001-energy-policy-ledger
status: active
owner: Gonzalo / AI Engineer LIDR

## Slice 1: Energy-core CLI decision evaluator

Goal:
Build a deterministic CLI evaluator for candidate state decisions.

Non goals:
No model calls, API endpoints, UI, adapters, or bridge work.

Red tests:
Policy loading, accept decision, hard reject, hard repair, ledger append-only, and CLI output.

Validation:
Ruff, py_compile, focused pytest, full pytest, diff check, and staged scan before commit.

Stop point:
Stop after a draft PR with validation evidence.
