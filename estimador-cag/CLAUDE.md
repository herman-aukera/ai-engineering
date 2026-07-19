# EACODE Claude Code Project Memory

Claude Code loads this file as project memory when started from `estimador-cag/` or a descendant.

## Mandatory imports

Read and follow:

- @docs/eacode_phase3c_claude_deepseek_handoff.md
- @docs/eacode_handoff_status.md
- @docs/eacode_threat_model.md
- @docs/energy_aware_product_family_provider_and_context_strategy.md
- @.energy/specs/0007-controlled-execution-evidence/requirements.md
- @.energy/specs/0008-execution-authorization/requirements.md
- @.energy/specs/0010-provider-routing-context-compaction/requirements.md
- @.energy/specs/0010-provider-routing-context-compaction/design.md
- @.energy/specs/0010-provider-routing-context-compaction/acceptance.md

Use current repository state, tests, command output, and CI as stronger evidence than documentation.

## Current implementation priority

The active delegated implementation slice remains:

```text
Spec 0009 — disabled-by-default sandboxed tool adapter
```

Spec 0010 is architecture guidance and a future implementation packet. Do not mix live provider routing, context-compaction runtime, or multi-agent execution into Spec 0009.

## Product family

- EACODE supervises coding agents, repositories, commands, evidence, repair, and authorization.
- EACHAT supervises general-purpose conversational answers with chat-specific critics and memory.
- LIDR tasks must perfect mandatory requirements first; extras must be isolated and evidenced.
- EACORE is optional shared documentation/contracts until two products prove stable semantic overlap.

## Provider policy

Provider-neutral public profiles:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Current policy intent:

- DeepSeek is the default cost-sensitive provider.
- Kimi is the user-preferred frontier/open-model provider; Kimi K3 is the max path.
- OpenAI GPT-5.6 is an explicit budget-gated premium escalation.

Do not call Kimi K3 objectively superior without project benchmark evidence.

Do not invent unsupported capability symmetry:

- DeepSeek effective thinking effort is high/max.
- Kimi K3 launches at max effort; lower effort availability must be discovered.
- GPT-5.6 Luna/Terra/Sol support none/low/medium/high/xhigh/max through the API.

## Context policy

Every future long-running workflow must preserve:

```text
immutable raw events
+ typed canonical state
+ versioned hierarchical summaries
+ recent working window
+ evidence rehydration
```

Never replace raw evidence with a summary. Never persist secrets or hidden chain of thought. Preserve hard constraints, decisions, evidence references, conflicts, open questions, next actions, hashes, and rollback/rehydration references.

## Multi-agent policy

Use bounded multi-agent execution only for independent critics, alternative proposals, benchmark comparisons, or parallel evidence collection.

Required:

- typed shared state;
- independent ownership;
- deterministic aggregation;
- disagreement records;
- cost, time, tool, and concurrency budgets;
- no concurrent edits to one worktree;
- no self-approval;
- deterministic boss owns final disposition.

## Git and terminal rules

- Do not modify `EACODE` directly; use the designated worktree branch.
- Do not merge, force-push, reset, clean, switch, or delete branches without explicit user authorization.
- Do not auto-commit or auto-push.
- Do not use `set -e` or `set -euo pipefail` in user-pasteable terminal blocks.
- Never place Markdown fences inside shell heredocs.
- Never print or persist API key values.
- Deterministic CI uses fake providers and fake tools only.

## Response footer

End implementation responses with:

```text
Decider verdict:
Evidence used:
Current branch and SHA:
Execution mode proven:
Energy delta summary:
Checkpoint state:
Next exact command or slice:
```
