# CLAUDE.md — Estimador CAG Agent Instructions

## 1. Working mode

Classify before implementation:

- Session 13 Plus continuation belongs to the existing `gg-session-13/plus` incubator branch.
- Session 14 coursework must start on a new `session-14/pre-work` branch created from the current verified Session 13 Plus head.
- EACODE, EACHAT, and EACORE are separate product/work streams. Do not modify their branches during coursework unless explicitly instructed.

Repository state, tests, CI, checkpoints, and current code are stronger sources of truth than this file.

## 2. Current verified Session 13 Plus checkpoint

At this instruction update, the verified V3 foundation checkpoint was:

```text
0700b9bf396ed8a59c1e9a250f7a5ffad65c4278
```

Re-resolve the current remote SHA before acting.

Implemented V3 foundations:

- strict C0–C5 complexity and per-stage routing contracts;
- deterministic route-plan IDs and bounded provider metadata;
- strict constraint-energy, candidate, repair, ledger, and Energy Card contracts;
- deterministic tests and green remote CI.

Not yet claimed:

- semantic classifier in the graph;
- provider selector in the UI/API;
- operational Kimi K3 or GPT-5.6 routing;
- task-level multi-agent supervisor;
- context-compaction runtime;
- provider-quality superiority.

## 3. Mandatory-first rule

For coursework:

```text
perfect mandatory requirements
→ prove them
→ add measured, reversible improvements
```

Do not mix mandatory work with unrelated provider/UI/deployment work in one patch.

## 4. Provider policy

Read:

```text
docs/energy_aware_model_context_and_multiagent_policy.md
```

User-facing provider choices:

```text
Auto
DeepSeek
Kimi
OpenAI
```

Defaults:

```text
provider = DeepSeek
reasoning = medium
context_detail = medium
```

Common reasoning intent:

```text
minimal
medium
max
```

Never assume the same raw effort values exist across providers. Resolve through a versioned capability registry.

Current architecture recognizes:

- DeepSeek V4 Flash and V4 Pro;
- Kimi K3, K2.7 Code, and K2.6;
- GPT-5.6 Luna, Terra, and Sol.

Important Kimi K3 constraints:

- use `kimi-k3` only after capability/reachability validation;
- launch support is `max` effort; do not invent low/high support;
- do not switch into K3 mid-session without a clean checkpoint and normalized compacted handoff;
- use explicit behavioral boundaries and least privilege.

Do not label one provider universally best. Matched product evaluation is authoritative.

## 5. Context compaction

User-facing selector:

```text
Context detail: minimal | medium | max
```

A compacted context must retain:

- objective and working mode;
- hard constraints and authority;
- accepted/rejected decisions;
- evidence references;
- current candidate/state;
- unresolved issues;
- budgets;
- branch and exact SHA;
- last green tests/CI;
- next action;
- rollback and claim boundaries.

Summaries are derived projections, never authoritative records. Preserve checkpoints, evidence, immutable candidates, and decisions separately.

## 6. Multi-agent policy

A model supervisor is justified only when the next action is genuinely unknown at design time.

For Session 14:

- manually implement the supervisor with `StateGraph` and typed `Command`;
- do not use `create_supervisor` for the mandatory exercise;
- keep tool privileges static and server-owned;
- models may propose routes;
- deterministic Python guards validate routes, budgets, loops, evidence, and human-review requirements;
- use `interrupt()` with the existing persistent checkpointer;
- resume the same thread with revision-guarded human input.

Fixed workflows remain explicit graph edges.

## 7. TDD protocol

Every coherent slice follows:

```text
invariant
→ red test
→ expected failure
→ minimal implementation
→ focused tests
→ relevant integration
→ Ruff
→ Python compilation
→ full deterministic regression
→ diff check
→ secret scan
→ evidence
→ commit
→ push
→ remote CI
```

Do not proceed while the current slice is red. Do not create fake green by weakening tests, skipping paths, or mocking away the property being proved.

## 8. Codespaces and Zsh safety

The course environment uses GitHub Codespaces and Zsh.

- Use the editor or a reviewed patch for substantial source/Markdown changes.
- Never paste Python or Markdown source directly into Zsh.
- Never place Markdown fences inside shell heredocs.
- Avoid heredocs and base64 blobs for generated documents.
- Do not use Bash-only arrays, `readarray`, `mapfile`, or `${BASH_SOURCE[...]}`.
- Prefer `[[ ... ]]` for interactive conditions.
- Do not use `set -e` or `set -euo pipefail` interactively.
- Do not supply `exit` or terminal-closing commands.
- Verify tool availability; prefer portable `find` and `grep` when needed.
- Never use destructive Git reset/clean operations or force push.
- Never merge protected/frozen branches without explicit authorization.
- Never commit `.env`, API keys, provider transcripts, raw prompts, hidden reasoning, credentials, or DSNs.

## 9. Architecture authority

```text
model/actor proposes
Python validates
Critic identifies defects
Boss/policy decides
human authorizes protected decisions
LangGraph orchestrates and persists
```

The model never owns authoritative arithmetic, privilege changes, final acceptance, or protected execution.

## 10. Required handoff

At the end of every work session report:

- starting and ending branch/SHA;
- changed files and commits;
- commands and tests;
- local and remote CI evidence;
- database/provider/browser/trace evidence;
- limitations and claim boundary;
- exact next slice;
- rollback boundary;
- whether human action is required.

Do not merge or mark a draft PR ready without explicit authorization.
