# Spec 0010 — Provider Routing and Context Compaction Requirements

Status: partial runtime implementation; rescue and capability refresh required  
Product owner: EACODE  
Cross-product relevance: EACHAT, LIDR task branches, possible EACORE extraction  
Recovery audit: `docs/eacode_provider_execution_rescue_audit_2026-07-20.md`

## Objective

Provide a provider-neutral selection layer, context-compaction contract, and bounded multi-agent governance model without coupling Spec 0009 process execution to any model provider.

The deterministic capability registry and selector exist. Live provider adapters, served-model evidence, context compaction, multi-agent execution, and product UI remain incomplete.

## Functional requirements

### REQ-001 — Provider-neutral selector

The system shall accept:

- provider: `auto`, `deepseek`, `kimi`, or `openai`;
- profile: `minimal`, `medium`, or `max`;
- context profile: `minimal`, `medium`, or `max`;
- fallback policy: `none`, `same_provider`, or `governed_cross_provider`;
- explicit input/output token assumptions;
- explicit request budget;
- explicit premium-escalation reason when applicable.

### REQ-002 — Capability registry

The system shall resolve selections through a versioned capability manifest containing:

- provider and surface;
- exact model identity and aliases;
- context and output limits;
- supported reasoning modes and effort values;
- speed class;
- tool, structured-output, vision, and prompt-cache support;
- current input, cached-input, and output prices with units;
- availability and entitlement state;
- verification timestamp;
- source identity and source version.

Unknown, stale, unavailable, or unsupported capabilities shall fail closed.

A provider `/models` response may confirm reachability or availability but does not replace curated capability verification.

### REQ-003 — Default and escalation policy

The default policy shall be:

1. DeepSeek for normal cost-sensitive work;
2. Kimi as the user-preferred frontier/open-model path;
3. OpenAI GPT-5.6 as explicit budget-gated premium escalation.

Cross-provider fallback shall record reason, budget, provider, exact model, requested and served effort, attempts, retries, and circuit-breaker state.

Every fallback candidate shall re-enter the same product critics and deterministic decider. Model output never approves itself.

### REQ-004 — Current provider mappings

The curated registry shall distinguish provider surfaces and use current official facts.

#### DeepSeek API

Support:

- `deepseek-v4-flash`;
- `deepseek-v4-pro`.

Record current official context, output, cache, effort, and pricing capabilities. Thinking efforts are `high` and `max`; compatibility values must not be represented as independent native capabilities.

#### Kimi API and Kimi Code

Distinguish:

- Kimi general API `kimi-k3`;
- Kimi Code `k3`;
- Kimi Code `kimi-for-coding`;
- Kimi Code `kimi-for-coding-highspeed` where entitled.

Kimi Code K3 currently supports `low`, `high`, and `max` effort, with `max` as the default. Do not retain the obsolete max-only assumption.

Kimi Code model or effort switching shall create a clean provider-session boundary because prompt-cache compatibility and retained thinking history may change.

#### OpenAI API

Support:

- `gpt-5.6-luna`;
- `gpt-5.6-terra`;
- `gpt-5.6-sol`.

Record current official context, output, effort, and pricing capabilities. Premium or multi-agent modes remain separate authorized capabilities.

The UI and API shall expose only currently supported and entitled provider/profile combinations.

### REQ-005 — Planned route versus served route

A deterministic selector result is a `ProviderPlan`, not proof of external execution.

Live execution evidence shall separately record:

- requested provider/model/profile;
- planned provider/model/effort;
- exact served provider/model/effort;
- provider request ID where safe;
- capability snapshot hash;
- response status;
- fallback steps;
- retries and circuit state;
- token, latency, and cost actuals;
- whether the candidate re-entered critics and the decider.

### REQ-006 — Budget correctness

Budget estimates shall use explicit expected input and output token quantities, current price units, cached-input assumptions, and model-specific pricing.

Budget enforcement applies to every provider, not only OpenAI. OpenAI additionally requires an explicit premium reason and authorization.

### REQ-007 — Context compaction

The system shall maintain:

- immutable raw events and source artifacts;
- versioned structured state;
- hierarchical summaries;
- a bounded recent working window;
- retrieval of original evidence on demand.

Compaction shall preserve hard constraints, decisions, evidence references, conflicts, unresolved questions, next actions, hashes, repository revisions, and rehydration references.

### REQ-008 — User context profiles

The system shall expose `minimal`, `medium`, and `max` context profiles. `max` means maximum retained useful context within budget, not maximum compression.

### REQ-009 — Compaction safety

The system shall:

- never replace raw source-of-truth records with summaries;
- never persist hidden chain of thought;
- never summarize secrets into durable context;
- version every summary;
- record source ranges and hashes;
- detect stale and contradictory summaries;
- detect summary-of-summary decay;
- run deterministic loss-audit fixtures;
- support evidence rehydration;
- use hysteresis around compaction thresholds;
- invalidate summaries whose branch, repository snapshot, policy, or schema version is stale.

A failed loss audit blocks acceptance and requires rehydration or a safer profile.

### REQ-010 — Multi-agent governance

Multi-agent execution shall require typed shared state, bounded fan-out, independent ownership, deterministic aggregation, disagreement records, cost/time/tool/concurrency budgets, and human gates for high-risk outcomes.

Model consensus is evidence, never authority. The deterministic boss owns final disposition.

No two agents may mutate the same worktree concurrently.

### REQ-011 — Product boundaries

- EACODE owns repository/code/tool supervision.
- EACHAT owns general conversation and answer quality.
- LIDR task branches own teacher-mandated deliverables plus isolated extras.
- EACORE remains documentation or architecture until at least two products prove equivalent stable contracts.

### REQ-012 — Spec 0009 isolation

Spec 0009 remains provider-neutral. It shall not add live provider calls, model routing, autonomous repair, or multi-agent execution as part of process execution.

Provider selection can produce candidate or routing evidence but cannot grant tool authority.

### REQ-013 — Real execution isolation

A plan whose mode is `dry_run` or `fake` shall never start a real OS process.

Real process execution requires:

- an explicit typed live-execution intent;
- an exact plan hash;
- an exact repository snapshot;
- trusted authorization or policy authority appropriate to the risk;
- disabled-by-default runtime configuration;
- pre-start revalidation immediately before process creation.

Enabling an adapter flag alone is not an authority transition.

## Non-functional requirements

- deterministic CI requires no provider keys, network, or real EACODE-managed process execution;
- live providers and live processes remain opt-in manual evidence;
- all loops have explicit budgets;
- provider and compaction decisions are observable and replayable;
- model changes do not require domain-policy changes;
- capability changes require fixture and compatibility-test updates;
- selectors remain compatible with future model names through the capability registry;
- mutable global registry state is forbidden;
- an explicitly supplied empty registry remains empty and must not fall back silently;
- unsupported claims fail closed.

## Out of scope for the current rescue slice

- declaring Kimi K3 superior without matched project benchmarks;
- enabling OpenAI expenditure without explicit budget and reason;
- extracting EACORE runtime code;
- replacing Specs 0007–0009;
- changing the deterministic EACODE decider;
- implementing context compaction before provider and execution repairs are green;
- implementing multi-agent orchestration before a single-agent baseline exists.
