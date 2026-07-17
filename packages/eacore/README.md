# EACORE 0.1 — Neutral Kernel

EACORE is a framework-neutral Python package for strict Energy-Aware contracts,
deterministic energy arithmetic, universal transition invariants, canonical
serialization, integrity helpers, and append-only reference ledgers.

It deliberately does **not** contain LangGraph, FastAPI, Streamlit, provider
SDKs, retrieval, shell execution, repository mutation, product policies, or
product-specific decision enums.

## Boundary

```text
product candidate
→ product adapter
→ EACORE references and observations
→ EACORE energy arithmetic
→ product decision policy
→ EACORE transition verification and audit envelope
→ product graph/API/UI/action
```

## Install for development

    python -m pip install -e ".[dev]"
    python -m pytest

## Claim boundary

EACORE 0.1 is a neutral-kernel incubator. It does not claim that Session 13
Plus, EACHAT, or EACODE already consume this package.
