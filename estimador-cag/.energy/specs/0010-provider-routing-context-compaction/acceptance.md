# Spec 0010 — Acceptance

Status: deterministic runtime accepted; live provider/browser/manual quality evidence pending

## SDD and documentation

- [x] Provider preference is separated from benchmark claims.
- [x] DeepSeek, Kimi Platform, Kimi Code, and OpenAI surfaces are explicit.
- [x] EACODE, EACHAT, LIDR, and EACORE boundaries are explicit.
- [x] Context compaction preserves immutable source-of-truth references.
- [x] Multi-agent consensus is evidence, never authority.
- [x] Rescue defects and corrected claim boundaries are recorded.
- [x] Authoritative release checkpoint synchronizes code, tests, specs, and docs.

## Provider registry and routing

- [x] Request supports auto/deepseek/kimi/openai and minimal/medium/max.
- [x] Unknown or unsupported combinations fail closed.
- [x] Explicit and auto routes resolve deterministically.
- [x] Capability snapshots are deterministic.
- [x] Verified overlay records source identity, source version, freshness, entitlement, and consistent price units.
- [x] DeepSeek price/cache and reasoning controls are corrected in the verified overlay.
- [x] Kimi Platform and Kimi Code are distinct.
- [x] Kimi Code K3 low/high/max and conservative context/entitlement are represented.
- [x] K2.7 Code does not invent provider-native effort evidence.
- [x] GPT-5.6 Luna/Terra/Sol pricing is corrected in the verified overlay.
- [x] Explicit empty/custom registries remain explicit and isolated.
- [x] Budget estimation uses input, cached-input, and output quantities.
- [x] Every provider is budget checked.
- [x] OpenAI premium escalation requires an explicit reason.
- [x] Requested, planned, configured, and served facts remain distinct.
- [x] Served effort is recorded only when provider evidence confirms it.
- [x] API fails closed for stale, unavailable, or unentitled routes.
- [x] Deterministic CI is keyless and network-free.

## Live-provider adapter contracts

- [x] Live adapters are disabled by default.
- [x] DeepSeek endpoint, thinking control, effort, timeout conversion, and sanitized errors are tested.
- [x] Kimi Code membership endpoint and K3 effort payload are tested.
- [x] OpenAI endpoint, effort payload, cached-token parsing, and cost evidence are tested.
- [x] HTTP timeout milliseconds are converted to seconds.
- [x] Provider errors do not persist raw credentials or response bodies.
- [x] Provider evidence re-enters deterministic critics and the boss through `EnergyAwareControlPlane`.
- [x] A provider/model/tool never self-authorizes downstream action.

Manual live evidence:

- [ ] Current DeepSeek smoke succeeds with a valid secret.
- [ ] Current Kimi Code smoke succeeds with a valid entitled secret.
- [ ] Current OpenAI smoke succeeds with a valid secret.
- [ ] Live provider/model/request/token/latency/cost evidence is sanitized and retained.

## Spec 0009 dependency

- [x] Fake and dry-run plans cannot start real processes.
- [x] Typed live intent and authority are mandatory.
- [x] Authority binds to plan hash and complete repository snapshot.
- [x] Receipt provenance is verified through an authoritative integrity store.
- [x] Cancellation, timeout, cleanup, truncation, and redaction fail closed.
- [x] Secure execution evidence re-enters deterministic critics and the boss.
- [ ] Harmless host process smoke is recorded.
- [ ] Windows timeout/cancellation/process-tree cleanup is demonstrated.

## Context compaction

- [x] Raw events and source artifacts remain immutable.
- [x] Summaries record source range and hashes.
- [x] Hard constraints survive all profiles.
- [x] Evidence, decision, and rehydration references remain resolvable.
- [x] Repository snapshot, policy, schema, source-hash, and age freshness are checked.
- [x] Secrets and hidden reasoning are rejected.
- [x] Loss audits pass for accepted fixtures.
- [x] Failed loss audit blocks acceptance and triggers rehydration.
- [x] Trigger/release hysteresis exists.
- [x] Contradiction, failing-gate, and summary-of-summary decay are detected.
- [x] Deterministic tests cover acceptance and rejection paths.

Blocked claim: model-generated compaction quality is not proven by deterministic fixtures.

## Boss, critics, and budgets

- [x] Missing or invalid findings escalate instead of accepting.
- [x] Hard constraints cannot be overturned by consensus.
- [x] Disagreement is preserved.
- [x] Per-agent cost, latency, and tool-call budgets are enforced.
- [x] Global cost, latency, tool, agent-count, and concurrency budgets are enforced.
- [x] Duplicate task ownership fails closed.
- [x] Budget overrun escalates.
- [x] Deterministic boss owns final disposition.
- [x] Provider and tool evidence re-enter the same boss boundary.

## API and UI

- [x] FastAPI router is registered in the application composition root.
- [x] Status, capabilities, selection, and same-origin UI routes exist.
- [x] Requested, planned, and served states are visually and structurally distinct.
- [x] Unentitled Kimi Code routes fail closed unless entitlement is declared.
- [x] API and HTML contracts pass deterministic tests.
- [ ] Manual browser smoke is recorded.

## Benchmark

- [x] Matched deterministic single-unchecked versus governed fixtures exist.
- [x] Default fixtures report 1/4 versus 4/4 expected dispositions.
- [x] The report refuses to invent improvement when modes tie.
- [x] Claim boundary states that this is a contract benchmark only.
- [ ] Live provider/agent quality, cost, and latency benchmark exists.
- [ ] Multi-agent mode is enabled or disabled from measured live benefit.

## Product boundary

- [x] Spec 0009 remains provider-neutral.
- [x] EACODE and EACHAT remain product-specific.
- [x] No EACORE runtime extraction is claimed.
- [x] Task extras remain separate from mandatory coursework.
- [ ] Equivalent selector and compaction semantics are proven independently in EACHAT.

## Allowed claims

- Deterministic provider routing, hardened adapter contracts, boss/critic governance, compaction acceptance, control-plane API/UI, and contract benchmark are implemented and CI-tested.
- Live process and provider behavior remain explicit, disabled by default, and separate from deterministic CI.

## Blocked claims

- current live success for every provider;
- exact served effort when not echoed;
- arbitrary-code sandboxing;
- real-world multi-agent or provider superiority;
- production readiness;
- EACORE extraction readiness.
