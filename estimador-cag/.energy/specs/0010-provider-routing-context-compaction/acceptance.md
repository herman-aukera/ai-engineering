# Spec 0010 — Acceptance

## Documentation acceptance

- [x] Provider facts are based on current official documentation.
- [x] Kimi K3 is represented as available but launch-limited to max effort.
- [x] The product preference for Kimi is separated from benchmark claims.
- [x] GPT-5.6 uses current Luna/Terra/Sol API naming rather than obsolete nano/instant assumptions.
- [x] DeepSeek effort coercion is documented.
- [x] EACODE, EACHAT, task branches, and EACORE boundaries are explicit.
- [x] Context compaction preserves immutable source-of-truth records.
- [x] Multi-agent consensus is not treated as authority.

## Runtime acceptance — required before implementation may be called complete

### Selector

- [ ] Invalid provider/profile combinations fail closed.
- [ ] The UI does not display unsupported effort values as available.
- [ ] DeepSeek minimal, medium, and max resolve deterministically.
- [ ] Kimi K3 max resolves only when capability and entitlement are confirmed.
- [ ] OpenAI escalation requires an explicit budget and reason.
- [ ] The exact served model and effort are recorded.
- [ ] Cross-provider fallback never bypasses critics or the deterministic decider.

### Compaction

- [ ] Raw events and source artifacts remain immutable.
- [ ] Every summary records source ranges and hashes.
- [ ] Hard constraints survive all profiles.
- [ ] Evidence and decision references remain resolvable.
- [ ] Secrets are absent from durable summaries.
- [ ] Hidden chain of thought is not persisted.
- [ ] Loss-audit fixtures pass for minimal, medium, and max profiles.
- [ ] Failed loss audit blocks acceptance and triggers rehydration.
- [ ] Hysteresis prevents repeated compaction churn.
- [ ] Quality, contradiction, latency, and token metrics are recorded.

### Multi-agent

- [ ] Fan-out is bounded by concurrency, cost, time, and tool budgets.
- [ ] Independent agents do not modify the same working tree concurrently.
- [ ] Disagreement is preserved in evidence.
- [ ] Hard constraints cannot be overturned by majority vote.
- [ ] The deterministic boss owns final disposition.
- [ ] A benchmark shows whether multi-agent mode improves over the single-agent baseline.

### Product boundaries

- [ ] Spec 0009 remains provider-neutral.
- [ ] EACODE and EACHAT keep product-specific critics and state.
- [ ] No EACORE runtime extraction occurs without two-product compatibility evidence.
- [ ] Task extras remain isolated from mandatory coursework gates.

## Claim boundary

Until the runtime gates pass, allowed claims are limited to:

- architecture and SDD are documented;
- current model catalogs and capability limitations were verified;
- implementation order and acceptance criteria are defined.

Do not claim runtime routing, superior quality, safe compaction, production multi-agent behavior, or shared-core readiness from this documentation alone.
