# Session 14 task compliance

## Mandatory requirements

| Teacher requirement | Status | Implementation or evidence |
| --- | --- | --- |
| Hand-built supervisor | Partial | `app/generation/graph/nodes/session14_supervisor.py` is explicit and safe, but currently selects every route deterministically; the typed model-proposal seam is still missing |
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
| Model route proposal | Adapt through a provider-neutral typed port with Python-owned legality and fallback; not complete at this checkpoint |
| Minimum privilege | Keep the immutable server-owned registry and fail-closed pre-execution check already implemented |
| Level 3 action audit | Next Plus quick win: enrich replay-safe contributions with sanitized action metadata instead of copying the teacher's state layout |
| Competition and stronger sandbox | Keep deferred until Mandatory Levels 1 and 2 are honestly complete and evidenced |

## Teacher-alignment validation

```text
Branch: session-14/pre-work
Base commit: ae5805e9ba0e02e995de2a8d2e7cec4abcc09440
Exact teacher fixture blob: 53b0a4625464fb5f4759972fa30a356972260986
Focused edge-case API test: 1 passed
Session 14 human-review API file: 6 passed
Full deterministic suite: 887 passed, 11 skipped
Ruff: passed
Python compilation: passed
```

The existing PostgreSQL proof remains the `1 passed` run captured before this
fixture-only alignment patch. It performs three connection lifecycles: pause,
reopen and resume, then reopen and reread. The next live evidence run must
repeat that lifecycle with the exact ORBITA transcript.

## Delivery gates

- [x] Teacher branch exists and is accessible.
- [ ] Level 1 hybrid supervisor routing is complete.
- [x] Level 2 persistent human review is implemented.
- [x] Deterministic full suite is green locally.
- [x] Real PostgreSQL pause/reopen/resume is green locally.
- [x] Public endpoint contracts are covered.
- [x] S7 documentation/evidence commit pushed at `c2b7a32`.
- [x] Session 14 node/resume observability pushed at `ae5805e`.
- [ ] Teacher-alignment patch committed and pushed.
- [ ] Remote CI green for the final alignment commit.
- [ ] Hosted pause/resume trace inspected and URL recorded.
- [ ] Branch URL and trace URL emailed to `lia@lidr.co`.

Optional competition and provider/context experiments remain outside the
mandatory delivery. The structured Level 3 action audit is the first safe
Plus slice after the hybrid supervisor is green.
