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
| Level 3 action/privilege audit | Complete locally | `app/services/session14_action_audit.py`, enriched replay-safe contributions, strict public payload, structured denial/failure events, and Logfire node attributes |
| Existing transcript-to-estimate contract | Complete | `POST /api/v1/estimate/graph` |
| Configurable low-confidence trigger | Complete | Session 14 supervision and review policies |
| Outside-range trigger | Complete | Session 14 human-review policy tests |
| No-precedent trigger | Complete | Session 14 human-review policy tests |
| Persistent `interrupt()` | Complete | Session 14 gate plus `AsyncPostgresSaver` integration proof |
| Paused public status | Complete | `awaiting_human_review` API test |
| Resume endpoint | Complete | `POST /api/v1/estimate/graph/{estimation_id}/resume` |
| Approve / adjust / reject | Complete | API and policy tests |
| Same-thread continuation | Complete | PostgreSQL close/reopen/resume proof |
| Complete pause/resume trace | Capture workflow prepared | `scripts/session14_hosted_evidence.py` creates one parent hosted journey with three PostgreSQL lifecycles and endpoint pause/resume; credentialed run and public share URL remain pending |
| Teacher edge-case fixture | Complete locally | `exercises/session-14/sample_transcript_edge_case.txt` plus public API pause/resume acceptance test |

## Teacher-reference alignment

The official `LIDR-academy/ai-engineering` `session_14` branch is a reference,
not an implementation source to copy wholesale.

| Reference idea | Decision in this project |
| --- | --- |
| ORBITA edge transcript | Preserve the course fixture exactly and execute it through this project's API, PostgreSQL, revision/idempotency, and Logfire path |
| Model route proposal | Adapted through a provider-neutral typed port; production uses the inherited structured LiteLLM provider while tests use deterministic fakes |
| Minimum privilege | Keep the immutable server-owned registry and fail-closed pre-execution check already implemented |
| Level 3 action audit | Implemented by enriching this project's conflict-detecting contribution reducer with sanitized action, privilege, input-shape, result-reference, status, and duration metadata |
| Competition and stronger sandbox | Keep deferred until Mandatory Levels 1 and 2 are honestly complete and evidenced |

## Hybrid-router validation

```text
Branch: session-14/pre-work
Implementation repair base: f6d91b9f881726f08bd6c59ff46290bcdc6525a2
Secure hosted evidence workflow: prepared on the teacher-facing branch
Exact teacher fixture blob: 53b0a4625464fb5f4759972fa30a356972260986
Focused hybrid supervisor/adapter/state/API suite: 59 passed
Focused Level 3 action-audit/state/worker/API/trace suite: 54 passed
Full deterministic suite: 908 passed, 11 skipped
Ruff: passed
Python compilation: passed
```

The guarded evidence workflow repeats the real PostgreSQL lifecycle with the
exact ORBITA transcript. It performs three connection lifecycles: pause,
reopen and endpoint resume, then reopen and reread. The workflow uses one
parent Logfire span so the complete journey can be shared as one trace.

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
- [x] Hybrid-router slice committed and pushed at `cf321b5`.
- [x] Optional Level 3 action audit complete locally.
- [x] Remote CI green for action-audit checkpoint `49cab6d` (run `29995480121`).
- [x] Secure hosted ORBITA capture script and CI job committed.
- [ ] Repository secret `SESSION14_LOGFIRE_TOKEN` configured with a fresh short-lived key.
- [ ] Credentialed hosted capture job green for the final branch head.
- [ ] Parent pause/resume trace shared publicly and URL recorded.
- [ ] Branch URL and fresh public trace URL emailed to `lia@lidr.co`.

Optional competition and provider/context experiments remain outside the
mandatory delivery. The structured Level 3 action audit is complete locally;
competition, stronger sandboxing, provider/context selection, and broader HITL
cases remain separate Plus slices.
