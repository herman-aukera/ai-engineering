# Spec 0010 — Tasks

Status: deterministic runtime complete; live/manual/product-extraction gates open

## Recovery and source correction

- [x] Stop direct repair on `EACODE` and use isolated PR #15.
- [x] Preserve the restored green EACODE checkpoint.
- [x] Audit stale provider, execution, compaction, boss, API, and documentation claims.
- [x] Re-verify mutable provider facts against official sources.
- [x] Remove temporary diagnostics after repair.

## Provider contracts and routing

- [x] ProviderSelection and ModelCapability contracts.
- [x] Distinct DeepSeek API, Kimi Platform, Kimi Code, and OpenAI surfaces.
- [x] Verified capability overlay with source/version/freshness/entitlement.
- [x] Correct DeepSeek and OpenAI price units and values in the verified overlay.
- [x] Conservative Kimi Code K3/K2.7 context and effort contracts.
- [x] Explicit empty/custom registry behavior.
- [x] Input, cached-input, output, cost, latency, and premium-reason budgets.
- [x] Requested/planned/configured/served distinction.
- [x] Unsupported, stale, unavailable, and unentitled API routes fail closed.

## Spec 0009 dependency

- [x] Typed live plan and intent.
- [x] Fake/dry-run non-promotion tests.
- [x] Complete repository snapshot binding.
- [x] Authoritative SQLite receipt integrity and provenance.
- [x] Atomic reservation and one-time completion.
- [x] Process-group/session lifecycle, prompt cancellation, timeout, and verified cleanup.
- [x] Accurate truncation and final redaction.
- [x] Secure CLI and legacy real-adapter shutdown.
- [x] Provider/tool evidence re-enters deterministic boss.

## Context compaction

- [x] CompactionRecord, source range, hashes, and rehydration references.
- [x] Minimal, medium, and max profiles.
- [x] Trigger/release hysteresis.
- [x] Repository snapshot, policy, schema, source-hash, and age freshness.
- [x] Secret and hidden-reasoning exclusion.
- [x] Loss audit and failed-audit rehydration.
- [x] Contradiction, failing-gate, and summary-decay detection.

## Provider adapters

- [x] Fake provider adapter for CI.
- [x] Hardened opt-in DeepSeek adapter.
- [x] Hardened opt-in Kimi Code adapter.
- [x] Hardened opt-in OpenAI adapter.
- [x] Correct endpoints and timeout conversion.
- [x] Provider-specific reasoning controls.
- [x] Sanitized failure evidence.
- [x] Served effort recorded only from provider echo.
- [x] Provider evidence re-enters critics and boss.

## Multi-agent governance

- [x] Typed roles, shared state, independent ownership, and disagreement records.
- [x] Empty/invalid findings escalate.
- [x] Hard constraints cannot be outvoted.
- [x] Per-agent cost, latency, and tool budgets.
- [x] Global cost, latency, tool, agent-count, and concurrency budgets.
- [x] Budget overrun escalates.
- [x] Deterministic boss owns final disposition.

## Product surface

- [x] Register a real FastAPI EACODE router.
- [x] Add status, capability, and deterministic selection endpoints.
- [x] Add same-origin selector UI.
- [x] Separate requested, planned, and served state.
- [x] Add Kimi Code entitlement confirmation and fail-closed route handling.
- [x] Add API and HTML contract tests.

## Benchmark

- [x] Add matched synthetic single-unchecked baseline.
- [x] Add deterministic governed-boss evaluation.
- [x] Report expected-disposition accuracy and delta.
- [x] Fail closed on empty cases.
- [x] Refuse to claim improvement when modes tie.
- [x] State contract-only benchmark boundary.

## Documentation and integration

- [x] Add authoritative 2026-07-22 release checkpoint.
- [x] Synchronize README_EACODE, CLAUDE memory, handoff, and product plan.
- [x] Synchronize Specs 0009/0010 tasks and acceptance.
- [x] Append final repair-branch CI evidence.
- [ ] Update PR #15 title/body and mark ready.
- [ ] Merge PR #15 into `EACODE` after final green CI.
- [ ] Verify post-merge EACODE CI.

Final clean repair-branch gate before merge:

```text
GitHub Actions run 29910822380 — SUCCESS
Ruff, compilation, full tests, every smoke, canonical full gate,
root smoke, and repository cleanliness passed.
```

## Manual evidence

- [ ] Harmless secure live-tool smoke.
- [ ] Windows timeout/cancellation/process-tree cleanup proof.
- [ ] Live DeepSeek smoke.
- [ ] Live Kimi Code smoke with entitlement.
- [ ] Live OpenAI smoke.
- [ ] Browser smoke of `/eacode/ui`.
- [ ] Matched live provider/agent quality, cost, and latency evaluation.

## EACORE extraction gate

- [ ] Prove equivalent stable selector contracts in EACHAT.
- [ ] Prove equivalent compaction semantics in EACHAT.
- [ ] Compare product-specific fields and failure modes.
- [ ] Extract only the minimal compatible shared contract with rollback tests.
