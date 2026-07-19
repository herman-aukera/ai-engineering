# Spec 0010 — Provider Routing and Context Compaction Requirements

Status: architecture accepted, runtime not implemented  
Product owner: EACODE  
Cross-product relevance: EACHAT, LIDR task branches, possible EACORE extraction

## Objective

Define a provider-neutral selection layer, context-compaction contract, and bounded multi-agent governance model without coupling Spec 0009 real process execution to any model provider.

## Functional requirements

### REQ-001 — Provider-neutral selector

The system shall accept:

- provider: `auto`, `deepseek`, `kimi`, or `openai`;
- profile: `minimal`, `medium`, or `max`;
- context profile: `minimal`, `medium`, or `max`;
- fallback policy: `none`, `same_provider`, or `governed_cross_provider`;
- explicit request budget.

### REQ-002 — Capability registry

The system shall resolve selections through a versioned capability manifest containing model identity, context limits, supported reasoning modes, effort values, speed class, tool/structured-output support, prices, availability, verification timestamp, and source version.

Unknown or unsupported capabilities shall fail closed.

### REQ-003 — Default and escalation policy

The default policy shall be:

1. DeepSeek for normal cost-sensitive work;
2. Kimi as the user-preferred frontier/open-model path;
3. OpenAI GPT-5.6 as explicit budget-gated premium escalation.

Cross-provider fallback shall record reason, budget, provider, exact model, effort, retries, and circuit-breaker state.

### REQ-004 — Current provider mappings

The initial curated mappings shall support:

- DeepSeek V4 Flash and V4 Pro;
- Kimi K3 plus capability-discovered compatible Kimi models;
- GPT-5.6 Luna, Terra, and Sol.

The UI and API shall expose only currently supported provider/profile combinations.

### REQ-005 — Context compaction

The system shall maintain:

- immutable raw events and source artifacts;
- versioned structured state;
- hierarchical summaries;
- a bounded recent working window;
- retrieval of original evidence on demand.

Compaction shall preserve hard constraints, decisions, evidence references, conflicts, unresolved questions, next actions, hashes, and rehydration references.

### REQ-006 — User context profiles

The system shall expose `minimal`, `medium`, and `max` context profiles. `max` means maximum retained useful context within budget, not maximum compression.

### REQ-007 — Compaction safety

The system shall:

- never replace raw source-of-truth records with summaries;
- never persist hidden chain of thought;
- never summarize secrets into durable context;
- version every summary;
- record source ranges and hashes;
- run loss-audit fixtures;
- support rehydration;
- use hysteresis around compaction thresholds.

### REQ-008 — Multi-agent governance

Multi-agent execution shall require typed shared state, bounded fan-out, independent ownership, deterministic aggregation, disagreement records, cost/time/tool budgets, and human gates for high-risk outcomes.

Model consensus shall be evidence, never authority.

### REQ-009 — Product boundaries

- EACODE owns repository/code/tool supervision.
- EACHAT owns general conversation and answer quality.
- LIDR task branches own teacher-mandated deliverables plus isolated extras.
- EACORE remains documentation or architecture until at least two products prove equivalent stable contracts.

### REQ-010 — Phase 3C isolation

Spec 0009 shall remain provider-neutral. It shall not add live provider calls, model routing, autonomous repair, or multi-agent execution as part of the sandboxed-tool adapter slice.

## Non-functional requirements

- deterministic CI requires no provider keys or network;
- live providers remain opt-in manual evidence;
- all loops have explicit budgets;
- provider and compaction decisions are observable and replayable;
- model changes do not require domain-policy changes;
- selectors remain compatible with future model names through the capability registry;
- unsupported claims fail closed.

## Out of scope

- implementing live adapters in this documentation slice;
- declaring Kimi K3 superior without project benchmarks;
- enabling OpenAI expenditure without explicit budget;
- extracting EACORE runtime code;
- replacing Specs 0007–0009;
- changing the deterministic EACODE decider.
