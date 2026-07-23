# Session 14 edge-case demo journey

## Goal

Demonstrate the teacher-required lifecycle through the public API:

```text
edge transcript
-> supervisor and specialists
-> low confidence
-> persisted interrupt
-> checkpointer reopen
-> human approval
-> same-thread completion
```

## Start the edge case

Use a stable UUID and the exact teacher edge transcript committed at
`exercises/session-14/sample_transcript_edge_case.txt`:

```bash
cd /workspaces/ai-engineering/estimador-cag

SESSION14_ESTIMATION_ID="f5317c82-05ad-4df5-bf43-f9b286f70e82"
SESSION14_TRANSCRIPT_PATH="exercises/session-14/sample_transcript_edge_case.txt"
SESSION14_START_REQUEST="/tmp/session14-edge-start-request.json"

jq -n \
  --arg estimation_id "$SESSION14_ESTIMATION_ID" \
  --rawfile transcript "$SESSION14_TRANSCRIPT_PATH" \
  '{
    estimation_id: $estimation_id,
    transcript: $transcript
  }' >"$SESSION14_START_REQUEST"

curl -sS -X POST http://127.0.0.1:8000/api/v1/estimate/graph \
  -H 'Content-Type: application/json' \
  --data-binary "@$SESSION14_START_REQUEST"
```

Expected evidence:

- `status` is `awaiting_human_review`;
- `revision` is `1`;
- `thread_id` is stable;
- the interrupt lists `approve`, `adjust`, and `reject`;
- the interrupt contains no transcript, provider payload, credential, or DSN.

Stop the API process after the paused response and start it again against the
same PostgreSQL database. This is the human-visible equivalent of the
automated close/reopen proof.

## Resume the original thread

```bash
curl -sS -X POST \
  "http://127.0.0.1:8000/api/v1/estimate/graph/$SESSION14_ESTIMATION_ID/resume" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "approve",
    "expected_revision": 1,
    "actor": "session14-demo-reviewer",
    "idempotency_key": "session14-demo-approve-001"
  }'
```

Expected evidence:

- terminal `status` is `validated`;
- `revision` is `2`;
- `human_review_status` is `approved`;
- the thread ID matches the paused response;
- the final trace ends with `session14_human_review_paused` and
  `session14_human_review_approve`.

## Alternatives

An `adjust` decision must include component hours and evidence references; the
service recalculates the total. A `reject` decision completes without
authorizing the estimate. A stale revision returns HTTP 409. Repeating an
identical decision with the same idempotency key returns the original result;
conflicting reuse returns HTTP 409.

## Hosted trace capture

Run the journey with `LOGFIRE_TOKEN` configured. In Logfire, filter service
`estimador-cag`, graph name `session14_estimation_graph`, and the stable
estimation ID. The paused request and resumed request appear as sanitized
`session14.graph.run` root spans, with `session14.graph.node` children. Confirm
that both roots share the same thread ID, the first root reports
`execution_status=awaiting_human_review`, and the second reports
`execution_mode=human_review_resume`. Share the filtered Logfire view containing
both roots, then copy its URL into `session14_evidence.md` and the delivery
email. Never paste credentials or the transcript into evidence.
