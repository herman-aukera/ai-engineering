# Acceptance

spec_id: 0001-energy-policy-ledger
status: active
owner: Gonzalo / AI Engineer LIDR

## Acceptance criteria

1. Policy loading returns a typed policy.
2. Candidate state loading returns a typed candidate.
3. Evidence JSONL loading returns typed evidence records.
4. Failed pytest evidence produces reject.
5. Failed lint evidence produces repair.
6. Missing required acceptance evidence produces repair.
7. Clean trusted evidence produces accept.
8. CLI prints valid JSON when requested.
9. Decision ledger appends JSONL rows without overwriting.

## Validation commands

Run from `estimador-cag`:

    uv run ruff check --fix energy_core tests
    uv run ruff check energy_core tests
    uv run python -m py_compile $(find energy_core tests -name '*.py' -type f)
    uv run pytest -q tests/test_energy_core_policy_loading.py tests/test_energy_core_decider_accept.py tests/test_energy_core_decider_hard_reject.py tests/test_energy_core_decider_hard_repair.py tests/test_energy_core_ledger_append_only.py tests/test_energy_core_cli.py
    uv run pytest -q
