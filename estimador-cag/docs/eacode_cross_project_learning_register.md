# EACODE Cross-Project Learning Register

Audit date: 2026-07-17  
Target: `EACODE`  
Target baseline before Spec 0007: `1d15dc3c06e0918781b945399b13351b1a86f005`

## Source projects

| Source | Branch | Immutable head | PR state | Evidence used |
|---|---|---|---|---|
| Session 13 Plus | `gg-session-13/plus` | `596f94d394e98c8063fcf476684f224af89cb6f5` | PR #10 open draft | strict human-review contracts, provider circuit breaker, V2 architecture and PR evidence |
| Energy Aware Chat | `EACHAT` | `bba803e11a34bcbd77311576573181f9a4970ff7` | PR #5 open | typed critic/energy/card contracts, repair result contracts, provider metrics and benchmark claim gates |

## Adoption matrix

| Adoption ID | Source capability | Source files | Target adaptation | Mode | Energy-aware gain | Decision |
|---|---|---|---|---|---|---|
| EACODE-XP-001 | strict revision-aware human decisions | `app/schemas/human_review.py` | reserve revision, actor, reason, one-time plan hash and expiry for a future execution-authorization record | additive design | prevents stale or replayed approval | accepted for Spec 0008, not implemented in 0007 |
| EACODE-XP-002 | serializable circuit breaker | `app/services/provider_circuit.py` | reuse the pure transition idea for future provider/tool adapters, not in deterministic command planning | additive design | bounds repeated provider/tool failure | deferred to provider/tool runtime phase |
| EACODE-XP-003 | visible staged journey and sanitized audit | Session 13 Plus V2 docs and UI | adapt information architecture into a future Code Review Console; do not copy estimation UI code | documentation-only | improves human control and evidence legibility | accepted for UI roadmap |
| EACODE-XP-004 | typed critic findings and energy summary | `app/energy_chat/contracts.py` | preserve EACODE product-local violation and decision contracts; later add a Code Decision Card projection | additive | makes decision/evidence state understandable | accepted for product interface phase |
| EACODE-XP-005 | explicit repair result and provider metrics | `app/energy_chat/contracts.py`, repair modules | design immutable command/candidate versions and bounded repair after controlled evidence exists | additive | detects repeated or non-improving repair | accepted for Spec 0009 planning |
| EACODE-XP-006 | release-claim gates | EACHAT release-claim modules and PR body | retain evidence-level claim boundaries for real execution, provider quality, benchmark superiority, and production readiness | additive | prevents unsupported product claims | adopted immediately in docs |

## Product-specific capabilities not copied

- Session 13 estimation arithmetic, budget retrieval, estimation scenarios, and estimate-specific Boss policy remain product-specific.
- EACHAT conversation modes, answer-generation prompts, grounding UI, and chat refusal semantics remain product-specific.
- No sibling runtime code is imported into EACODE.
- No EACORE extraction is justified by this learning audit.

## Additional useful ideas found

1. Separate candidate acceptance from execution authorization and final evidence acceptance.
2. Treat a human form submission as revision-guarded data, not ambient approval.
3. Keep circuit-breaker transitions pure and serializable for checkpoint replay.
4. Record provider/tool evidence separately from deterministic policy decisions.
5. Keep user-visible cards compact while preserving full reviewer packets behind them.
6. Use claim gates so fake-tool and dry-run evidence cannot be mistaken for real execution proof.

## Rollback

This register is documentation-only. Reverting it changes no runtime behavior. Runtime adoptions must keep their own migration and rollback evidence in the target EACODE spec packet.
