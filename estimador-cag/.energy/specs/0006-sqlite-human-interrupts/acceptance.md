# Acceptance

- A completed thread remains inspectable after closing and reopening SQLite.
- Saver setup is idempotent and retains checkpoint/write tables and thread state.
- Escalation exposes a typed human-review payload and resumes after process restart.
- Missing evidence exposes the clarify route and accepts contextual human response.
- Human review never changes `execution_performed` from false.
- CLI run persists state and a separate CLI inspect process reads it.
- Focused tests and the canonical clean gate pass.
