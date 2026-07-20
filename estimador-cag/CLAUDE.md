# EACODE Claude Code Project Memory

Claude Code loads this file as project memory when started from `estimador-cag/` or a descendant.

## Mandatory imports

Read and follow:

- @docs/eacode_provider_execution_rescue_audit_2026-07-20.md
- @docs/eacode_phase3c_claude_deepseek_handoff.md
- @docs/eacode_handoff_status.md
- @docs/eacode_threat_model.md
- @docs/energy_aware_product_family_provider_and_context_strategy.md
- @.energy/specs/0007-controlled-execution-evidence/requirements.md
- @.energy/specs/0008-execution-authorization/requirements.md
- @.energy/specs/0009-sandboxed-tool-adapter/requirements.md
- @.energy/specs/0009-sandboxed-tool-adapter/acceptance.md
- @.energy/specs/0010-provider-routing-context-compaction/requirements.md
- @.energy/specs/0010-provider-routing-context-compaction/design.md
- @.energy/specs/0010-provider-routing-context-compaction/tasks.md
- @.energy/specs/0010-provider-routing-context-compaction/acceptance.md

Use current repository state, tests, command output, and CI as stronger evidence than documentation.

## Current recovery status

```text
Spec 0007 — deterministic controlled planning and fake/dry-run evidence: COMPLETE at L2
Spec 0008 — logical-revision authorization and persistent interrupt: COMPLETE at L2
Spec 0009 — sandboxed-tool implementation and deterministic tests: IMPLEMENTED at L2; SECURITY REPAIR REQUIRED
Spec 0010 — provider registry and deterministic selector: PARTIALLY IMPLEMENTED; CAPABILITY FACT REPAIR REQUIRED
Context compaction runtime: LOCAL INTERRUPTED WORK MAY EXIST; NOT REMOTELY PROVEN
Multi-agent runtime: NOT IMPLEMENTED IN EACODE
```

Do not repeat these unsupported claims:

- PR #12 was merged;
- Spec 0009 has complete live/manual evidence;
- real-process sandboxing is proven safe;
- exact Git-repository snapshot authorization exists;
- Spec 0010 runtime is complete;
- provider catalog values are current merely because tests pass;
- context compaction is complete;
- Kimi K3 is objectively superior.

PR #12 remains an open draft according to current GitHub metadata. Spec 0009 code is integrated into EACODE, but that is not equivalent to PR #12 being merged.

## Mandatory recovery order

```text
R0 stop or close all competing Claude/agent sessions
R1 inspect local EACODE status and preserve interrupted local files
R2 compare local HEAD and diff with origin/EACODE without reset/clean/restore
R3 repair provider capability facts, contracts, and tests from current official sources
R4 repair Spec 0009 live-intent, exact repository-snapshot, cleanup,
   cancellation, truncation, redaction, and receipt-provenance invariants through red tests
R5 run focused and full deterministic gates
R6 request explicit user approval before commit or push
R7 resume context-compaction contracts as a separate slice
R8 start a fresh provider session for Kimi K3 rather than switching inside a damaged session
```

Do not continue context-compaction or multi-agent implementation until R3 and R4 are green.

## Critical Spec 0009 invariants to repair

- A plan whose execution mode is `dry_run` or `fake` must never start a real process.
- Real execution needs an explicit typed live-execution intent and authority transition.
- Authorization must bind to an exact repository snapshot, not only an integer revision.
- The snapshot must cover HEAD, tree, staged diff, unstaged diff, and untracked state/digest.
- Process-tree cleanup must be verified, not assumed.
- Cancellation must be observed promptly while the process is running.
- Output truncation flags must be accurate.
- Redaction must be safe across chunk boundaries and rerun on assembled output.
- Receipt provenance or authoritative-store verification must prevent fabricated in-memory receipts.
- Cleanup uncertainty fails closed.

## Provider policy and current correction boundary

Public profiles remain:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Policy intent:

- DeepSeek remains the default cost-sensitive route.
- Kimi is the user-preferred frontier/open-model route.
- OpenAI GPT-5.6 is an explicit budget-gated premium escalation.

Current provider facts must be refreshed before acceptance:

- DeepSeek V4 Flash/Pro use current official 1M-context, output, cache, effort, and pricing data.
- Kimi general API `kimi-k3` and Kimi Code `k3` are distinct surfaces.
- Kimi Code currently exposes `k3`, `kimi-for-coding`, and `kimi-for-coding-highspeed` where entitled.
- K3 currently supports low, high, and max effort in Kimi Code; do not retain the older max-only assumption.
- GPT-5.6 Luna/Terra/Sol use current official context, output, effort, and pricing data.
- A deterministic planned route is not evidence of the exact provider/model actually served.

A fresh Kimi-backed Claude Code session may map the main model to K3 at max effort and the lower-cost subagent/Haiku role to `kimi-for-coding`. Do not claim `kimi-for-coding` has a provider-native low-effort control unless current capability discovery proves it.

## Product family

- EACODE supervises coding agents, repositories, commands, evidence, repair, and authorization.
- EACHAT supervises general-purpose conversational answers with chat-specific critics and memory.
- LIDR tasks perfect mandatory requirements first; extras remain isolated and evidenced.
- EACORE extraction remains gated by equivalent stable semantics in at least two products.

Do not import task-specific estimation semantics or EACHAT chat semantics into EACODE.

## Context policy

Every future long-running workflow preserves:

```text
immutable raw events
+ typed canonical state
+ versioned hierarchical summaries
+ recent working window
+ evidence rehydration
```

Never replace raw evidence with a summary. Never persist secrets or hidden chain of thought. Preserve hard constraints, decisions, evidence references, conflicts, open questions, next actions, hashes, repository revisions, and rollback/rehydration references.

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

- The user explicitly authorizes the current rescue/audit work on `EACODE`.
- Do not create another branch or worktree unless the user asks.
- Do not merge, force-push, reset, clean, restore, switch, rebase, or delete branches.
- Do not auto-commit or auto-push. Request explicit approval after green gates and diff review.
- Do not overwrite uncommitted interrupted work before inspecting it.
- Do not use `set -e` or `set -euo pipefail` in user-pasteable terminal blocks.
- Never place Markdown fences inside shell heredocs.
- Never print or persist API key values.
- Deterministic CI uses fake providers and fake tools only.
- Live provider and live-process checks are opt-in manual evidence.

## First response contract

Before editing implementation files, report:

1. current directory, branch, local HEAD, remote HEAD, and working-tree status;
2. all uncommitted files and which appear to come from the interrupted session;
3. drift against this recovery boundary;
4. provider-fact corrections required;
5. Spec 0009 red-test plan;
6. exact first recovery slice;
7. files expected to change;
8. rollback boundary;
9. whether any stop condition applies.

Then proceed with the smallest safe red/green repair slice unless a stop condition applies.

## Response footer

End implementation responses with:

```text
Decider verdict:
Evidence used:
Current branch and SHA:
Local diff state:
Execution mode proven:
Provider mode proven:
Energy delta summary:
Checkpoint state:
Next exact slice:
User approval required:
```
