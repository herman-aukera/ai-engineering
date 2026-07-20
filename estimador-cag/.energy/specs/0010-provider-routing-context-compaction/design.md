# Spec 0010 — Design

Status: partial runtime implementation under rescue

## 1. Architectural position

Spec 0010 is an application and infrastructure boundary above product-local critics and below UI or external coding-agent adapters.

```text
User or agent request
    -> ProviderSelection
    -> CapabilityRegistry
    -> deterministic RoutingPolicy
    -> ProviderPlan
    -> optional ProviderAdapter
    -> Candidate
    -> product-local critics
    -> Energy score and deterministic decider
```

Context management is orthogonal:

```text
raw events + artifacts + decisions + evidence
    -> StructuredStateProjector
    -> CompactionPolicy
    -> CompactionRecord
    -> WorkingContextAssembler
    -> provider request
```

The provider never owns final product authority. A model proposes; EACODE validates, criticizes, repairs, gates, and records evidence.

Spec 0009 process execution remains provider-neutral and cannot receive authority from provider routing.

## 2. Current implementation boundary

Remote EACODE currently contains:

- strict provider-selection and model-capability contracts;
- a deterministic curated registry;
- profile-to-model resolution;
- DeepSeek-default auto selection;
- deterministic fallback metadata;
- deterministic capability hashes;
- keyless tests.

It does not yet contain accepted evidence for:

- current provider catalog accuracy;
- live provider adapters;
- exact served-model metadata;
- retry/circuit state;
- critic re-entry after fallback;
- context-compaction runtime;
- selector UI;
- multi-agent runtime.

Local interrupted context-compaction work may exist and must be audited before reuse.

## 3. Core contracts

```python
class ProviderSelection:
    provider: Literal["auto", "deepseek", "kimi", "openai"]
    profile: Literal["minimal", "medium", "max"]
    context_profile: Literal["minimal", "medium", "max"]
    fallback_policy: Literal["none", "same_provider", "governed_cross_provider"]
    expected_input_tokens: int
    expected_cached_input_tokens: int
    expected_output_tokens: int
    max_cost_usd: Decimal
    max_latency_ms: int | None
    premium_reason: str | None

class ModelCapability:
    provider: str
    surface: str
    model_id: str
    aliases: tuple[str, ...]
    model_family: str
    context_window: int
    max_output_tokens: int
    reasoning_modes: tuple[str, ...]
    reasoning_efforts: tuple[str, ...]
    speed_class: str
    supports_tools: bool
    supports_structured_output: bool
    supports_vision: bool
    supports_prompt_cache: bool
    pricing: PricingSnapshot
    price_unit: str
    availability_state: str
    entitlement_state: str
    verified_at: datetime
    source_id: str
    source_version: str
    freshness_state: str

class ProviderPlan:
    selection: ProviderSelection
    resolved_provider: str
    resolved_surface: str
    resolved_model_id: str
    reasoning_mode: str
    reasoning_effort: str
    estimated_input_cost_usd: Decimal
    estimated_output_cost_usd: Decimal
    estimated_total_cost_usd: Decimal
    fallback_steps: tuple[FallbackStep, ...]
    capability_snapshot_hash: str

class ProviderExecutionEvidence:
    requested_provider: str
    requested_profile: str
    planned_provider: str
    planned_model_id: str
    planned_effort: str
    served_provider: str
    served_model_id: str
    served_effort: str
    safe_provider_request_ref: str | None
    attempts: tuple[ProviderAttempt, ...]
    circuit_state: str
    tokens: TokenUsage
    latency_ms: int
    cost_usd: Decimal
    candidate_ref: str
    critic_evidence_refs: tuple[str, ...]
    final_decision_ref: str

class CompactionRecord:
    summary_id: str
    source_event_range: EventRange
    source_hashes: tuple[str, ...]
    repository_snapshot_ref: str
    policy_version: str
    schema_version: str
    compaction_profile: str
    objective: str
    hard_constraints: tuple[str, ...]
    accepted_decisions: tuple[DecisionRef, ...]
    superseded_decisions: tuple[DecisionRef, ...]
    current_state: Mapping[str, JSONValue]
    evidence_refs: tuple[EvidenceRef, ...]
    open_questions: tuple[str, ...]
    risks: tuple[str, ...]
    next_actions: tuple[str, ...]
    rehydration_refs: tuple[ArtifactRef, ...]
    tokens_before: int
    tokens_after: int
    loss_audit_status: str
```

Contracts remain product-local until equivalent EACODE and EACHAT semantics are proven.

## 4. Capability resolution

### DeepSeek API

Initial product mapping:

- minimal: V4 Flash, non-thinking;
- medium: V4 Flash, thinking with effective effort `high`;
- max: V4 Pro, thinking with effort `max`.

The curated manifest must use current official 1M-context, maximum-output, cache, and pricing data. Compatibility effort values that map to `high` or `max` must not be presented as independent native capabilities.

### Kimi surfaces

Treat general API and Kimi Code as separate surfaces.

General API includes:

- `kimi-k3`.

Kimi Code includes:

- `k3` for Kimi K3;
- `kimi-for-coding` for Kimi K2.7 Code;
- `kimi-for-coding-highspeed` where entitled.

Current Kimi Code K3 effort values are `low`, `high`, and `max`, with `max` as the default. The earlier max-only launch assumption is obsolete.

Recommended EACODE coding-agent mapping:

- minimal: `kimi-for-coding` or high-speed entitlement variant;
- medium: `k3` at `high` or `kimi-for-coding`, selected by budget and task class;
- max: `k3` or `k3[1m]` at `max`, subject to entitlement and current capability discovery.

Turning thinking off or changing model/effort can alter routing and cache compatibility. Start a fresh provider session and supply normalized compacted context when switching.

### OpenAI API

Initial mapping:

- minimal: GPT-5.6 Luna, effort `none` or `low`;
- medium: GPT-5.6 Terra, effort `medium`;
- max: GPT-5.6 Sol, effort `max`.

Use current official context, maximum-output, and pricing data. Premium, Pro, or multi-agent modes remain separate authorized capabilities.

## 5. Routing policy

```text
explicit provider
    -> validate capability, freshness, entitlement, budget, and policy

auto + normal cost-sensitive work
    -> DeepSeek

auto + explicit open-frontier preference
    -> Kimi

auto + unresolved high-stakes disagreement
    -> require explicit premium escalation reason and budget
    -> OpenAI only after authorization
```

Every fallback candidate re-enters product-local critics and the deterministic decider.

A planned route is not execution proof. Exact served metadata comes only from a provider response and sanitized execution evidence.

## 6. Budget design

Estimate cost using:

```text
uncached_input_tokens * uncached_input_price
+ cached_input_tokens * cached_input_price
+ expected_output_tokens * output_price
```

All prices must use explicit units and source versions. Budget enforcement applies to every provider.

Do not use a hidden constant such as “assume 100K input tokens.” Token assumptions are typed request data and appear in the decision record.

## 7. Multi-agent design

```text
Supervisor
    -> independent Critic A: correctness
    -> independent Critic B: constraints
    -> independent Critic C: security
    -> independent Critic D: cost/latency
    -> deterministic aggregation
    -> disagreement record and energy delta
    -> repair, human gate, or final decision
```

Parallelism is allowed only for independent work. Shared mutable worktrees are forbidden. Each task records ownership and output hashes.

Before enabling multi-agent mode, establish a single-agent quality, safety, cost, and latency baseline. Disable multi-agent mode when no measurable benefit is shown.

## 8. Context-compaction design

### Memory tiers

1. immutable raw log and artifacts;
2. canonical typed state;
3. checkpoint/phase summaries;
4. current working summary;
5. recent uncompressed window;
6. on-demand retrieved evidence.

### Profiles

| Profile | Working summary | Recent window | Retrieval | Intended use |
|---|---|---|---|---|
| minimal | objective, hard constraints, current state, blocker, next action | small | strict on demand | fast/high-volume |
| medium | minimal plus decisions, evidence digest, and pivots | moderate | normal | default |
| max | medium plus hierarchical history and broader evidence index | large but bounded | aggressive rehydration | difficult/high-stakes |

### Trigger and hysteresis

Compaction begins above a tested high threshold and does not repeat until context falls below a lower threshold.

Example fixture values—not universal constants:

```text
trigger: >= 70% of provider budget
release: <= 45% after compaction
```

### Freshness

A compacted record becomes stale when any protected identity changes:

- branch;
- HEAD/tree/worktree snapshot;
- product policy version;
- graph version;
- schema version;
- source hash set.

### Loss audit

Fixtures verify preservation of:

- hard constraints;
- accepted and rejected decisions;
- evidence IDs and hashes;
- current revision and repository snapshot;
- unresolved blockers;
- relevant user preferences;
- rollback and rehydration references.

A failed audit invalidates the summary and requires rehydration or a safer profile.

## 9. Cache-aware provider switching

Provider/model/effort switching may invalidate cache economics and semantics. The router shall:

- record the switch;
- start a new provider session where required;
- build a normalized provider-neutral handoff;
- reuse only provider-compatible cached context;
- preserve canonical product state independently of provider cache;
- measure cache hits, tokens, latency, and cost before and after switching.

Do not carry an incomplete DeepSeek agent session directly into Kimi K3. Checkpoint repository state and start a clean Kimi session.

## 10. Spec 0009 dependency

Provider routing cannot repair or bypass process-execution authority.

Before live tool evidence is accepted:

- fake/dry-run plans cannot become real execution;
- live execution has an explicit typed intent;
- authorization binds to a complete repository snapshot;
- receipt provenance is verified;
- cancellation is promptly observed;
- process-tree cleanup is demonstrably checked;
- output truncation and redaction are safe across chunks and final assembly;
- cleanup uncertainty fails closed.

## 11. Failure handling

- stale or unavailable model: fail closed or use an authorized fallback;
- unsupported or unentitled effort: reject selection;
- budget exceeded: clarify or escalate;
- provider schema failure: bounded repair, then fallback or stop;
- repeated provider failure: open circuit breaker;
- DNS/name-resolution failure: record infrastructure failure; do not classify it as exhausted credit;
- compaction loss-audit failure: rehydrate and block acceptance;
- multi-agent disagreement: preserve findings and route to boss/human policy.

## 12. Observability

Record:

- requested, planned, and served provider/model/profile;
- capability snapshot hash and source version;
- reasoning mode and effort;
- fallback reason and attempts;
- retry and circuit state;
- token and cost estimates and actuals;
- provider/session switch events;
- compaction profile and token reduction;
- source hashes and loss-audit result;
- critic disagreement and final deterministic disposition.

## 13. Migration and rollback

Implementation remains additive:

- retain existing provider configuration;
- keep fake adapters as deterministic CI defaults;
- repair the registry behind tests before live use;
- run shadow selection before serving it;
- keep live provider adapters opt-in;
- permit rollback to the previous fixed routing ladder;
- never require Spec 0010 to complete or authorize Spec 0009;
- inspect interrupted local compaction work before reuse;
- request user approval before commit or push during rescue.
