# Teacher demonstration versus Control Room V2

This is a capability comparison, not a claim about the teacher's complete codebase.
The reference is the supplied Session 12 live archive and the observed five-step UI.

| Capability | Teacher demonstration | Control Room V2 |
|---|---|---|
| Product journey | Rich guided wizard | One eight-stage control room with reconnect and progress |
| Structure | Editable modules/tasks | Editable modules/tasks persisted through a durable structure gate |
| Execution | Agent-oriented flow | One canonical graph execution; UI is a projection, not a second engine |
| Arithmetic | Product result | Python-owned task/module/project totals with range invariants |
| Evidence | Visible agent reasoning | Stable source/chunk provenance attached to tasks |
| Quality control | Agent personas | Typed Critic findings plus deterministic Boss policy |
| Recovery | Agent retry behavior | Selected recovery, explicit retry/fallback budgets and circuit breaker |
| Human control | Wizard confirmation | Revision-guarded interrupts, override, reject, recovery and resume |
| Durability | Demo application state | Checkpoint identity, history, scenario branching and PostgreSQL saver |
| Rollout | Single demonstrated product | Additive `/api/v2`, legacy rollback and sanitized shadow comparison |
| Audit | UI result | Exportable packet with decisions, budgets, provenance and lineage |
| Evaluation | Demonstration quality | Contract suite plus reproducible 4×4 concurrency matrix |

The strongest improvement is architectural: the rich UI and the durable graph are
not competing versions. Context, reformulation, structure, evidence, estimation,
Critic/Boss, approval and audit are stages of one execution. The remaining honest
gap is production-scale evidence, not a missing product path.
