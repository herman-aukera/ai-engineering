# EACHAT provider routing, reasoning and context-compaction specification

**Status:** canonical architecture. Provider catalog/adapters, strict provider routing, and request-scoped BYOK are implemented. Context-compaction extensions and expanded multi-agent execution remain evidence-gated follow-on work.  
**Updated:** 2026-08-23  
**Current provider fact authority:** `docs/energy_aware_chat_provider_fact_audit_2026-08-23.md`

## 1. Purpose

This specification defines how EACHAT separates stable product intent from provider-specific model names, reasoning controls, credentials, and temporal capability facts.

The governing rule is:

```text
user intent -> stable EACHAT effort profile -> allow-listed provider capability
            -> provider-specific parameters -> candidate proposal
            -> deterministic EACHAT governance
```

Provider output is never hard authority. Deterministic EACHAT policy owns evidence sufficiency, hard constraints, repair bounds, disposition, human escalation, and final record semantics.

## 2. Stable product controls

EACHAT exposes three stable effort profiles:

- `fast`
- `balanced`
- `max`

These product values are deliberately independent from changing vendor model names. A vendor may rename, replace, reprice, or change a model without changing the public EACHAT effort vocabulary. Such a vendor change requires a reviewed catalog revision rather than silent runtime substitution.

Provider choice and effort are separate dimensions:

```text
provider = deepseek | kimi | openai
effort   = fast | balanced | max
```

`auto` routing is not treated as calibrated production authority. Until cross-provider evidence proves a stable policy, an explicit provider selection is required for live routing.

## 3. Capability catalog contract

Executable authority lives in:

```text
app/energy_chat/provider_catalog.py
```

Current catalog contract:

```text
catalog version: 2.1.0
verified at:     2026-08-23
review by:       2026-09-22
maximum age:     30 days
```

Each allow-listed entry carries at least:

- provider;
- API surface;
- server-owned endpoint base URL;
- exact model ID;
- display name;
- availability status;
- source references;
- verification date;
- context/output limits when published;
- modality/tool/structured-output/streaming/cache capabilities;
- supported product effort profiles;
- provider reasoning controls;
- temporal price facts when published;
- billing model;
- adapter status;
- calibration status;
- EACHAT eligibility;
- entitlement notes where relevant.

Unknown facts remain `None`; they are never guessed.

### 3.1 Temporal freshness

Provider capabilities and prices are external temporal facts. Structural validation alone is insufficient.

`assert_catalog_fresh(...)` fails closed when:

- the verification date is in the future;
- the declared review window exceeds the configured maximum age;
- the current validation date is after `CATALOG_REVIEW_BY`;
- the catalog age exceeds `CATALOG_MAX_AGE_DAYS`.

The normal deterministic test suite evaluates this freshness contract using the CI calendar date. After 2026-09-22, the repository must turn RED until official provider sources are reviewed and the catalog/evidence are advanced.

The deadline is a maximum review interval, not permission to ignore an earlier known vendor change. Material provider changes require immediate re-verification.

## 4. Provider surfaces and routing

### 4.1 DeepSeek

Product API surface:

```text
provider: deepseek
base URL: https://api.deepseek.com
```

Current deterministic mapping:

| EACHAT effort | Model | Provider control |
| --- | --- | --- |
| `fast` | `deepseek-v4-flash` | thinking disabled |
| `balanced` | `deepseek-v4-flash` | thinking enabled |
| `max` | `deepseek-v4-pro` | thinking enabled |

The current fact audit records the published context, output limits, prompt-cache behavior, tools/structured-output support and pricing.

### 4.2 Kimi Platform

EACHAT product-runtime Kimi calls use the Kimi API Platform surface:

```text
provider: kimi
base URL: https://api.moonshot.ai/v1
model: kimi-k3
```

Current deterministic mapping:

| EACHAT effort | Model | Provider control |
| --- | --- | --- |
| `fast` | `kimi-k3` | `reasoning_effort=low` |
| `balanced` | `kimi-k3` | `reasoning_effort=high` |
| `max` | `kimi-k3` | `reasoning_effort=max` |

The catalog records the currently published 1M context, output-token ceiling, multimodal input, tools, structured output, streaming, caching and pricing.

### 4.3 Kimi Code is a different entitlement surface

Kimi Code membership is explicitly **not** an EACHAT product-runtime credential.

The catalog may retain Kimi Code entries such as:

- `k3`;
- `kimi-for-coding`.

Those entries exist to preserve factual product/coding-surface separation and entitlement evidence. They have `eligible_for_eachat=False` and cannot become an EACHAT runtime route merely because Kimi Code was used to develop the repository.

Current documented boundaries include:

- K3 availability to Moderato and above;
- up-to-1M K3 context requiring Allegretto or above;
- K2.7 Code at 256K context with Thinking ON.

### 4.4 OpenAI

EACHAT uses the OpenAI Responses API surface:

```text
provider: openai
base URL: https://api.openai.com/v1
```

Current deterministic mapping:

| EACHAT effort | Model | Product/provider control |
| --- | --- | --- |
| `fast` | `gpt-5.6-luna` | Luna profile |
| `balanced` | `gpt-5.6-terra` | Terra profile |
| `max` | `gpt-5.6-sol` | `reasoning.effort=max` |

Catalog `2.1.0` represents the current general-availability GPT-5.6 API family, published 1.05M context, 128K maximum output, current reasoning-effort vocabulary, tool/structured-output/streaming/cache support, and source-dated prices.

Pricing is temporal evidence, not a permanent protocol invariant. In particular, the current Sol price includes the reduction announced on 2026-08-21 and must be rechecked by the catalog review deadline or sooner if OpenAI changes it.

## 5. Strict provider authority boundary

Provider routing is allow-list based.

The client may select an allowed provider and stable effort profile. It may not inject:

- an arbitrary base URL;
- an arbitrary model ID;
- an unregistered provider;
- an unsupported provider parameter;
- a silent fallback ladder.

Server-controlled capability data determines endpoint and model identity.

If a provider/effort combination cannot be resolved, routing fails closed rather than inventing a substitute.

A requested provider and a served provider/model are distinct observable facts. Silent cross-provider substitution is forbidden.

## 6. Request-scoped BYOK

EACHAT supports request-scoped BYOK credentials with explicit role ownership:

```text
fast          -> Worker credential
balanced/max  -> Critic/Advisor credential
```

The roles are intentionally independent. A Worker key does not implicitly authorize Critic/Advisor calls and vice versa.

Credential state is request-local and must not become durable conversation state, checkpoint state, audit payload, telemetry, model-visible prompt content, or application configuration.

Secrets are excluded from ordinary object representations and first-party telemetry. Browser engineering surfaces do not intentionally persist BYOK keys.

### 6.1 Hard call budgets

Each BYOK role has a server-enforced call budget. The budget is consumed immediately before the delegated provider call.

This prevents provider-side failure from creating an accidental unbounded retry/funding path.

### 6.2 BYOK-exclusive fail-closed behavior

When a request enters BYOK-exclusive routing, a missing required role credential is an error.

It must **not** fall back to:

- a service-funded key;
- another BYOK role;
- another provider;
- a hidden global credential.

This is an authority invariant, not a UI preference.

## 7. Provider adapters

Current V2 live-provider adapters are isolated behind the candidate-provider contract.

Implemented repository behavior includes:

- DeepSeek product adapter;
- Kimi Platform adapter;
- OpenAI Responses adapter;
- provider-neutral candidate result contract;
- server-controlled endpoint/model selection;
- strict effort mapping;
- bounded timeout/call semantics;
- requested-versus-served provider/model evidence;
- fake transport injection for deterministic CI;
- sentinel/test credential rejection where applicable;
- no adapter-internal cross-provider fallback.

Legacy LiteLLM coursework routing is not the canonical EACHAT V2 production provider path.

Live credential success remains a separate evidence class and is deliberately excluded from blocking deterministic CI.

## 8. Deterministic governance remains above providers

The provider produces a candidate. It does not determine whether the answer may be served.

The canonical control loop remains:

```text
UNDERSTAND
-> GATHER_EVIDENCE
-> PROPOSE
-> CRITIQUE
-> SCORE / DECIDE
-> bounded REPAIR
-> AUTHORIZE when protected
-> RECORD
```

Deterministic code owns:

- hard constraints;
- evidence requirements;
- critic interpretation;
- Energy/disposition policy;
- repair limits;
- refusal/escalation decisions;
- protected human continuation;
- authoritative record state.

A stronger model or higher reasoning setting cannot bypass these controls.

## 9. Context compaction

Context compaction is a separate concern from provider selection and reasoning effort.

Conceptually:

```text
provider selection != model tier != reasoning effort != context profile
```

Any future compaction implementation must preserve:

- system/developer authority instructions;
- user objective and current request;
- unresolved constraints;
- authoritative evidence and citations;
- durable human decisions;
- relevant repair/critic state;
- stable ownership identifiers without secret material.

It must not turn lossy summaries into new authority or silently discard evidence required by deterministic gates.

Expanded context-compaction behavior remains evidence-gated follow-on work. The current provider catalog does not imply that all vendor context windows should be filled or that longer context is automatically better.

## 10. Multi-agent execution

Provider selection, reasoning effort and multi-agent parallelism are distinct controls.

Future expanded agent committees must remain subordinate to deterministic governance and bounded by explicit budgets. Parallelism cannot multiply provider calls without a deterministic cap.

The current production claim does **not** require an unbounded provider-agent swarm. Existing deterministic critics and bounded repair remain the authoritative product path.

## 11. Observability

Provider telemetry may record safe, non-secret operational facts such as:

- requested provider;
- served provider;
- requested effort;
- served model;
- fallback-used flag where explicitly supported;
- duration;
- bounded call counters;
- stable failure/reason code.

It must not record:

- API keys;
- authorization headers;
- raw private prompts/transcripts as generic operational telemetry;
- arbitrary client-injected endpoint values.

The neutral production envelope remains `energy-aware.event.v1`.

## 12. Validation and release gates

Provider-routing changes require deterministic validation of at least:

1. catalog schema and source references;
2. exact provider/model allowlisting;
3. stable effort resolution;
4. surface separation, especially Kimi Platform versus Kimi Code;
5. BYOK role isolation and call budgets;
6. missing-role fail-closed behavior;
7. no arbitrary endpoint injection;
8. no silent cross-provider fallback;
9. requested-versus-served evidence;
10. provider temporal-fact freshness;
11. canonical documentation alignment;
12. production dependency/supply-chain contracts.

Credentialed live smoke remains separate, bounded and non-blocking for deterministic CI.

## 13. Migration status

Completed:

- versioned provider capability catalog;
- DeepSeek/Kimi/OpenAI explicit model mappings;
- Kimi Platform versus Kimi Code surface separation;
- isolated provider adapters;
- strict provider/effort resolution;
- request-scoped Worker and Critic/Advisor BYOK;
- hard BYOK call budgets;
- no hidden BYOK-to-service-funded fallback;
- legacy LiteLLM removal from the V2 production routing path;
- source-dated current provider fact audit;
- fail-closed 30-day temporal freshness contract.

Evidence-gated / not claimed complete:

- current-head credentialed success for every provider/model;
- calibrated `auto` cross-provider selection;
- superiority claims between providers;
- expanded context-compaction policies;
- expanded multi-agent parallel execution;
- real public-production traffic behavior.

## 14. Current claim boundary

EACHAT has an implemented, source-dated provider capability catalog and isolated provider-routing architecture for DeepSeek, Kimi K3 and OpenAI GPT-5.6, subordinate to deterministic governance, with request-scoped BYOK isolation and a fail-closed temporal fact-review deadline.

This does **not** claim that:

- all current-head provider credentials have been live-tested;
- one provider is objectively best;
- `auto` routing is calibrated;
- vendor prices or availability will remain unchanged after the verification date;
- the public beta is production-ready;
- coding-agent membership credentials are interchangeable with EACHAT product API credentials.

For temporal provider facts, `docs/energy_aware_chat_provider_fact_audit_2026-08-23.md` and catalog `2.1.0` are the current repository authority until their review deadline or an earlier known vendor change.
