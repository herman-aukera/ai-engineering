# Session 14 evidence

## Evidence ledger

| Evidence | Maturity | Result |
| --- | --- | --- |
| Hybrid typed route proposal | L1 local | Provider-neutral port, guarded production adapter, deterministic fallback, and replay-safe provenance; focused suite `59 passed` |
| Level 3 action audit | L1 local | Pre-execution privilege decision, sanitized success/denial/failure envelope, replay-safe duration handling, public payload, and node-span projection; focused suite `54 passed` |
| Exact teacher edge-case fixture | L1 local | Git blob `53b0a4625464fb5f4759972fa30a356972260986`; public API pause/resume test passed |
| Full deterministic suite | L1 local | `908 passed, 11 skipped`; Ruff and Python compilation passed |
| PostgreSQL pause/reopen/resume | L3 integration | `1 passed` |
| Action-audit checkpoint CI | L2 remote | Run `29995480121` passed for exact SHA `49cab6d8423e383c765df619ba42fb169bb01eee` |
| Secure hosted evidence workflow | Prepared | `scripts/session14_hosted_evidence.py` plus the `session14-hosted-evidence` CI job; requires GitHub secret `SESSION14_LOGFIRE_TOKEN` |
| Fresh hosted pause/resume trace | Pending credentialed run | Workflow captures one parent trace containing pause, PostgreSQL close/reopen, endpoint resume, terminal reread, and hosted API verification |

## Secure hosted evidence capture

The hosted capture never commits credentials. Create a short-lived Logfire API
key with only **Send telemetry** and **Read**, then save it as the GitHub Actions
repository secret `SESSION14_LOGFIRE_TOKEN`.

On the next push to `session-14/pre-work`, the `session14-hosted-evidence` job:

1. starts PostgreSQL;
2. reads the exact ORBITA fixture;
3. executes the graph through `POST /api/v1/estimate/graph`;
4. verifies `awaiting_human_review` at revision `1`;
5. closes the checkpointer;
6. reopens PostgreSQL persistence and resumes through the public endpoint with
   an approval decision;
7. verifies the same thread reaches `validated` at revision `2`;
8. reopens persistence a third time and verifies the terminal response is
   unchanged;
9. force-flushes Logfire;
10. queries the hosted trace and verifies that both
    `awaiting_human_review` and `completed` spans exist;
11. uploads only the sanitized trace IDs and lifecycle results as a workflow
    artifact.

The capture uses a parent span named `session14.evidence.journey`, so pause and
resume appear inside one trace rather than as unrelated roots. After the job
succeeds, search Logfire for the artifact's `trace_id`, select the parent span,
and use **Private → Create** to produce the public link required by the teacher.

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
proves persistence across checkpointer lifetimes; the secure hosted capture
combines both properties with this exact fixture.

## Historical hosted trace

```text
Historical finalized resume trace: https://logfire-eu.pydantic.dev/public-trace/f0067a79-72a8-44e7-8182-3801e7b00d40?spanId=c2cf5f6eb51ccbcd
```

The historical link proves only the finalized automated-approval resume root.
It does not prove a finalized pause root or a genuine human decision. Replace
it in the delivery email after the secure hosted evidence workflow succeeds
and the resulting parent trace is shared publicly.

## Sanitization

Committed and hosted evidence may contain stable IDs, reason codes, counts,
statuses, route names, revision numbers, sanitized input-shape keys, result
references, and durations. It must not contain the transcript, tool arguments,
input values, prompts, raw model output, exception messages, hidden reasoning,
keys, tokens, database URLs, or environment values.

## Delivery links

```text
Branch: https://github.com/herman-aukera/ai-engineering/tree/session-14/pre-work
Historical resume trace: https://logfire-eu.pydantic.dev/public-trace/f0067a79-72a8-44e7-8182-3801e7b00d40?spanId=c2cf5f6eb51ccbcd
Fresh parent pause/resume trace: pending secure credentialed workflow
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
