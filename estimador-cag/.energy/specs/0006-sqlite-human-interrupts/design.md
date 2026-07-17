# Design: SQLite Persistence and Human Interrupts

`sqlite_judge_graph` is a context manager that bounds the SQLite connection lifetime, runs the saver setup/migrations idempotently, and compiles the unchanged graph with that saver. Reopening the database constructs a new graph and connection while retaining thread checkpoints.

The record router first uses the existing bounded retry rule. When no retry remains, an escalate decision or a missing-evidence repair enters `human_review`. The node calls LangGraph `interrupt()` with only JSON-compatible fields: route, identifiers, decision summary, repairs, allowed actions, and an explicit no-execution marker. Resume uses `Command(resume=...)` on the same thread. The node validates `acknowledge`, `provide_context`, or `cancel`, records the response, and proceeds to finalize without altering the domain decision.

The CLI persists proposals and state through SQLite across separate run, inspect, and resume processes. It never invokes a shell or provider.

## Migration and rollback

SQLite saver setup is idempotent and retains existing threads. Rollback closes the connection and preserves the database for inspection; removing the database is an explicit operator action outside this slice.

## Security

Interrupt payloads and responses are data only. Human acknowledgement is not execution authorization. The state remains `execution_performed: false`.
