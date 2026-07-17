# Acceptance

- Strict proposal contracts reject executable paths and malformed fields.
- Denied proposals never invoke a tool adapter.
- Read-only git proposals require a separate human authorization; mutating git proposals are denied.
- Working-directory traversal, absolute path escape, and symlink escape are rejected.
- Non-allowlisted environment names deny the plan without storing values.
- Dry-run mode produces evidence without adapter invocation or execution.
- Fake mode produces deterministic evidence with redaction, truncation, hashes, and exit status.
- Plan hashes are deterministic and change when relevant inputs change.
- Execution evidence converts to the existing strict `EvidenceRecord` contract.
- The judge graph adds preview evidence only after candidate acceptance, reevaluates through the existing Python decider, and never performs real execution.
- Existing graph runs without command proposals retain their original route and trace.
- Focused tests and the canonical deterministic CI gate pass.
- No real command, provider, commit, push, or merge path is introduced.
