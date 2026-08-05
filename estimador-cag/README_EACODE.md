# Energy Aware Code (EACODE) ⚡

Canonical status: deterministic alpha control plane  
Current stacked candidate: tenant-scoped simulated beta hardening  
Canonical branch: `EACODE`  
Hardening specification: `.energy/specs/0012-production-hardening/`

## What EACODE is

EACODE is a provider-neutral supervision layer between coding agents, language models, repositories, and tools.

```text
SDD specification + policy + candidate + evidence
    -> independent critics
    -> constraint-energy evaluation
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> bounded authorization and action
    -> normalized evidence, reevaluation, and ledger
```

Models and agentic tools may propose work. They do not approve themselves. Deterministic Python owns hard constraints, budgets, repository verification, authority, evidence sufficiency, and final disposition.

## Current beta journey

```text
signed tenant session
-> provider-neutral CodingProposal
-> concrete deterministic hard gates
-> independent semantic jury
-> deterministic governor
-> bounded repair and effective proposal revision
-> durable inert record
-> signed operator/admin authorization
-> exact-scope short-lived receipt
-> atomic one-time execution reservation
-> simulated bounded execution
-> effective-proposal reevaluation
-> durable timeline and rollback evidence
```

### API

```text
GET  /health
GET  /eacode/status
GET  /eacode/capabilities
POST /eacode/select
GET  /eacode/ui
POST /eacode/demo
POST /eacode/demo/{proposal_id}/authorize
POST /eacode/demo/{proposal_id}/execute
GET  /eacode/demo/{proposal_id}
```

Proposal preparation and inspection require a signed backend session. Viewer, reviewer, operator, and admin roles may prepare and inspect inert proposals. Only operator and admin roles may authorize and execute. Non-admin access is scoped to the verified backend user ID; admin cross-tenant access is explicit.

The beta API does not accept client-controlled human authorization. Authorization is a server-issued capability bound to proposal ID, authenticated actor, exact effective command scope, and expiry. Receipt consumption and the proposal's single execution reservation occur atomically.

Execution in this beta remains simulated.

## Deterministic hard gates

The current beta checks:

- changed-file scope exists;
- paths are repository-relative and traversal-free;
- patch size remains within the beta budget;
- credential-shaped material and private keys are absent;
- deterministic test-weakening markers are absent;
- proposed commands use the bounded read/test allowlist;
- workflow, deployment, infrastructure, and migration surfaces trigger human review.

These gates are product policy evidence. They are not a proof that arbitrary code is safe.

## Durable evidence

`SQLiteBetaDemoStore` provides single-node beta durability with:

- WAL mode;
- tenant ownership;
- typed canonical JSON records;
- SHA-256 integrity digests;
- short-lived actor/scope-bound authorization receipts;
- nonce replay rejection;
- atomic receipt consumption;
- atomic single-execution reservation;
- application-restart persistence.

SQLite is not claimed as horizontally scaled or multi-region production storage.

## Benchmark

The versioned 12-case benchmark compares:

```text
unchecked_agent
hard_gates_only
single_semantic_judge
jury_action_governor
```

The final mode calculates decisions from proposal evidence. Expected labels are never used to generate actual decisions; a poisoned-label regression enforces that boundary.

This benchmark proves only the encoded deterministic cases. It does not prove real-world coding-agent superiority.

## Product image

The EACODE product image uses the dedicated `app.eacode_main` composition root rather than the estimator/coursework application.

The minimal runtime:

- exposes only EACODE product routes;
- runs as UID 10001;
- persists state under `/data`;
- uses a pinned small FastAPI/Pydantic/Uvicorn dependency set;
- excludes tests, `pytest`, Torch, Jupyter, Streamlit, sentence-transformers, estimator routes, and database/cache clients not used by this beta path;
- uses an explicit non-wildcard CORS allowlist.

The repository separately retains a full development runtime and a test image for coursework compatibility.

## Container and supply-chain gates

The EACODE image workflow must:

1. validate the `demo` Compose profile;
2. start the minimal product container and wait for health;
3. prove UID 10001 and excluded heavy/test dependencies;
4. reject unsigned proposal preparation;
5. create a signed tenant proposal, restart the API, and retrieve the durable record;
6. fail on fixed high or critical OS/library vulnerabilities;
7. export an SPDX SBOM artifact;
8. prove the separate UID 10002 read-only, capability-dropped runner boundary;
9. publish only from a push to canonical `EACODE`;
10. publish only an immutable commit-SHA tag with BuildKit SBOM and provenance.

Pull requests and non-canonical branches do not publish images.

## Existing deeper execution contracts

Earlier specifications already provide:

- typed controlled execution plans;
- exact repository snapshot binding;
- authoritative one-time live authorization storage;
- `shell=False` argument-list execution;
- process-group/session handling, cancellation, timeout, and cleanup verification;
- bounded and redacted output;
- normalized evidence for reevaluation;
- a permanently disabled legacy real adapter.

Those contracts remain separate from the beta HTTP journey. The beta API does not silently enable real process execution.

## Provider-neutral model routing

Public request contract:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Implemented:

- source-versioned capability facts;
- distinct DeepSeek API, Kimi Platform, Kimi Code, and OpenAI surfaces;
- entitlement, freshness, context, effort, output, cache, and pricing metadata;
- token-aware budget checks;
- requested, planned, configured, and served facts kept distinct;
- keyless and network-free deterministic CI.

A route-selection response is a plan. It is not evidence that a provider or model actually served a request.

## SDD layer

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

The SDD packets live under `.energy/specs/`. This is Kiro-like methodology, not a claim of IDE feature parity.

## Product family

- **EACODE:** coding, repository, tool, evidence, repair, and authorization supervision.
- **EACHAT:** conversational answers, grounding, memory, critics, and repair.
- **LIDR branches:** exact coursework plus isolated evidenced extras.
- **EACORE:** extraction candidate only after equivalent stable semantics are proven independently in EACODE and EACHAT.

## Claim boundary

Do not claim:

- production readiness;
- real coding-agent integration from the beta API;
- real process execution from the beta API;
- arbitrary-code sandboxing;
- horizontal or multi-region durability;
- live Google or Apple login;
- successful live provider routing without current secret-backed evidence;
- exact served effort when the provider does not echo it;
- provider or multi-agent superiority without matched live benchmarks;
- external deployment;
- EACORE extraction readiness.

## Reviewer entry points

```text
CLAUDE.md
.energy/specs/0011-demo-ready-beta/
.energy/specs/0012-production-hardening/
docs/eacode_release_checkpoint_2026-07-22.md
docs/eacode_handoff_status.md
docs/eacode_threat_model.md
```
