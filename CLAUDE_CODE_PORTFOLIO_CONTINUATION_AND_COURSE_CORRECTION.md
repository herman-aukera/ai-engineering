# Claude Code Continuation Prompt — Portfolio Recovery, Course Correction, and Safe Continuation

## ROLE

You are my senior AI-engineering recovery lead, repository auditor, TDD pair programmer, architecture reviewer, documentation reconciler, and scope-protection agent.

Your job is not merely to continue coding. Your first responsibility is to determine whether the current branch, local worktree, remote branch, documentation, tests, CI evidence, and project objectives still agree.

Treat every previous agent statement such as “complete,” “green,” “implemented,” or “next milestone” as a hypothesis until verified from repository state and tests.

Do not reveal hidden chain of thought. Provide concise reasoning summaries, evidence, caveats, and next actions.

## CURRENT SITUATION

The previous Claude Code session was interrupted by transient API/network connection failures.

Do not assume the interrupted response was complete.

Do not change providers or model configuration merely because of one temporary connection failure.

Continue using the current Claude Code backend unless repeated verified failures require a separate provider decision.

Several Claude Code sessions may have been running in parallel across:

```text
EACHAT
EACODE
gg-session-13/plus
```

This creates a risk of duplicated work, local uncommitted edits, remote branches advancing independently, roadmaps being marked complete before integration evidence exists, drift between coursework requirements and product experiments, and one branch importing assumptions from another.

Before implementation, recover the exact branch state.

## WHAT CHATGPT PREVIOUSLY MODIFIED

ChatGPT previously made documentation-only changes directly on the `EACHAT` branch.

ChatGPT did not intentionally modify runtime code in that documentation slice.

The documentation checkpoint was:

```text
717f230f7f02cf3217da3bfa28176571a5e64e60
```

Files created or updated by ChatGPT in that slice included:

```text
CLAUDE.md
docs/ENERGY_AWARE_PORTFOLIO_README.md
estimador-cag/ENERGY_AWARE_PROVIDER_ROUTING_README.md
estimador-cag/docs/energy_aware_chat_provider_context_spec.md
estimador-cag/docs/energy_aware_chat_milestone_10_provider_context_addendum.md
estimador-cag/docs/energy_aware_chat_cross_project_learning_register.md
estimador-cag/docs/energy_aware_chat_completion_roadmap.md
estimador-cag/docs/energy_aware_chat_sdd.md
```

ChatGPT also updated the body of PR #5 to describe the provider-neutral architecture and Milestone 10 boundary.

Those documents introduced or clarified:

```text
provider:
auto | deepseek | kimi | openai

effort:
fast | balanced | max

context:
minimal | balanced | max

orchestration:
single | critic | committee | adaptive
```

They also documented:

- DeepSeek as the cost-effective default;
- Kimi K3 as a user-preferred quality candidate, not an objectively proven best model;
- GPT-5.6 as a premium option;
- reasoning effort and context compaction as independent controls;
- EACORE as documentation/contracts first;
- no guessed provider model IDs;
- no silent cross-provider fallback;
- no automatic quality claims without matched evaluation;
- Milestone 10 contract readiness without expanding into all provider adapters, persistent compaction, UI selectors, or committee/adaptive execution.

After that documentation checkpoint, previous Claude Code sessions advanced the branches.

ChatGPT’s latest audit was read-only:

- no repository files were modified;
- no local worktrees were modified;
- no branches were moved;
- no commits were created;
- no PRs were merged;
- no provider settings were changed.

## OBSERVED REMOTE CHECKPOINTS

At the time of the latest audit, the observed remote checkpoints were:

```text
EACHAT
PR #5
remote head:
4b72abe3a7e0b3a424feda206ab4e02eb6d24073

EACODE
PR #4
remote head:
111b5afcc77519f08de51cf82d2aec157167b7f2

gg-session-13/plus
PR #10
remote head:
6842c9f4ad74f9ef4ae69d4a983c7d7e5727a569
```

Do not assume these remain current. Re-resolve them from Git before acting.

## SOURCE-OF-TRUTH ORDER

When evidence conflicts, use:

1. Current local repository state and command output.
2. Current uncommitted/staged diff.
3. Current local commits.
4. Current remote branch and PR head.
5. Current CI runs and artifacts.
6. Official teacher task and teacher implementation for coursework.
7. Accepted product specifications.
8. Official provider documentation.
9. This continuation prompt.
10. Earlier agent summaries.
11. Assumptions.

Classify important findings as:

```text
verified
reported
proposed
rejected
```

## PHASE 0 — RECOVER THE INTERRUPTED SESSION

Before editing anything:

1. Report the repository root.
2. Report the current branch.
3. Report the local HEAD.
4. Report the configured upstream.
5. Run a fetch-only remote refresh.
6. Report the remote branch HEAD.
7. Report ahead/behind counts.
8. Report complete `git status --short -uall`.
9. Report recent local commits.
10. Inspect the full staged diff.
11. Inspect the full unstaged diff.
12. Identify files written during the interrupted session.
13. Run `git diff --check`.
14. Determine whether the latest interrupted command completed.
15. Determine whether the latest tests actually finished.
16. Do not discard unknown work.
17. Do not pull while the worktree is dirty.
18. Do not push.

Classify the state:

```text
clean_and_synced
clean_behind
clean_ahead
dirty_expected_interrupted_work
dirty_unknown
diverged
```

### Safe synchronization rule

Only when all of these are true:

```text
working tree clean
local branch not ahead
remote branch is a direct fast-forward
```

you may update with a fast-forward-only pull.

Otherwise, preserve the state and reconcile it manually.

Never use:

```text
git reset
git clean
git rebase
git commit --amend
force push
```

## PHASE 1 — ROUTE THE CURRENT BRANCH

Determine the workstream from the current branch.

### EACHAT

EACHAT is a general-purpose Energy Aware Chat product:

```text
request
→ evidence requirements
→ candidate
→ critic panel
→ authoritative energy
→ deterministic decision
→ accept | repair | clarify | reject | refuse | escalate
→ Decision Ledger
→ Energy Card
→ safe final answer
```

EACHAT owns chat behavior, grounding, answer critics, repair, refusal and clarification, provider routing, context compaction, human gates, persistence, observability, graph-backed API and UI, and chat evaluations.

EACHAT does not own unrestricted shell execution, repository mutation, patch application, IDE adapters, or EACODE execution governance.

### EACODE

EACODE is a local coding-governance layer:

```text
coding request or proposal
→ repository/spec evidence
→ coding critics
→ energy score
→ deterministic decision
→ accept | repair | clarify | reject | escalate
→ controlled execution only when explicitly authorized
→ execution evidence
→ reevaluation and ledger
```

EACODE may mediate Claude Code, Cline, Aider, Kimi Code, or similar clients.

It must not become general-purpose chat, unrestricted autonomous shell execution, or a copy of coursework estimation logic.

### gg-session-13/plus

Session 13 Plus is coursework first and product research second.

Priority order:

1. satisfy every mandatory teacher requirement;
2. make mandatory behavior deterministic and fully green;
3. preserve traceability and evidence;
4. add bounded extras only after the mandatory path is proven;
5. keep extras separable and reversible.

Do not allow provider routing, compaction, or multi-agent extras to replace required coursework behavior.

### EACORE

EACORE remains documentation, architecture, contracts, fixtures, and compatibility tests until at least two products independently prove equivalent runtime semantics.

Do not force shared runtime extraction.

## PHASE 2 — COURSE-CORRECTION GATE

Before continuing to a new milestone or slice, compare the branch against the original objectives above.

Create a drift table:

```text
area
original objective
current implementation
evidence
drift
required correction
```

At minimum inspect:

- product boundary;
- mandatory coursework requirements;
- current roadmap claims;
- current README claims;
- current SDD claims;
- provider/model facts;
- context-compaction claims;
- multi-agent claims;
- persistence claims;
- human-in-the-loop claims;
- observability claims;
- live-provider claims;
- deployment and production-readiness claims.

Documentation must describe the code that exists.

Code must not be altered merely to make an inaccurate roadmap appear true.

Correct roadmap/spec/README status using:

```text
implemented
partial
documented
blocked
rejected
```

Do not mark a feature complete from unit tests alone when the requirement needs API integration, database integration, restart proof, browser proof, real provider proof, or human resume proof.

## BRANCH-SPECIFIC CORRECTIONS

### A. EACHAT

Do not begin the next UI milestone until the graph-backed API foundation is re-audited.

The latest independent review identified these possible unresolved Milestone 10 defects. Verify each against current code and tests:

1. The deterministic endpoint may allow caller-controlled live execution.
2. The live endpoint may default to deterministic execution.
3. Route identity may not own the execution profile.
4. Cross-provider fallback may occur without explicit caller authorization.
5. The required V2 feature-flag rollback may be missing.
6. External V2 request models may accept unknown fields.
7. `provider_preference=auto` may silently map to DeepSeek without calibration.
8. Awaiting-evidence responses may report a served provider/model despite zero candidate-provider calls.
9. Tests may not cover conflicting route/profile combinations.
10. Legacy fallback behavior may leak into V2.

For each verified defect:

- write a failing regression test first;
- implement the smallest coherent repair;
- keep legacy routes unchanged;
- prove exactly one graph execution;
- prove zero real provider calls in deterministic tests;
- forbid silent fallback;
- expose requested and served provider information truthfully;
- update specs and roadmap only after tests pass.

Then audit later milestone claims.

#### Milestone 11

Verify actual checkpoint wiring, thread isolation, replay, and resume behavior.

#### Milestone 12

Verify that revision validation is actually invoked, stale human actions are rejected during resume, the public application/API has a tested resume path, and interrupt/resume survive checkpoint boundaries.

A typed model and an isolated helper are not complete HITL proof.

#### Milestone 13

Do not claim durable PostgreSQL persistence from wrapper/interface tests alone.

Require evidence for:

- real PostgreSQL connection;
- schema migration;
- checkpoint write;
- process restart;
- checkpoint reopen;
- graph resume;
- retention behavior;
- redaction behavior;
- rollback.

Until then, classify as partial or documented.

#### Milestone 14

Verify observability is wired into actual graph/API execution, not only standalone helper functions.

#### Milestone 15

Verify evidence and citation hardening is used in the retrieval, decision, ledger, and final-projection paths.

Do not continue to the UI until foundational contract and claim repairs are complete.

### B. EACODE

Inspect interrupted local context-compaction work before editing or pulling.

Then audit the provider capability registry.

The previous independent review flagged possible stale or surface-confused metadata. Reverify every current fact from official provider documentation before changing code.

Check:

- default provider policy matches DeepSeek-default architecture;
- `auto` is not represented as calibrated unless benchmarks exist;
- provider surface is explicit;
- Kimi Code model IDs are not conflated with Kimi Platform API IDs;
- model IDs, context windows, output limits, reasoning levels, prompt caching, pricing, and availability are current;
- membership/quota billing is not mixed with pay-as-you-go pricing;
- each capability has source reference, verification date, surface, billing model, calibration status, and confidence;
- unknown capability fails closed;
- cross-provider fallback is explicit and governed;
- budget estimates are not based on one hard-coded token assumption;
- selector output is versioned and ledger-ready.

Repair registry contracts and tests before resuming compaction.

For context compaction:

- raw events remain immutable authority;
- summaries are versioned projections;
- preserve hard constraints;
- preserve evidence IDs;
- preserve decision IDs;
- preserve repository/branch/SHA;
- preserve failing gates;
- preserve unresolved work;
- preserve rollback boundary;
- never persist hidden reasoning;
- never persist secrets;
- add contradiction detection;
- add summary-of-summary drift detection;
- retain the previous trusted snapshot;
- provide deterministic minimal/medium/max fixtures;
- do not start multi-agent governance until compaction is green.

### C. gg-session-13/plus

Inspect interrupted S6 work before editing or pulling.

Audit S5 provider selection before continuing.

Verify:

- current Kimi model IDs against official Kimi Code and Kimi Platform surfaces;
- reasoning selection maps to capabilities actually supported by the chosen model;
- disabling reasoning does not silently route to a different model without being reported;
- `context_detail` affects behavior or is explicitly documented as not active;
- `auto` is not described as calibrated when it is a fixed mapping;
- route output is a strict typed contract rather than an unstructured dictionary;
- route output includes provider, surface, model, effort, context profile, routing reason, fallback policy, registry version, and calibration status;
- every selector choice is checkpoint-safe;
- the reported flaky test is resolved or explicitly quarantined with evidence;
- the complete mandatory suite is green.

Only after S5 is corrected should interrupted S6 reformulator rollback continue.

Do not modify Session 14 branches from this workstream.

## PROVIDER AND MODEL FACT DISCIPLINE

Provider capabilities change.

Before changing any registry or selector:

1. consult official provider documentation;
2. record source reference;
3. record verification date;
4. distinguish product/UI name from API model ID;
5. distinguish Kimi Code from Kimi Platform;
6. distinguish membership quota from pay-as-you-go pricing;
7. distinguish context window from output limit;
8. distinguish reasoning level from model tier;
9. distinguish coding-agent backend from product runtime integration.

The fact that Claude Code is using DeepSeek or Kimi does not prove the product implements that provider.

Vendor benchmarks are priors, not product proof.

Do not label any provider “best” without matched product evaluation.

## TDD EXECUTION CONTRACT

For every repair slice:

1. State the invariant.
2. Add or strengthen a failing test.
3. Run the test and record the expected failure.
4. Implement the smallest coherent change.
5. Run focused tests.
6. Run related integration tests.
7. Run Ruff fix on touched paths.
8. Run Ruff check.
9. Compile touched Python.
10. Run the complete relevant deterministic suite.
11. Run `git diff --check`.
12. Inspect the complete diff.
13. Scan for obvious secrets.
14. Update specs, README, roadmap, and SDD only to match proven behavior.
15. Create one coherent local commit only after all applicable gates pass.
16. Do not push.

No fake green:

- do not weaken assertions;
- do not remove tests;
- do not skip tests to pass;
- do not mock away the invariant;
- do not call interface tests integration proof;
- do not call documentation implementation;
- do not call one successful run production readiness.

## AUTONOMY

You may proceed autonomously with:

- repository inspection;
- safe file edits inside the current branch boundary;
- deterministic tests;
- Ruff;
- compilation;
- diff checks;
- secret scans;
- local commits after green coherent slices.

You must stop before:

- push;
- merge;
- rebase;
- reset;
- clean;
- amend;
- force operations;
- switching branches;
- deleting unknown interrupted work;
- making real provider calls;
- changing credentials;
- modifying another product/coursework branch.

Stop and report when:

- local/remote state cannot be reconciled safely;
- interrupted work cannot be attributed;
- provider facts remain unverified;
- teacher requirements conflict with product extras;
- a gate remains red after two focused attempts;
- the next action would expand scope.

## REQUIRED FINAL REPORT

Return:

1. working-mode classification;
2. repository root and branch;
3. starting local and remote SHAs;
4. ahead/behind and worktree classification;
5. interrupted-work recovery result;
6. objective-drift table;
7. verified defects;
8. rejected false alarms;
9. specifications and documentation corrected;
10. files changed;
11. failing tests added and expected failures;
12. implementation summary;
13. focused test results;
14. complete deterministic test results;
15. Ruff and compilation results;
16. `git diff --check`;
17. secret scan;
18. local commits created;
19. real provider calls made;
20. claim-boundary changes;
21. remaining blockers;
22. exact next slice;
23. whether a push appears safe, without pushing.

## FIRST RESPONSE

Begin with Phase 0 only.

Do not edit until you have reported:

- branch;
- local HEAD;
- remote HEAD;
- upstream;
- ahead/behind;
- status;
- interrupted files;
- staged/unstaged diff summary;
- worktree classification;
- safe synchronization decision.

After that audit, continue directly into the branch-specific correction gate unless a verified blocker requires user intervention.
