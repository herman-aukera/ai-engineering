# Requirements: Retention and Trusted Manifest

## Operator problem

Hash values exist, but lifecycle decisions and digest authenticity remain undefined unless a manifest is obtained through a trusted channel. Corrupted evidence also needs the same safe recovery path as decisions.

## Functional requirements

- Classify evidence as release, audit, or transient with explicit retention periods.
- Report expired records as eligible for human review without deleting or rewriting anything.
- Retain records with missing timestamps and surface them explicitly.
- Build create-only manifests for files bounded by a root directory.
- Verify size and SHA-256 against a trusted manifest and fail on missing, changed, or path-escaping entries.
- Recover valid evidence rows and quarantine invalid rows without mutating source bytes.
- Provide generate/verify, retention-report, and evidence-recovery CLIs.

## Hard constraints

- No automated deletion.
- No manifest overwrite.
- No file outside the declared root.
- No authenticity claim unless the manifest copy itself came from a trusted channel.

## Non-goals

- Signing keys, remote transparency logs, legal retention advice, or automated disposal.
