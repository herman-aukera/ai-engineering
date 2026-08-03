# AI Engineering Coursework

## Session 13 + 14 Plus consolidation candidate

The current additive consolidation candidate is:

```text
Branch: gg-session-14/plus-consolidated
Pull request: #21
Graph: session13_14_plus_unified_graph
Graph version: session13_14_plus.unified.v1
Status: audited, draft, open and unmerged
```

It semantically combines the completed Session 13 Plus reviewed/production architecture with the Session 14 Plus supervised, persistent-HITL, capability/context and Energy-aware architecture. It does not replace or rewrite either source branch.

Primary entrypoints:

- `estimador-cag/docs/session13_14_plus_unified_architecture.md`
- `estimador-cag/docs/session13_14_plus_unified_evidence.md`
- `estimador-cag/docs/session13_14_plus_unified_audit.md`
- `estimador-cag/docs/session13_14_plus_unified_final_handoff.md`

Claim boundary:

- PR #21 is not merged;
- supervised and reviewed rollback paths remain available;
- live-provider reachability is not inferred from deterministic CI;
- superiority, lossless context compaction and historical-checkpoint migration are not yet claimed.

## Repository scope

This repository contains the LIDR AI Engineering coursework.

## Current historical submission record

- Active project: `estimador-cag/`
- Historical branch: `gg-session-13/pre-work`
- Teacher-facing branch: `session-13/pre-work`
- Deliverable: **Session 13 — agent orchestration with LangGraph**

Teacher-facing branch:

https://github.com/herman-aukera/ai-engineering/tree/session-13/pre-work

## What Session 13 delivers

The Session 12 hand-written estimation loop has been re-expressed as an
explicit LangGraph workflow inside the AI service:

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

The mandatory pre-session implementation includes:

1. Typed shared graph state.
2. Accumulator reducers using `Annotated[..., operator.add]`.
3. Five sequential nodes that return partial state updates.
4. An additive graph endpoint at `POST /api/v1/estimate/graph`.
5. PostgreSQL persistence through `AsyncPostgresSaver`.
6. Stable thread identity derived from the estimation identifier.
7. A Logfire root span and one child span per graph node.
8. A complete execution trace for the complex sample transcript.
9. Deterministic fake adapters for CI.
10. Separate live PostgreSQL, Logfire, and provider evidence.

## Evidence

- Deterministic execution:
  `estimador-cag/artifacts/session13/complex_graph_execution_deterministic.json`
- PostgreSQL persistence:
  `estimador-cag/artifacts/session13/postgres_persistence_proof.json`
- Live PostgreSQL and Logfire trace:
  `estimador-cag/artifacts/session13/live_postgres_logfire_trace_summary.json`
- Auxiliary live-provider smoke:
  `estimador-cag/artifacts/session13/live_provider_smoke/`
- Mandatory compliance:
  `estimador-cag/docs/session13_task13_compliance.md`
- Non-mandatory Plus roadmap:
  `estimador-cag/docs/session13_plus_roadmap.md`
- Plus credentialed runtime evidence:
  `estimador-cag/docs/session13_plus_live_runtime_evidence.md`
- Spanish presentation guide:
  `estimador-cag/docs/session13_presentation_guide_es.md`

## Historical validation snapshot

The historical implementation checkpoint recorded:

```text
667 passed, 9 skipped
Ruff passed
Python compilation passed
Secret scan passed
Remote CI passed
```

Normal CI remains deterministic. Real-provider and hosted observability checks
are manual and opt-in.

## Historical scope boundary

Parallel retrieval with the LangGraph `Send` API, advanced retry/fallback
policies, circuit breakers, `interrupt()`-based human review, and the full graph
wizard UI were originally tracked as Session 13 Plus work. The current
consolidation documentation supersedes that historical planning statement for
PR #21 without changing the mandatory submission record.

## Historical Session 10 retrieval work

Session 10 remains available as historical coursework:

```text
Branch: gg-session-10/pre-work
Deliverable: Session 10 — advanced retrieval compass and A/B/C/D retrieval evaluation
```

### A/B/C/D retrieval variants

The deterministic historical runner is:

```zsh
cd /workspaces/ai-engineering/estimador-cag
uv run python -m evals.session10_retrieval.run   --output evals/session10_retrieval/results.json   --report evals/session10_retrieval/REPORT.md   --k 5   --recall-k 8
```

Historical outputs:

```text
evals/session10_retrieval/results.json
evals/session10_retrieval/REPORT.md
```

The historical report distinguishes `result budget precision@5` from
`unique budget precision@5`. The small corpus provided wiring and smoke
evidence; it was not proof that hybrid search or reranking improves quality in
production.

Historical provider policy: prefer DeepSeek first and use Kimi only as fallback
or comparison.

Security policy: Do not commit `.env`, real API keys, copied credentials, or
credential-bearing connection strings.

## Session 13 Plus/V3 architecture addendum

The Session 13 Plus source branch is `gg-session-13/plus`. Its verified deterministic V3 foundation before the provider/context documentation update was `0700b9bf396ed8a59c1e9a250f7a5ffad65c4278`.

The architecture documents:

- provider selector: `Auto | DeepSeek | Kimi | OpenAI`;
- default provider: DeepSeek;
- reasoning intent: `minimal | medium | max`;
- context detail: `minimal | medium | max`;
- DeepSeek V4 Flash/Pro;
- Kimi K3/K2.7 Code/K2.6;
- GPT-5.6 Luna/Terra/Sol;
- versioned capability discovery;
- context compaction and rotten-context prevention;
- Session 14 manual-supervisor and persistent-HITL direction;
- EACODE, EACHAT, and evidence-gated EACORE boundaries.

Source entrypoints:

- `estimador-cag/docs/energy_aware_model_context_and_multiagent_policy.md`
- `estimador-cag/docs/session13_plus_v3_foundation.md`
- `estimador-cag/CLAUDE.md`

Historical documentation statements must not be read as current provider reachability claims. The unified runtime uses the sanitized benchmark-backed capability registry and fails closed when required capabilities are absent.

## Session 13 Plus stabilization boundary

The Session 13 Plus line repairs the reviewed-service API contract, separates deterministic and live-provider CI, hardens the SSE activity projection, removes contradictory routing evidence, and labels provider selection through evidence-backed capability gates. The consolidation branch imports that source line without modifying it.
