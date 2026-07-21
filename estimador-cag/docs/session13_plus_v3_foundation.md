# Session 13 Plus V3 Foundation — Beyond-Teacher Implementation Status

**Branch:** `gg-session-13/plus`  
**Verified implementation checkpoint before documentation updates:** `0700b9bf396ed8a59c1e9a250f7a5ffad65c4278`  
**Status:** additive deterministic foundation implemented; graph/API/UI integration pending  
**Design target:** Estimation Control Room V3

## 1. Architectural decision

The teacher’s Session 13 live implementation is a strong pedagogical reference for:

- explicit `Command(goto=...)` handovers;
- semantic complexity classification and transcript reformulation;
- modules containing real tasks;
- one `Send` branch per approved task;
- keyed task reducers;
- two human interrupts;
- read-only reliability analysis;
- background `astream(..., stream_mode="updates")` execution;
- visible agent activity;
- pooled PostgreSQL checkpointing;
- FastAPI and HTTPX Logfire instrumentation.

Session 13 Plus already has stronger deterministic policy, bounded recovery, provider circuits, revision-guarded human review, scenario branching, audit export, rollout controls, and adverse-case evaluation.

The correct evolution is additive. V3 preserves the reviewed V2 product while introducing the teacher’s strongest runtime patterns behind new versioned contracts and rollback controls.

## 2. Implemented foundation

### 2.1 Checkpoint-safe routing contracts

Implemented in:

```text
app/schemas/v3_routing.py
```

Contracts:

- `ComplexitySignals`;
- `ComplexityAssessment`;
- `ModelRoute`;
- `ModelRoutingPlan`;
- C0–C5 complexity levels;
- deterministic, instant, and thinking modes;
- explicit reasoning effort;
- stage-specific routes;
- execution profiles;
- immutable strict Pydantic records;
- C5 human-review invariant;
- exact stage-coverage validation.

### 2.2 Deterministic complexity baseline

Implemented in:

```text
app/services/v3_complexity_router.py
```

The baseline calculates a 0–100 score from:

- scope;
- integrations;
- risk;
- ambiguity;
- evidence difficulty;
- input complexity.

Critical security/compliance ambiguity or complex data migration can force C5 independently of the simple score band. The result is versioned, checkpoint safe, and reproducible.

### 2.3 Deterministic per-stage route plan

The current policy creates distinct routes for:

```text
complexity
structure
recovery
reliability
proposal
```

Each route records:

- provider;
- model;
- deterministic/instant/thinking mode;
- reasoning effort;
- output limit;
- timeout;
- tool-call limit;
- cost limit;
- fallback route IDs;
- reason codes.

The model never selects or promotes its own tier. A stable plan ID is calculated from canonical policy inputs, excluding creation time.

Current route values are policy priors, not proof of provider superiority.

### 2.4 Constraint-energy and decision foundation

Implemented in:

```text
app/schemas/v3_energy.py
app/services/v3_estimation_energy.py
```

Contracts and utilities:

- evidence-integrity metadata;
- constraint observations;
- immutable candidate references;
- deterministic constraint-energy snapshots;
- candidate fingerprints;
- repair outcomes;
- replay-safe estimate decision records;
- Estimate Energy Card projection.

Invariants:

- hard blockers dominate soft penalties;
- required missing evidence is not acceptance;
- material conflict is not acceptance;
- repair is improved only when energy falls and blocking gaps are absent;
- identical replay is idempotent;
- conflicting identifier reuse fails closed.

### 2.5 Deterministic tests

Implemented in:

```text
tests/test_session13_plus_v3_routing.py
tests/test_session13_plus_v3_energy.py
```

The tests cover:

- low-cost routes for simple work;
- C5 human review;
- deterministic route-plan identity;
- checkpoint-safe JSON;
- dimension arithmetic;
- bounded quality-mode cost changes;
- stable candidate fingerprints;
- hard-constraint dominance;
- missing evidence;
- non-improving repair;
- idempotent decision replay;
- conflicting-ID rejection.

Remote CI was green at the verified implementation checkpoint.

## 3. Provider-neutral product requirement

Canonical provider/context policy:

```text
docs/energy_aware_model_context_and_multiagent_policy.md
```

### 3.1 User-facing provider selector

```text
Auto
DeepSeek
Kimi
OpenAI
```

Default:

```text
DeepSeek
```

`Auto` must select the least expensive currently verified route satisfying stage, complexity, risk, modality, context, tool, and quality requirements.

### 3.2 Common reasoning intent

```text
minimal
medium
max
```

This is a stable product abstraction. Provider adapters map it to verified supported capabilities. Unsupported combinations fail before execution.

### 3.3 DeepSeek

Initial family:

```text
deepseek-v4-flash
deepseek-v4-pro
```

Initial mapping:

| Product intent | Route prior |
|---|---|
| `minimal` | V4 Flash non-thinking |
| `medium` | V4 Flash `high` or V4 Pro `high`, selected by stage/complexity |
| `max` | V4 Pro `max` |

DeepSeek remains the default cost-aware provider until matched product evidence supports another policy.

### 3.4 Kimi K3 and Kimi family

Recognized architecture targets:

```text
kimi-k3
Kimi K2.7 Code
Kimi K2.6
```

Kimi K3 requirements:

- register the provider model only after reachability/capability validation;
- record 1M context and native multimodality;
- launch effort is `max`;
- do not claim low/high effort until discovery verifies availability;
- avoid switching to K3 in the middle of a session without a clean checkpoint and normalized compacted handoff;
- enforce explicit behavioral boundaries because the vendor reports excessive proactiveness.

Initial mapping:

| Product intent | Route prior |
|---|---|
| `minimal` | K2.6 instant or K2.7 Code for coding stages |
| `medium` | calibrated K2.6/K2.7 route |
| `max` | K3 `max` |

Kimi is a strong alternative/max-capability candidate. It is not documented as universally superior.

### 3.5 OpenAI GPT-5.6

Recognized capability tiers:

```text
Luna
Terra
Sol
```

Initial mapping:

| Product intent | Route prior |
|---|---|
| `minimal` | GPT-5.6 Luna |
| `medium` | GPT-5.6 Terra |
| `max` | GPT-5.6 Sol `max` |
| exceptional opt-in | Sol `ultra`/multi-agent only when account, API, policy, and budget support are verified |

OpenAI is the premium route. Do not invent account availability, raw effort values, or model IDs; resolve them through the model registry and capability probe.

## 4. Versioned model registry requirement

Each model record must include:

```text
provider
provider_model_id
display_name
capability_tier
context_window
max_output
modalities
tool_support
structured_output_support
reasoning_efforts
speed_class
cost_metadata_version
availability
verified_at
calibration_status
```

Lifecycle:

```text
documented
→ configured
→ reachable
→ contract_verified
→ benchmark_calibrated
→ enabled
```

Documentation alone does not make a route executable.

## 5. Context-detail and compaction requirement

User selector:

```text
Context detail: minimal | medium | max
```

- `minimal`: aggressive compaction;
- `medium`: balanced default;
- `max`: preserve the most verified detail.

Every compacted handoff preserves:

- identity and versions;
- working mode and objective;
- hard constraints and authority;
- accepted decisions;
- rejected alternatives;
- evidence references;
- current candidate/state;
- unresolved issues;
- budgets/provider route;
- branch and exact SHA;
- last green tests/CI;
- checkpoint/revision;
- next action;
- rollback and claim boundaries.

A compacted context is a derived projection, not source of truth. Checkpoints, immutable candidates, evidence references, and decision records remain authoritative.

Compaction should occur at measured token thresholds and safe stage/checkpoint/provider-switch boundaries. Reject stale or contradictory summaries.

## 6. Multi-agent relationship

Session 14 will introduce a manually constructed supervisor and least-privilege specialists on a separate branch.

The V3 provider/energy contracts may support that work, but fixed deterministic sequences must not be replaced by model routing merely to appear agentic.

Recommended supervisor authority:

```text
deterministic prerequisites and safety guards
→ optional typed route proposal
→ deterministic route/privilege/budget validation
→ Command
```

## 7. Why the foundation exceeds the teacher in design scope

| Capability | Teacher live reference | V3 foundation/requirement |
|---|---|---|
| Complexity | low/medium/high | C0–C5 plus deterministic dimensions |
| Routing | configured model/effort | separate stage routes, provider abstraction, budgets, stable IDs |
| Critical risk | high complexity | C5 forces human review by contract |
| Energy | implicit quality decisions | explicit hard/soft energy and repair improvement |
| Audit | graph trace | candidate/energy/decision references plus safe audit projection |
| Providers | one configured family | capability-discovered DeepSeek/Kimi/OpenAI policy |
| Context | graph state/history | explicit context-detail and compaction integrity policy |
| Calibration | configured mapping | versioned matched product benchmark requirement |

This is design/foundation superiority, not operational V3 superiority.

## 8. Implemented (post-S6, post-repair)

As of `d9f6674` (2026-07-20), the following are implemented and tested:

- ✅ semantic LLM classifier (provider-neutral contracts, deterministic fake, live adapter);
- ✅ graph-state integration (4 TypedDict fields, classifier node);
- ✅ classifier-to-structure `Command(update=..., goto=...)` handover;
- ✅ deterministic/semantic arbitration (C5 lock, low-confidence gate, disagreement guard);
- ✅ model registry (lifecycle validation, `ModelRegistry` service);
- ✅ provider selector (registry-backed route resolution, fail-closed);
- ✅ context compaction runtime (`minimal/medium/max`, source fingerprint, freshness);
- ✅ deterministic reformulator rollback (idempotent, preserves project context);
- ✅ capability probe (`probe_model_reachable`);
- ✅ live DeepSeek smoke tests (gated behind `stress_fake_provider`).

Still not implemented:

- provider selector in API/UI (Streamlit control room);
- operational Kimi K3 or GPT-5.6 calls;
- native module-to-task generation;
- task-level `Send`;
- task-level recovery;
- reliability analyst;
- task-hours editor;
- proposal node;
- background execution/SSE;
- pooled checkpointer migration;
- complete Logfire hierarchy;
- matched provider calibration.

No V1 or V2 behavior was replaced.

## 9. Next Session 13 Plus slice

The next coherent slice is the **Streamlit provider selector UI** — expose
`ProviderSelection` (provider, reasoning, context_detail) in the control room
and wire it through the reviewed graph runtime.

Remaining slices:
- operational Kimi K3 / GPT-5.6 routing (requires live API access);
- background execution / SSE;
- matched provider calibration (requires benchmark data).

## 10. Session 14 branch boundary

Session 14 coursework must branch from the current verified Plus state into:

```text
session-14/pre-work
```

Do not implement Session 14 supervisor/HITL work directly on `gg-session-13/plus`.

## 11. Acceptance gate before further V3 integration

- focused V3 tests pass;
- complete deterministic suite passes;
- Ruff and compilation pass;
- remote CI passes at current head;
- PR remains draft;
- no secrets/raw provider output are committed;
- V1/V2 rollback remains unchanged;
- docs and PR evidence match actual code;
- provider/runtime claims remain capability-gated.

## 12. Claim boundary

Supported wording:

> Session 13 Plus contains strict V3 complexity, model-route, constraint-energy, candidate, repair, ledger, and Energy Card foundations; a provider-neutral semantic classifier with typed `Command` handover, arbitration safety gates, and graph integration; a versioned model registry with lifecycle validation; a registry-backed provider selector; a deterministic context-compaction runtime with source fingerprinting and freshness detection; and a deterministic reformulator rollback.  The provider-neutral policy covers DeepSeek, Kimi K3, and GPT-5.6.

Blocked wording:

- V3 graph is operational;
- adaptive routing improves estimate quality;
- Kimi K3 is universally best;
- GPT-5.6 is always worth its cost;
- real provider fallback is proven;
- context compaction is lossless;
- provider selectors are exposed in the UI;
- streaming UI is implemented;
- V3 is production-ready;
- provider-quality superiority is proven.

## 13. Stabilization correction record

The final repair pass separates deterministic complexity evidence from arbitrated routing authority, removes the redundant static classifier edge, fixes the reviewed-service provider-selection signature, adds a safe allow-listed SSE activity projection, and moves live-provider tests behind an explicit marker/workflow. Reliability and proposal nodes are implemented; provider selection remains a routing preview until runtime adapters consume the selection per stage. Current proof is the exact stabilization-branch CI result, not earlier test-count claims.
