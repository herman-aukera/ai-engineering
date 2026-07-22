# AI Engineering Coursework and Energy-Aware Product Incubators

This repository contains LIDR AI Engineering coursework and the Energy-Aware product incubators derived from it.

## Current product branch

```text
EACODE
```

`EACODE` is a long-lived product incubator. It is not a routine coursework merge into `main`.

Authoritative product checkpoint:

```text
estimador-cag/docs/eacode_release_checkpoint_2026-07-22.md
```

## Energy Aware Code ⚡

EACODE is a provider-neutral control plane between coding agents, language models, repositories, and tools.

```text
SDD specification + policy + candidate + evidence
    -> independent critics
    -> constraint-energy evaluation
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded authorized action
    -> normalized evidence
    -> reevaluation and decision ledger
```

Models and agentic tools propose. Deterministic Python owns hard constraints, budgets, repository verification, authorization, evidence sufficiency, and final disposition.

## Implemented deterministic alpha

- Kiro-like SDD packets: requirements, design, tasks, policy, acceptance, decisions, and evidence;
- deterministic Energy-Aware critics, scorer, and boss;
- integrity-protected evidence and decision ledgers;
- persistent LangGraph judge and human gates;
- controlled planning and fake/dry-run evidence;
- typed live plan and intent;
- complete repository snapshot authorization;
- one-time integrity-protected SQLite authority;
- disabled-by-default secure process lifecycle and normalized evidence;
- verified provider selection for DeepSeek, Kimi, and OpenAI;
- hardened opt-in provider adapters;
- deterministic context-compaction acceptance and rehydration;
- fail-closed multi-agent budgets and disagreements;
- FastAPI EACODE status/capability/selection routes and same-origin UI;
- matched deterministic governance contract benchmark.

Detailed product README:

```text
estimador-cag/README_EACODE.md
```

Agent project memory:

```text
estimador-cag/CLAUDE.md
```

## Provider request surface

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

- DeepSeek is the default cost-sensitive route.
- Kimi is the user-preferred frontier/open route.
- OpenAI GPT-5.6 is an explicit budget-gated premium route.
- Unsupported, stale, unavailable, or unentitled combinations fail closed.
- Planned routes are never reported as models actually served.

## EACODE API

```text
GET  /eacode/status
GET  /eacode/capabilities
POST /eacode/select
GET  /eacode/ui
```

These routes are deterministic and do not make live provider calls.

## Product family

| Product or track | Responsibility |
|---|---|
| EACODE | Coding-agent, repository, tool, evidence, repair, and authorization supervision |
| EACHAT | Conversational generation, grounding, memory, criticism, and repair |
| LIDR tasks | Exact mandatory coursework plus isolated evidenced extras |
| EACORE | Optional common contracts after equivalent semantics are independently proven in two products |

## Context policy

```text
immutable raw events and artifacts
-> typed canonical state
-> versioned summaries
-> bounded recent working window
-> evidence rehydration
```

Summaries never replace source evidence. Secrets and hidden chain of thought are never persisted.

## Multi-agent policy

Required:

- independent ownership;
- bounded fan-out;
- deterministic aggregation;
- disagreement records;
- cost, latency, tool, agent-count, and concurrency budgets;
- no concurrent edits to one working tree;
- no majority override of hard constraints;
- no self-approval;
- deterministic boss owns final disposition.

## Claim boundary

The deterministic alpha does not prove:

- production readiness;
- arbitrary untrusted-code sandboxing;
- VM/container/kernel isolation;
- complete Windows cleanup without manual host evidence;
- current success for every live provider without secret-backed smoke runs;
- provider or multi-agent superiority without matched live evaluations;
- EACORE extraction readiness.

Deterministic CI remains provider-free and real-process-free. Live provider, process, and browser evidence are explicit manual gates.
