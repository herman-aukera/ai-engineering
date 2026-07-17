# Design: Retention and Trusted Manifest

The retention reporter uses three classes: release records are indefinite, audit records are reviewed after 365 days, and transient records after 30 days. Missing timestamps force retention. The reporter is read-only and reports zero deletions by contract.

Manifests contain relative POSIX paths, byte sizes, labeled SHA-256 digests, generation time, and an explicit `requires-trusted-manifest-copy` authenticity statement. Generation rejects paths outside the root and uses create-only writes. Verification resolves every path under the root and compares both size and digest.

Evidence recovery mirrors decision recovery: valid migrated records go to a new recovered JSONL file; invalid raw rows and diagnostics go to a new quarantine file; source bytes are hashed before processing and never changed.

## Rollback

All reports are read-only and recovery/manifest outputs are new files. Rollback removes newly created outputs after review; source ledgers remain unchanged.
