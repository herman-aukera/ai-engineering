# Session 13 Plus V3 Foundation — Beyond-Teacher Implementation Status

**Branch:** `gg-session-13/plus`  
**Status:** additive foundation implemented; graph/API/UI integration pending  
**Design target:** Estimation Control Room V3

## 1. Decision

The teacher's Session 13 live implementation is a strong pedagogical reference for:

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

Session 13 Plus already has stronger deterministic policy, bounded recovery, provider circuits,
revision-guarded human review, scenario branching, audit export, rollout controls and adverse-case
evaluation. The correct evolution is therefore additive. V3 preserves the reviewed V2 product while
introducing the teacher's strongest runtime patterns behind new versioned contracts and rollout
controls.

## 2. Implemented in this foundation slice

### 2.1 Checkpoint-safe V3 routing contracts

Implemented in:

```text
app/schemas/v3_routing.py
```

Contracts:

- `ComplexitySignals`;
- `ComplexityAssessment`;
- `ModelRoute`;
- `ModelRoutingPlan`;
- C0-C5 complexity levels;
- deterministic, instant and thinking modes;
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

The baseline calculates a 0-100 score from explicit dimensions:

- scope;
- integrations;
- risk;
- ambiguity;
- evidence difficulty;
- input complexity.

Critical security/compliance ambiguity or complex data migration can force C5 regardless of the
simple score band. The result is versioned, checkpoint-safe and reproducible.

### 2.3 Deterministic per-stage routing policy

The policy creates distinct routes for:

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
- output-token limit;
- timeout;
- tool-call limit;
- cost limit;
- fallback route IDs;
- reason codes.

The model never selects or promotes its own tier. A stable plan ID is calculated from canonical
policy inputs, excluding creation time, so the same normalized request and profile produce the same
routing identity across replay.

### 2.4 Energy-aware cost behavior

The routing profile changes bounded cost without changing the authoritative project complexity.
`cost_first`, `balanced`, `quality_first` and `human_controlled` remain explicit policy choices.

### 2.5 Deterministic tests

Implemented in:

```text
tests/test_session13_plus_v3_routing.py
```

The focused test set proves:

- simple work uses low-cost stage-specific routes;
- critical work becomes C5 and requires human review;
- route-plan IDs are deterministic;
- routing plans serialize to checkpoint-safe JSON;
- invalid C5 records fail closed;
- dimension totals reconcile to the authoritative score;
- quality mode increases a bounded budget without mutating complexity.

## 3. Why this is beyond the teacher reference

| Capability | Teacher live | V3 foundation |
|---|---|---|
| Complexity scale | low / medium / high | C0-C5 plus numeric score |
| Complexity inputs | semantic model result | deterministic dimensions plus future semantic arbitration |
| Routing | complexity mapped mainly to reasoning effort | separate route for every LLM stage |
| Provider choice | static configured model | explicit DeepSeek/Kimi route and fallback plan |
| Cost policy | runtime configuration | checkpointed per-stage cost ceilings |
| Replay | graph checkpoint | stable route-plan identity across replay |
| Critical risk | high complexity | C5 forces human review by contract |
| Calibration | configured mapping | versioned calibration dataset reference |
| Model authority | model classifies complexity | deterministic policy owns routing |

The current routes remain policy priors, not evidence of universal model superiority. They must be
replaced or confirmed by the planned matched domain benchmark.

## 4. Deliberately not implemented yet

This slice does not claim:

- an LLM semantic classifier;
- automatic extraction of deterministic signals from transcripts;
- graph-state integration;
- `Command` handover from classifier to structure actor;
- native module-to-task generation;
- task-level `Send` fan-out;
- task-level recovery;
- reliability analyst;
- task-hours UI editor;
- proposal node;
- background API execution;
- SSE activity feed;
- pooled checkpointer migration;
- complete Logfire hierarchy;
- model-quality calibration.

No V1 or V2 behavior was replaced.

## 5. Next implementation slice

The next coherent slice is **semantic classifier and graph integration**:

1. add a provider-neutral semantic-classifier port and deterministic fake;
2. produce a typed semantic assessment and normalized brief;
3. arbitrate deterministic and semantic disagreement;
4. checkpoint the final complexity assessment and route plan;
5. add a typed `Command(update=..., goto=...)` handover;
6. preserve the current deterministic reformulator as rollback;
7. prove replay and route-plan stability;
8. add live DeepSeek smoke outside deterministic CI.

This slice touches graph state, graph topology, provider adapters, compatibility paths and multiple
integration tests. It is the appropriate boundary for a repository-aware coding agent such as
Claude Code using DeepSeek, under the continuation prompt and safety rules.

## 6. Acceptance gate before graph integration

- focused V3 tests pass;
- complete deterministic suite passes;
- Ruff and Python compilation pass;
- remote CI passes at the new head;
- PR remains draft;
- no secrets or raw provider output are committed;
- current V1/V2 rollback remains unchanged;
- this document and the PR evidence are updated with the actual CI run.

## 7. Claim boundary

Supported wording:

> Session 13 Plus now contains strict V3 complexity and model-routing contracts plus a deterministic,
> checkpoint-safe C0-C5 routing baseline with per-stage DeepSeek/Kimi plans and bounded budgets.

Blocked wording:

- V3 graph is operational;
- adaptive routing has improved estimate quality;
- DeepSeek or Kimi is universally superior;
- real provider fallback is proven;
- streaming UI is implemented;
- V3 is production-ready.
