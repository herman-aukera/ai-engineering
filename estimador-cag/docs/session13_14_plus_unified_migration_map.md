# Session 13 + 14 Plus — Semantic Migration Map

## Principle

The consolidation is not a blind Git overlay. Session 14 Plus already descended from an earlier Session 13 Plus checkpoint, while Session 13 Plus continued independently to production readiness. The writable consolidation branch imports the complete later Session 13 Plus ancestry and reconciles semantic conflicts explicitly.

## Lineage

```text
d9caf76d  common ancestor
├─ Session 13 Plus → f87605cb
│  └─ merged to main through PR #10
└─ Session 14 mandatory → 286ed83f
   └─ Session 14 Plus → 34011bcd
      └─ consolidation branch
         └─ controlled S13 ancestry merge: 6e0289cb
```

No source branch was rewritten.

## Conflict reconciliation

| File | Session 13 strength | Session 14 strength | Consolidated decision |
|---|---|---|---|
| `.github/workflows/ci.yml` | production/provider/container readiness | Plus PostgreSQL evidence | retain production CI and add unified PostgreSQL + unified container gates |
| `README.md` | production-readiness context | Session 14 Plus handoff | replace with final unified status after evidence |
| `app/config.py` | provider/readiness settings | Session 14 confidence threshold | combine with fail-closed validation |
| `graph/observability.py` | stage-route binding | Session 14 command/HITL audit | one module supporting mandatory, reviewed, supervised and unified spans |
| `graph/review_state.py` | V2/V3 reviewed fields | replay-safe supervisor/HITL reducers | supervised state extends reviewed state; authority fields remain distinct |
| `app/main.py` | readiness + reviewed runtime | supervised runtime + Logfire flush | three isolated runtimes plus additive unified runtime |

## Capability decisions

| Capability | Decision | Rationale |
|---|---|---|
| Session 13 structure review | adapt into unified structure phase | valuable distinct authority before estimation |
| Session 13 parallel retrieval | retain with sequential rollback | measured production path and safe rollback |
| Session 13 Critic | retain as advisory evidence | must not become route authority |
| Session 13 Boss | retain as bounded recommendation | unified supervisor owns routing |
| Session 13 recovery | retain behind cycle and execution budgets | prevents unbounded repair loops |
| Session 13 proposal | retain as final product projection | occurs only after coherence/human policy |
| Session 13 provider benchmark | adapt into strict capability registry | exact evidence-backed enablement |
| Session 14 supervisor | supersede with unified supervisor | preserves single authority while routing larger lifecycle |
| Session 14 specialists | retain where used directly | least privilege and action audit remain valid |
| Session 14 human gate | canonical final authority | strongest persisted approve/adjust/reject contract |
| Session 14 Plus compact context | retain as derived evidence | safe provider/checkpoint handoff |
| Session 14 Plus competition | retain before Critic/coherence | deterministic variation under Energy policy |
| separate V2 final-review authority | preserve only as rollback | avoids competing final authorities in unified graph |
| model-generated competing personas | reject for now | no matched accuracy evidence |

## State migration

No historical checkpoint is silently interpreted as a unified checkpoint.

New unified threads use:

```text
graph_name = session13_14_plus_unified_graph
graph_version = session13_14_plus.unified.v1
thread_id = estimate:<estimation_id>
```

Existing reviewed and supervised threads continue through their original services and graph versions.

The unified state is a typed superset, but checkpoint compatibility is versioned, not inferred from structural similarity.

## Authority migration

### Before

- Session 13 reviewed graph: Critic/Boss and multiple review phases drove their own graph path.
- Session 14 graph: supervisor routed specialists and final HITL.

### After

```text
structure review edits structure only
Critic emits typed findings
Boss emits bounded recommendation
unified supervisor owns all route transitions
coherence validator independently checks arithmetic/state
Session 14 human gate owns approve/adjust/reject
```

## API migration

No endpoint is replaced.

```text
Existing supervised: /api/v1/estimate/graph
Existing reviewed:   /api/v1/estimate/graph/reviewed/start
Unified:             /api/v1/estimate/graph/unified
Unified control:     /api/v1/estimate/graph/unified/control
```

Promotion to a default product path requires matched evaluation and explicit authorization.

## Provider migration

The documentation-era `kimi-k2.6` route is not promoted. The imported benchmark verified `kimi-k3`; the unified plan rewrites Moonshot priors to this exact ID and validates every fallback.

Output ceilings are clamped to measured capability metadata rather than expanded to satisfy a prior route plan.

## Rollback

1. Disable or stop calling the unified endpoint.
2. Continue using supervised or reviewed endpoints.
3. Revert unified commits in reverse order only on the writable branch.
4. Preserve all original source branches and their evidence.
5. Never reinterpret an existing thread with another graph version.

## Deferred migrations

- make unified graph the default backend;
- retire reviewed/supervised paths;
- convert old checkpoints;
- allow UI-selected provider overrides;
- run model-generated candidate competition;
- extract a shared EACORE package.

Each remains evidence-gated and requires separate authorization.
