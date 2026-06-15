# Energy Aware Code Extraction Readiness

Status: incubator readiness report.

This document describes the deterministic extraction-readiness surface for EACODE.

The report answers whether the current incubator branch has enough explicit inventory, reviewer artifacts, surface consistency, known-gap reporting, and closeout handoff information for a future standalone repository extraction review.

It does not extract files, create a repository, run shell commands, call providers, or approve adapters.

## Command

```bash
python -m energy_core.extraction_readiness_cli --format markdown --fail-on-incomplete
```

## Expected proof

```text
# Energy Aware Code Extraction Readiness
- Complete: True
- Checks: 5/5
```

## Review meaning

A complete report means:

1. the package manifest is complete;
2. reviewer artifacts are declared;
3. surface consistency is complete;
4. blocking gaps are absent;
5. closeout handoff is complete.

## Boundary

This is a planning and review artifact only. Standalone extraction remains a later explicit decision.
