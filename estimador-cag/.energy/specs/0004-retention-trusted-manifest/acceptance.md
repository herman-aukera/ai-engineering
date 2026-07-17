# Acceptance

- Exact manifest verification passes before and fails after byte tampering.
- Manifest generation rejects root escapes and existing destinations.
- Expired evidence is only marked eligible for review; no records are deleted.
- Missing timestamps force retention.
- Mixed evidence recovery preserves source bytes and separates one valid and one invalid row.
- Portable focused and regression tests pass.
