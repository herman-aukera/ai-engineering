# Energy Aware Code Demo Walkthrough

This document describes the generated demo walkthrough for EACODE.

The walkthrough is a human-facing proof order. It tells a reviewer what to open first, which command proves each claim, and which limitation should be stated explicitly.

## Command

```bash
python -m energy_core.demo_walkthrough_cli --format markdown --fail-on-incomplete
```

## Purpose

Use this report before a live review, portfolio recording, or teacher demo. It is deliberately non-mutating.

## Non-goals

1. It does not execute shell actions.
2. It does not call LLM providers.
3. It does not mutate evidence or the decision ledger.
4. It does not claim benchmark or production readiness.
