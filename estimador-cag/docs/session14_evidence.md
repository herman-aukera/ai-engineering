# Session 14 evidence

## Evidence ledger

| Evidence | Maturity | Result |
| --- | --- | --- |
| Typed contracts and routing tests | L1 local | Passed at `9de934e` |
| Full deterministic suite | L1 local | `885 passed, 11 skipped` |
| PostgreSQL pause/reopen/resume | L3 integration | `1 passed` |
| S7 remote CI | L2 remote | Pending final S7 push |
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

## Hosted trace

```text
Hosted trace URL: PENDING_REAL_LOGFIRE_CAPTURE
```

This placeholder must be replaced only with the URL copied from the actual
hosted pause/resume execution. A local test result or invented identifier is
not a substitute for the teacher-required trace URL.

## Sanitization

Committed and hosted evidence may contain stable IDs, reason codes, counts,
statuses, route names, revision numbers, and durations. It must not contain
the transcript, prompts, raw model output, hidden reasoning, keys, tokens,
database URLs, or environment values.

## Delivery links

```text
Branch: https://github.com/herman-aukera/ai-engineering/tree/session-14/pre-work
Trace:  PENDING_REAL_LOGFIRE_CAPTURE
```

## Claim boundary

After remote CI and hosted trace capture, the evidence supports this claim:

> Session 14 reorganizes estimation as a manually supervised multi-agent
> LangGraph with typed state, least-privilege specialists, visible routing,
> persistent human review, same-thread resume, and a traced pause/resume run.

It does not establish production SLOs, superior estimation quality, or
universal benefit from multi-agent architecture.
