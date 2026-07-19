# EACHAT Milestone 10 addendum — provider, effort and context neutrality

Status: mandatory clarification for Milestone 10 implementation.

This addendum supplements `energy_aware_chat_milestone_10_graph_api_spec.md`. It does not replace that specification.

## 1. Purpose

Milestone 10 must not hard-code the new graph-backed API to a permanent DeepSeek-only product contract. At the same time, it must not expand into full Kimi K3, GPT-5.6, context-persistence or multi-agent implementation.

The goal is **contract readiness without scope inflation**.

## 2. Request compatibility fields

The V2 request may define strict additive selectors:

```text
provider_preference = auto | deepseek | kimi | openai
effort_profile = fast | balanced | max
context_profile = minimal | balanced | max
orchestration_mode = single | critic | committee | adaptive
```

Milestone 10 requirements:

- defaults are explicit and deterministic;
- unknown values fail validation;
- deterministic route remains keyless and external-provider-free;
- live route supports only adapters proven in the current repository;
- unsupported requested providers return a typed safe `provider_unavailable` result or validation error;
- no silent cross-provider fallback;
- response echoes requested and served profiles safely;
- no arbitrary caller-supplied model ID is accepted.

Recommended current defaults:

```text
provider_preference=deepseek
effort_profile=balanced
context_profile=balanced
orchestration_mode=critic
```

`critic` here refers to the existing Energy Aware critic pipeline, not a new parallel multi-agent implementation.

## 3. Current implementation boundary

### Implement in Milestone 10 when minimal

- provider-neutral selector enums/contracts;
- requested/served profile fields in V2 projection;
- strict defaults;
- deterministic route reports `deterministic_local` as served provider;
- live route reports the actual existing provider/model metrics;
- typed unsupported-provider behavior;
- no-double-execution and no-silent-fallback tests;
- documentation links to the canonical provider/context spec.

### Defer to later provider/context milestones

- Kimi K3 credentialed adapter;
- GPT-5.6 Responses API adapter;
- provider `/models` discovery cache;
- provider price synchronization;
- automatic cross-provider escalation;
- UI selectors;
- persistent context snapshots;
- summary compaction execution;
- committee/adaptive multi-agent execution;
- provider quality benchmarks.

Milestone 10 must remain the graph-backed API slice.

## 4. Model catalog facts and caveats

As of 2026-07-19:

- DeepSeek V4 Flash/Pro model names and thinking support are documented and may continue through the existing seam.
- Kimi K3 is publicly released, but committed code must not guess the API model ID or reasoning parameters. Enable only after account-visible API verification.
- OpenAI GPT-5.6 uses Luna, Terra and Sol capability tiers. The product should map the common fast/balanced/max selector through a provider adapter rather than expose obsolete generic labels as model IDs.

These facts are temporal. Provider metadata must be revalidated before credentialed implementation.

## 5. Response additions

When added without destabilizing the base contract, V2 may expose:

```text
requested_provider
requested_effort
requested_context_profile
requested_orchestration_mode
served_provider
served_model
served_effort
fallback_used
routing_reason
```

Rules:

- values come from validated request/configuration and authoritative provider metrics;
- no credentials, raw prompts or provider transcripts;
- deterministic responses explicitly state no external provider call;
- unsupported live provider selection does not silently become DeepSeek.

## 6. Context profile in Milestone 10

The selector may be accepted and echoed for forward compatibility, but no claim of context compaction is allowed unless compaction actually runs and is tested.

Until the dedicated context milestone:

- `balanced` is the only active behavior;
- `minimal` and `max` may either fail as unsupported or map through an explicitly documented compatibility behavior;
- the API must disclose that no durable compaction snapshot was created;
- no fake `context_snapshot_id` is returned.

Failing explicitly is preferred over pretending profiles have distinct behavior.

## 7. Multi-agent mode in Milestone 10

The existing graph already contains multiple decision roles/nodes. That does not prove committee-style multi-agent execution.

During Milestone 10:

- `critic` may identify the existing generator-plus-critic flow;
- `single`, `committee` and `adaptive` must not claim distinct runtime behavior unless implemented and tested;
- unsupported modes fail clearly;
- do not add parallel agents, quorum or provider comparison to this slice.

## 8. Required tests

Add only tests justified by fields implemented in Milestone 10:

1. defaults resolve to DeepSeek/balanced/balanced/critic for live contract metadata;
2. deterministic route remains external-provider-free regardless of live preference;
3. arbitrary model IDs are rejected or impossible by schema;
4. unsupported Kimi/OpenAI selection fails safely until adapters exist;
5. no silent fallback changes the selected provider;
6. requested and served values are distinguishable;
7. existing graph call count remains exactly one;
8. legacy routes remain unchanged.

## 9. Claude Code instruction

Claude must read:

```text
../../CLAUDE.md
../../docs/ENERGY_AWARE_PORTFOLIO_README.md
../ENERGY_AWARE_PROVIDER_ROUTING_README.md
energy_aware_chat_provider_context_spec.md
energy_aware_chat_milestone_10_graph_api_spec.md
```

Claude must preserve Milestone 10 scope. Provider-neutral contracts are required; full provider/context/multi-agent integrations are deferred.

## 10. Acceptance statement

Milestone 10 remains complete only when the graph-backed API requirements pass. This addendum permits a future-compatible selection contract; it does not add new provider-quality claims or move later roadmap work into the milestone.
