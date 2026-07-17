# Acceptance

- Known test vectors produce exact labeled SHA-256 digests.
- Unknown evidence types and malformed hashes fail validation.
- A mixed ledger produces separate recovered and quarantine files while source bytes remain unchanged.
- Recovery refuses source/output aliasing and existing outputs.
- CLI returns nonzero with `--fail-on-quarantine` when corruption exists.
