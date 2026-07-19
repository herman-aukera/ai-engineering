# Provider Routing, Context Compaction, and Multi-Agent Portfolio Architecture

**Status:** architecture decision and product guidance  
**Effective date:** 2026-07-19  
**Shared runtime status:** not implemented  
**Owner:** EACORE documentation and contract governance  
**Product implementation owners:** EACODE, EACHAT, and each coursework branch

## 1. Executive decision

The portfolio will support three primary providers:

1. **DeepSeek** as the default cost/performance route.
2. **Kimi** as the frontier open-model route, beginning with Kimi K3.
3. **OpenAI** as the premium reference and escalation route, beginning with the
   GPT-5.6 family.

The product UI and APIs must separate:

- provider selection;
- model/execution tier;
- reasoning effort;
- context-compaction profile;
- multi-agent parallelism.

These are different decisions and must not be compressed into one ambiguous
"model quality" switch.

No provider-specific mode may be advertised or selected until a versioned
capability registry proves that it is available to the current account and API.

## 2. Verified provider state on 2026-07-19

### 2.1 DeepSeek

Verified official models:

- `deepseek-v4-flash`;
- `deepseek-v4-pro`.

Both support 1M context, thinking and non-thinking modes, tools, and structured
JSON. Thinking effort supports `high` and `max`. Lower effort values are mapped
up by the provider rather than representing distinct native levels.

Portfolio mapping:

| Execution profile | Model | Thinking | Effort |
|---|---|---|---|
| instant | `deepseek-v4-flash` | disabled | not applicable |
| balanced | `deepseek-v4-flash` | enabled | high |
| max | `deepseek-v4-pro` | enabled | max |

DeepSeek is the default provider because it offers the strongest current
cost/performance fit for routine agentic work. This is a portfolio policy, not a
claim that it wins every benchmark.

### 2.2 Kimi

Kimi K3 was officially released on 2026-07-16. Moonshot describes it as a
2.8T-parameter, natively multimodal model with a 1M-token context window for
long-horizon coding, knowledge work, and deep reasoning.

Official API model ID:

- `kimi-k3`.

At launch, Kimi K3 uses `max` thinking effort. Moonshot announced low and high
effort modes for later releases. Until the official API exposes and verifies
those modes, the capability registry must represent:

| Execution profile | Kimi model | Status |
|---|---|---|
| instant | no K3 mapping | unsupported at launch |
| balanced | no K3 mapping | unsupported at launch |
| max | `kimi-k3` | supported, max effort |

A product may optionally use Kimi K2.7 Code or K2.6 as separate Kimi-family
fallbacks, but it must not label them as Kimi K3 modes.

Kimi K3 must normally start a fresh provider session. Moonshot warns that K3
depends on preserved thinking history and may become unstable when switched
into an ongoing session created by another model.

### 2.3 OpenAI

GPT-5.6 is available in three durable capability tiers:

- Luna — fastest and lowest-cost;
- Terra — balanced everyday model;
- Sol — flagship.

GPT-5.6 also introduces `max` reasoning and an explicit `ultra` mode that
coordinates multiple agents. Ultra is not merely a higher scalar reasoning
setting; it is a different orchestration mode.

Portfolio mapping:

| Execution profile | GPT-5.6 tier | Default reasoning |
|---|---|---|
| instant | Luna | minimal or low when supported |
| balanced | Terra | medium |
| max | Sol | max |
| ultra | Sol | explicit multi-agent mode |

The UI may display friendly labels such as Instant, Balanced, and Max, but it
must preserve exact provider/model/effort metadata in traces and ledgers.

## 3. Normalized selection contract

Proposed user request:

```json
{
  "provider": "auto",
  "execution_profile": "balanced",
  "reasoning_profile": "medium",
  "context_profile": "medium",
  "parallelism": "off",
  "strict_provider": false,
  "allow_fallback": true,
  "max_cost_usd": null,
  "max_latency_ms": null
}
```

Allowed normalized values:

```text
provider:
  auto | deepseek | kimi | openai

execution_profile:
  instant | balanced | max

reasoning_profile:
  minimal | medium | max

context_profile:
  minimal | medium | max

parallelism:
  off | bounded | swarm
```

`swarm` must remain unavailable unless the selected provider and product
orchestrator explicitly support it.

Proposed resolution result:

```json
{
  "status": "exact",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "thinking": "enabled",
  "reasoning_effort": "high",
  "context_profile": "medium",
  "parallelism": "off",
  "capability_snapshot": "providers-2026-07-19",
  "warnings": [],
  "fallback_chain": []
}
```

Resolution status:

- `exact` — all requested capabilities are available;
- `repaired` — the product adjusted an unsupported combination and explains it;
- `fallback` — provider/model changed under an explicit fallback policy;
- `rejected` — hard constraints prevent safe or truthful resolution.

No silent fallback is allowed.

## 4. Energy-Aware routing policy

### Hard constraints

- provider credentials are available without exposing them;
- exact model exists and account access is verified;
- requested modalities and tools are supported;
- context fits after compaction;
- safety and data-handling policy allows the provider;
- cost and latency hard budgets are not exceeded;
- provider-session compatibility is satisfied;
- a deprecated model is not selected after its removal date.

### Soft constraints

- expected answer quality;
- coding or general-task specialization;
- cache effectiveness;
- latency;
- token price;
- repair history;
- provider reliability;
- current benchmark/evaluation evidence.

### Decision sequence

```text
read user selectors
→ load capability registry
→ evaluate hard constraints
→ score valid candidates
→ choose exact candidate
→ otherwise repair, request fallback permission, or reject
→ record selection evidence
→ pin provider/model for the session
```

The model does not authorize its own selection. Product policy owns the final
route.

## 5. Product application

### 5.1 EACODE

EACODE may become a local, continuously running Energy-Aware coding gateway.

Possible topology:

```text
Claude Code / Cline / Aider / IDE / local client
→ EACODE-compatible local API
→ provider router
→ actor model
→ parallel coding critics
→ deterministic Boss
→ repair/refine loop
→ safe tool authorization
→ audited response, patch, or refusal
```

Recommended critics:

- specification compliance;
- test adequacy;
- architecture boundary;
- security and secret hygiene;
- command safety;
- rollback readiness;
- diff scope;
- evidence completeness.

EACODE owns repository mutation, command authorization, patch application, and
coding-specific decisions. EACORE must not own them.

An Anthropic-compatible or OpenAI-compatible local endpoint may be designed
later so external coding clients can use EACODE as a gateway. That compatibility
surface requires its own specification, authentication, streaming, tool-call,
error, and cancellation tests.

### 5.2 EACHAT

EACHAT should be an Energy-Aware general-purpose chat product with a familiar
ChatGPT-style interface.

Possible topology:

```text
user request
→ provider/model/context selectors
→ request and evidence classification
→ one or more answer candidates
→ parallel chat critics
→ deterministic Boss
→ accept / repair / clarify / refuse / escalate
→ Energy Card and answer
```

Recommended critics:

- grounding and citation validity;
- current-information requirements;
- safety;
- privacy;
- instruction following;
- completeness;
- consistency;
- usefulness;
- verbosity and structure;
- provider cost/latency.

EACHAT owns the chat UX, memory, retrieval, answer repair, refusals, and Energy
Card.

### 5.3 Session 13 Plus and later coursework

Coursework should:

1. satisfy every mandatory teacher requirement;
2. prove it with tests, traces, CI, and the required demo;
3. improve architecture and pedagogy where the improvement is bounded;
4. add optional extras only after the mandatory path is green;
5. document extras separately so they cannot hide missing requirements.

"Better than the teacher" means stronger correctness, clarity, tests,
observability, rollback, and explanation. It does not mean uncontrolled scope.

Session 13's Critic/Boss and multi-agent graph are a valuable laboratory for the
other products, but coursework code is not automatically production or shared
core code.

### 5.4 EACORE

EACORE may own:

- provider capability and selection envelopes;
- normalized profile names;
- provider/model references;
- compaction policy and record envelopes;
- selection and compaction audit events;
- compatibility fixtures;
- cross-product evaluation schemas.

EACORE must not own:

- API clients or keys;
- provider-specific prompts;
- live routing weights;
- product fallback policy;
- provider billing accounts;
- chat or coding decision semantics;
- multi-agent graph topology.

Documentation-only commonality is a valid EACORE outcome.

## 6. Context-compaction architecture

### 6.1 Objective

Prevent context rot without losing the information needed to continue work
safely and accurately.

### 6.2 Structured compaction record

Every compaction should preserve:

- session and thread identity;
- provider/model identity;
- source context profile;
- current objective;
- accepted decisions;
- hard and soft constraints;
- user preferences;
- repository/product state;
- evidence references;
- completed work;
- unresolved work;
- risks and stop conditions;
- recent raw-turn window;
- next exact action;
- rollback boundary;
- token counts before and after;
- compaction algorithm/prompt version;
- summary hash;
- source-range references.

Do not store private chain of thought.

### 6.3 User profiles

Initial benchmark defaults:

| Context profile | Intended behavior |
|---|---|
| minimal | Preserve anchors, unresolved items, evidence refs, and a small recent-turn window |
| medium | Preserve detailed decisions, state, risks, and a moderate recent-turn window |
| max | Preserve the fullest structured summary and a large recent raw window |

The names describe retained detail, not compression aggressiveness.

Token thresholds are product configuration and must be benchmarked rather than
treated as universal constants.

### 6.4 Compaction sequence

```text
measure context utilization
→ identify immutable anchors
→ extract decisions and unresolved work
→ preserve evidence references
→ summarize older episodes
→ retain recent raw turns
→ validate against source
→ hash and version the compaction
→ continue or start a provider-compatible session
```

### 6.5 Model switching

A provider or model switch requires:

- explicit user or policy reason;
- capability re-resolution;
- a structured handoff summary;
- preservation of evidence and decision references;
- a fresh session when provider thinking-history requirements differ;
- an audit event linking the old and new sessions.

For Kimi K3, default to a fresh K3 session.

## 7. Multi-agent applicability

The released Session 13 multi-agent task is directly useful across the
portfolio when agents have independent roles and produce inspectable evidence.

### Good applications

| Product | Multi-agent application |
|---|---|
| EACODE | parallel spec, tests, security, architecture, and rollback critics |
| EACHAT | parallel grounding, safety, instruction, consistency, and usefulness critics |
| Coursework | parallel nodes, bounded retries, fallback, Boss routing, and human gates |
| Evals | same prompt across providers, independent graders, disagreement analysis |
| Context compaction | summary generator plus factuality/coverage validator |

### Bad applications

- simple questions with no decomposable work;
- several agents repeating the same prompt;
- agents that share one unverified assumption;
- majority voting without deterministic policy;
- unbounded parallelism;
- using an expensive swarm before a single-agent baseline;
- letting model consensus override hard constraints.

### Required controls

- bounded concurrency;
- per-agent role and input contract;
- independent evidence;
- deterministic aggregation;
- disagreement policy;
- retry, cost, and latency budgets;
- cancellation;
- trace correlation;
- redaction;
- human escalation for unresolved high-risk disagreement.

## 8. Context and routing telemetry

Record:

- selected provider and exact model;
- execution, reasoning, and context profiles;
- resolution status;
- capability-registry version;
- fallback and repair reasons;
- token use;
- cache use;
- latency;
- estimated cost;
- compaction count;
- context before/after;
- summary version/hash;
- multi-agent fan-out and completion;
- final product decision.

Do not record keys or hidden reasoning.

## 9. Implementation order

1. Documentation and capability snapshot.
2. Product-local provider registry.
3. Deterministic selector and failure behavior.
4. Fake-provider contract tests.
5. Structured compaction records and fixtures.
6. Context-profile tests.
7. One product-local UI/CLI selector.
8. Provider smoke tests outside deterministic CI.
9. Multi-agent critic pilot with bounded concurrency.
10. Cross-product extraction only after two products prove equivalent contracts.

## 10. Official sources

- Moonshot Kimi K3 release:
  https://www.kimi.com/blog/kimi-k3
- Kimi API platform:
  https://platform.kimi.ai/
- DeepSeek Claude Code integration:
  https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code
- DeepSeek model and reasoning API:
  https://api-docs.deepseek.com/
- OpenAI GPT-5.6 release:
  https://openai.com/index/gpt-5-6/
- Anthropic Claude Code gateway configuration:
  https://docs.anthropic.com/en/docs/claude-code/llm-gateway
