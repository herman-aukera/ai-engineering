# AI Engineering Coursework and Energy-Aware Product Incubator

This repository contains the LIDR AI Engineering coursework and the incubator branches for the Energy-Aware portfolio.

## Current verified work

```text
Active Plus branch: gg-session-13/plus
Verified V3 foundation checkpoint before this documentation update:
0700b9bf396ed8a59c1e9a250f7a5ffad65c4278
Draft PR: #10
Frozen teacher-facing Session 13 base: session-13/pre-work
```

The mandatory Session 13 implementation remains frozen. The Plus branch evolves it additively and is not merged automatically.

## Session 13 mandatory graph

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

The teacher-facing implementation includes typed state, reducers, FastAPI integration, PostgreSQL checkpointing, stable thread identity, Logfire spans, deterministic CI adapters, and complete execution evidence.

## Session 13 Plus

The Plus branch adds or preserves:

- one reviewed LangGraph source of truth;
- structure and final human gates;
- revision protection;
- parallel retrieval with sequential rollback;
- bounded retries, fallbacks, tools, cost, and latency;
- typed Critic and deterministic Boss policy;
- provider circuits;
- checkpoint history and scenarios;
- sanitized audit export;
- V1/V2 compatibility and rollout controls.

### V3 deterministic foundation

Implemented foundations:

- C0–C5 complexity and stage-specific model-route contracts;
- deterministic route-plan identity and bounded provider metadata;
- immutable estimation candidate references;
- constraint-energy snapshots;
- repair classification;
- replay-safe decision records;
- Estimate Energy Card projection.

Graph, API, and UI integration of those V3 foundations remains a later slice.

See:

- `estimador-cag/docs/session13_plus_v3_foundation.md`
- `estimador-cag/docs/energy_aware_model_context_and_multiagent_policy.md`
- `estimador-cag/CLAUDE.md`

## Session 14 direction

Session 14 must branch from the current verified Session 13 Plus state and implement:

- a manually constructed `StateGraph` supervisor;
- visible typed `Command` routing;
- least-privilege specialists;
- typed shared state and reducer behavior;
- persistent `interrupt()` human review;
- same-thread approve/adjust/reject resume;
- complete pause/resume trace.

The mandatory teacher contract is completed first. Provider selectors, context compaction, competition patterns, and broader portfolio integrations remain additive follow-up slices.

## Provider and context policy

The products use stable user-facing abstractions rather than hard-coding one provider’s API vocabulary.

Provider selector:

```text
Auto | DeepSeek | Kimi | OpenAI
```

Defaults:

```text
provider = DeepSeek
reasoning = medium
context detail = medium
```

Common reasoning selector:

```text
minimal | medium | max
```

Current capability families documented by the architecture:

- DeepSeek V4 Flash / V4 Pro;
- Kimi K3 / K2.7 Code / K2.6;
- GPT-5.6 Luna / Terra / Sol.

Runtime availability, exact model IDs, effort modes, and account access must be verified through a versioned capability registry. Vendor claims are not product calibration evidence.

## Energy-Aware product boundaries

### EACODE

A future local Energy-Aware coding control plane between coding agents and protected repository/tool execution. It evaluates proposals through evidence, critics, constraint energy, deterministic Boss decisions, bounded repair, human authorization, controlled execution, and re-evaluation.

### EACHAT

A future general-purpose Energy-Aware conversational product with candidate answers, grounding, critics, constraint energy, bounded repair, clarification/refusal/escalation, and an Energy Card.

### EACORE

A potential neutral documentation/contracts/evaluation layer. Shared runtime extraction is evidence-gated and must not be forced merely because products use similar record names.

## Context integrity

All products should expose:

```text
Context detail: minimal | medium | max
```

Compacted context preserves hard constraints, decisions, evidence references, current state, unresolved issues, budgets, branch/SHA, last green tests, next action, rollback, and claim boundaries. Summaries remain derived projections; checkpoints and immutable records remain authoritative.

## Validation policy

Normal CI is deterministic and keyless. Credentialed provider, browser, PostgreSQL, and hosted-observability proofs are separate, bounded, and sanitized.

Never commit `.env`, API keys, raw prompts, raw provider transcripts, hidden reasoning, credentials, or connection strings.

## Historical coursework

Earlier session branches and artifacts remain available for retrieval, CAG, memory, structured output, streaming, evaluation, and agentic-loop history. Historical results are preserved honestly and are not silently promoted to current production claims.
