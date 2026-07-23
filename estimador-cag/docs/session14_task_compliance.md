# Session 14 task compliance

## Mandatory requirements

| Teacher requirement | Status | Implementation or evidence |
| --- | --- | --- |
| Hand-built supervisor | Complete locally | Explicit `StateGraph` supervisor with typed model proposal, Python legality guards, hop budget, deterministic fallback, and `Command(goto=...)` |
| `StateGraph` plus visible `Command` routing | Complete | `app/generation/graph/session14_build.py` and route-event tests |
| Typed state extended from Session 13 | Complete | `app/generation/graph/review_state.py` |
| Accumulator reducer | Complete | Replay-safe route and contribution reducers |
| Pure partial specialist updates | Complete | `app/generation/graph/nodes/session14_workers.py` |
| Least-privilege tool access | Complete | `app/services/session14_privileges.py` and privilege tests |
| Existing transcript-to-estimate contract | Complete | `POST /api/v1/estimate/graph` |
| Configurable low-confidence trigger | Complete | Session 14 supervision and review policies |
| Outside-range trigger | Complete | Session 14 human-review policy tests |
| No-precedent trigger | Complete | Session 14 human-review policy tests |
| Persistent `interrupt()` | Complete | Session 14 gate plus `AsyncPostgresSaver` integration proof |
| Paused public status | Complete | `awaiting_human_review` API test |
| Resume endpoint | Complete | `POST /api/v1/estimate/graph/{estimation_id}/resume` |
| Approve / adjust / reject | Complete | API and policy tests |
| Same-thread continuation | Complete | PostgreSQL close/reopen/resume proof |
| Complete pause/resume trace | Complete locally; hosted link pending | Sanitized artifact plus Logfire capture procedure |
| Teacher edge-case fixture | Complete locally | `exercises/session-14/sample_transcript_edge_case.txt` plus public API pause/resume acceptance test |

## Teacher-reference alignment

The official `LIDR-academy/ai-engineering` `session_14` branch is a reference,
not an implementation source to copy wholesale.

| Reference idea | Decision in this project |
| --- | --- |
| ORBITA edge transcript | Preserve the course fixture exactly and execute it through this project's API, PostgreSQL, revision/idempotency, and Logfire path |
| Model route proposal | Adapted through a provider-neutral typed port; production uses the inherited structured LiteLLM provider while tests use deterministic fakes |
| Minimum privilege | Keep the immutable server-owned registry and fail-closed pre-execution check already implemented |
| Level 3 action audit | Next Plus quick win: enrich replay-safe contributions with sanitized action metadata instead of copying the teacher's state layout |
| Competition and stronger sandbox | Keep deferred until Mandatory Levels 1 and 2 are honestly complete and evidenced |

## Hybrid-router validation

```text
Branch: session-14/pre-work
Base commit: 6d7d56267dfdb5a7d1a615d44f099e7875e148a4
Exact teacher fixture blob: 53b0a4625464fb5f4759972fa30a356972260986
Focused hybrid supervisor/adapter/state/API suite: 59 passed
Full deterministic suite: 899 passed, 11 skipped
Ruff: passed
Python compilation: passed
```

The existing PostgreSQL proof remains the `1 passed` run captured before this
fixture-only alignment patch. It performs three connection lifecycles: pause,
reopen and resume, then reopen and reread. The next live evidence run must
repeat that lifecycle with the exact ORBITA transcript.

## Delivery gates

- [x] Teacher branch exists and is accessible.
- [x] Level 1 hybrid supervisor routing is complete locally.
- [x] Level 2 persistent human review is implemented.
- [x] Deterministic full suite is green locally.
- [x] Real PostgreSQL pause/reopen/resume is green locally.
- [x] Public endpoint contracts are covered.
- [x] S7 documentation/evidence commit pushed at `c2b7a32`.
- [x] Session 14 node/resume observability pushed at `ae5805e`.
- [x] Teacher alignment committed and pushed at `6d7d562`.
- [ ] Hybrid-router slice committed and pushed.
- [ ] Remote CI green for the final hybrid-router commit.
- [ ] Hosted pause/resume trace inspected and URL recorded.
- [ ] Branch URL and trace URL emailed to `lia@lidr.co`.

Optional competition and provider/context experiments remain outside the
mandatory delivery. The structured Level 3 action audit is the first safe
Plus slice after the hybrid supervisor is green.
