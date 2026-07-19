# Spec 0010 — Tasks

## Documentation checkpoint

- [x] Verify current official DeepSeek V4 model and effort surface.
- [x] Verify Kimi K3 release, IDs, context, and launch effort limitations.
- [x] Verify GPT-5.6 Luna/Terra/Sol API models and effort surface.
- [x] Define EACODE, EACHAT, LIDR task, and EACORE boundaries.
- [x] Define provider-neutral selection profiles.
- [x] Define context-compaction profiles and anti-rot invariants.
- [x] Define bounded multi-agent governance.

## Runtime implementation — deferred until Spec 0009 checkpoint

### Slice A — contracts and fake registry

- [ ] Add strict `ProviderSelection` and `ModelCapability` contracts.
- [ ] Add deterministic curated capability fixtures.
- [ ] Add fake capability registry and unsupported-combination tests.
- [ ] Add `ProviderPlan` with budget and fallback metadata.
- [ ] Keep existing runtime routing unchanged behind a feature flag.

### Slice B — routing policy

- [ ] Implement deterministic minimal/medium/max resolution.
- [ ] Implement explicit provider selection.
- [ ] Implement DeepSeek-default auto policy.
- [ ] Implement Kimi preferred-frontier policy.
- [ ] Implement explicit budget-gated OpenAI escalation.
- [ ] Add circuit-breaker and retry budgets.
- [ ] Add shadow-routing reports.

### Slice C — context compaction contracts

- [ ] Add `CompactionRecord` and source-range/hash contracts.
- [ ] Add structured state projector.
- [ ] Add minimal, medium, and max assemblers.
- [ ] Add threshold hysteresis.
- [ ] Add rehydration references.
- [ ] Add deterministic loss-audit fixtures.
- [ ] Add contradiction and stale-summary detection.

### Slice D — provider adapters

- [ ] Add fake provider adapter for CI.
- [ ] Add opt-in DeepSeek adapter and sanitized smoke.
- [ ] Add opt-in Kimi adapter with K3 capability discovery.
- [ ] Add opt-in OpenAI GPT-5.6 adapter.
- [ ] Record exact served model and effort.
- [ ] Ensure every candidate re-enters product critics and decider.

### Slice E — multi-agent evaluation

- [ ] Establish single-agent baselines.
- [ ] Add bounded parallel critic prototype.
- [ ] Add disagreement and aggregation records.
- [ ] Add cost, latency, tool, and concurrency budgets.
- [ ] Compare quality and safety against the baseline.
- [ ] Disable multi-agent mode when no measurable gain is shown.

### Slice F — product surfaces

- [ ] Add selector API schema.
- [ ] Add UI controls that disable unsupported combinations.
- [ ] Add compact provider/model/effort/context status card.
- [ ] Add browser smoke.
- [ ] Add migration and rollback documentation.

## EACORE extraction gate

- [ ] Prove equivalent stable selector contracts in EACODE and EACHAT.
- [ ] Prove equivalent compaction semantics in both products.
- [ ] Compare product-specific fields and failure modes.
- [ ] Extract only the minimal shared contract with compatibility tests.
