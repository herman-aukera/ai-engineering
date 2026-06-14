# Energy Aware Code CLI usage

Status: incubator judge layer.

Scope: deterministic judge only. This tool evaluates supplied candidate state and evidence. It does not execute shell commands, call LLM providers, edit files, open Cline, run Aider, or push commits.

## Validate the branch

Run from `estimador-cag`:

    uv run ruff check --fix energy_core tests scripts
    uv run ruff check energy_core tests scripts
    uv run python -m py_compile $(find energy_core tests scripts -name '*.py' -type f)
    uv run pytest -q tests/test_energy_core_policy_loading.py tests/test_energy_core_decider_accept.py tests/test_energy_core_decider_hard_reject.py tests/test_energy_core_decider_hard_repair.py tests/test_energy_core_ledger_append_only.py tests/test_energy_core_cli.py tests/test_energy_core_evidence_summary.py tests/test_energy_core_package_boundary.py tests/test_energy_core_spec_coverage.py tests/test_energy_core_validation.py tests/test_energy_core_audit_pack.py
    uv run pytest -q
    uv run python scripts/energy_core_boundary_check.py
    uv run python scripts/energy_core_smoke.py

From the repository root, the incubator branch also supports `python -m energy_core.cli` through a small compatibility shim:

    estimador-cag/.venv/bin/python -m energy_core.cli --help
    estimador-cag/.venv/bin/python scripts/energy_core_root_smoke.py

The CI pipeline runs both the project smoke and the repository-root smoke so examples cannot drift silently.

## Validate the policy contract

From `estimador-cag`:

    uv run python -m energy_core.cli policy-validate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --format markdown \
      --fail-on-invalid

From the repository root:

    estimador-cag/.venv/bin/python -m energy_core.cli policy-validate \
      --policy estimador-cag/.energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --format markdown \
      --fail-on-invalid

This command checks required hard constraints, required evidence types, acceptance evidence, decision rules, and threshold consistency before candidate evaluation starts.

## Validate a candidate contract

From `estimador-cag`:

    uv run python -m energy_core.cli candidate-validate \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --format markdown \
      --fail-on-invalid

From the repository root:

    estimador-cag/.venv/bin/python -m energy_core.cli candidate-validate \
      --policy estimador-cag/.energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate estimador-cag/.energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --format markdown \
      --fail-on-invalid

This command checks that a candidate state is internally usable before it is evaluated against evidence.

## Check spec package coverage

    uv run python -m energy_core.cli spec-coverage \
      --spec-dir .energy/specs/0001-energy-policy-ledger \
      --format markdown \
      --fail-on-incomplete

This command validates that the spec package has the required requirements, design, tasks, acceptance, policy, evidence, and example candidate artifacts before evaluation starts.

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

## Build one audit pack before human review

From `estimador-cag`:

    uv run python -m energy_core.cli audit-pack \
      --spec-dir .energy/specs/0001-energy-policy-ledger \
      --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate .energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --evidence .energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --decisions /tmp/eac-decisions.jsonl \
      --format markdown \
      --report /tmp/eac-audit-pack.md \
      --fail-on-not-ready

From the repository root:

    estimador-cag/.venv/bin/python -m energy_core.cli audit-pack \
      --spec-dir estimador-cag/.energy/specs/0001-energy-policy-ledger \
      --policy estimador-cag/.energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
      --candidate estimador-cag/.energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json \
      --evidence estimador-cag/.energy/specs/0001-energy-policy-ledger/evidence.jsonl \
      --decisions /tmp/eac-decisions.jsonl \
      --format markdown \
      --fail-on-not-ready

This command combines spec coverage, policy validation, candidate validation, evidence summary, decision preview, and ledger summary into one deterministic review packet. It does not append to the ledger.

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

The current product layer is the judge: spec package, policy, candidate state, evidence, critics, score, decision, reports, and ledger inspection.
