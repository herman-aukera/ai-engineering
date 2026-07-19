# AI Engineering Coursework and Energy-Aware Product Incubators

This repository contains the LIDR AI Engineering coursework and the living Energy-Aware product incubators derived from it.

## Current branch

```text
EACODE
```

`EACODE` is a long-lived incubator branch. PR #4 remains open and draft and must not be merged into `main` as a routine coursework delivery.

## Current product

### Energy Aware Code

EACODE supervises coding agents, repositories, proposed commands, repair loops, evidence, and human authorization.

```text
specification + policy + candidate + evidence
    -> critics
    -> constraint-energy score
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded action or human gate
    -> normalized evidence and decision ledger
```

Current product README:

```text
estimador-cag/README_EACODE.md
```

Claude Code project memory:

```text
estimador-cag/CLAUDE.md
```

Current delegated implementation charter:

```text
estimador-cag/docs/eacode_phase3c_claude_deepseek_handoff.md
```

## Energy-Aware product family

| Product or track | Responsibility |
|---|---|
| EACODE | Coding-agent, repository, command, evidence, repair, and authorization supervision |
| EACHAT | General conversational answer generation, criticism, repair, grounding, memory, and chat UI |
| LIDR tasks and Session 13 Plus | Exact mandatory coursework, with isolated and evidenced extra work |
| EACORE | Optional common architecture/contracts after stable overlap is proven in at least two products |

Session 13 Plus supplies useful supervisor/boss, interrupt, retry, trace, and multi-agent patterns. Domain-specific estimation logic remains in the task branch.

Canonical cross-product architecture:

```text
estimador-cag/docs/energy_aware_product_family_provider_and_context_strategy.md
```

## Provider and model strategy

The planned provider-neutral selector is:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Policy intent:

- **DeepSeek** is the default cost-sensitive provider using V4 Flash or V4 Pro.
- **Kimi** is the user-preferred frontier/open-model provider, with Kimi K3 as the max path.
- **OpenAI GPT-5.6** is an explicit budget-gated premium escalation using Luna, Terra, or Sol.

Provider capabilities differ. The selector must use a versioned capability registry and must reject unsupported combinations rather than inventing uniform reasoning levels.

The SDD packet is:

```text
estimador-cag/.energy/specs/0010-provider-routing-context-compaction/
```

## Context compaction

Long-running product and coursework workflows must preserve:

```text
immutable raw events and artifacts
-> typed canonical state
-> versioned hierarchical summaries
-> bounded recent working window
-> evidence rehydration
```

User profiles:

- `minimal`: objective, hard constraints, current state, blocker, next action;
- `medium`: minimal plus decision/evidence digest and relevant pivots;
- `max`: medium plus hierarchical history and broader evidence retrieval within budget.

Summaries never replace source-of-truth evidence. Secrets and hidden chain of thought are never persisted.

## Multi-agent policy

Multi-agent orchestration is encouraged when independent parallel critics, alternative proposals, retrieval, security review, provider comparison, or benchmark evaluation create measurable value.

Required controls:

- typed shared state;
- bounded fan-out;
- deterministic aggregation;
- disagreement records;
- cost, time, tool, and concurrency budgets;
- no concurrent edits to one working tree;
- no agent self-approval;
- deterministic boss owns final disposition.

## Current implementation boundary

Implemented and remotely CI validated on EACODE:

- deterministic Energy-Aware judge;
- evidence integrity, hashing, recovery, manifests, and retention;
- persistent LangGraph orchestration with SQLite restart/resume;
- human clarification and escalation;
- controlled command planning and fake/dry-run evidence;
- one-time execution authorization and replay protection.

Next implementation slice:

```text
Spec 0009 — disabled-by-default sandboxed tool adapter
```

Provider routing, context-compaction runtime, and multi-agent execution remain later slices and must not be mixed into Spec 0009.

## Repository map

```text
.
├── estimador-cag/
│   ├── CLAUDE.md
│   ├── README_EACODE.md
│   ├── .energy/specs/
│   ├── docs/
│   ├── energy_core/
│   ├── app/
│   ├── evals/
│   └── tests/
├── docs/
├── scripts/
├── docker-compose.yml
└── README.md
```

## Safety and evidence rules

- Mandatory coursework requirements come before optional extras.
- Extra work must be isolated, reversible, and evidence-backed.
- Deterministic CI uses fake providers and fake tools.
- Live provider and real tool validation are explicit manual smokes.
- No automatic commit, push, merge, reset, clean, or force-push.
- No secrets in repository files, logs, screenshots, summaries, or evidence.
- Do not claim runtime capability, safety, or benchmark superiority without matching evidence.
