# EACODE Handoff Status

Date: 2026-07-20  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`  
PR: #4 open draft; PR #12 open draft  
Do not merge as routine coursework

## Current maturity

- Phase 0: audit and product completion plan — complete.
- Phase 1: versioned trust, hashing, recovery, retention, and manifests — complete.
- Phase 2: persistent deterministic LangGraph judge, SQLite restart, human clarification/escalation — complete.
- Phase 3A / Spec 0007: controlled planning plus dry-run/fake evidence — complete and L2 validated.
- Phase 3B / Spec 0008: logical-revision one-time authorization — complete and L2 validated.
- Phase 3C / Spec 0009: sandboxed-tool implementation and deterministic tests — present and L2 validated; security repair and trustworthy L3 proof remain open.
- Spec 0010 provider registry/selector: deterministic implementation present and CI validated against curated fixtures; current capability facts and routing contracts require repair.
- Spec 0010 context compaction: interrupted local work may exist; not present or proven at the audited remote checkpoint.
- Provider actors, served-model evidence, autonomous repair, and multi-agent runtime — not implemented in EACODE.

## Completed deterministic boundary

### Spec 0007

- strict command proposal, policy, plan, fake result, and evidence contracts;
- deterministic executable and argument policy;
- root, working-directory, path-traversal, and symlink-escape checks;
- timeout, output, and environment-name budgets;
- deterministic plan hashing;
- secret redaction and output truncation;
- fake tool port and adapter;
- dry-run and fake evidence with `execution_performed=false`;
- conversion to the existing `EvidenceRecord`;
- controlled-execution preview CLI;
- optional judge-graph preview, evidence append, and deterministic reevaluation.

### Spec 0008

- strict authorization scope, authorization, context, decision, and receipt contracts;
- exact plan-hash and logical integer-revision binding;
- explicit trusted actors;
- timezone-aware creation and expiry;
- one-time nonce hashing and replay rejection;
- exact scope and rollback-acknowledgement checks;
- deterministic verify and consume operations;
- verify/consume CLI with replay-safe artifacts;
- separate execution-authorization LangGraph interrupt;
- SQLite restart/resume proof;
- sanitized consumed authorization, receipt, and normalized evidence;
- cancellation and fail-closed graph paths;
- `execution_authorized` and `execution_performed` preserved as distinct facts.

Spec 0008 does not yet bind authorization to a complete Git repository snapshot.

### Spec 0009 implementation present

- `SandboxedToolConfig` with `enabled=False` by default;
- independent pre-start verifier;
- structured `subprocess.Popen` argument sequence with `shell=False`;
- bounded environment allowlist;
- concurrent stdout/stderr readers;
- timeout/cancellation/result contracts;
- platform-specific process-tree cleanup attempts;
- typed `RealToolResult` and normalized execution evidence;
- deterministic `FailureInjectingAdapter`;
- CLI with explicit `--live-tool` gate;
- deterministic security and failure tests;
- destructive Git subcommands denied.

This implementation is not accepted as safely complete until the repair gates below pass.

### Spec 0010 deterministic registry/selector present

- `ProviderSelection`, `ModelCapability`, `PricingSnapshot`, and `ResolvedProvider` contracts;
- deterministic capability registry;
- minimal/medium/max profile mapping;
- DeepSeek-default auto selection;
- explicit DeepSeek, Kimi, and OpenAI selection;
- governed cross-provider fallback metadata;
- deterministic capability hash;
- keyless tests and CI.

This proves implementation behavior against its fixtures, not current provider truth or live routing.

## Validation evidence

Remote CI run `29746712434` validated EACODE head `111b5afcc77519f08de51cf82d2aec157167b7f2` and passed.

That evidence supports deterministic implementation claims at L2. It does not prove live Kimi/DeepSeek/OpenAI execution, current pricing/catalog accuracy, context-compaction runtime, or safe real-process behavior.

The repository evidence file for Spec 0009 records CI and that Python/uv were unavailable locally at the time. It does not contain an accepted harmless live-process smoke artifact. Therefore documentation must not claim the complete L3 manual gate is proven.

## Mandatory rescue findings

Canonical audit:

```text
docs/eacode_provider_execution_rescue_audit_2026-07-20.md
```

### Spec 0009 critical blockers

1. `dry_run` and `fake` plans must never be promoted into real process execution by enabling the adapter.
2. Real execution needs explicit typed live intent and authority.
3. Authorization needs exact repository-snapshot binding: HEAD, tree, staged diff, unstaged diff, and untracked state/digest.
4. Receipt provenance or authoritative-store verification is required.
5. Unix child process-group setup and cleanup verification are incomplete.
6. Windows cleanup result is not currently proven before reporting success.
7. Cancellation responsiveness, truncation flags, cross-chunk redaction, and final-output sanitation need red-test repair.
8. Cleanup uncertainty must fail closed.

### Spec 0010 critical blockers

1. Provider fixtures contain stale context, output, effort, cache, and pricing values.
2. Kimi API and Kimi Code surfaces must be distinguished.
3. K3 now supports low/high/max effort in Kimi Code; the old max-only assumption is obsolete.
4. Planned route and exact externally served route must remain distinct facts.
5. Budget estimates need explicit input/output/cached-token assumptions and all-provider enforcement.
6. OpenAI premium escalation needs explicit reason and authorization.
7. Retry/circuit state, live capability probes, provider adapters, critic re-entry evidence, and UI remain incomplete.
8. Module-global registry mutation and empty-custom-registry fallback require repair.

### Interrupted context-compaction work

The user screenshot shows a local agent wrote approximately 338 lines to `energy_core/context_compaction.py` before an API connection failure. That file was not present at the audited remote head.

The next agent must inspect the local working tree before writing or pulling over it. Do not reset, clean, restore, or overwrite uncommitted work blindly.

## Current claim boundary

Allowed:

- EACODE can deterministically plan, deny, or human-gate structured command proposals.
- EACODE can produce bounded dry-run and fake evidence.
- EACODE has one-time plan-hash/logical-revision authorization with persistent graph interruption.
- EACODE has a disabled-by-default sandboxed-tool implementation and deterministic tests.
- EACODE has a deterministic provider registry and selector implementation.
- Current remote CI validates these deterministic paths against current repository tests.
- Recovery defects and repair acceptance gates are documented.

Blocked:

- safe production or host-level sandboxing;
- reliable complete process-tree cleanup;
- exact Git-snapshot authorization;
- trustworthy authorization-receipt provenance;
- live provider routing or exact served-model evidence;
- current provider catalog accuracy until fixture refresh;
- safe context compaction;
- autonomous repair quality;
- multi-agent quality improvement;
- browser product readiness;
- production readiness.

## Required continuation order

```text
1. Stop competing local agent sessions.
2. Inspect local EACODE HEAD, status, and interrupted diff.
3. Fetch and compare origin/EACODE without destructive reconciliation.
4. Preserve useful local work and identify conflicts with the recovery documentation.
5. Repair provider facts and registry tests.
6. Repair Spec 0009 security invariants through failing tests first.
7. Run focused and full deterministic gates.
8. Ask the user before commit or push.
9. Resume context compaction as an isolated slice.
10. Start Kimi K3 in a fresh provider session, not inside the failed DeepSeek session.
```

## Provider migration recommendation

The observed `ENOTFOUND` error indicates name-resolution/network failure. It does not prove exhausted DeepSeek credit. Do not add balance solely to address that error.

A fresh Kimi Code-backed Claude Code session is an appropriate continuation path after local-state inspection:

- main role: Kimi K3 at max effort;
- lower-cost planning/subagent role: `kimi-for-coding`;
- fresh provider session after switching;
- exact branch, SHA, local diff, and recovery audit included in the continuation prompt.
