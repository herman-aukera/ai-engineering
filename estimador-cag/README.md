# Estimador CAG — Durable Energy-Aware Estimation

## Current Session 13 status

```text
Current incubator branch: gg-session-13/plus
Verified V3 foundation checkpoint before documentation updates:
0700b9bf396ed8a59c1e9a250f7a5ffad65c4278
Draft PR: #10
Frozen teacher-facing branch: session-13/pre-work
```

The mandatory Session 13 branch remains frozen. The Plus branch is additive, draft, and unmerged.

## Product objective

Transform project transcripts into evidence-backed software estimates while preserving typed contracts, deterministic arithmetic, durable LangGraph execution, human authority, replay safety, provider/tool budgets, Critic/Boss policy, and sanitized audit evidence.

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

## Public API integration

The mandatory graph remains exposed through the additive endpoint:

```text
POST /api/v1/estimate/graph
```

The legacy estimation route was not silently replaced. V2 lifecycle routes and the reviewed Control Room remain additive and independently documented.

## Session 13 Plus reviewed product

The Plus path adds:

- canonical V2 estimation lifecycle;
- editable structure and final-estimate gates;
- revision guards;
- parallel retrieval with sequential rollback;
- selective recovery;
- typed Critic findings;
- deterministic Boss routing;
- bounded retry/fallback/tool/cost/latency policy;
- provider circuits;
- checkpoint history and scenario comparison;
- sanitized audit export;
- legacy/graph rollout controls.

## V3 deterministic foundation

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

The foundation provides:

- C0–C5 complexity and deterministic dimensions;
- C5 mandatory human review;
- stage-specific provider/model/mode/effort/budget plans;
- stable route-plan identity;
- evidence-integrity metadata;
- immutable candidate references;
- deterministic constraint energy;
- candidate fingerprints;
- non-improving repair detection;
- replay-safe decision entries;
- Estimate Energy Card projection.

Operational graph integration, provider selectors, context compaction, task-level multi-agent execution, and matched provider calibration remain later slices.

## Provider and context policy

Canonical policy:

```text
docs/energy_aware_model_context_and_multiagent_policy.md
```

Provider selector:

```text
Auto | DeepSeek | Kimi | OpenAI
```

Defaults:

```text
provider = DeepSeek
reasoning = medium
context detail = medium
```

Common reasoning intent:

```text
minimal | medium | max
```

Initial capability families:

| Provider | Minimal | Medium | Max |
|---|---|---|---|
| DeepSeek | V4 Flash non-thinking | V4 Flash/Pro high by stage | V4 Pro max |
| Kimi | K2.6 instant or K2.7 Code | calibrated K2.6/K2.7 | K3 max |
| OpenAI | GPT-5.6 Luna | GPT-5.6 Terra | GPT-5.6 Sol max |

These are routing priors, not proof of universal superiority. Runtime adapters must verify model availability and supported effort values.

### Kimi K3 constraints

- use `kimi-k3` only after reachability validation;
- record 1M context and native multimodality;
- launch effort is `max`;
- do not assume low/high modes until capability discovery confirms them;
- avoid mid-session switching without a clean checkpoint and normalized handoff;
- enforce explicit behavioral boundaries and least privilege.

### GPT-5.6 constraints

Recognize Luna, Terra, and Sol as cost/capability tiers. Premium and exceptional routes require explicit budget and capability verification. Do not invent unsupported model identifiers or effort modes.

## Context compaction

User selector:

```text
Context detail: minimal | medium | max
```

Every compacted context preserves objective, working mode, hard constraints, authority, decisions, evidence references, current state, unresolved issues, provider/budgets, checkpoint/revision, branch/SHA, last green tests/CI, next action, rollback, and claim boundary.

A summary is a derived projection. Checkpoints, evidence, immutable candidates, and decisions remain authoritative.

## Session 14 continuation

Session 14 must start from the current verified Plus state on a separate branch:

```text
session-14/pre-work
```

Mandatory scope:

- supervisor constructed manually with `StateGraph` and typed `Command`;
- requirements extractor with no business tools;
- budget searcher with only `search_budgets`;
- estimate generator with only `calculate_estimate`;
- coherence validator with only `validate_estimate`;
- supervisor with no business tools;
- typed shared state and reducer;
- persistent `interrupt()` human review;
- `awaiting_human_review` response;
- approve/adjust/reject same-thread resume;
- complete pause/resume trace.

Provider selectors, context compaction, competition, and broader portfolio extensions follow only after the mandatory gate is green.

## Execution semantics

- New run starts a new thread.
- Incomplete run resumes the same thread.
- Completed duplicate returns stored terminal state.
- Replay requires explicit checkpoint identity.
- Recalculation uses a new thread.
- Human actions require revision checks.

## Persistence and observability

The reviewed graph uses PostgreSQL checkpoints. Real close/reopen evidence remains separate from the in-memory demo composition.

Telemetry may include safe identifiers, counts, route IDs, budgets, status, duration, tokens/cost, and state-delta keys.

Exclude transcript/attachment bodies, prompts, raw model responses, hidden reasoning, API keys, and DSNs.

## Local deterministic validation

From `estimador-cag`:

```zsh
uv run ruff check app scripts tests evals

find app scripts tests evals -name '*.py' -type f -print0 |
  xargs -0 uv run python -m py_compile

OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test \
  uv run pytest -q
```

Normal CI is deterministic and keyless. Provider, PostgreSQL, browser, and hosted-trace proofs are separate bounded evidence.

## Control Room and evaluation

```zsh
uv run streamlit run app/ui/review_control_room.py
uv run python -m evals.session13_plus_parallel_retrieval_benchmark
uv run python -m evals.session13_plus_evaluation_matrix
```

Keyless demo:

```zsh
uv run uvicorn scripts.session13_plus_demo_api:app --port 8001
ESTIMADOR_BACKEND_URL=http://localhost:8001 \
  uv run streamlit run app/ui/review_control_room.py
```

The in-memory demo does not substitute for PostgreSQL restart evidence.

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

- Never commit `.env`, API keys, credentials, raw prompts/provider output, hidden reasoning, or connection strings.
- Do not merge or rewrite frozen branches without authorization.
- Do not force push.
- Do not manufacture green by weakening tests.
- Keep substantial source/Markdown edits out of interactive Zsh; use the editor or reviewed patches.
- Never put Markdown fences inside shell heredocs.

## Historical Session 12 agentic work

Session 12 historical hand-written agent-loop documentation remains indexed in `docs/HISTORICAL_SESSIONS.md` and its original branch. It is not the current front door.
