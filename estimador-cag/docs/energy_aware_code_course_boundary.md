# Energy Aware Code Course Boundary

This document describes the static boundary report that separates the long-lived `EACODE` incubator branch from normal LIDR coursework branches.

## Purpose

`EACODE` is a product incubator for Energy Aware Code. It is not the canonical Session 08 pgvector branch, not the canonical Session 09 evaluation-quality branch, and not the final project delivery branch.

The report exists so future work does not mix unrelated scopes in one branch.

## Command

```bash
python -m energy_core.course_boundary_cli \
  --project-root . \
  --format markdown \
  --fail-on-conflict
```

## Expected result

```text
Complete: True
Blocking conflicts: none
```

## Non-goals

- It does not execute shell actions.
- It does not inspect live git state.
- It does not call LLM providers.
- It does not mutate evidence or the decision ledger.
