# EACODE Handoff Status

Date: 2026-07-17  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`  
PR: #4, open draft, do not merge as routine coursework

## Current maturity

- Phase 0: audit and product completion plan — complete.
- Phase 1: versioned trust, hashing, recovery, retention, manifests — complete.
- Phase 2: persistent deterministic LangGraph judge, SQLite restart, human clarification/escalation — complete.
- Phase 3A: controlled execution planning plus dry-run/fake evidence — complete pending final documentation CI.
- Real execution — not implemented.
- Provider actors — not implemented.

## Slice completed

Spec 0007 — Controlled Execution Evidence.

Implemented:

- strict command proposal, policy, plan, fake result, and evidence contracts;
- deterministic executable and argument policy;
- root, working-directory, path traversal, and symlink escape checks;
- timeout, output, and environment-name budgets;
- deterministic plan hashing;
- secret redaction and output truncation;
- fake tool port and adapter;
- dry-run and fake evidence with `execution_performed=false`;
- conversion to the existing `EvidenceRecord`;
- controlled-execution preview CLI;
- optional judge-graph preview, evidence append, and deterministic reevaluation;
- cross-project learning register;
- active threat model;
- Spec 0007 requirements, design, tasks, acceptance, policy, fixtures, evidence, and decision records.

## Validation evidence

Remote CI run `29608664559` validated head `d70c88b19b586003a381521fa6778a8844f6a3f0` and passed:

- Ruff;
- Python compilation;
- Energy Core boundary check;
- full test suite, including Spec 0007 contract, CLI, security, and graph tests;
- every existing smoke script;
- canonical Energy Core full gate;
- root compatibility smoke;
- repository cleanliness.

Later documentation/evidence commits require their own final CI before the current branch head is called green.

## Claim boundary

Allowed:

- EACODE can deterministically plan, deny, or human-gate structured command proposals.
- EACODE can produce bounded dry-run and fake execution evidence.
- EACODE can attach that evidence to the persistent judge and reevaluate through the existing Python decider.
- The controlled-execution foundation is remotely CI validated.

Not allowed:

- safe real shell execution;
- production sandboxing;
- provider integration;
- autonomous repair quality;
- benchmark superiority;
- production readiness.

## Exact next slice

Spec 0008 — Revision-Guarded Human Execution Authorization.

Required contracts:

- `ExecutionAuthorization`;
- trusted actor identity field;
- exact plan hash;
- expected and accepted revision;
- bounded command scope;
- expiry;
- one-time nonce;
- reason;
- rollback acknowledgement;
- consumed state;
- authorization verifier;
- append-only authorization audit record.

Required failure tests:

- wrong plan hash;
- stale expected revision;
- expired authorization;
- replayed nonce;
- conflicting nonce reuse;
- untrusted actor;
- broader command scope than plan;
- missing rollback acknowledgement;
- restart and resume with consumed authorization;
- any execution attempt without authorization.

Do not add real subprocess execution in Spec 0008.

## Delegation boundary

After Spec 0008 is green, delegate the real sandboxed tool adapter to Claude Code using DeepSeek. That work requires a local repository, OS/process inspection, repeated test execution, manual tool smoke, and controlled environment validation that the GitHub file connector cannot safely perform.

The delegated adapter must preserve the current `ToolPort`, never use `shell=True`, build a minimal environment, revalidate root/symlink boundaries immediately before start, enforce timeout and process-tree cleanup, stream bounded redacted output, produce rollback evidence, and remain disabled by default.

## Resume commands

```text
git fetch origin
git switch EACODE
git pull --ff-only
git status --short -uall
git log --oneline --decorate -20
```

Then run the repository-native deterministic full gate before starting Spec 0008.
