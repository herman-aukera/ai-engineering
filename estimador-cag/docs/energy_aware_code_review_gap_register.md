# Energy Aware Code Review Gap Register

The review gap register gives reviewers one explicit list of known gaps and accepted boundaries.

It separates:

- blocking gaps that should fail review,
- planned policy boundaries that are intentionally not implemented yet,
- informational gaps such as optional evidence with no records,
- example scenarios that are intentionally not ready to accept.

## Command

```bash
python -m energy_core.review_gap_register_cli \
  --project-root . \
  --format markdown \
  --fail-on-blocking
```

## Current intent

A green full gate does not mean the product is finished. It means the current judge-layer implementation is internally consistent. The review gap register keeps future execution-layer work visible without pretending it already exists.

## Non goals

- It does not execute shell actions.
- It does not call LLM providers.
- It does not mutate evidence or the decision ledger.
