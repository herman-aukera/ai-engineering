# EACODE Handoff Status

Date: 2026-07-22  
Repository: `herman-aukera/ai-engineering`  
Canonical branch: `EACODE`  
Repair integration: PR #15  
Authoritative checkpoint: `docs/eacode_release_checkpoint_2026-07-22.md`

## Working mode

EACODE deterministic-alpha integration and handoff.

## Completed deterministic architecture

### Trust foundation

- typed policies, candidates, evidence, findings, decisions, and ledgers;
- deterministic critics, scorer, boss, and dispositions;
- hashing, referential integrity, retention, manifests, and recovery;
- persistent LangGraph judge with SQLite restart/resume;
- clarification, human gate, and escalation.

### Specs 0007 and 0008

- bounded command proposals and deterministic risk policy;
- repository, path, symlink, executable, argument, timeout, output, and environment constraints;
- fake/dry-run evidence with `execution_performed=false`;
- trusted actors, plan-hash authority, expiry, nonce replay protection, rollback acknowledgement, and persistent interrupt.

### Spec 0009 repair

- explicit typed live plan and intent;
- fake/dry-run plans cannot launch real processes;
- full repository snapshot: HEAD, tree, staged diff, unstaged diff, and untracked-state digest;
- authoritative SQLite authorization store with integrity checks, restart persistence, atomic reservation, and one-time completion;
- fail-closed pre-start verification;
- `shell=False`, argument-list execution, minimal environment, process groups/sessions, prompt cancellation, timeout, and verified cleanup;
- bounded concurrent output capture, cross-chunk/final redaction, and accurate truncation;
- normalized execution evidence for critic/decider reevaluation;
- secure CLI with typed artifacts and explicit `--live-tool`;
- legacy real-process adapter permanently disabled;
- deterministic CI uses fake/injected processes only.

Manual host smoke remains required before claiming complete OS-level evidence.

### Spec 0010 repair

- source-versioned verified capability overlay;
- distinct DeepSeek API, Kimi Platform, Kimi Code, and OpenAI surfaces;
- corrected price units, endpoints, timeout conversion, and reasoning controls;
- requested/planned/served evidence separation;
- served effort is blank unless provider evidence confirms it;
- context-compaction freshness, loss, secret, hidden-reasoning, contradiction, decay, and rehydration gates;
- fail-closed deterministic boss with per-agent/global cost, latency, tool, agent-count, and concurrency budgets;
- FastAPI control-plane routes and same-origin selector UI;
- deterministic matched governance contract benchmark.

## Product routes

```text
GET  /eacode/status
GET  /eacode/capabilities
POST /eacode/select
GET  /eacode/ui
```

These routes plan and display governed selection. They do not make live provider calls.

## Benchmark boundary

The deterministic fixture benchmark reports:

```text
single unchecked: 1/4
governed boss:    4/4
```

This proves the encoded governance contracts only. It does not prove live LLM or multi-agent superiority.

## Allowed claims

- Kiro-like SDD packets exist and are enforced through tests and CI.
- A provider-neutral Energy-Aware boss/critic layer exists.
- DeepSeek, Kimi, and OpenAI have governed selection and opt-in adapter contracts.
- The local process boundary is explicit, one-time-authorized, disabled by default, and deterministically tested.
- Compaction has deterministic acceptance and rehydration gates.
- The API/UI control plane is HTTP-tested.

## Blocked claims

- production readiness;
- arbitrary untrusted-code sandboxing;
- VM/container/kernel isolation;
- complete Windows cleanup proof without manual host evidence;
- current live success for every provider without secret-backed smoke runs;
- exact served effort when not echoed;
- real-world provider or multi-agent superiority;
- EACORE extraction readiness.

## Remaining manual evidence

1. Harmless local live-tool command using the secure CLI.
2. Local timeout, cancellation, child-process, and cleanup demonstration on Windows.
3. Secret-free evidence inspection.
4. Live DeepSeek/Kimi/OpenAI smoke runs with valid secrets as available.
5. Browser smoke of `/eacode/ui`.

These gates do not belong in deterministic CI.

## Integration rule

PR #15 may merge into `EACODE` only after the complete normal CI is green, temporary diagnostics are absent, SDD/status documents agree, and PR metadata reflects this claim boundary. After merge, verify a fresh `EACODE` CI run.
