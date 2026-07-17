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
- Spec 0007 adds typed controlled-execution proposals, deterministic risk policy, repository/path/symlink boundaries, budgets, redaction, a fake tool port, a dry-run/fake CLI, normalized execution evidence, and optional judge-graph preview plus deterministic reevaluation.
- Spec 0007 does not add real subprocess execution, provider calls, commits, pushes, merges, or execution authorization.
- Remote CI run `29608664559` passed Ruff, compilation, Energy Core boundary checks, all tests, all smoke scripts, the canonical full gate, root smoke, and repository cleanliness for head `d70c88b19b586003a381521fa6778a8844f6a3f0`.

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
| Controlled execution planning | Implemented | `CommandProposal`, risk policy, root/path/symlink checks, plan hashing | Spec 0007 complete |
| Dry-run and fake execution evidence | Implemented | fake adapter, redaction, truncation, normalized `EvidenceRecord`, graph reevaluation | L2 deterministic evidence |
| Real execution authorization | Missing | explicitly excluded | Spec 0008 |
| Real sandboxed tool adapter | Missing | no subprocess implementation | after Spec 0008 |
| Bounded actor repair | Missing | current graph retries supplied candidates only | later phase |
| Provider-neutral actor layer | Missing | no fake/live actor contract in EACODE | later phase |
| Product API and review console | Missing | host coursework UI is not an EACODE product surface | later phase |
| Benchmark comparison | Partial | implementation tests and reports exist; agent baseline benchmark absent | later phase |
| Dedicated packaging and extraction | Partial | extraction plans exist; product remains embedded | release phase |

## Gap matrix

| Gap | User impact | Dependency | Priority | Exit evidence |
|---|---|---|---|---|
| No revision-guarded execution authorization | safe plans cannot receive durable scoped approval | Spec 0007 plan hash and persistence | P0 | stale/replay/expiry/revision tests and restart proof |
| No real sandboxed adapter | no real command can produce execution evidence | authorization plus OS safety design | P0/P1 | controlled manual smoke and failure injection |
| No real bounded repair actor | critics cannot request and evaluate generated candidate v2 | stable execution evidence | P1 | repetition, energy-improvement, and budget tests |
| No provider-neutral actor | DeepSeek/Kimi cannot participate through one governed contract | bounded repair contract | P1 | fake actor CI and manual provider smoke |
| No benchmark harness | quality and safety gains cannot be compared | stable end-to-end scenarios | P1 | versioned baseline/regression report |
| No dedicated review interface | operator lacks one execution-approval and timeline surface | application services and authorization | P2 | browser-tested review console |
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
3. Complete Spec 0007 controlled execution planning and fake/dry-run evidence without real execution.
4. Implement Spec 0008 revision-guarded, one-time execution authorization tied to exact plan hash, actor, expiry, scope, reason, expected revision, and rollback acknowledgement.
5. Delegate the real sandboxed adapter to a local coding agent that can inspect and execute the repository safely; require no-shell process creation, minimal environment, timeout, cancellation, process-tree cleanup, output streaming, redaction, path-race controls, and failure injection.
6. Add immutable candidate versions and bounded repair with repetition, energy-delta, time, tool, token, and cost budgets.
7. Add a provider-neutral fake actor, then opt-in DeepSeek and Kimi adapters outside deterministic CI.
8. Add one workflow-tested API/review console and Code Decision Card only after backend contracts are stable.
9. Add baseline/regression benchmarks, threat-model evidence, telemetry, packaging, demo, and extraction rehearsal.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| judge and executor authority become coupled | critical | adapters return evidence only; policy and authorization verifier remain independent |
| fake evidence is mistaken for real execution | critical | explicit mode, `execution_performed=false`, claim gates, separate evidence levels |
| stale or replayed human approval | critical | exact plan hash, revision guard, actor, expiry, nonce, one-time consumption |
| path or symlink race after planning | high | revalidate immediately before real process start and use OS sandbox boundaries |
| secrets appear in output or environment | high | minimal environment, redaction, bounded output, sanitized artifacts, security tests |
| autonomous repair fails to progress | high | candidate fingerprint, minimum energy improvement, hard budgets, escalation |
| review/report proliferation increases maintenance | medium | one canonical domain projection with thin CLI/API/UI renderers |
| providers destabilize deterministic CI | medium | fake actors in CI; manual sanitized live smoke only |
| shared-core extraction creates coupling | medium | product-local contracts until semantic equivalence is independently proven |

## Acceptance gates

- Every slice has a canonical spec packet, failing contract test or proven gap, minimal implementation, focused tests, full regression, security review, migration/rollback notes, and synchronized documentation.
- Deterministic CI requires no credentials, network, provider calls, or real shell execution.
- Persisted or public contract changes require compatibility and rollback coverage.
- Real execution requires revision-guarded one-time human authorization and independent policy verification.
- Loops and tools require explicit iteration, repetition, time, output, tool, token, cost, and energy-improvement budgets as applicable.
- UI claims require browser smoke. Provider claims require manual provider evidence. Improvement claims require benchmarks.
- A release candidate requires clean full gate, threat model, reproducible demo, benchmark report, packaging proof, known limitations, and extraction rollback rehearsal.

## Deferred capabilities

- Real shell execution is blocked until Spec 0008 authorization and sandbox requirements are green.
- DeepSeek, Kimi, and OpenAI calls remain manual and opt-in; no live provider belongs in deterministic CI.
- Aider, Cline, OpenCode, automatic commit/push, force-push, merge, and EACHAT bridges remain deferred.
- Multi-user authorization, billing, hosted infrastructure, and production deployment remain deferred until the local workflow and security model are proven.
- Shared Energy Core extraction remains an audit decision, not an implementation default.

## Evidence level

Current controlled-execution contracts, dry-run/fake adapter, security policy, and graph integration are **L2**: remote deterministic CI is green.

This does not prove real command execution, OS sandbox safety, provider integration, benchmark superiority, browser UX, or production readiness.

## Current checkpoint

Phase 0, Phase 1, Phase 2, and Spec 0007 Phase 3A are implemented. An accepted coding candidate may now carry an optional typed command proposal. The graph creates a bounded execution plan, denies disallowed actions, classifies human-required actions, produces dry-run or deterministic fake evidence, converts it into the existing evidence contract, and reevaluates through the existing Python decider. Real execution remains impossible and `execution_performed` remains false.

The cross-project learning register records the exact Session 13 Plus and EACHAT source SHAs and keeps borrowed ideas product-local.

## Next slice

Spec 0008: revision-guarded human execution authorization.

Implement strict authorization records containing trusted actor, exact plan hash, expected revision, bounded command scope, expiry, one-time nonce, reason, rollback acknowledgement, and consumed state. Prove stale revision, wrong hash, expired authorization, replay, conflicting nonce, restart/resume, and non-authorized execution all fail closed.

Do not add a real subprocess adapter in the same slice.
