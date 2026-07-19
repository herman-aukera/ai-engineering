# Estimador CAG — Durable Energy-Aware Estimation

## Current working state

```text
Current incubator branch: gg-session-13/plus
Verified V3 foundation checkpoint before this documentation update:
0700b9bf396ed8a59c1e9a250f7a5ffad65c4278
Draft PR: #10
Frozen teacher-facing branch: session-13/pre-work
```

The mandatory Session 13 branch remains frozen. The Plus branch is additive, draft, and unmerged.

## Product objective

Transform project transcripts into evidence-backed software estimates while preserving:

- typed contracts;
- deterministic arithmetic;
- durable LangGraph execution;
- human authority;
- replay safety;
- provider/tool budgets;
- explicit Critic/Boss policy;
- sanitized trace and audit evidence.

## Mandatory Session 13 graph

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

The mandatory path uses typed shared state, reducer-backed fields, PostgreSQL `AsyncPostgresSaver`, stable thread identity, FastAPI integration, deterministic fakes for CI, and sanitized Logfire spans.

## Session 13 Plus reviewed product

The Plus path adds:

- canonical V2 estimation lifecycle;
- editable structure and final-estimate gates;
- revision guards;
- component-level parallel retrieval with sequential rollback;
- selective recovery;
- typed Critic findings;
- deterministic Boss routing;
- bounded retry/fallback/tool/cost/latency policy;
- serializable provider circuits;
- checkpoint history;
- scenario branching and comparison;
- sanitized audit export;
- legacy/graph rollout controls.

## V3 foundation

Implemented:

```text
app/schemas/v3_routing.py
app/services/v3_complexity_router.py
app/schemas/v3_energy.py
app/services/v3_estimation_energy.py
tests/test_session13_plus_v3_routing.py
tests/test_session13_plus_v3_energy.py
docs/session13_plus_v3_foundation.md
```

The current V3 foundation provides:

- strict immutable C0–C5 complexity records;
- deterministic 0–100 dimensions;
- C5 mandatory human-review invariant;
- per-stage provider/model/mode/effort/budget plans;
- stable route-plan IDs;
- evidence-integrity metadata;
- immutable estimate candidate references;
- deterministic constraint-energy snapshots;
- candidate fingerprints;
- non-improving repair classification;
- replay-safe decision entries;
- Estimate Energy Card projection.

Not yet implemented in the operational graph:

- semantic complexity classifier;
- graph-state route-plan integration;
- typed classifier-to-structure `Command` handover;
- native module-to-task generation;
- task-level `Send` fan-out;
- task-level recovery;
- reliability analyst;
- final task-hours editor;
- background streaming/activity;
- pooled checkpointer migration;
- complete Logfire hierarchy;
- matched model calibration.

## Provider selector policy

Read the canonical policy:

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
context detail = medium
```

Common reasoning intent:

```text
minimal
medium
max
```

Initial provider families:

| Provider | Minimal | Medium | Max |
|---|---|---|---|
| DeepSeek | V4 Flash non-thinking | V4 Flash/Pro high by stage | V4 Pro max |
| Kimi | K2.6 instant or K2.7 Code | calibrated K2.6/K2.7 | K3 max |
| OpenAI | GPT-5.6 Luna | GPT-5.6 Terra | GPT-5.6 Sol max |

The table is a routing policy prior, not proof of universal model superiority. Runtime adapters must verify availability and supported effort values.

### Kimi K3

Architecture requirements:

- model identifier `kimi-k3` after reachability verification;
- 1M context and native multimodality metadata;
- max effort at launch;
- do not assume low/high modes until capability discovery confirms them;
- avoid switching into K3 mid-session without a clean checkpoint and normalized compacted handoff;
- enforce explicit behavioral boundaries and least privilege.

### GPT-5.6

Architecture recognizes Luna, Terra, and Sol as cost/capability tiers. Premium or exceptional routes require explicit budget and capability verification. Do not invent API identifiers or unsupported effort modes.

## Context compaction

User selector:

```text
Context detail: minimal | medium | max
```

Every compacted context must preserve:

- objective and working mode;
- hard constraints and authority boundaries;
- accepted and rejected decisions;
- evidence references;
- current candidate/state;
- unresolved issues;
- budgets/provider route;
- current checkpoint/revision;
- branch and exact SHA;
- last green tests and CI;
- next action;
- rollback and claim boundaries.

A summary is not the source of truth. Checkpoints, evidence, immutable candidates, and decision records remain authoritative.

## Session 14 continuation

Session 14 should start from the current verified `gg-session-13/plus` head on a separate branch:

```text
session-14/pre-work
```

Mandatory Session 14 scope:

- supervisor constructed manually with `StateGraph` and typed `Command`;
- requirements extractor with no business tools;
- budget searcher with only `search_budgets`;
- estimate generator with only `calculate_estimate`;
- coherence validator with only `validate_estimate`;
- supervisor with no business tools;
- typed shared state and reducer;
- persistent low-confidence `interrupt()`;
- `awaiting_human_review` response;
- approve/adjust/reject resume from the same checkpoint/thread;
- complete pause/resume trace.

The mandatory task is completed before provider-selector, compaction, competition, or broader portfolio extensions.

## Public API and execution semantics

The mandatory graph endpoint remains additive. V2 lifecycle routes and the reviewed Control Room remain documented under `docs/session13_plus_v2_*`.

Execution semantics:

- new run starts a new thread;
- incomplete run resumes the same thread;
- completed duplicate returns stored terminal state;
- replay requires explicit checkpoint identity;
- recalculation uses a new thread;
- human actions require revision checks.

## Persistence

The reviewed graph uses PostgreSQL checkpoints. Application lifecycle owns saver initialization and shutdown. Real close/reopen evidence remains separate from in-memory demo composition.

## Observability

Telemetry must contain safe identifiers, counts, route IDs, budgets, status, duration, token/cost summaries, and state-delta keys.

Exclude:

- transcript;
- attachment bodies;
- prompts;
- raw model responses;
- hidden reasoning;
- API keys;
- database DSNs.

Domain events, logs, and telemetry spans are distinct records.

## Local deterministic validation

From `estimador-cag`:

```zsh
uv run ruff check app scripts tests evals

find app scripts tests evals -name '*.py' -type f -print0 |
  xargs -0 uv run python -m py_compile

OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test \
  uv run pytest -q
```

Normal CI is deterministic and keyless. Live provider, PostgreSQL, browser, and hosted-trace proofs are bounded, manual/integration evidence and must be sanitized.

## Control Room and evaluation

```zsh
uv run streamlit run app/ui/review_control_room.py
uv run python -m evals.session13_plus_parallel_retrieval_benchmark
uv run python -m evals.session13_plus_evaluation_matrix
```

Keyless demo composition:

```zsh
uv run uvicorn scripts.session13_plus_demo_api:app --port 8001
ESTIMADOR_BACKEND_URL=http://localhost:8001 \
  uv run streamlit run app/ui/review_control_room.py
```

The in-memory demo does not substitute for real PostgreSQL restart evidence.

## Documentation entry points

- `CLAUDE.md`
- `docs/energy_aware_model_context_and_multiagent_policy.md`
- `docs/session13_plus_v3_foundation.md`
- `docs/session13_plus_v2_architecture.md`
- `docs/session13_plus_v2_api.md`
- `docs/session13_plus_v2_product_journey.md`
- `docs/session13_plus_roadmap.md`
- `docs/session13_task13_compliance.md`
- `docs/HISTORICAL_SESSIONS.md`

## Security and Git safety

- Never commit `.env`, real API keys, copied credentials, raw provider output, prompts, hidden reasoning, or connection strings.
- Do not merge or rewrite frozen/course branches without explicit authorization.
- Do not force push.
- Do not manufacture green by weakening tests.
- Keep substantial source/Markdown edits out of interactive Zsh; use the editor or reviewed patches.
- Never put Markdown fences inside shell heredocs.
