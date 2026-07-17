# Energy Aware Chat cross-project learning register

## Verified source checkpoints

| Project | Branch | Pull request | Full source SHA | Status |
|---|---|---:|---|---|
| EACHAT | `EACHAT` | #5 | `dd79bf4befd625ce673242e843c14a023c0862d6` | Milestone 9 code and tests green |
| Session 13 Plus | `gg-session-13/plus` | #10 | `596f94d394e98c8063fcf476684f224af89cb6f5` | draft incubator; do not merge or rewrite |
| EACODE | `EACODE` | #4 | `1d15dc3c06e0918781b945399b13351b1a86f005` | draft incubator; do not merge or rewrite |

The products share proven ideas before runtime code. EACHAT remains product-local and does not import Session 13 or EACODE runtime packages.

## Adoption matrix

| Adoption ID | Source and files | Capability | EACHAT adaptation | Mode | Energy-aware gain | Compatibility and rollback | Tests/evidence | Decision |
|---|---|---|---|---|---|---|---|---|
| `eachat-s13-sanitized-projection-v1` | Session 13 Plus `596f94d...`; `app/services/audit_export.py`, `docs/session13_plus_v2_architecture.md` | allow-listed audit projection without prompts, transcripts, credentials, or raw provider bodies | Decision Ledger and Energy Card v2 expose IDs, safe reasons, numeric energy, evidence references, provider-call IDs, repairs, and limitations only | additive | improves evidence quality and reviewability without increasing disclosure energy | legacy Energy Card remains available; rollback removes new projection nodes and fields | `test_energy_chat_finalization.py`; remote CI | implemented |
| `eachat-s13-single-graph-v1` | Session 13 Plus `596f94d...`; `docs/session13_plus_v2_architecture.md` | one canonical graph behind additive API/UI, no double execution | Milestone 10 will add graph routes without silently invoking both graph and legacy paths | additive, feature-flagged | avoids duplicate provider cost and contradictory decisions | legacy routes remain rollback surfaces until parity is proven | Milestone 10 API parity tests | accepted for next slice |
| `eachat-s13-human-revision-guard-v1` | Session 13 Plus `596f94d...`; `app/schemas/human_review.py` | strict human actions with expected revision | clarify/escalate resume payloads will require expected revision, typed action, reason, and trusted actor model | additive | prevents stale human actions from increasing state inconsistency | no human-gate claim until interrupt/resume tests pass | Milestone 12 tests | accepted, deferred |
| `eachat-eacode-ledger-integrity-v1` | EACODE `1d15dc3...`; `energy_core/ledger.py`, `energy_core/models.py` | append-only, versioned decision records | product-local `DecisionLedgerEntry` links exact chat candidate, critic panel, score, decision, policy, evidence, provider metrics, repair history, and limitations | additive | preserves authoritative history and prevents silent decision rewriting | identical replay is a no-op; conflicting ID reuse fails closed | conflict and replay tests; remote CI | implemented |
| `eachat-eacode-reference-hash-v1` | EACODE `1d15dc3...`; `energy_core/hashing.py` | SHA-256 integrity labels | hash the exact evidence reference string; do not claim it hashes a sensitive evidence body | additive | adds tamper-evident reference identity without persisting evidence bodies | field is optional v1 state addition; rollback ignores v2 projection | SHA format and no-body tests | implemented |
| `eachat-eacode-trust-redaction-v1` | EACODE `1d15dc3...`; `energy_core/models.py`, `energy_core/evidence.py` | trust and redaction classification | evidence integrity metadata records trust, freshness, reference-only redaction, and `body_included=false` | additive | improves evidence sufficiency analysis and privacy | unknown remains the safe default | projection tests | implemented, intentionally narrow |
| `eachat-eacode-review-pack-v1` | EACODE `1d15dc3...`; `energy_core/review_pack.py`, `energy_core/manifest.py` | reviewer pack and trusted manifest | later audit export will use an allow-listed manifest of ledger, state schema, evidence references, limitations, and claim status | additive | improves release traceability | no audit-export claim until export contract and secret scan pass | later audit packet tests | accepted, deferred |

## Explicitly rejected transfers

The following source capabilities are product-specific and must not be copied into EACHAT:

- EACODE shell execution, repository mutation, patch application, command allowlists, IDE adapters, auto-commit, and auto-push.
- Session 13 estimation arithmetic, module/task estimation schemas, budget-specific Critic/Boss semantics, and estimation scenario calculations.
- Shared EACORE runtime extraction before two independently stable product contracts prove identical semantics.

## Additional lessons discovered

1. A graph checkpoint and a reviewer audit packet are different artifacts. The checkpoint may contain internal state; the audit packet must be allow-listed and user-safe.
2. A hash must state exactly what it covers. EACHAT Milestone 9 hashes evidence-reference strings only, not evidence bodies.
3. A no-provider or no-tool marker is useful positive evidence. Final projections now declare `no_external_provider_call` when applicable and always declare `no_tool_execution` for the chat graph.
4. Human actions require revision guards before persistence; an interrupt alone is not sufficient proof of human control.
5. Public API migration must not execute legacy and graph runtimes in parallel unless an explicit, bounded shadow experiment is requested and separately metered.
