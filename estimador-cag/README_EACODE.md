# Energy Aware Code (EACODE)

Status: living product incubator inside the LIDR AI Engineering repository  
Canonical branch: `EACODE`  
PR: #4, open draft, not a routine merge target

## Product

EACODE is a provider-neutral supervision layer for coding agents and tools.

```text
specification + policy + candidate + evidence
    -> critics
    -> constraint-energy score
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded action or human gate
    -> normalized evidence and immutable ledger
```

The intended consumers include Claude Code, Cline, Aider, OpenCode, IDE adapters, and local automation. Models and tools may propose work; they do not approve themselves.

## Current proven boundary

Implemented and remotely CI validated:

- typed Energy policies, candidates, evidence, decisions, and ledgers;
- deterministic critics, scoring, and disposition;
- evidence integrity, hashing, recovery, manifests, and retention;
- persistent LangGraph judge with SQLite restart/resume;
- typed human clarification and escalation;
- controlled command planning with root/path/symlink checks;
- dry-run and fake execution evidence;
- revision-guarded one-time authorization with replay protection;
- deterministic keyless CI.

Not yet proven:

- safe real process execution;
- live provider routing;
- autonomous repair quality;
- multi-agent quality improvement;
- context-compaction fidelity;
- product UI or production readiness.

## Current implementation slice

```text
Spec 0009 — disabled-by-default sandboxed tool adapter
```

The complete Claude Code handoff is:

```text
docs/eacode_phase3c_claude_deepseek_handoff.md
```

Claude Code automatically loads:

```text
CLAUDE.md
```

## Provider strategy

The future common selector is:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Policy intent:

| Role | Provider/model path |
|---|---|
| Default cost-sensitive path | DeepSeek V4 Flash/Pro |
| User-preferred frontier/open path | Kimi, with Kimi K3 as max |
| Explicit premium escalation | OpenAI GPT-5.6 Luna/Terra/Sol |

Selectors must resolve through a capability registry. Unsupported combinations must be disabled or rejected rather than silently coerced.

Canonical architecture:

```text
docs/energy_aware_product_family_provider_and_context_strategy.md
.energy/specs/0010-provider-routing-context-compaction/
```

## Product family

- **EACODE:** coding/repository/tool supervision.
- **EACHAT:** general conversational answer supervision and repair.
- **LIDR task branches:** exact mandatory coursework plus isolated, evidenced extras.
- **EACORE:** optional shared documentation/contracts after two-product proof.

Session 13 Plus is a major source of supervisor/boss, interrupt, retry, trace, and multi-agent orchestration patterns. Estimation-specific domain logic remains task-specific.

## Context compaction

Every long-running workflow must separate:

```text
immutable raw events and artifacts
-> typed canonical state
-> versioned hierarchical summaries
-> bounded recent working window
-> evidence rehydration
```

User context profiles:

- `minimal`: active objective, constraints, state, blocker, next action;
- `medium`: minimal plus decisions, evidence digest, pivots, and a larger recent window;
- `max`: medium plus hierarchical history and broader evidence rehydration within budget.

Raw evidence is never replaced by a summary. Secrets and hidden chain of thought are never persisted.

## Multi-agent policy

Useful for:

- independent parallel critics;
- alternative repair proposals;
- provider comparisons;
- benchmark evaluators;
- security, cost, retrieval, and correctness specialists.

Required controls:

- bounded fan-out;
- typed shared state;
- deterministic aggregation;
- disagreement records;
- cost/time/tool budgets;
- no shared mutable worktree;
- no self-approval;
- deterministic boss owns final disposition.

## Reviewer entry points

```text
docs/eacode_handoff_status.md
docs/eacode_product_completion_plan.md
docs/eacode_threat_model.md
docs/eacode_phase3c_claude_deepseek_handoff.md
docs/energy_aware_product_family_provider_and_context_strategy.md
.energy/specs/0010-provider-routing-context-compaction/
```

## Safety boundary

- no automatic commit or push;
- no force-push, reset, clean, merge, or branch deletion;
- no real provider calls in deterministic CI;
- no real tool execution unless explicitly enabled and authorized;
- no secret values in repository, logs, summaries, or evidence;
- no unsupported completion or benchmark claims.
