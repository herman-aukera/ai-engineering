# Spec 0010 — Design

## 1. Architectural position

Spec 0010 is an application and infrastructure boundary above product-local critics and below UI or external agent adapters.

```text
User or agent request
    -> SelectionRequest
    -> CapabilityRegistry
    -> RoutingPolicy
    -> ProviderPlan
    -> ProviderAdapter
    -> Candidate
    -> product-local critics and Energy decider
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

The provider never owns the final product decision.

## 2. Proposed contracts

```python
class ProviderSelection:
    provider: Literal["auto", "deepseek", "kimi", "openai"]
    profile: Literal["minimal", "medium", "max"]
    context_profile: Literal["minimal", "medium", "max"]
    fallback_policy: Literal["none", "same_provider", "governed_cross_provider"]
    max_cost_usd: Decimal
    max_latency_ms: int | None

class ModelCapability:
    provider: str
    surface: str
    model_id: str
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
    availability_state: str
    verified_at: datetime
    source_version: str

class ProviderPlan:
    selection: ProviderSelection
    resolved_provider: str
    resolved_model_id: str
    reasoning_mode: str
    reasoning_effort: str
    estimated_cost_ceiling_usd: Decimal
    fallback_steps: tuple[FallbackStep, ...]
    capability_snapshot_hash: str

class CompactionRecord:
    summary_id: str
    source_event_range: EventRange
    source_hashes: tuple[str, ...]
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

## 3. Capability resolution

### DeepSeek

- minimal: `deepseek-v4-flash`, thinking disabled;
- medium: `deepseek-v4-flash`, thinking enabled, effective effort `high`;
- max: `deepseek-v4-pro`, thinking enabled, effort `max`.

The resolver records that DeepSeek maps compatibility `low` and `medium` efforts to `high`.

### Kimi

Kimi has two surfaces:

- general API IDs such as `kimi-k3`;
- Kimi Code IDs `k3`, `kimi-for-coding`, and `kimi-for-coding-highspeed`.

K3 launches at max effort. Lower profiles must resolve to another compatible model or be disabled until K3 exposes the requested effort. The system must not silently pretend that `medium` K3 exists.

### OpenAI

- minimal: `gpt-5.6-luna`, effort `none` or `low`;
- medium: `gpt-5.6-terra`, effort `medium`;
- max: `gpt-5.6-sol`, effort `max`.

Pro or multi-agent/ultra modes are separate premium capabilities and require explicit support, access, and budgets.

## 4. Routing policy

```text
explicit provider
    -> validate capability and budget

auto + normal complexity
    -> DeepSeek

auto + quality/open-frontier preference
    -> Kimi

auto + unresolved high-stakes disagreement
    -> require explicit premium escalation
    -> OpenAI only after authorization
```

Fallback does not bypass critics. Every result re-enters the same product-local evaluation path.

## 5. Multi-agent design

```text
Supervisor
    -> parallel Critic A: correctness
    -> parallel Critic B: constraints
    -> parallel Critic C: security
    -> parallel Critic D: cost/latency
    -> deterministic aggregation
    -> disagreement and energy delta
    -> repair, human gate, or final decision
```

Parallelism is allowed only for independent work. Shared mutable worktrees are forbidden. Each branch records task ownership and output hashes.

## 6. Context compaction design

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
| minimal | objective, constraints, state, blocker, next action | small | strict on-demand | fast/high-volume |
| medium | minimal plus decisions, evidence digest, pivots | moderate | normal | default |
| max | medium plus hierarchical history and broader evidence index | large but bounded | aggressive rehydration | difficult/high-stakes |

### Trigger and hysteresis

Compaction begins above a high threshold and does not repeat until context falls below a lower threshold. Example defaults should be tested rather than hard-coded as universal truth.

```text
trigger: >= 70% of provider budget
release: <= 45% after compaction
```

### Loss audit

Fixtures must verify preservation of:

- hard constraints;
- accepted and rejected decisions;
- evidence IDs and hashes;
- current revision;
- unresolved blockers;
- user preferences relevant to the task;
- rollback and rehydration references.

A failed audit invalidates the summary and requires rehydration or a safer profile.

## 7. Cache-aware model switching

Provider/model switching may invalidate cache economics and semantics. The router shall:

- record the switch;
- start a new provider session where required;
- reuse only provider-compatible cached context;
- preserve canonical product state independently of provider cache;
- measure cache hit, tokens, latency, and cost before and after switching.

## 8. Failure handling

- unavailable model: fail closed or use an authorized fallback;
- unsupported effort: reject selection, do not coerce invisibly;
- budget exceeded: clarify or escalate;
- provider schema failure: repair within budget, then fallback or stop;
- repeated provider failure: open circuit breaker;
- compaction loss audit failure: rehydrate and block final acceptance;
- multi-agent disagreement: preserve findings and route to boss/human policy.

## 9. Observability

Record:

- requested and served provider/model/profile;
- capability snapshot hash;
- reasoning mode and effort;
- fallback reason;
- attempts and circuit state;
- token and cost estimates and actuals;
- compaction profile and token reduction;
- source hashes and loss-audit result;
- critic disagreement and final deterministic disposition.

## 10. Migration and rollback

Initial implementation must be additive:

- retain existing provider configuration;
- add the registry behind a feature flag;
- run shadow selection before serving it;
- keep fake adapters as deterministic CI defaults;
- permit rollback to the previous fixed routing ladder;
- never require Spec 0010 to complete Spec 0009.
