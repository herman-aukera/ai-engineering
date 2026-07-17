# Design: Versioned Record Integrity

`record_schema.py` owns current schema constants and pure legacy migration functions. Pydantic contracts expose the current envelope with compatibility defaults. Readers migrate dictionary payloads before validation; source JSONL remains unchanged. `append_decision` enriches only the new row being appended.

`build_ledger_integrity` accepts an optional evidence path. Omitting it preserves historical CLI behavior and emits a warning. Supplying it activates duplicate evidence-ID and referential-integrity checks. Duplicate candidate IDs remain warnings because repeated evaluation is a valid use case; duplicate decision IDs are failures.

## Data and migration

- Source version: implicit legacy/unversioned.
- Target version: `1.0.0`.
- Rollback: remove the new optional fields and migration call sites; historical source files require no rollback.
- Recovery: invalid JSON continues to be reported as invalid rather than silently repaired.

## Security

Trust classification and redaction state are explicit but descriptive. They do not independently prove trust or redaction. Hash fields are optional until controlled execution can generate them from actual bytes.
