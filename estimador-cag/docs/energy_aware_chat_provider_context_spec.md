# EACHAT provider routing, reasoning and context-compaction specification

Status: canonical design specification; implementation pending dedicated milestones.

Updated: 2026-07-19.

## 1. Objective

Define a stable provider-neutral contract for:

- DeepSeek as the cost-effective default;
- Kimi K3 as the user-preferred quality candidate after API capability verification;
- OpenAI GPT-5.6 as a premium option;
- cross-provider effort selection;
- user-selectable context compaction;
- bounded single-agent and multi-agent orchestration;
- deterministic energy-aware escalation, audit and rollback.

This document does not claim that all adapters or UI selectors are implemented.

## 2. Architectural position

Provider/model selection happens before candidate generation but remains subordinate to deterministic policy.

```text
request
-> classify task, evidence, privacy, modality and tool needs
-> resolve provider/model/context/orchestration profile
-> generate candidate(s)
-> run critics
-> calculate authoritative energy
-> decide
-> optional bounded repair or escalation
-> append Decision Ledger entry
-> project Energy Card and safe answer
```

A provider cannot override hard constraints, evidence sufficiency, retry/cost budgets or final disposition.

## 3. Stable user-facing contracts

### 3.1 Provider preference

```text
auto | deepseek | kimi | openai
```

- `deepseek` is the explicit default until auto-routing benchmark evidence exists.
- `kimi` targets Kimi K3 after model discovery verifies the account-visible ID and supported parameters.
- `openai` targets the GPT-5.6 family and requires a premium cost budget.
- `auto` is disabled by default until controlled routing evals prove safe behavior.

### 3.2 Effort profile

```text
fast | balanced | max
```

This is a product abstraction, not a provider parameter. Adapters map it to verified capabilities.

### 3.3 Context profile

```text
minimal | balanced | max
```

This controls retained conversation/project context. It is independent of model reasoning effort.

### 3.4 Orchestration mode

```text
single | critic | committee | adaptive
```

- `single`: one generator; deterministic policy still runs.
- `critic`: one generator plus independent critic panel.
- `committee`: multiple bounded candidates/specialists and deterministic adjudication.
- `adaptive`: begins with the cheapest allowed path and expands only when policy thresholds require it.

## 4. Provider catalog contract

The domain must depend on a versioned capability catalog, not scattered environment-variable conditionals.

Suggested strict contract:

```text
ProviderModelCapability
- catalog_version
- provider
- model_id
- display_name
- availability_status
- verified_at
- context_window_tokens
- max_output_tokens
- modalities
- supports_tools
- supports_structured_output
- supports_streaming
- supported_effort_profiles
- provider_reasoning_parameters
- speed_class
- cost_class
- input_price_per_million
- output_price_per_million
- data_handling_profile
- source_refs
```

Requirements:

1. Model identifiers are configuration, not user-controlled arbitrary strings.
2. Catalog entries are allow-listed and versioned.
3. Time-sensitive metadata records `verified_at` and source references.
4. Unknown capability fails closed or falls back only through an explicit, ledgered policy.
5. A model cannot be selected when required modality/tool/schema/privacy capabilities are absent.
6. Prices are optional metadata and never silently treated as permanent constants.

## 5. Current provider mapping

### 5.1 DeepSeek

Officially verified family:

```text
deepseek-v4-flash
deepseek-v4-pro
```

Both currently document 1M context and thinking/non-thinking modes.

Recommended mapping:

| Product effort | Mapping |
|---|---|
| `fast` | V4 Flash, non-thinking |
| `balanced` | V4 Flash thinking for reasoning-heavy low-cost work, or V4 Pro non-thinking when quality policy prefers the larger model |
| `max` | V4 Pro thinking |

The router chooses the balanced mapping from task complexity, latency budget and evaluation evidence; it must record the result.

### 5.2 Kimi

Official public release facts currently verified:

- Kimi K3 exists;
- 2.8T parameters are advertised;
- natively multimodal;
- 1M-token context;
- positioned for long-horizon coding, knowledge work and deep reasoning.

Not yet treated as verified by this repository:

- exact API model ID;
- exact reasoning-mode parameter names;
- separate speed tiers;
- API pricing and availability for this account;
- Claude-compatible endpoint mapping.

Therefore:

| Product effort | Mapping policy |
|---|---|
| `fast` | use a verified K3 fast/instant capability only when provider metadata exposes it |
| `balanced` | use the verified default K3 capability |
| `max` | use a verified K3 deep-reasoning or agentic capability only when supported |

No guessed K3 identifiers may enter committed code, tests or configuration defaults.

### 5.3 OpenAI

Official GPT-5.6 family:

```text
Luna | Terra | Sol
```

Recommended mapping:

| Product effort | Mapping |
|---|---|
| `fast` | GPT-5.6 Luna |
| `balanced` | GPT-5.6 Terra with medium effort |
| `max` | GPT-5.6 Sol with max effort |

`ultra` is provider-specific and optional. It is not part of the stable cross-provider three-level contract. It may be exposed as an advanced capability only after endpoint/account support, budget and multi-agent behavior are verified.

## 6. Routing policy

### 6.1 Default

```text
provider=deepseek
effort=balanced
context=balanced
orchestration=critic
```

The deterministic route uses the local provider regardless of the live preference and records that no external provider was called.

### 6.2 Compatibility filter

Before cost/quality selection, reject models that cannot satisfy:

- required modality;
- required tool/structured-output behavior;
- context length;
- privacy/data handling;
- regional/provider policy;
- maximum cost;
- maximum latency;
- availability;
- evidence/grounding requirements.

### 6.3 Escalation

Escalation is allowed only when:

- a hard constraint remains unresolved but another verified profile can address it;
- energy exceeds a configured threshold;
- critic uncertainty is above threshold;
- repair on the current profile failed or is not suitable;
- the user explicitly selected a stronger profile;
- risk policy requires a stronger reviewer/adjudicator.

Escalation order is policy-driven, not globally fixed. A typical bounded path is:

```text
DeepSeek balanced
-> repair on same profile
-> DeepSeek max
-> Kimi balanced/max or GPT-5.6 premium, only when selected/allowed
-> clarify or escalate to human
```

No silent cross-provider fallback is allowed. A fallback must preserve privacy requirements and be visible in the response and ledger.

## 7. Multi-agent policy

Multi-agent execution is a bounded orchestration profile, not an automatic synonym for quality.

### 7.1 Roles

Possible roles:

- generator;
- evidence researcher;
- domain critic;
- safety/policy critic;
- consistency critic;
- cost/latency critic;
- deterministic boss/adjudicator;
- human gate.

The boss may use model observations but deterministic Python owns:

- hard-constraint precedence;
- energy aggregation;
- quorum;
- candidate eligibility;
- retry/turn/cost/token ceilings;
- terminal disposition;
- ledger authority.

### 7.2 Product application

- EACHAT: compare general-purpose answers, grounding and usefulness; repair the selected answer.
- EACODE: critique specifications, patches, tests and commands before returning safe advice/actions to Claude Code, Cline or Aider.
- Session 13 Plus: improve the mandatory estimator graph with explicit agents, typed state, persistence, human gates and observability, while retaining domain-specific arithmetic.
- EACORE: document shared role/result contracts first; extract runtime only after equivalent implementations exist in at least two products.

### 7.3 Limits

Required budgets:

- maximum agent count;
- maximum parallel branches;
- maximum turns per branch;
- token and cost ceilings;
- wall-clock deadline;
- retry ceiling;
- provider concurrency ceiling.

## 8. Context compaction contract

Suggested contracts:

```text
ContextCompactionPolicy
- profile
- target_input_tokens
- recent_raw_turns
- preserve_pinned_facts
- preserve_evidence_refs
- preserve_ledger_refs
- preserve_open_questions
- preserve_failures
- preserve_exact_identifiers
- summarizer_profile
- max_summary_depth
- drift_check_enabled
```

```text
ContextSnapshot
- snapshot_id
- thread_id
- revision
- profile
- source_start_revision
- source_end_revision
- created_at
- summary_text
- pinned_facts
- hard_constraints
- accepted_decisions
- unresolved_items
- evidence_refs
- ledger_entry_ids
- recent_raw_message_ids
- source_hash
- summary_hash
- token_count_before
- token_count_after
- limitations
```

### 8.1 Minimal

Retain:

- current task and success criteria;
- hard constraints and safety rules;
- pinned facts;
- exact IDs/SHAs/paths required for correctness;
- unresolved decisions/failures;
- latest relevant turns;
- evidence and ledger references.

### 8.2 Balanced

Retain everything in minimal plus:

- structured rolling summary;
- broader recent raw window;
- important accepted/rejected alternatives;
- current plan and next slice;
- relevant provider/routing history.

This is the default.

### 8.3 Max

Retain everything in balanced plus:

- larger raw window;
- hierarchical summaries by phase/topic;
- selected evidence excerpts within privacy limits;
- complete unresolved-decision lineage;
- additional audit metadata.

Max context does not mean “send all history blindly.” Irrelevant and duplicate content is still removed.

### 8.4 Anti-rot controls

1. Pinned facts and constraints are separate from generated prose summaries.
2. Exact identifiers and evidence references are copied, not paraphrased.
3. Every compaction is revisioned and hash-linked to its source range.
4. The system retains a recent raw-message window.
5. Contradiction checks compare the new summary against pinned facts and prior accepted decisions.
6. Failed checks reject the summary and preserve the previous trusted snapshot.
7. Users may request recompression or rollback.
8. Hidden chain-of-thought is never persisted or exposed.
9. Secrets and raw environment dumps are never summarized into durable memory.

## 9. API projection

Future live requests may include:

```text
provider_preference
effort_profile
context_profile
orchestration_mode
allow_provider_fallback
max_cost_usd
max_latency_ms
```

Responses should safely expose:

```text
requested_profile
served_profile
provider
model
reasoning_mode
context_profile
orchestration_mode
fallback_used
escalation_count
routing_reason
context_snapshot_id
context_tokens_before
context_tokens_after
provider_metrics
limitations
```

Do not expose credentials, raw prompts, hidden reasoning, provider transcripts or sensitive context bodies.

## 10. Ledger additions

Each external candidate decision should record:

- requested and served provider/model profile;
- capability catalog version;
- effort/context/orchestration profiles;
- fallback and escalation reasons;
- cost/latency/token facts;
- context snapshot ID and revision;
- compaction policy version;
- candidate/critic/score/decision linkage;
- limitations and unverified capability warnings.

## 11. Tests and evaluations

### Deterministic tests

- strict selector validation;
- catalog allow-list behavior;
- unsupported capability failure;
- no silent fallback;
- routing budget enforcement;
- deterministic profile resolution;
- context profile invariants;
- pinned fact/constraint preservation;
- exact ID/evidence preservation;
- compaction replay/idempotency;
- summary contradiction rejection;
- multi-agent budget termination;
- ledger projection.

### Manual provider smoke

For each enabled provider/profile:

- account-visible model discovery;
- one bounded sanitized response;
- structured output/tool behavior if required;
- measured tokens, latency and cost;
- no secret leakage;
- explicit provider/model result.

### Benchmark

Compare providers and orchestration modes on the same fixed corpus and rubric:

- constraint satisfaction;
- source grounding;
- repair effectiveness;
- answer usefulness;
- coding/spec quality for EACODE;
- latency;
- cost;
- failure rate;
- context retention accuracy;
- summary drift;
- human preference.

No provider receives the label “best” without this evidence.

## 12. Migration sequence

1. Add provider-neutral enums and catalog contracts.
2. Preserve current DeepSeek behavior through an adapter.
3. Add request/response metadata without UI change.
4. Add deterministic routing tests.
5. Add Kimi K3 discovery and adapter after API verification.
6. Add GPT-5.6 Responses API adapter with explicit premium budget.
7. Add context snapshot/compaction contracts.
8. Add selectors to the graph-backed UI.
9. Add adaptive and committee modes behind feature flags.
10. Benchmark before changing defaults or quality claims.

## 13. Rollback

- Default back to the existing DeepSeek seam.
- Disable provider adapters independently.
- Disable auto/adaptive/committee modes independently.
- Ignore additive routing/context fields in older readers.
- Retain the previous trusted context snapshot.
- Never delete ledger history during rollback.

## 14. Current claim boundary

Allowed:

> EACHAT has a documented provider-neutral routing and context-compaction architecture covering DeepSeek, Kimi K3 and GPT-5.6, with evidence-gated multi-agent escalation.

Blocked until implementation/evidence:

- all three providers are available in the product;
- Kimi K3 is objectively best;
- automatic routing improves quality or cost;
- context compaction prevents all context rot;
- multi-agent mode improves every task;
- provider switching is production-ready.
