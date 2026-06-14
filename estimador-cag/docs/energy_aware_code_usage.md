# Energy Aware Code CLI usage

Status: Slice 1 plus judge usability hardening.

Scope: deterministic judge only. This tool evaluates supplied candidate state and evidence. It does not execute shell commands, call LLM providers, edit files, open Cline, run Aider, or push commits.

## Validate the branch

Run from `estimador-cag`:

    uv run ruff check --fix energy_core tests scripts
    uv run ruff check energy_core tests scripts
    uv run python -m py_compile $(find energy_core tests scripts -name '*.py' -type f)
    uv run pytest -q tests/test_energy_core_policy_loading.py tests/test_energy_core_decider_accept.py tests/test_energy_core_decider_hard_reject.py tests/test_energy_core_decider_hard_repair.py tests/test_energy_core_ledger_append_only.py tests/test_energy_core_cli.py tests/test_energy_core_evidence_summary.py
    uv run pytest -q
    uv run python scripts/energy_core_smoke.py

The smoke script exercises the same commands shown below so CLI examples cannot drift silently.

## Evaluate a candidate and append a decision

    uv run python -m energy_core.cli evaluate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --evidence .energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --decisions /tmp/eac-decisions.jsonl \
      --format text

## Preview a candidate without ledger mutation

    uv run python -m energy_core.cli evaluate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --evidence .energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --format json \
      --dry-run

## Write a Markdown decision report

    uv run python -m energy_core.cli evaluate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --evidence .energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --decisions /tmp/eac-decisions.jsonl \
      --format text \
      --report /tmp/eac-decision-report.md

## Summarize evidence quality

    uv run python -m energy_core.cli evidence-summary \
      --evidence .energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --format markdown

## Summarize the decision ledger

    uv run python -m energy_core.cli ledger-summary \
      --decisions /tmp/eac-decisions.jsonl \
      --format markdown

## Fail automation on non-accept decisions

    uv run python -m energy_core.cli evaluate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_reject_tests_failed.json \
      --evidence /tmp/eac-failed-evidence.jsonl \
      --decisions /tmp/eac-decisions.jsonl \
      --format text \
      --fail-on-non-accept

Decision exit codes:

| Decision | Exit code |
|---|---:|
| accept | 0 |
| repair | 1 |
| reject | 2 |
| escalate | 3 |

## Current non-goals

1. No shell command execution.
2. No Aider adapter.
3. No Cline adapter.
4. No OpenCode adapter.
5. No FastAPI or Streamlit integration.
6. No DeepSeek, OpenAI, or Kimi calls.
7. No bridge with Energy Aware Chat.

The current product layer is the judge: policy, candidate state, evidence, critics, score, decision, reports, and ledger inspection.
