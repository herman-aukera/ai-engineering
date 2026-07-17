# Design: Hashing and Ledger Recovery

`hashing.py` hashes exact bytes and labels digests as `sha256:<hex>`. No newline normalization occurs.

`validate_evidence_records` validates policy membership and the syntax/presence of claimed command and artifact hashes. It does not rerun commands or assume a syntactically valid hash is trustworthy.

`ledger_recovery.py` reads the source once, validates each nonblank row through the current migration and decision schema, writes canonical valid rows to a new recovered ledger, and records invalid raw rows plus line/error metadata in a new quarantine ledger. A preflight rejects overlapping paths and existing outputs. The source hash is computed from bytes read before processing; output hashes are computed after writes.

## Migration and rollback

No persisted schema changes are required. Rollback deletes newly created recovery outputs after human review; the source remains untouched.

## Append-only semantics

- File level: normal decisions append through `append_decision`; recovery never edits that file.
- Application level: recovery outputs are create-only and refuse overwrite.
- Git level: this code does not prove or enforce append-only git history; repository policy and review remain required.
