# EACODE Product Completion Plan

Audit date: 2026-07-17  
Product: Energy Aware Code (EACODE)  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`

## Verified current state

- Local and remote branch head: `9482ef454ffae9eddcd24782dd7dcb9f5b21bc3b`.
- PR #4 is open, draft, mergeable, and unmerged. Do not merge it into `main` as routine coursework.
- The checkout was clean before this plan slice.
- Baseline inventory: 65 `energy_core` Python modules, 44 Energy Core test modules, 24 Energy Core smoke scripts, and one spec packet. Phase 1 adds eleven domain/CLI modules, three test modules, and three spec packets.
- The existing product is a deterministic judge with typed contracts, critics, scoring, decisions, reporting, ledger checks, CLI surfaces, and broad deterministic review artifacts.
- The persisted example ledger contains five evidence records and no decisions. This is demonstration data, not production telemetry.
- The full gate is defined, but could not be executed in this environment because `uv` is unavailable. This is an environment blocker, not passing evidence.
- No applicable `AGENTS.md` was found.

## Product vision

EACODE is a provider-neutral supervision product that evaluates proposed coding actions against a versioned specification and policy. It must keep deterministic authorization separate from actors and tools, preserve auditable evidence, bound every loop, and make unsafe or unsupported transitions impossible to approve silently.

## Capability matrix

| Capability | State | Evidence | Maturity judgment |
|---|---|---|---|
| Typed domain contracts | Implemented | `energy_core/models.py`, adapter contracts, schema export | Established |
| Deterministic critics, scorer, decider | Implemented | Unit tests and review surfaces | Established |
| Evidence and decision ledgers | Implemented | Versioning, provenance, hashing, reference integrity, retention, trusted manifests, recovery | Phase 1 trust gate complete |
| CLI and machine-readable reporting | Implemented | CLI modules and smoke scripts | Broad but fragmented |
| Persistent LangGraph orchestration | Implemented | Typed bounded graph, SQLite restart persistence, human interrupts, CLI, traces | Phase 2 gate complete |
| Controlled shell evidence adapter | Missing | Explicit PR exclusion | Phase 3 |
| Bounded repair loop | Missing | No repair orchestration | Phase 4 |
| Live provider adapters | Missing | Explicit PR exclusion | Phase 5 |
| Product API and review UI | Missing | Existing API/UI belong to the host course app | Phase 6 |
| Benchmarks and regression comparison | Partial | Review artifacts exist; benchmark harness absent | Phase 7 |
| Dedicated packaging and extraction | Partial | Extraction plan/readiness reports | Phase 8 |

## Gap matrix

| Gap | User impact | Dependency | Priority | Exit evidence |
|---|---|---|---|---|
| No controlled execution evidence adapter | Accepted proposals cannot produce governed execution evidence | Persistent deterministic graph | P0 | Fake-tool risk, boundary, timeout, redaction, rollback tests |
| No dedicated product review interface | Operators lack one approval and timeline surface | Stable application services | P2 | Workflow-tested API or review console |
| No bounded agentic repair | Repairs cannot be automated safely | Execution evidence | P1 | Budget and non-progress tests |
| No provider-neutral actor layer | Live or fake actors lack one governed contract | Bounded repair state | P1 | Structured fake and adapter contract tests |
| No benchmark harness | Product quality cannot be compared over time | Stable domain scenarios | P1 | Versioned cases and regression report |
| Product is embedded in course repository | Installation and ownership remain unclear | Stable public contracts | P2 | Extraction rehearsal and rollback proof |

## Dependency graph

```text
Phase 0 audit and plan
  -> Phase 1 trust foundation
    -> Phase 2 persistent deterministic graph
      -> Phase 3 controlled shell evidence
        -> Phase 4 bounded repair
          -> Phase 5 provider adapters
            -> Phase 6 developer interfaces
Phase 1 -> Phase 7 benchmarks and observability
Phases 1-7 -> Phase 8 packaging and extraction
```

## Ordered phases

1. Keep this audit and plan synchronized with verified repository evidence.
2. Version and harden evidence and decision records, provenance, referential integrity, append semantics, migrations, and recovery.
3. Add a persistent deterministic LangGraph topology without shell execution.
4. Add a replaceable controlled shell evidence adapter with fake tools in CI and human gates for risk.
5. Add bounded repair with iteration, time, tool, repetition, energy-delta, token, and cost budgets.
6. Add provider-neutral structured actors, deterministic fakes, then opt-in live providers.
7. Consolidate the CLI and add only the API/review console surfaces proven useful by workflow tests.
8. Add benchmark cases, failure injection, regression comparison, telemetry, and developer-UX evaluation.
9. Package, rehearse extraction, document migrations and rollback, then prepare a release candidate.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Judge and executor authority become coupled | Critical | Enforce inward dependencies and separate policy authorization from adapters |
| Ledger claims exceed actual guarantees | High | Document file/application/git semantics and avoid cryptographic language without proof |
| Host course application leaks into core | High | Boundary tests and extraction rehearsal |
| Autonomous loop fails to make progress | High | Hard budgets, repeated-proposal detection, energy-delta gate, escalation |
| Secrets appear in execution evidence | High | Environment allowlist, redaction tests, output limits, artifact hashes |
| Review/report surface proliferation raises maintenance cost | Medium | One canonical report model with thin renderers and consistency tests |
| Optional providers destabilize deterministic CI | Medium | Fake provider required in CI; live smoke remains manual and opt-in |

## Acceptance gates

- Each slice has a spec packet, a failing test that proves the gap, minimal implementation, focused tests, regression evidence, security review, migration/rollback notes, and synchronized docs.
- Deterministic CI never requires credentials, network access, live providers, or real shell execution.
- Persisted schema changes include backward-compatible migration and corrupted-data recovery tests.
- Loops and commands have explicit budgets, working-directory boundaries, output limits, and escalation behavior.
- A release candidate requires clean full gate, reproducible demo, benchmark comparison, threat model, packaging proof, and extraction rollback rehearsal.

## Deferred capabilities

- Live provider calls, public deployment, automatic commit/push, force push, PR state changes, and merging require explicit authorization.
- Aider, Cline, OpenCode, and EACHAT bridges remain adapter work after neutral contracts stabilize.
- Multi-user auth, billing, and hosted infrastructure are deferred until a local product workflow is proven.

## Evidence level

Current confidence is **repository-audited, gate-unverified in this environment**. File inventory, git head, and live PR state were verified on 2026-07-17. Tests and smokes are present, but the full gate was not run because `uv` is unavailable. No capability is considered green solely because a roadmap or report names it.

## Current checkpoint

Phase 0, Phase 1, and Phase 2 are implemented locally. The deterministic judge now runs as a typed LangGraph with explicit reducers, bounded proposal/repair routing, thread/run IDs, graph/policy/spec versions, domain traces, SQLite checkpoint persistence, process-restart recovery, isolated threads, and JSON-safe human interrupts for clarify/escalate routes. It performs no shell or provider execution and delegates authorization to the Python decider. The Phase 2B pre-commit gate passed all functional stages with 416 tests; only the expected cleanliness guard rejected the uncommitted slice. The product is not complete.

## Next slice

Phase 3A: define typed command proposals, deterministic command-risk classification, explicit allow/deny policy, working-directory boundaries, time/output/environment budgets, redaction contracts, dry-run plans, approval requirements, and fake-tool execution evidence. Do not execute real commands in CI and do not add commit or push behavior.
