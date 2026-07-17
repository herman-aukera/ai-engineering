# Security Model

- EACORE stores references, not sensitive evidence bodies.
- Canonical hashes provide integrity against a trusted reference, not authenticity.
- Hidden reasoning, prompt bodies, raw provider transcripts, credentials, environment dumps, and raw shell output are outside the contract.
- Runtime imports are restricted by an AST dependency-boundary test.
- Manifest paths are resolved beneath an explicit root and path escape fails closed.
- Unknown major schema versions fail explicitly.
- Corrupted JSONL rows are reported; append is blocked until recovery.
- EACORE never executes commands or calls providers.
