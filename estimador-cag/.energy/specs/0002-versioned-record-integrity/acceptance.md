# Acceptance

- Legacy evidence loads as schema `1.0.0`, run `legacy`, with derived trust classification.
- A newly appended decision contains schema version, unique decision ID, unique run ID, UTC timestamp, and writer provenance.
- Duplicate decision IDs make ledger integrity incomplete.
- Duplicate evidence IDs and dangling evidence references make ledger integrity incomplete when an evidence ledger is supplied.
- Existing append, ledger, evidence, and adapter tests remain green, except environment-specific root-venv probes when that venv is absent.
