# Requirements: Hashing and Ledger Recovery

## Operator problem

Versioned records identify provenance fields but do not yet compute hashes from actual bytes or provide a safe way to separate valid decision rows from corruption.

## Functional requirements

- Compute labeled SHA-256 digests from exact bytes, UTF-8 text, and file bytes.
- Reject unknown evidence types, duplicate evidence IDs, malformed claimed hashes, and missing hashes when a command or artifact path is present.
- Recover valid decision rows to a new file and invalid rows to a quarantine file.
- Never mutate the source ledger or overwrite an existing output.
- Report exact source, recovered, and quarantine hashes and record counts.
- Provide a CLI that can fail when quarantine is non-empty.

## Hard constraints

- No in-place repair or deletion.
- No claim of cryptographic authenticity; SHA-256 detects byte changes only when compared with a trusted digest.
- No shell execution, provider call, commit, or push.

## Non-goals

- Automatic semantic repair of corrupt records.
- Signing, key management, retention, or remote storage.
