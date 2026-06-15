# Energy Aware Code Closeout Pack

The closeout pack is an end-of-day handoff report for the EACODE incubator branch.

It combines five reviewer-facing checkpoints:

1. incubator status
2. reviewer evidence index
3. acceptance evidence trace
4. day-end handoff checklist
5. next-slice roadmap

## Command

```bash
python -m energy_core.closeout_pack_cli --format markdown --fail-on-incomplete
```

## What it proves

The report proves that EACODE can be handed to a reviewer or resumed later without pretending the project is finished.

It checks package completeness, surface consistency, acceptance trace completeness, demo walkthrough completeness, known blocking gaps, and course-boundary conflicts.

## Non-goals

The closeout pack does not execute shell actions, call LLM providers, mutate evidence, append to the decision ledger, authorize adapters, or claim benchmark results.
