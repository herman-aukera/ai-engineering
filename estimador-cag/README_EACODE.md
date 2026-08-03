# Energy Aware Code (EACODE) ⚡

Status: deterministic alpha control plane  
Canonical branch: `EACODE`  
Authoritative checkpoint: `docs/eacode_release_checkpoint_2026-07-22.md`

## Demo-ready beta work

Spec 0011 adds a provider-neutral proposal boundary, explicit deterministic hard gates,
typed independent semantic-judge results, jury disagreement, optional meta-judge evidence,
and a deterministic action governor. The keyless demo repairs one fixture proposal, records
human authorization for a protected simulated test action, captures sanitized evidence,
reevaluates, and exposes the full timeline and rollback boundary at `POST /eacode/demo`,
`GET /eacode/demo/{proposal_id}`, and `/eacode/ui`.

Local identity contracts keep users separate from linked provider identities and use signed,
expiring backend sessions. Google and Apple OIDC are configuration contracts only; live login
is not claimed. The versioned golden set compares unchecked, hard-gate-only, single-judge, and
jury-plus-governor modes across twelve deterministic cases.

Docker `dev`, `test`, and `demo` profiles and GHCR build assets are present. Compose configuration
is verified; container build/startup remains a separate gate where a Docker engine is available.

## Product

EACODE is a provider-neutral supervision layer between coding agents, language models, repositories, and tools.

```text
SDD specification + policy + candidate + evidence
    -> independent critics
    -> constraint-energy evaluation
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded authorization and action
    -> normalized evidence and append-only ledger
```

Models and agentic tools may propose work. They do not approve themselves. Deterministic Python owns hard constraints, budgets, repository verification, authority, evidence sufficiency, and final disposition.

## Kiro-like SDD layer

Every governed feature is represented through versioned:

```text
requirements
-> design
-> tasks
-> energy policy
-> red-green implementation
-> acceptance
-> decisions
-> evidence
```

The SDD packets live under `.energy/specs/`. This is Kiro-like methodology, not a claim of IDE feature parity with Kiro.

## Current implemented boundary

### Trust and deterministic judgment

- typed Energy policies, candidates, findings, evidence, decisions, and ledgers;
- deterministic critics, scoring, and boss disposition;
- hashing, integrity, recovery, retention, and manifests;
- persistent LangGraph judge with SQLite restart/resume;
- typed clarification, human gate, and escalation;
- no self-approval.

### Governed command execution

- controlled planning with executable, argument, repository, path, symlink, timeout, output, and environment policy;
- fake and dry-run evidence remain non-executing;
- explicit typed live plan and intent;
- exact repository snapshot binding: HEAD, tree, staged diff, unstaged diff, and untracked-state digest;
- one-time SQLite authorization with integrity, replay protection, atomic reservation, and restart persistence;
- pre-start actor, authority, snapshot, path, executable, argument, and environment verification;
- `shell=False`, argument lists, process-group/session isolation, cancellation polling, timeout, and verified cleanup;
- cross-chunk and final redaction, bounded output, accurate truncation, and normalized evidence;
- secure CLI requires typed live artifacts, authoritative receipt store, receipt ID, and `--live-tool`;
- legacy real adapter is permanently disabled;
- deterministic CI creates no real OS process.

A harmless host-level smoke and Windows cleanup demonstration remain manual evidence gates. EACODE does not claim VM/container isolation or safety for arbitrary untrusted code.

### Provider-neutral model routing

Public request contract:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Implemented:

- verified, source-versioned capability overlay;
- DeepSeek API, Kimi Platform, Kimi Code, and OpenAI API represented as distinct surfaces;
- entitlement, freshness, context, effort, output, cache, and pricing metadata;
- consistent per-1K price fields and token-aware budget checks;
- Kimi Code `k3`, `kimi-for-coding`, and entitlement-dependent high-speed route;
- provider-specific reasoning controls and corrected HTTP timeout units;
- requested, planned, configured, and served provider/model/effort remain distinct facts;
- served effort is not asserted unless the provider echoes evidence;
- deterministic CI remains keyless and network-free.

Live DeepSeek, Kimi, and OpenAI success requires separate opt-in secret-backed smoke evidence.

### Context compaction

- immutable raw source references and hashes;
- typed canonical state and versioned summaries;
- minimal, medium, and max profiles;
- branch/repository snapshot, policy, schema, source-hash, and age freshness checks;
- constraint, decision, evidence, conflict, question, and rehydration preservation;
- secret and hidden-reasoning exclusion;
- loss audit, contradiction detection, summary-decay detection, and fail-closed rehydration.

This proves deterministic compaction contracts, not LLM summary quality.

### Energy-Aware boss and critics

- typed proposer, critic, reviewer, and boss roles;
- independent task ownership;
- preserved disagreement records;
- per-agent and global cost, latency, tool-call, agent-count, and concurrency budgets;
- missing findings escalate;
- hard constraints cannot be outvoted;
- budget overruns escalate;
- deterministic boss owns the final disposition.

### Product API and UI

FastAPI exposes:

```text
GET  /eacode/status
GET  /eacode/capabilities
POST /eacode/select
GET  /eacode/ui
```

The selector UI and API explicitly separate requested, planned, and served state. Route selection does not call a provider and does not claim that a provider served the request.

### Deterministic governance benchmark

A matched synthetic contract benchmark compares a single unchecked proposal with the deterministic governed boss:

```text
single unchecked: 1/4 expected dispositions
governed boss:    4/4 expected dispositions
```

This is evidence for the encoded governance cases only. It is not evidence that multi-agent LLM execution improves real-world quality, cost, or latency.

## Product family

- **EACODE:** coding, repository, tool, evidence, repair, and authorization supervision.
- **EACHAT:** conversational answers, grounding, memory, critics, and repair.
- **LIDR branches:** exact coursework plus isolated evidenced extras.
- **EACORE:** extraction candidate only after equivalent stable semantics are proven independently in EACODE and EACHAT.

## Safety and claim boundary

Allowed claims are defined in `docs/eacode_release_checkpoint_2026-07-22.md`.

Do not claim:

- production readiness;
- arbitrary-code sandboxing;
- complete Windows host cleanup proof;
- successful live routing for all providers without current smoke evidence;
- exact served effort when the provider does not echo it;
- provider or multi-agent superiority without matched live benchmarks;
- EACORE extraction readiness.

## Reviewer entry points

```text
docs/eacode_release_checkpoint_2026-07-22.md
docs/eacode_handoff_status.md
docs/eacode_product_completion_plan.md
docs/eacode_threat_model.md
CLAUDE.md
.energy/specs/0009-sandboxed-tool-adapter/
.energy/specs/0010-provider-routing-context-compaction/
```
