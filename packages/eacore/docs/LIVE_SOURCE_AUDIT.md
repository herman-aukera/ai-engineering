# Live Source Audit — 2026-07-17

## Repository base

- Repository: `herman-aukera/ai-engineering`
- EACORE base: `main`
- Verified base SHA: `4e4011974785e23b0ec7dc2d9e60a27342942e80`
- Existing EACORE branch before this work: none found

## Product source heads

| Product | Branch | Head SHA | PR | Current CI observed during audit |
|---|---|---|---:|---|
| Session 13 Plus | `gg-session-13/plus` | `596f94d394e98c8063fcf476684f224af89cb6f5` | #10 draft | run `29559900320`: success |
| EACHAT | `EACHAT` | `6044c3d7f003a44bf69b77fd567e93f4a2267e42` | #5 open | runs `29608480795` and `29608481797`: failure |
| EACODE | `EACODE` | `397226d2574d04e516c5c8d4b71423aa912a3d32` | #4 draft | run `29608598496`: in progress at audit time |

## Contract evidence inspected

### Session 13 Plus

- `estimador-cag/app/schemas/review_policy.py`
- PR #10 changed-file inventory and evidence summary

Verified characteristics:

- strict typed Critic findings;
- four-level severity semantics;
- deterministic Boss actions;
- explicit retry, fallback, tool, latency, and cost budgets;
- product-specific human-review and graph semantics.

### EACHAT

- `estimador-cag/app/energy_chat/contracts.py`
- PR #5 changed-file inventory and release claim boundary

Verified characteristics:

- six product dispositions: accept, repair, reject, clarify, refuse, escalate;
- typed critic findings and energy score;
- evidence references and Energy Card projection;
- product-specific chat modes, source grounding, provider and UI contracts.

### EACODE

- `estimador-cag/energy_core/models.py`
- PR #4 changed-file inventory and incubator boundary

Verified characteristics:

- strict coding-specific candidate and evidence records;
- deterministic violations, scoring, decision and append-only ledger concepts;
- coding-specific decision enum and policy thresholds;
- shell and controlled-execution concerns that must remain outside EACORE.

## Audit conclusion

The three branches provide enough representational overlap for a neutral-kernel
pilot, but not enough evidence to unify product policies, decision enums,
weights, graph runtimes, human-gate semantics, tools or persistence backends.

The EACORE branch therefore contains only neutral references, observations,
envelopes, arithmetic, invariants, integrity helpers, ports and reference
adapters. No product branch is modified and no product consumes EACORE in Spec
0001.
