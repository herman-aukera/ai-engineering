# Spec 0010 — Tasks

Status: rescue checkpoint after interrupted provider session

## Documentation checkpoint

- [x] Define EACODE, EACHAT, LIDR task, and EACORE boundaries.
- [x] Define provider-neutral selection profiles.
- [x] Define context-compaction profiles and anti-rot invariants.
- [x] Define bounded multi-agent governance.
- [x] Record the 2026-07-20 provider and execution rescue audit.
- [x] Correct the obsolete Kimi K3 max-only documentation assumption.
- [ ] Re-verify every curated provider capability and price against current official sources in code fixtures.

## Recovery gate — mandatory before new feature work

- [ ] Close or stop competing agent sessions.
- [ ] Inspect the local EACODE working tree and preserve interrupted files.
- [ ] Compare local HEAD and diff with `origin/EACODE` without destructive commands.
- [ ] Identify the local-only `context_compaction.py` and related tests/docs, if present.
- [ ] Classify each local file as keep, repair, rewrite, or discard-with-evidence.
- [ ] Run `git diff --check` before implementation edits.
- [ ] Do not commit or push without explicit user approval.

## Slice A — provider contracts and deterministic registry

Implemented but requiring repair:

- [x] Add strict `ProviderSelection` and `ModelCapability` contracts.
- [x] Add deterministic curated capability fixtures.
- [x] Add capability registry and unsupported-combination tests.
- [x] Add deterministic resolved-provider/plan metadata.
- [x] Keep live provider calls out of deterministic CI.

Repair work:

- [ ] Add explicit source identity/version and price units to capability records.
- [ ] Correct DeepSeek V4 context, output, cache, effort, and pricing data.
- [ ] Distinguish Kimi API `kimi-k3` from Kimi Code `k3`.
- [ ] Add Kimi Code `kimi-for-coding-highspeed` as entitlement-dependent.
- [ ] Correct K3 effort support to low/high/max and K2.7 Code context limits.
- [ ] Correct GPT-5.6 Luna/Terra/Sol context, output, and pricing data.
- [ ] Remove mutable module-global registry state.
- [ ] Preserve explicitly supplied empty registries rather than silently loading defaults.
- [ ] Add capability freshness/staleness tests.

## Slice B — deterministic routing policy

Implemented but requiring repair:

- [x] Implement deterministic minimal/medium/max resolution.
- [x] Implement explicit provider selection.
- [x] Implement DeepSeek-default auto policy.
- [x] Add governed cross-provider fallback metadata.

Incomplete or defective:

- [ ] Replace fixed 100K-input-only cost estimation with explicit input/output/cached-token assumptions.
- [ ] Enforce budgets across every provider.
- [ ] Require explicit premium reason and authorization for OpenAI escalation.
- [ ] Add retry and circuit-breaker state.
- [ ] Add shadow-routing reports.
- [ ] Distinguish planned provider/model from externally served provider/model.
- [ ] Prove every fallback candidate re-enters critics and the deterministic decider.

## Slice C — Spec 0009 security repair dependency

This repair blocks context compaction and live provider work:

- [ ] Add a red test proving `dry_run` plans cannot invoke a real process.
- [ ] Add a red test proving `fake`/`allow_fake` plans cannot invoke a real process.
- [ ] Add explicit typed live-execution intent and authority transition.
- [ ] Bind authority to HEAD, tree, staged diff, unstaged diff, and untracked-state digest.
- [ ] Verify authorization-receipt provenance or authoritative-store lookup.
- [ ] Start Unix children in a dedicated process group/session before using `killpg`.
- [ ] Verify Windows and Unix cleanup results; do not assume success.
- [ ] Make cancellation polling prompt rather than waiting for the command timeout.
- [ ] Correct truncation flags when reader budgets are reached.
- [ ] Add cross-chunk and final-assembly secret-redaction tests.
- [ ] Fail closed when cleanup or output sanitation cannot be proven.
- [ ] Run focused Spec 0007/0008/0009 regression tests.

## Slice D — context compaction contracts

Do not begin until the recovery gate and Slice C are green.

- [ ] Audit and recover or reject interrupted local compaction work.
- [ ] Add `CompactionRecord` and source-range/hash contracts.
- [ ] Add structured state projector.
- [ ] Add minimal, medium, and max assemblers.
- [ ] Add threshold hysteresis.
- [ ] Add branch/repository-snapshot/policy/schema freshness guards.
- [ ] Add rehydration references.
- [ ] Add deterministic loss-audit fixtures.
- [ ] Add contradiction and stale-summary detection.
- [ ] Add summary-of-summary decay detection.

## Slice E — provider adapters

- [ ] Add fake provider adapter for CI.
- [ ] Add opt-in DeepSeek adapter and sanitized smoke.
- [ ] Add opt-in Kimi Code adapter with K3 capability discovery.
- [ ] Add opt-in OpenAI GPT-5.6 adapter.
- [ ] Record exact served provider, model, effort, request ID, latency, tokens, and cost.
- [ ] Ensure every candidate re-enters product critics and decider.
- [ ] Add clean-session handoff tests for model/effort/provider switching.

## Slice F — multi-agent evaluation

- [ ] Establish single-agent baselines.
- [ ] Add bounded parallel critic prototype.
- [ ] Add disagreement and aggregation records.
- [ ] Add cost, latency, tool, and concurrency budgets.
- [ ] Compare quality and safety against the baseline.
- [ ] Disable multi-agent mode when no measurable gain is shown.

## Slice G — product surfaces

- [ ] Add selector API schema.
- [ ] Add UI controls that disable unsupported or unavailable combinations.
- [ ] Add compact requested/planned/served provider status card.
- [ ] Add context-profile control and compaction status.
- [ ] Add browser smoke.
- [ ] Add migration and rollback documentation.

## EACORE extraction gate

- [ ] Prove equivalent stable selector contracts in EACODE and EACHAT.
- [ ] Prove equivalent compaction semantics in both products.
- [ ] Compare product-specific fields and failure modes.
- [ ] Extract only the minimal shared contract with compatibility tests.
