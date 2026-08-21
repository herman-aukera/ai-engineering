# Historical branch cleanup disposition — 2026-08-21

This document is the semantic review companion to `BRANCH_ARCHAEOLOGY_2026-08-21.md`. It records why noncanonical branch heads may be removed while preserving useful work.

Canonical branch set after cleanup:

- `main` — Energy-Aware Estimator;
- `EACHAT` — Energy-Aware Chat;
- `EACODE` — Energy-Aware Code.

## Rule

A branch head is removable when one of these is true:

1. its head is already reachable from a canonical branch;
2. useful unique evidence/research has been retained canonically;
3. its unique changes are obsolete environment/coursework experiments superseded by stronger current contracts;
4. its unique behavior is deliberately rejected because retaining it would weaken the current product boundary.

Git history and closed PRs remain historical references; dead runtime source is not copied into archive directories.

## Unique-head dispositions

| Historical branch | Disposition | Canonical retention / reason |
| --- | --- | --- |
| `EACORE` | **RETAIN KNOWLEDGE, DELETE BRANCH** | Neutral-kernel decisions retained in `docs/history/EACORE_RESEARCH_RETENTION.md`; current `ENERGY_AWARE_PROTOCOL_V1.md` and per-product manifests are authoritative. The historical shared runtime prototype is deliberately not promoted because shared-code extraction remains semantic-equivalence gated. |
| `gg-eachat/live-smoke-20260805` | **RETAIN EVIDENCE, DELETE BRANCH** | Sanitized bounded DeepSeek evidence retained on `EACHAT` at `evals/energy_chat/live_provider_smoke_deepseek_2026-08-05.json`, explicitly marked historical rather than current-head proof. |
| `gg-devex-container-engine-lab` | **SUPERSEDED** | Container/devcontainer smoke and non-paging shell experiments are development-environment work. Current production containers, exact-head CI, isolated dependency locks and product split contracts supersede them. |
| `gg-devex-startup-modes` | **SUPERSEDED** | Switchable Codespaces startup behavior is not a production invariant; current explicit production composition roots and Compose contracts supersede it. |
| `gg-pre-session-05-live-plus` | **SUPERSEDED / HISTORICAL COURSEWORK** | Actor/critic, session and tool experiments are represented by later Session 13/14 estimator and EACHAT/EACODE domain implementations. The duplicate `estimator/` prototype is not a current product boundary. |
| `gg-pre-session-06-cag-stress-test` | **SUPERSEDED / HISTORICAL COURSEWORK** | Unique delta is stress-report/devcontainer documentation; current evaluation/resilience work has a stronger versioned portfolio contract. |
| `gg-session-06-live-completion` | **SUPERSEDED** | LiteLLM timeout/stress work is historical input. Current bounded provider routing, deterministic CI separation and product-level timeout/recovery policies supersede the old startup hook. |
| `gg-session-07-pre-exercise` | **SUPERSEDED** | Only unique delta is a historical devcontainer setting. |
| `gg-session-08-homework-submission` | **HISTORICAL COURSEWORK** | Query/output examples were submission evidence, not production runtime. Session 08 retrieval functionality is already represented in canonical estimator history and current retrieval components. |
| `gg-session-13/plus-stabilization` | **SUPERSEDED BY CONSOLIDATED MAIN** | This was an intermediate stabilization line. `gg-session-13/plus`, Session 14 consolidation and the current `main` product contain the accepted evolutionary path; its unique CI/cleanup iterations are not a separate runtime source of truth. |
| `ggc-codespaces-recovery` | **DELIBERATELY REJECTED AS CURRENT STATE** | Temporarily disabling the devcontainer was a recovery maneuver. Preserving it as a live branch would reintroduce ambiguity and conflict with the stabilized environment. |

## Ancestor branches

Every other historical branch listed in `BRANCH_ARCHAEOLOGY_2026-08-21.md` is already reachable from at least one canonical branch. Deleting those branch names removes navigation clutter only; it does not remove their commits from canonical ancestry.

## Claim boundary

Branch cleanup does **not** mean every historical implementation is production-supported. It means the useful knowledge/evidence has either reached a canonical product or has an explicit historical disposition, leaving exactly three active evolutionary product lines without silently discarding known valuable work.
