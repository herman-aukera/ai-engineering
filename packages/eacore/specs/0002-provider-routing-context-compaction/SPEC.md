# Spec 0002 — Provider Routing, Context Compaction, and Multi-Agent Contracts

**Status:** proposed architecture; documentation-only  
**Date:** 2026-07-19  
**Implementation:** not started  
**Products:** EACODE, EACHAT, Session 13 Plus and later coursework  
**Shared owner:** EACORE contract governance

## 1. Problem

The portfolio needs:

- selectable DeepSeek, Kimi, and OpenAI providers;
- provider-specific models and reasoning modes;
- one understandable user selector across incompatible provider APIs;
- predictable cost, speed, and quality choices;
- structured context compaction;
- safe model switching;
- bounded multi-agent orchestration;
- shared audit metadata without forcing provider runtime code into EACORE.

## 2. Product goals

### EACODE

Provide a local Energy-Aware coding gateway that can evaluate, repair, reject,
or escalate model output before returning it to coding clients such as Claude
Code, Cline, Aider, or IDE integrations.

### EACHAT

Provide a general-purpose Energy-Aware chat product with provider/model/context
selectors, parallel critics, deterministic Boss decisions, repair, evidence, and
an Energy Card.

### Coursework

Complete mandatory requirements first and prove them, then add bounded extras
that improve correctness, observability, pedagogy, and reusable learning.

### EACORE

Own only proven neutral contracts, fixtures, and architecture. A documentation-
only common layer is acceptable.

## 3. Functional requirements

### R-001 Provider selection

Support:

```text
auto | deepseek | kimi | openai
```

Default `auto` should prefer DeepSeek unless hard constraints, product policy,
or explicit user preference require another route.

### R-002 Execution profile

Support user-facing:

```text
instant | balanced | max
```

This profile chooses a provider-specific model tier.

### R-003 Reasoning profile

Support user-facing:

```text
minimal | medium | max
```

The resolver must map only to verified native capabilities.

### R-004 Context profile

Support retained-detail levels:

```text
minimal | medium | max
```

Each profile must produce a structured, versioned compaction record.

### R-005 Capability registry

Every provider/model entry must include:

- exact ID;
- verification date;
- access status;
- modalities;
- context length;
- reasoning modes;
- tool and structured-output support;
- streaming;
- session-switch constraints;
- deprecation date;
- cost snapshot;
- source reference.

### R-006 Explicit resolution

Return exactly one:

```text
exact | repaired | fallback | rejected
```

No silent fallback.

### R-007 Provider session pinning

Pin provider and model within a session unless an explicit handoff is created.

### R-008 Kimi K3 handling

Support `kimi-k3` at max effort. Do not expose K3 low/high until verified as
available. Start a fresh K3 session by default when switching providers.

### R-009 DeepSeek handling

Verified mappings:

- instant → V4 Flash, non-thinking;
- balanced → V4 Flash, thinking, high;
- max → V4 Pro, thinking, max.

### R-010 GPT-5.6 handling

Verified tier mapping:

- instant → Luna;
- balanced → Terra;
- max → Sol.

Treat `ultra` as a separate explicit multi-agent mode, not a synonym for max.

### R-011 Compaction content

Preserve:

- objective;
- decisions;
- constraints;
- preferences;
- state;
- evidence refs;
- completed and unresolved work;
- risks;
- recent raw turns;
- provider/model/session identity;
- next action and rollback;
- source references;
- compaction version and hash.

### R-012 Multi-agent controls

Require:

- bounded concurrency;
- explicit roles;
- independent evidence;
- deterministic aggregation;
- disagreement policy;
- budgets;
- cancellation;
- trace correlation;
- human escalation where needed.

## 4. Non-functional requirements

- deterministic selection for a fixed capability snapshot and request;
- no secrets in state, logs, fixtures, or compaction records;
- fake providers in CI;
- live provider tests are optional smoke tests;
- provider failures cannot bypass hard constraints;
- old compaction records remain readable or fail with explicit compatibility
  errors;
- provider runtime packages remain product-local;
- shared contracts remain framework-neutral.

## 5. Proposed neutral contracts

Documentation candidates:

```text
ProviderRef
ModelRef
ProviderCapability
CapabilitySnapshot
ModelSelectionRequest
ModelSelectionResult
ExecutionProfile
ReasoningProfile
ContextProfile
FallbackPolicy
CompactionRequest
CompactionRecord
SessionHandoffRef
ParallelismProfile
AgentRoleRef
AgentRunRef
AggregationResult
```

These are not approved for shared implementation until at least two products
prove stable equivalent contracts.

## 6. Decision policy

Hard blockers:

- missing credentials;
- unavailable model;
- unsupported modality/tool;
- unsupported reasoning mode under strict selection;
- budget exceeded;
- unsafe data route;
- incompatible session history;
- deprecated model;
- context cannot be compacted safely.

Soft scoring:

- product fit;
- quality evidence;
- latency;
- cost;
- reliability;
- cache behavior;
- prior repair performance.

## 7. Product mappings

### EACODE

```text
client
→ local gateway
→ selector
→ actor
→ coding critics
→ deterministic Boss
→ repair/tool authorization
→ audited response
```

### EACHAT

```text
user
→ selector and context policy
→ candidate answer(s)
→ chat critics
→ deterministic Boss
→ repair/clarify/refuse
→ answer + Energy Card
```

### Coursework

```text
mandatory sequential baseline
→ trace and CI proof
→ bounded parallel critics
→ Boss/fallback/human gate
→ separately evidenced extras
```

## 8. Acceptance criteria

Documentation phase is complete when:

- README contains the portfolio roles;
- provider mappings reflect verified official capabilities;
- Kimi K3 unsupported efforts are not invented;
- GPT-5.6 uses Luna/Terra/Sol rather than fabricated nano/instant model IDs;
- normalized selectors are unambiguous;
- compaction profile semantics are explicit;
- model-switch behavior is documented;
- multi-agent good and bad uses are documented;
- CLAUDE.md contains scope and stop rules;
- no product code or provider SDK is added;
- existing EACORE tests and CI remain green.

Runtime implementation is not complete until a product-local pilot has:

- deterministic capability fixtures;
- selector tests;
- fake-provider tests;
- compaction round trips;
- fallback/rejection tests;
- provider smoke evidence;
- cost and latency telemetry;
- feature-flag rollback.

## 9. Ordered tasks

1. Commit architecture documentation.
2. Update Claude Code handoff and authentication troubleshooting.
3. Freeze a provider capability snapshot with official sources.
4. Select the first product pilot.
5. Implement registry and resolver locally in that product.
6. Add fake-provider tests.
7. Add structured compaction and validation.
8. Add one user-facing selector.
9. Run provider smoke tests outside CI.
10. Evaluate whether two products justify neutral contract extraction.

## 10. Stop conditions

Stop if:

- a provider mode is guessed;
- Kimi K3 low/high is exposed before release;
- GPT-5.6 tier and reasoning effort are conflated;
- provider keys enter repository files;
- one provider silently replaces another;
- a model switch discards incompatible history;
- free-form summaries replace evidence and decision records;
- multi-agent fan-out is unbounded;
- model consensus overrides hard policy;
- EACORE imports a provider SDK;
- product branches are modified from EACORE.
