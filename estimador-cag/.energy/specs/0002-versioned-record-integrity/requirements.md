# Requirements: Versioned Record Integrity

## Operator problem

Legacy evidence and decisions can be parsed, but they do not carry enough metadata to reproduce a run or prove evidence-to-decision integrity.

## Functional requirements

- Legacy unversioned JSONL must remain readable without rewriting source files.
- In-memory legacy records must migrate to schema version `1.0.0` and retain an explicit legacy provenance marker.
- Newly appended decisions must receive a unique decision ID, run ID, UTC timestamp, schema version, and writer provenance.
- Integrity inspection must fail on duplicate non-null decision IDs, duplicate evidence IDs, and evidence references that do not exist in a supplied evidence ledger.

## Non-functional requirements

- Migration is deterministic and side-effect free.
- Domain records remain independent of shell, provider, API, and orchestration frameworks.
- Existing callers that construct records without envelope fields remain source compatible.

## Hard constraints

- Do not rewrite historical ledger rows automatically.
- Do not claim cryptographic tamper resistance.
- Do not execute commands or contact providers.

## Non-goals

- Hash-chain signing, retention policy, corrupted-ledger recovery, and persistent graph run storage are later Phase 1 slices.
