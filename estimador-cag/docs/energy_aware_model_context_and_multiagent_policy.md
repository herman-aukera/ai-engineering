# Energy-Aware Provider, Context, and Multi-Agent Policy

**Applies to:** Session 13 Plus, future Session 14 work, EACHAT, EACODE, and EACORE extraction discussions  
**Document status:** architecture and product policy; implementation varies by product  
**Updated:** 2026-07-19  
**Default provider:** DeepSeek  
**Default reasoning intent:** `medium`  
**Default context detail:** `medium`

## 1. Purpose

This document defines a provider-neutral policy for:

- selecting DeepSeek, Kimi, or OpenAI models;
- mapping a common user-facing reasoning level to provider-supported capabilities;
- compacting long-running context without turning summaries into a false source of truth;
- deciding when multi-agent control is justified;
- keeping the four Energy-Aware products related without forcing premature shared runtime code.

Provider names, model IDs, prices, context windows, and effort modes are time-varying facts. Runtime behavior must use a versioned capability registry and explicit availability checks. Documentation is not proof that the current account can invoke a model.

## 2. Product boundaries

### 2.1 Session 13 Plus and coursework

Coursework follows:

```text
mandatory contract perfected first
→ measured additive improvements second
```

Session 13 Plus owns project-estimation orchestration, evidence-backed hour calculation, Critic/Boss policy, human review, checkpointing, scenarios, API/UI, and estimation audit.

### 2.2 EACODE

EACODE is intended to become a local Energy-Aware coding control plane between coding agents and protected repository/tool execution.

Conceptual flow:

```text
coding-agent proposal
→ repository/evidence inspection
→ coding critics
→ constraint energy
→ deterministic Boss
→ accept | repair | clarify | reject | human authorization
→ bounded execution
→ execution evidence
→ complete re-evaluation
```

Potential clients include Claude Code, Cline, Aider, Kimi Code, and other coding agents. EACODE must not become an unvalidated proxy that forwards raw model output directly to shell or repository mutation.

### 2.3 EACHAT

EACHAT is intended to become a general-purpose Energy-Aware conversational product.

Conceptual flow:

```text
user request
→ answer candidate
→ grounding/evidence route
→ typed critics
→ constraint energy
→ deterministic decision
→ bounded repair | clarify | refuse | escalate | accept
→ Energy Card
```

Multi-agent specialists may be useful for retrieval, domain analysis, selected repair, or high-risk review. They are not mandatory for every ordinary chat turn.

### 2.4 EACORE

EACORE may initially remain a documentation, architecture, contract, fixture, and evaluation layer.

Do not force code extraction because records have similar names. Extract only when at least two products independently prove equivalent semantics, versioning, compatibility, and rollback.

## 3. Provider selector

User-facing provider choices:

```text
Auto
DeepSeek
Kimi
OpenAI
```

Policy:

- `DeepSeek` is the default cost-aware provider.
- `Kimi` is the preferred alternative for long-context, multimodal, or independently calibrated agentic work.
- `OpenAI` is the premium route for cases whose expected quality gain justifies its cost.
- `Auto` selects the least expensive currently verified route satisfying stage, risk, context, modality, tool, latency, and quality requirements.

Do not label Kimi or any other provider as universally best. Vendor benchmarks are priors. Product-specific matched evaluation is the routing source of truth.

## 4. Common reasoning selector

Expose a stable product intent:

```text
minimal
medium
max
```

This is not copied blindly into provider API parameters. Each adapter resolves it through the current capability registry.

Unsupported combinations are disabled in the UI or rejected before execution.

### 4.1 DeepSeek mapping

Current configured family:

```text
deepseek-v4-flash
deepseek-v4-pro
```

Initial mapping:

| Common level | Initial route |
|---|---|
| `minimal` | V4 Flash, non-thinking / no explicit effort |
| `medium` | V4 Flash `high` or V4 Pro `high`, selected by stage and complexity |
| `max` | V4 Pro `max` |

DeepSeek remains the default until matched evidence supports another policy.

### 4.2 Kimi mapping

Current architecture should recognize:

```text
kimi-k3
Kimi K2.7 Code
Kimi K2.6
```

Kimi K3 launch constraints to encode:

- 1M-token context;
- native multimodality;
- `max` thinking effort at launch;
- do not claim `low` or `high` until capability discovery confirms availability;
- avoid switching into K3 mid-session without a clean checkpoint and normalized compacted handoff;
- impose explicit behavioral boundaries because the vendor reports excessive proactiveness.

Initial mapping:

| Common level | Initial route |
|---|---|
| `minimal` | K2.6 instant or K2.7 Code for coding stages |
| `medium` | calibrated K2.6/K2.7 route |
| `max` | K3 `max` |

K3 is a strong max-capability candidate, not a universal replacement for cheaper or more predictable routes.

### 4.3 OpenAI GPT-5.6 mapping

Current GPT-5.6 capability tiers:

```text
Luna
Terra
Sol
```

Initial mapping:

| Common level | Initial route |
|---|---|
| `minimal` | GPT-5.6 Luna with the lowest verified supported effort |
| `medium` | GPT-5.6 Terra at a verified medium/high effort |
| `max` | GPT-5.6 Sol at `max` |
| exceptional opt-in | Sol `ultra` or API multi-agent only when account support, policy, and budget are verified |

Do not invent aliases or effort values. Use official model-list/capability discovery and account-level verification.

## 5. Versioned capability registry

Each model record contains:

```text
provider
provider_model_id
display_name
capability_tier
context_window
max_output
input_modalities
tool_support
structured_output_support
reasoning_efforts
speed_class
cost_metadata_version
availability
verified_at
calibration_status
```

Lifecycle:

```text
documented
→ configured
→ reachable
→ contract_verified
→ benchmark_calibrated
→ enabled
```

A model may also be `disabled` with a reason.

The UI renders only valid provider/model/reasoning combinations.

## 6. Routing authority

```text
model/actor proposes
→ deterministic policy validates
→ product Boss decides
```

A model cannot:

- promote itself to a higher tier;
- raise its cost or tool budget;
- change privileges;
- bypass a human gate;
- declare its own output accepted;
- silently switch provider or model.

Every escalation requires a reason code and consumes an explicit budget.

## 7. Context-detail selector

Use the label:

```text
Context detail
```

Values:

```text
minimal
medium
max
```

Meaning:

| Setting | Behavior |
|---|---|
| `minimal` | aggressive compaction; retain active objective, hard constraints, authoritative decisions, evidence references, current state, budgets, and next action |
| `medium` | balanced default; retain structured history plus recent relevant detail |
| `max` | preserve the most verified detail; compact later while retaining broad decision/evidence history |

This label avoids the inversion of “compaction strength,” where `max` could otherwise mean less retained context.

## 8. Canonical compacted context

Every compacted handoff preserves:

```text
identity and schema/policy versions
repository, branch, and exact SHA
working mode and current objective
hard constraints and authority boundaries
accepted decisions
rejected alternatives and reasons
verified evidence references
current candidate/state
unresolved questions and risks
budgets and provider route
last green tests and CI
current checkpoint/revision
next exact action
rollback boundary
claim boundary
```

A summary is a derived projection, never the sole source of truth.

## 9. Compaction triggers

Compact at controlled boundaries:

- configured context/token occupancy;
- graph-stage transitions;
- before supervisor re-entry after large tool output;
- before provider/model switching;
- before and after a human pause;
- after a completed implementation slice;
- when duplicate or contradictory context is detected.

Keep immutable source records, checkpoints, evidence references, and candidate/decision history outside the summary.

## 10. Rotten-context prevention

Before consuming a compacted context:

- verify branch and SHA freshness;
- verify schema, policy, and model-registry versions;
- preserve authoritative identifiers;
- ensure assumptions were not promoted to facts;
- ensure unresolved decisions were not marked accepted;
- detect contradictory summaries;
- avoid repeated summary-of-summary degradation;
- retrieve the authoritative source when a critical detail is absent;
- generate a fresh normalized handoff before switching providers.

Kimi K3 requires special care because its vendor documents sensitivity to preserved thinking history and mid-session model switching.

## 11. Multi-agent decision rule

Use multiple agents only when they buy a concrete property.

### Cooperation

Use specialists for orthogonal work:

- requirements;
- retrieval;
- estimation;
- validation;
- security review;
- proposal generation.

### Competition

Use competing agents only when divergence is useful evidence:

- conservative versus aggressive estimates;
- independent high-risk provider review;
- alternative repair or patch strategies.

Competition must differ materially in evidence, policy, prompt, or provider. Two copies of the same model with adjective-only prompts are correlated output, not independent evidence.

### Supervisor

Use a supervisor when the next action is genuinely unknown at design time.

A fixed sequence belongs in explicit graph edges, not in a model call pretending to route.

## 12. Manual supervisor policy

For Session 14, construct the supervisor as an explicit `StateGraph` node returning typed `Command` updates.

Recommended pattern:

```text
deterministic prerequisites and safety guards
→ optional typed route proposal
→ deterministic allow-list validation
→ budget/loop/privilege checks
→ Command(goto=..., update=...)
```

Do not use a high-level `create_supervisor` helper for the mandatory exercise because it hides the routing behavior the task requires in traces.

## 13. Security boundaries

- Model output is untrusted input.
- Tool privileges are server-owned.
- Arguments are strictly typed.
- Arithmetic is Python-owned.
- Evidence is referenced rather than copied into public audit packets.
- Human decisions require actor, reason, revision, and authorization scope.
- Prompts, transcripts, raw provider output, hidden reasoning, credentials, and DSNs are excluded from summaries, traces, and audit exports.
- No destructive action is inferred from acknowledgement or generic approval.

## 14. Evaluation policy

For each route measure:

- schema validity;
- task success;
- evidence precision/coverage;
- hallucinated scope;
- Critic defect recall;
- repair improvement;
- human correction magnitude;
- latency p50/p95;
- tokens and cost;
- retries/fallbacks;
- checkpoint/resume success;
- duplicate-free replay;
- trace completeness.

Select routes from a Pareto frontier rather than a single vendor score.

## 15. Claim boundary

Allowed:

> The products define a provider-neutral, capability-discovered policy with DeepSeek as default, Kimi K3 as a documented max-capability candidate, GPT-5.6 as a premium family, common reasoning/context selectors, and explicit multi-agent/context-compaction safeguards.

Blocked until implementation and evidence:

- every product exposes the selectors;
- Kimi K3 is universally superior;
- GPT-5.6 is always worth its cost;
- adaptive routing improves quality;
- compaction never loses important context;
- EACORE is a shared production runtime;
- multi-agent architecture improves every task.

## Operational claim correction

Provider records seeded from documentation are not automatically enabled. `Auto` is a deterministic policy preview unless a registry snapshot contains explicitly promoted, available models. Current Kimi Code catalogue IDs are `k3`, `kimi-for-coding`, and `kimi-for-coding-highspeed`; K3 exposes low/high/max effort, while K2.7 Code requires thinking to remain enabled. Runtime superiority and least-cost claims require matched evidence.
