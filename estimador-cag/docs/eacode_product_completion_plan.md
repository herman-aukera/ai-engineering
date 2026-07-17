# EACODE Product Completion Plan

Audit date: 2026-07-17  
Product: Energy Aware Code (EACODE)  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`

## Verified current state

- Historical audited baseline before the Codex completion run: `9482ef454ffae9eddcd24782dd7dcb9f5b21bc3b`.
- Phase 0-2 checkpoint before controlled execution work: `1d15dc3c06e0918781b945399b13351b1a86f005`.
- PR #4 remains open, draft, mergeable, and unmerged. Do not merge it into `main` as routine coursework.
- The deterministic core includes typed policies, candidates, evidence, critics, scoring, decisions, ledgers, integrity checks, recovery, retention, manifests, CLI review surfaces, a persistent LangGraph judge, SQLite restart persistence, and typed human clarification/escalation.
- Spec 0007 adds typed controlled-execution proposals, deterministic risk policy, repository/path/symlink boundaries, budgets, redaction, a fake tool port, dry-run/fake evidence, and graph reevaluation.
- Spec 0008 adds exact revision-guarded human execution authorization, trusted actors, expiry, one-time nonce replay protection, strict scope, rollback acknowledgement, CLI verification/consumption, a separate persisted LangGraph interrupt, sanitized state, receipts, and authorization evidence.
- Remote CI run `29610364281` passed Ruff, compilation, Energy Core boundary checks, all tests, all smoke scripts, the canonical full gate, root smoke, and repository cleanliness for head `715555a47f1c4b3a78f46056e0c8548307d670ec`.
- No real subprocess execution, provider calls, commits, pushes, merges, resets, or execution side effects have been added.

## Product vision

EACODE is a provider-neutral coding supervision product. Models, tools, shell adapters, and IDE agents may propose actions, but deterministic Python policy owns evidence sufficiency, hard constraints, constraint energy, budgets, authorization requirements, and final disposition.

The operating principle remains:

```text
First build the judge.
Then give it controlled hands.
The hands never approve themselves.
```

## Capability matrix

| Capability | State | Evidence | Maturity judgment |
|---|---|---|---|
| Typed domain contracts | Implemented | strict Pydantic models, schema export, contract tests | established |
| Deterministic critics, scorer, decider | Implemented | unit tests and review surfaces | established |
| Evidence and decision ledgers | Implemented | versioning, provenance, hashing, referential integrity, retention, manifests, recovery | Phase 1 complete |
| Persistent LangGraph orchestration | Implemented | typed bounded graph, SQLite restart persistence, thread isolation, human interrupts, CLI | Phase 2 complete |
| Controlled execution planning | Implemented | command contracts, risk policy, root/path/symlink checks, budgets, plan hashing | Spec 0007 complete |
| Dry-run and fake execution evidence | Implemented | fake adapter, redaction, truncation, normalized evidence, graph reevaluation | L2 deterministic evidence |
| Revision-guarded execution authorization | Implemented | exact hash/revision/scope, actor, expiry, nonce, receipt, SQLite restart | Spec 0008 complete |
| Real sandboxed tool adapter | Missing | no subprocess implementation | delegated next phase |
| Bounded actor repair | Missing | current graph retries supplied candidates only | after controlled tool proof |
| Provider-neutral actor layer | Missing | no fake/live actor contract in EACODE | after bounded repair contract |
| Product API and review console | Missing | host coursework UI is not an EACODE product surface | later phase |
| Benchmark comparison | Partial | implementation tests and reports exist; agent baseline benchmark absent | later phase |
| Dedicated packaging and extraction | Partial | extraction plans exist; product remains embedded | release phase |

## Gap matrix

| Gap | User impact | Dependency | Priority | Exit evidence |
|---|---|---|---|---|
| No real sandboxed adapter | no real command can produce governed execution evidence | Specs 0007 and 0008 | P0 | controlled local/manual smoke, failure injection, timeout and cleanup evidence |
| No real bounded repair actor | critics cannot request and evaluate generated candidate v2 | stable controlled tool evidence | P1 | repetition, energy-improvement, and budget tests |
| No provider-neutral actor | DeepSeek/Kimi cannot participate through one governed contract | bounded repair contract | P1 | fake actor CI and manual provider smoke |
| No benchmark harness | quality and safety gains cannot be compared | stable end-to-end scenarios | P1 | versioned baseline/regression report |
| No dedicated review interface | operator lacks one plan, authorization, evidence, and timeline surface | application services plus controlled adapter | P2 | browser-tested review console |
| Product remains in course repository | installation and ownership remain unclear | stable package boundary | P2 | extraction rehearsal and rollback proof |

## Dependency graph

```text
Phase 0 audit and plan
  -> Phase 1 trust foundation
    -> Phase 2 persistent deterministic judge
      -> Phase 3A controlled execution preview and fake evidence
        -> Phase 3B revision-guarded human execution authorization
          -> Phase 3C real sandboxed tool adapter
            -> Phase 4 bounded repair actor
              -> Phase 5 provider adapters
                -> Phase 6 review API/UI
Phase 1-6 -> Phase 7 benchmark, security, and observability evidence
Phases 1-7 -> Phase 8 packaging, release, and extraction rehearsal
```

## Ordered phases

1. Keep this plan synchronized with current branch, PR, CI, specs, and evidence.
2. Preserve the deterministic trust foundation and persistent judge.
3. Preserve Specs 0007 and 0008 as the non-executing policy and authorization boundary.
4. Delegate the real sandboxed adapter to a local coding agent that can inspect the OS and repository, execute tests repeatedly, and produce controlled manual evidence.
5. Require no-shell process creation, minimal environment, immediate root/symlink revalidation, timeout, cancellation, process-tree cleanup, bounded streaming, redaction, rollback evidence, failure injection, and disabled-by-default configuration.
6. Add immutable candidate versions and bounded repair with repetition, energy-delta, time, tool, token, and cost budgets.
7. Add a provider-neutral fake actor, then opt-in DeepSeek and Kimi adapters outside deterministic CI.
8. Add one workflow-tested API/review console and Code Decision Card only after backend contracts are stable.
9. Add baseline/regression benchmarks, threat-model evidence, telemetry, packaging, demo, and extraction rehearsal.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| judge and executor authority become coupled | critical | adapter returns evidence only; policy and authorization verifier remain independent |
| fake evidence is mistaken for real execution | critical | explicit mode, `execution_performed=false`, claim gates, separate evidence levels |
| stale or replayed human approval | critical | exact plan hash, revision guard, actor, expiry, nonce hash, one-time consumption |
| path or symlink race after planning | high | revalidate immediately before process start and add OS-level boundaries |
| secrets appear in output or environment | high | minimal environment, redaction, bounded output, sanitized artifacts, security tests |
| process survives timeout or cancellation | high | process group isolation and verified process-tree cleanup |
| autonomous repair fails to progress | high | candidate fingerprint, minimum energy improvement, hard budgets, escalation |
| providers destabilize deterministic CI | medium | fake actors in CI; manual sanitized live smoke only |
| shared-core extraction creates coupling | medium | product-local contracts until semantic equivalence is independently proven |

## Acceptance gates

- Every slice has a canonical spec packet, failing contract test or proven gap, minimal implementation, focused tests, full regression, security review, migration/rollback notes, and synchronized documentation.
- Deterministic CI requires no credentials, network, provider calls, or real shell execution.
- Persisted or public contract changes require compatibility and rollback coverage.
- Real execution requires a valid consumed Spec 0008 receipt plus independent pre-start revalidation.
- Real process execution must avoid shell interpolation, use a minimal environment, enforce timeout/cancellation/process-tree cleanup, and remain disabled by default.
- Loops and tools require explicit iteration, repetition, time, output, tool, token, cost, and energy-improvement budgets as applicable.
- UI claims require browser smoke. Provider claims require manual provider evidence. Improvement claims require benchmarks.
- A release candidate requires clean full gate, threat model, reproducible demo, benchmark report, packaging proof, known limitations, and extraction rollback rehearsal.

## Deferred capabilities

- Real shell/tool execution is delegated and blocked until the local sandbox slice passes its deterministic and manual gates.
- DeepSeek, Kimi, and OpenAI calls remain manual and opt-in; no live provider belongs in deterministic CI.
- Aider, Cline, OpenCode, automatic commit/push, force-push, merge, and EACHAT bridges remain deferred.
- Multi-user identity, billing, hosted infrastructure, and production deployment remain deferred until the local workflow and security model are proven.
- Shared Energy Core extraction remains an audit decision, not an implementation default.

## Evidence level

Controlled-execution planning, dry-run/fake evidence, revision-guarded authorization, replay protection, persistence, and graph integration are **L2**: remote deterministic CI is green.

This does not prove real command execution, OS sandbox safety, provider integration, benchmark superiority, browser UX, or production readiness.

## Current checkpoint

Phase 0, Phase 1, Phase 2, Spec 0007, and Spec 0008 are implemented. An accepted candidate may carry a typed command proposal. EACODE can deny it, require human authority, or generate dry-run/fake evidence. Human-required plans enter a separate persisted interrupt and may consume exactly one authorization bound to the plan hash, revision, actor, expiry, scope, reason, and rollback acknowledgement. The graph records a sanitized receipt and reevaluates through the existing deterministic Python decider.

Real execution remains impossible and `execution_performed` remains false.

## Next slice

Delegated Phase 3C: real sandboxed tool adapter.

The implementation must preserve `ToolPort`, require a valid consumed authorization receipt, perform no shell interpolation, construct a minimal environment, revalidate root and symlink boundaries immediately before start, enforce timeout and process-tree cleanup, stream bounded redacted output, record partial-failure and rollback evidence, remain disabled by default, and keep deterministic CI on fake tools.

This is the first slice that requires a local coding agent with operating-system and repository access. Claude Code using DeepSeek is the selected implementation tool.
