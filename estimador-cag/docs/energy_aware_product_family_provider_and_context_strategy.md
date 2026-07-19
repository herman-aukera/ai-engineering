# Energy-Aware Product Family, Provider Routing, Multi-Agent, and Context Strategy

Status: canonical architecture guidance  
Verified: 2026-07-19  
Applies to: EACODE, EACHAT, LIDR task branches including Session 13 Plus, and possible EACORE extraction

## 1. Purpose

This document aligns the product family around four separable ideas:

1. a provider-neutral model selection contract;
2. an Energy-Aware critic/supervisor engine;
3. bounded multi-agent orchestration;
4. versioned context compaction that prevents context rot.

It is architecture and product policy. It does not enable live providers, autonomous repair, real shell execution, or shared-core extraction by itself.

## 2. Product family

### EACODE

EACODE is a local or self-hosted supervision layer for coding agents and tools such as Claude Code, Cline, Aider, OpenCode, and future adapters.

Its governing loop is:

```text
specification + policy + candidate + evidence
    -> deterministic and optional model critics
    -> constraint-energy score
    -> boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded action or human gate
    -> normalized evidence
    -> immutable decision ledger
```

EACODE is not a model wrapper that blindly forwards prompts. The provider proposes. EACODE judges, requests repairs, authorizes bounded actions, and records evidence.

Session 13 Plus is architectural inspiration for the supervisor/boss workflow, human interruption, revision guards, bounded retries, parallelizable stages, and visible trace. Estimation-specific arithmetic and tools remain task-specific.

### EACHAT

EACHAT is a general-purpose Energy-Aware conversational product. It may resemble a ChatGPT-style interface, but its distinguishing capability is the engine behind the answer:

```text
conversation + user intent + grounding + policy
    -> candidate answer
    -> chat-specific critics
    -> energy score
    -> repair/refusal/clarification decision
    -> improved answer + compact Energy Card
```

EACHAT owns chat memory, grounding, answer repair, refusals, clarification, conversation UI, and chat evaluations. It must not import EACODE shell, repository, patch, or execution semantics.

### LIDR tasks and Session 13 Plus

Course tasks remain independent deliverables. The policy is:

- mandatory requirements must be exact, green, explainable, and demonstrable;
- extra work must be isolated, reversible, and must not destabilize mandatory scope;
- every extra capability requires explicit evidence and a clear claim boundary;
- the goal is not decorative overengineering, but a demonstrably stronger implementation than the minimum reference.

Multi-agent orchestration from Session 13 is reusable when stages are genuinely independent or when a supervisor must compare alternatives. It must not be copied into every task without a measured benefit.

### EACORE

EACORE is a possible shared architecture and contract layer, not a forced package.

It may remain:

- documentation and architecture decisions;
- shared schemas proven equivalent in at least two products;
- test fixtures and compatibility contracts;
- a later extracted package.

Do not extract a shared runtime abstraction merely because two files look similar. Extract only after EACODE and EACHAT independently prove stable semantic overlap.

## 3. Current provider facts

### DeepSeek

Current official API models:

- `deepseek-v4-flash`: fast and economical;
- `deepseek-v4-pro`: higher-capability model.

Both support thinking and non-thinking modes. In thinking mode, the effective effort values are `high` and `max`. Compatibility values `low` and `medium` map to `high`; `xhigh` maps to `max`.

DeepSeek remains the default provider because it is already integrated into the engineering workflow and offers the lowest-cost default path.

### Kimi

Kimi K3 is the current Moonshot flagship:

- API model ID: `kimi-k3`;
- Kimi Code model ID: `k3`;
- native multimodal input;
- up to a 1M-token context window;
- designed for long-horizon coding, knowledge work, and deep reasoning.

At launch, Kimi K3 uses maximum thinking effort by default. Lower effort modes are rolling out and must be capability-discovered rather than assumed.

Kimi Code also exposes:

- `kimi-for-coding`: mature Kimi coding model;
- `kimi-for-coding-highspeed`: high-speed coding variant where entitlement permits it.

Kimi is the user's preferred frontier/open-model path. That is a product preference, not an unsupported claim that Kimi K3 is objectively superior to every proprietary model.

### OpenAI

Current GPT-5.6 API family:

- `gpt-5.6-luna`: fastest and lowest-cost GPT-5.6 tier;
- `gpt-5.6-terra`: balanced capability/cost tier;
- `gpt-5.6-sol`: flagship tier, alias `gpt-5.6`.

All three expose reasoning levels `none`, `low`, `medium`, `high`, `xhigh`, and `max` through the API. Product surfaces may additionally expose Pro or multi-agent/ultra modes subject to access and budget.

OpenAI is the expensive escalation provider. It must never be selected silently when a request exceeds the configured budget.

## 4. Common selector contract

The public selector uses provider-neutral profiles:

```text
provider: deepseek | kimi | openai | auto
profile: minimal | medium | max
context_profile: minimal | medium | max
fallback_policy: none | same_provider | governed_cross_provider
```

The selector must resolve through a capability registry. It must not assume that every provider supports every profile.

### Recommended mapping

| Provider | Minimal | Medium | Max |
|---|---|---|---|
| DeepSeek | V4 Flash, thinking disabled | V4 Flash, thinking enabled, effective effort high | V4 Pro, thinking enabled, effort max |
| Kimi API | cheapest currently available compatible model discovered from registry | stable compatible Kimi model discovered from registry | `kimi-k3`, effort max |
| Kimi Code | `kimi-for-coding-highspeed` when entitled, otherwise `kimi-for-coding` | `kimi-for-coding` | `k3`, effort max |
| OpenAI API | `gpt-5.6-luna`, none or low | `gpt-5.6-terra`, medium | `gpt-5.6-sol`, max |

### Default routing policy

```text
normal request
    -> DeepSeek default

quality-sensitive or open-frontier request
    -> Kimi preferred path

high-stakes, failed consensus, or explicit premium request
    -> OpenAI governed escalation
```

Cross-provider fallback requires:

- explicit budget ceiling;
- recorded reason;
- provider/model/effort metadata;
- retry and circuit-breaker budget;
- evidence that the fallback result re-enters the same critics and decider;
- no provider self-approval.

## 5. Capability registry

Every adapter must expose a versioned capability manifest rather than scattering model-name conditionals throughout the products.

Minimum fields:

```text
provider
surface
model_id
model_family
context_window
max_output_tokens
reasoning_modes
reasoning_efforts
speed_class
supports_tools
supports_structured_output
supports_vision
supports_prompt_cache
input_price
cached_input_price
output_price
availability_state
verified_at
source_version
```

Rules:

- unknown capabilities fail closed;
- unsupported selector combinations are disabled in the UI and rejected by the API;
- a provider `/models` response may confirm availability but does not replace the curated capability manifest;
- model aliases are allowed only when resolved and recorded;
- production evidence records the exact model ID actually served;
- capability changes require compatibility tests.

## 6. Bounded multi-agent architecture

Multi-agent orchestration is useful across the projects when it reduces latency, increases independent evidence, or produces measurable quality improvement.

### Good uses

- parallel independent critics;
- alternative repair proposals;
- provider comparison under a fixed benchmark;
- retrieval, policy, cost, security, and quality specialists;
- independent implementation and reviewer agents;
- benchmark judges with disagreement escalation;
- Task 13 fan-out/fan-in patterns with a deterministic boss.

### Bad uses

- several agents editing the same working tree concurrently;
- agents approving their own output;
- parallel calls with no cost or time budget;
- duplicated agents that provide no independent evidence;
- using majority vote to override a hard constraint;
- hiding disagreement behind a synthesized answer.

### Required governance

```text
shared typed state
+ independent task ownership
+ bounded fan-out
+ deterministic aggregation
+ disagreement record
+ cost/time/tool budgets
+ human gate for high-risk decisions
+ trace and replay
```

The deterministic boss owns the final disposition. Model consensus may be evidence, never authority.

## 7. Context compaction and anti-rot policy

A large context window does not remove the need for memory management. Long histories accumulate stale assumptions, duplicated evidence, contradictory summaries, irrelevant tool logs, and expensive cache churn.

### Core design

Maintain separate layers:

```text
immutable raw events and source artifacts
    -> versioned structured state
    -> hierarchical summaries
    -> recent working window
    -> retrieved evidence on demand
```

Never replace the raw source of truth with a summary.

### Structured compaction record

Each compaction record contains:

```text
summary_id
source_event_range
source_hashes
created_at
creator_model_or_rule
compaction_profile
objective
hard_constraints
accepted_decisions
rejected_or_superseded_decisions
current_state
verified_evidence_refs
open_questions
risks
next_actions
rollback_or_rehydration_refs
token_counts_before_after
loss_audit_status
```

### User-facing context profiles

`minimal`:

- active objective;
- hard constraints;
- current state;
- unresolved blocker;
- next action;
- small recent-message window;
- retrieved evidence only when needed.

`medium`:

- everything in minimal;
- accepted decisions and rationale summaries;
- compact decision/evidence ledger;
- relevant historical pivots;
- larger recent window;
- default profile for normal product use.

`max`:

- everything in medium;
- hierarchical summaries from earlier phases;
- broader evidence index;
- alternative and rejected paths where relevant;
- larger recent window within a strict token budget;
- explicit rehydration of original artifacts for high-stakes work.

`max` means maximum retained useful context, not maximum compression.

### Compaction triggers

Compact when any configured threshold is crossed:

- percentage of provider context window;
- absolute input-token budget;
- repeated or superseded state density;
- tool-log volume;
- cache invalidation or model switch;
- phase or task checkpoint;
- conversation age.

Use hysteresis so the system does not compact on every turn.

### Safety rules

- keep hard constraints verbatim or in typed fields;
- preserve evidence IDs, decision IDs, timestamps, hashes, and revision references;
- mark uncertainty and conflict explicitly;
- never summarize secrets into persistent context;
- do not preserve hidden chain of thought;
- run a loss audit against a fixture set;
- permit rehydration from original sources;
- start a new provider session when model switching invalidates context cache assumptions;
- measure answer quality, latency, token reduction, and contradiction rate.

## 8. Implementation order

1. Finish EACODE Spec 0009 sandboxed-tool adapter without coupling it to a provider.
2. Implement the provider capability registry and selector behind a fake adapter in deterministic CI.
3. Implement context compaction contracts and deterministic fixtures.
4. Add DeepSeek live adapter as default manual path.
5. Add Kimi K3 as the preferred frontier/open path after capability discovery tests.
6. Add OpenAI GPT-5.6 as budget-gated premium escalation.
7. Add bounded multi-agent critics and repair only after single-agent baselines exist.
8. Benchmark each configuration before claiming improvement.
9. Evaluate shared EACORE extraction only after both EACODE and EACHAT prove equivalent contracts.

## 9. Claim boundary

This document supports architectural intent and verified model catalog facts as of 2026-07-19.

It does not prove:

- runtime provider selection exists;
- Kimi K3 is superior on the project's own benchmarks;
- multi-agent execution improves quality;
- context compaction preserves all relevant information;
- OpenAI escalation is cost-effective;
- EACORE extraction is justified.

Those claims require implementation, deterministic tests, live sanitized evidence, and comparative benchmarks.
