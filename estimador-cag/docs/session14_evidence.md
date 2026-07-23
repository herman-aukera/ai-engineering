# Session 14 evidence

## Evidence ledger

| Evidence | Maturity | Result |
| --- | --- | --- |
| Hybrid typed route proposal | L1 local | Provider-neutral port, guarded production adapter, deterministic fallback, and replay-safe provenance; focused suite `59 passed` |
| Level 3 action audit | L1 local | Pre-execution privilege decision, sanitized success/denial/failure envelope, replay-safe duration handling, public payload, and node-span projection; focused suite `54 passed` |
| Exact teacher edge-case fixture | L1 local | Git blob `53b0a4625464fb5f4759972fa30a356972260986`; public API pause/resume test passed |
| Full deterministic suite | L1 local | `906 passed, 11 skipped` |
| PostgreSQL pause/reopen/resume | L3 integration | `1 passed` |
| Final remote CI | L2 remote | Must be captured after the action-audit commit; pushed base `cf321b57e29a116e0e66fdfddb40bd68df2fd272` exposed no status contexts at audit time |
| Hosted pause/resume trace | L3 hosted | Pending manual Logfire capture |

## PostgreSQL proof

The real integration test is
`tests/integration/test_session14_postgres_human_review.py`.
It proves:

1. the graph reaches `awaiting_human_review`;
2. revision `1` and the interrupt survive checkpointer closure;
3. a new checkpointer resumes with `Command(resume=...)`;
4. the resumed run keeps the same thread ID;
5. a third checkpointer rereads the terminal state without replay;
6. the trace contains the pause and approval events.

The sanitized machine-readable proof is committed at
`artifacts/session14/postgres_pause_resume_proof.json`. The test can replace
it with fresh run-specific evidence by setting
`SESSION14_POSTGRES_EVIDENCE_PATH` during execution. The current artifact
deliberately omits the random estimation ID because the captured command
output did not expose it.

## Teacher edge-case source

The required ORBITA transcript is committed at
`exercises/session-14/sample_transcript_edge_case.txt`. Its Git blob matches
the official `LIDR-academy/ai-engineering` `session_14` reference:

```text
53b0a4625464fb5f4759972fa30a356972260986
```

The local acceptance test sends that exact file through the public graph API,
asserts the checkpoint-backed review pause, approves revision `1`, and
verifies same-thread completion at revision `2`. The separate PostgreSQL test
proves persistence across checkpointer lifetimes; the hosted proof must combine
both properties with this exact fixture.

## Hosted trace

```text
Hosted trace URL: PENDING_REAL_LOGFIRE_CAPTURE
```

This placeholder must be replaced only with the URL copied from the actual
hosted pause/resume execution. A local test result or invented identifier is
not a substitute for the teacher-required trace URL.

## Sanitization

Committed and hosted evidence may contain stable IDs, reason codes, counts,
statuses, route names, revision numbers, sanitized input-shape keys, result
references, and durations. It must not contain the transcript, tool arguments,
input values, prompts, raw model output, exception messages, hidden reasoning,
keys, tokens, database URLs, or environment values.

## Delivery links

```text
Branch: https://github.com/herman-aukera/ai-engineering/tree/session-14/pre-work
Trace:  PENDING_REAL_LOGFIRE_CAPTURE
```

## Claim boundary

After remote CI and hosted trace capture, the evidence may support this claim:

> Session 14 reorganizes estimation as a manually implemented hybrid
> supervisor/workers LangGraph with typed state, least-privilege specialists,
> guarded model route proposals, visible deterministic fallbacks, persistent
> human review, same-thread resume, a sanitized Level 3 action audit, and a
> traced pause/resume run.

It does not establish production SLOs, superior estimation quality, or
universal benefit from multi-agent architecture.
