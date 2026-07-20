# Spec 0010 — Acceptance

Status: partial implementation; recovery gates open

## Documentation acceptance

- [x] Product preference for Kimi is separated from benchmark claims.
- [x] GPT-5.6 uses Luna/Terra/Sol product naming rather than obsolete nano/instant assumptions.
- [x] EACODE, EACHAT, task branches, and EACORE boundaries are explicit.
- [x] Context compaction is designed to preserve immutable source-of-truth records.
- [x] Multi-agent consensus is not treated as authority.
- [x] Rescue audit records provider, selector, and Spec 0009 drift.
- [x] Kimi K3 documentation reflects current low/high/max Kimi Code effort support.
- [ ] Every runtime capability fixture is refreshed and source-versioned from current official documentation.

## Runtime acceptance — selector and registry

### Implemented deterministic evidence

- [x] Provider selection contract accepts auto/deepseek/kimi/openai.
- [x] Profiles accept minimal/medium/max.
- [x] Unknown provider/profile combinations fail closed.
- [x] Explicit DeepSeek, Kimi, and OpenAI selections resolve deterministically against curated fixtures.
- [x] Auto selection defaults to DeepSeek.
- [x] Deterministic capability snapshot hashes are produced.
- [x] Keyless deterministic tests run in CI.

### Required repair evidence

- [ ] DeepSeek context, output, cache, effort, and price fixtures match current official facts.
- [ ] Kimi API and Kimi Code model surfaces are represented separately.
- [ ] K3 low/high/max and K2.7 Code context/entitlement facts are represented correctly.
- [ ] GPT-5.6 context, output, effort, and price fixtures match current official facts.
- [ ] Capability records contain source identity, version, price units, and freshness state.
- [ ] Explicitly supplied empty/custom registries do not silently load or mutate defaults.
- [ ] Budget estimation uses explicit input, cached-input, and output token quantities.
- [ ] Budget checks apply to every provider.
- [ ] OpenAI escalation requires explicit premium reason and authorization.
- [ ] Requested, planned, and served provider/model/effort remain distinct facts.
- [ ] Exact served model and effort are recorded only from live-provider evidence.
- [ ] Cross-provider fallback records retries and circuit state.
- [ ] Cross-provider fallback never bypasses critics or the deterministic decider.
- [ ] UI/API disable unsupported, stale, unavailable, or unentitled combinations.

## Runtime acceptance — Spec 0009 dependency

These gates must pass before EACODE can rely on live-process evidence:

- [ ] `dry_run` plans cannot start real processes.
- [ ] `fake` or `allow_fake` plans cannot start real processes.
- [ ] Real process execution requires explicit typed live intent.
- [ ] Authorization binds to exact plan hash and exact repository snapshot.
- [ ] Repository snapshot covers HEAD, tree, staged diff, unstaged diff, and untracked state/digest.
- [ ] Authorization receipt provenance is verified against an authoritative store or integrity contract.
- [ ] Cancellation is observed promptly during execution.
- [ ] Unix process-group cleanup is structurally valid and demonstrated.
- [ ] Windows cleanup result is checked rather than assumed.
- [ ] Cleanup uncertainty fails closed.
- [ ] Output truncation flags are accurate.
- [ ] Cross-chunk and final-output redaction fixtures pass.
- [ ] A harmless opt-in manual process smoke is recorded without secrets.
- [ ] Timeout and complete process-tree cleanup are demonstrated on the host OS.

## Runtime acceptance — compaction

- [ ] Local interrupted compaction work is inspected before reuse.
- [ ] Raw events and source artifacts remain immutable.
- [ ] Every summary records source ranges and hashes.
- [ ] Hard constraints survive all profiles.
- [ ] Evidence and decision references remain resolvable.
- [ ] Branch, repository snapshot, policy, and schema freshness are checked.
- [ ] Secrets are absent from durable summaries.
- [ ] Hidden chain of thought is not persisted.
- [ ] Loss-audit fixtures pass for minimal, medium, and max profiles.
- [ ] Failed loss audit blocks acceptance and triggers rehydration.
- [ ] Hysteresis prevents repeated compaction churn.
- [ ] Contradictory and summary-of-summary decay cases are detected.
- [ ] Quality, contradiction, latency, and token metrics are recorded.

## Runtime acceptance — multi-agent

- [ ] Single-agent quality, safety, cost, and latency baselines exist.
- [ ] Fan-out is bounded by concurrency, cost, time, and tool budgets.
- [ ] Independent agents do not modify the same working tree concurrently.
- [ ] Disagreement is preserved in evidence.
- [ ] Hard constraints cannot be overturned by majority vote.
- [ ] The deterministic boss owns final disposition.
- [ ] A benchmark shows whether multi-agent mode improves over the single-agent baseline.
- [ ] Multi-agent mode is disabled when no measurable gain is shown.

## Product boundaries

- [x] Spec 0009 remains provider-neutral in module ownership.
- [x] EACODE and EACHAT retain product-specific objectives and critics.
- [x] No EACORE runtime extraction is claimed.
- [x] Task extras remain separate from mandatory coursework gates.
- [ ] Provider and compaction contracts are proven independently in both products before extraction.

## Current claim boundary

Allowed:

- architecture and SDD are documented;
- a deterministic provider registry and selector implementation exists;
- provider selection behavior is CI-tested against curated fixtures;
- Spec 0009 implementation and deterministic tests exist and are CI-validated;
- real process execution remains disabled by default;
- recovery defects and required repair gates are documented.

Blocked:

- current provider catalog accuracy until fixture refresh passes;
- live DeepSeek, Kimi K3, or OpenAI routing;
- exact served-model claims;
- safe real-process sandboxing;
- exact Git-snapshot authorization;
- safe context compaction;
- multi-agent quality improvement;
- shared-core readiness;
- production readiness.
