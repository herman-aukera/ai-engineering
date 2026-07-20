# EACODE Provider and Execution Rescue Audit — 2026-07-20

Status: canonical recovery checkpoint  
Repository: `herman-aukera/ai-engineering`  
Branch audited: `EACODE`  
Audited remote head before this document: `111b5afcc77519f08de51cf82d2aec157167b7f2`  
Remote CI at that head: run `29746712434`, success

## 1. Working-mode classification

This is:

```text
EACODE rescue/recovery
+ source-of-truth audit
+ provider migration planning
```

It is not Session 13/14 coursework implementation, EACHAT implementation, or EACORE extraction.

## 2. Verified completed remote work

The remote EACODE branch contains:

- Spec 0007 controlled planning and fake/dry-run evidence;
- Spec 0008 one-time authorization contracts and persistent graph interrupt;
- Spec 0009 sandboxed-tool SDD, implementation, CLI, deterministic failure adapter, and tests;
- Spec 0010 provider capability registry and deterministic selector implementation;
- CI-success evidence for head `111b5af`.

The branch is open under draft PR #4. PR #12 remains open and draft; it is not merged according to GitHub metadata. Spec 0009 code is present on EACODE, so documentation must say integrated or incorporated, not merged through PR #12.

## 3. Local-only interrupted work

The user screenshot shows an agent wrote approximately 338 lines to:

```text
energy_core/context_compaction.py
```

before provider connectivity failed. That file is not present at remote head `111b5af`.

Therefore the next agent must treat local context-compaction files as untrusted, uncommitted recovery candidates:

1. inspect `git status --short -uall`;
2. inspect every local diff;
3. preserve useful work;
4. reject or rewrite code that lacks red tests or violates Spec 0010;
5. do not reset, clean, restore, or overwrite blindly.

## 4. Provider-fact drift

The current `provider_registry.py` is deterministic and tested, but several curated values are stale or incorrect relative to current official documentation.

### DeepSeek

Current official V4 API facts include:

- `deepseek-v4-flash` and `deepseek-v4-pro`;
- 1M context;
- up to 384K output;
- thinking and non-thinking modes;
- thinking efforts `high` and `max`;
- current cache-hit/cache-miss/output prices published per 1M tokens.

The registry currently stores 128K context, 8K output, no prompt-cache support, and stale Pro pricing.

### Kimi Code

Current official Kimi Code facts include:

- `k3` for Kimi K3;
- `kimi-for-coding` for Kimi K2.7 Code;
- `kimi-for-coding-highspeed` for K2.7 Code HighSpeed;
- K3 supports `low`, `high`, and `max` effort, defaulting to `max`;
- K3 supports up to 1,048,576 context tokens subject to membership entitlement;
- K2.7 Code uses 262,144 context tokens;
- turning thinking off routes K3/K2.7 requests to K2.6;
- model or effort switches invalidate prompt-cache economics and should start a new session.

The registry currently models K3 as max-only and stores K2.7 Code at 128K.

The product must distinguish the Kimi general API ID `kimi-k3` from the Kimi Code model ID `k3`. EACODE's coding-agent integration should prefer the Kimi Code surface when using membership credits through Claude Code or Kimi Code.

### OpenAI GPT-5.6

Current official API facts include:

- `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`;
- 1,050,000 context;
- 128,000 max output;
- efforts `none`, `low`, `medium`, `high`, `xhigh`, and `max`;
- current official pricing substantially differs from the registry values.

The registry currently stores 128K context, 16K output, and stale pricing.

## 5. Provider-selector implementation gaps

Green tests currently prove deterministic behavior against the implementation's own fixtures. They do not prove current provider truth or live routing.

Remaining defects and missing contracts:

1. capability facts and tests must be refreshed from official sources;
2. capability snapshots need source identity/version, not only a date;
3. empty custom registries must not silently fall back to defaults;
4. the module-level default registry must not retain mutable cross-test/process state;
5. budget estimation must use explicit input/output token assumptions and current prices;
6. budget checks must apply consistently, not only to OpenAI;
7. premium escalation requires an explicit reason/authorization contract;
8. `ResolvedProvider` is a planned route, not proof of the model actually served;
9. governed fallback still needs retry/circuit-breaker state and critic re-entry evidence;
10. no live provider adapter, capability probe, or selector UI is implemented in EACODE.

## 6. Spec 0009 execution audit

The implementation is useful, but current claims exceed the proven boundary.

### Critical authorization gap

Spec 0007 plans use execution modes `dry_run` and `fake`, and disposition `allow_fake`. The real adapter currently accepts those plans and can start a real process when `config.enabled=True`.

A fake/dry-run plan must never become real execution merely because a local adapter flag is enabled. Real execution needs an explicit typed live-execution intent and authority transition bound to the exact plan and repository snapshot.

### Repository revision gap

Current authorization uses a logical integer revision. It is not bound to:

- Git HEAD SHA;
- tree SHA;
- staged-diff digest;
- unstaged-diff digest;
- untracked-file digest/state.

The pre-start verifier must compare an exact repository snapshot immediately before process creation.

### Process-control gaps

- Unix process-group cleanup is invoked without proving the child was started in its own process group/session.
- Windows `taskkill` and Unix `killpg` results are ignored, yet cleanup is reported as successful.
- cancellation waits inside `process.wait(timeout=...)` and is not promptly observed;
- cleanup failure does not consistently fail closed.

### Output-control gaps

- stream truncation can occur without setting the truncation flags;
- per-chunk redaction may miss a secret split across chunk boundaries;
- final assembled output needs a second redaction pass before evidence persistence;
- process/stream exceptions are collapsed into a generic cleanup failure without a precise safe failure class.

### Receipt trust gap

The adapter accepts an `AuthorizationReceipt` value but does not prove that it came from the authoritative persisted authorization store. A structurally valid receipt can be constructed in memory. The runtime needs receipt provenance/integrity verification or a trusted store lookup.

## 7. Correct evidence boundary

Allowed now:

- Specs 0007/0008 are deterministic and CI-validated;
- Spec 0009 implementation and tests exist and are CI-validated;
- the real adapter is disabled by default;
- the provider registry and selector exist as deterministic, keyless runtime code;
- no live provider routing or context compaction is remotely proven.

Blocked until repaired and evidenced:

- safe real-process sandboxing;
- reliable process-tree cleanup;
- prompt cancellation responsiveness;
- exact Git-snapshot authorization;
- current/accurate provider capability catalog;
- Kimi K3 live integration;
- context-compaction correctness;
- multi-agent quality improvement;
- production readiness.

## 8. Required recovery order

```text
R0 close or stop all competing agent sessions
R1 inspect local EACODE status and preserve interrupted files
R2 reconcile local head with origin/EACODE without destructive commands
R3 repair provider capability facts and tests
R4 repair Spec 0009 live-intent, repository-snapshot, cleanup, cancellation,
   truncation, and redaction invariants through red tests
R5 run focused and full deterministic gates
R6 commit/push only after explicit user approval
R7 resume context-compaction contracts as a separate slice
R8 configure a fresh Kimi K3 session for continuation
```

Do not implement context compaction or multi-agent orchestration while R3/R4 are unresolved.

## 9. Provider migration recommendation

The observed `ENOTFOUND` error is a network/name-resolution class failure, not proof of insufficient provider credit. Adding DeepSeek balance is unlikely to repair DNS resolution.

A fresh Kimi Code-backed Claude Code session is an appropriate continuation path after the repository recovery checkpoint. Use K3 at max effort for the main repair agent and `kimi-for-coding` for lower-cost subagent/planning work where the client permits distinct model mappings.

Do not switch provider inside the damaged/incomplete session. Start a new session with a compact, source-grounded continuation prompt and exact branch/SHA/diff state.
