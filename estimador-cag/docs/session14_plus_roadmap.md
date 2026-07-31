# Session 14 Plus Roadmap

**Working mode:** LIDR coursework + additive portfolio hardening  
**Protected academic branch:** `session-14/pre-work`  
**Plus branch:** `gg-session-14/plus`  
**Draft PR:** `#19`  
**Plus base checkpoint:** `286ed83f3a1133af88a51c9abb88726e4c072261`  
**Validated Plus technical checkpoint:** `c6f82e4dcdf15af3039d34dcca5e441e4eaeb89c`

## Decision

Session 14 mandatory delivery remains frozen. Plus work is separate, additive, draft, and unmerged.

## Completed Plus v1 core

### 14P-1 — provider and context integrity ✅

- strict capability registry;
- lifecycle-gated enablement;
- fail-closed primary-route validation;
- deterministic `minimal | medium | max` context detail;
- sensitive-field and secret-like value rejection;
- stable fingerprints;
- stale-context rejection;
- replay-safe compaction events.

### 14P-2 — graph integration ✅

- separate `session14_plus_estimation_graph`;
- server-owned policy bootstrap;
- authorized V3 route plan;
- context refresh on supervisor decisions;
- academic graph and API left unchanged;
- additive rollback to `session-14/pre-work`.

### 14P-3 — bounded competition and Energy gate ✅

- baseline, aggressive, conservative, and synthesized candidates;
- Python-owned arithmetic and synthesis;
- confidence-aware weighting;
- deterministic divergence measurement;
- V3 constraint-energy assessment;
- hard missing-evidence/conflict escalation;
- layered coherence validation retained.

### 14P-4 — persisted lifecycle evidence ✅

- context refresh after an authorized human decision;
- real PostgreSQL pause, close, reopen, same-thread resume, close/reopen, terminal reread;
- exact ORBITA fixture;
- competition and capability evidence persisted;
- remote CI and artifact evidence.

Validation checkpoint:

```text
GitHub Actions run 30654656662
Ruff passed
Python compilation passed
923 passed, 11 skipped
Diff and secret gates passed
session14-plus-postgres-evidence passed
```

Durable artifact:

```text
artifacts/session14_plus/postgres_pause_resume.json
```

## Next gate: Session 13 Plus ↔ Session 14 Plus audit

No further architecture or product exposure should be implemented until the continuation audit decides:

1. which reviewed V2 controls must remain separate;
2. which V3 contracts are already reused correctly;
3. which abstractions are duplicated or incompatible;
4. whether a compatibility adapter or migration is justified;
5. which graph becomes the next feature-flagged product path;
6. which docs are canonical versus historical.

Audit prompt:

```text
docs/session13_plus_session14_plus_audit_continuation_prompt.md
```

## Deferred product slices

These are not part of the completed Plus v1 core:

### Provider calibration

- capability discovery before live enablement;
- matched DeepSeek/Kimi/OpenAI evaluation;
- fallback-route capability validation;
- no provider-superiority claim without product evidence.

### API/UI exposure

- additive feature-flagged Plus composition root;
- provider/reasoning/context selectors;
- Control Room integration;
- browser evidence;
- explicit rollback to reviewed V2 and mandatory Session 14.

### Model-generated competition

- conservative/aggressive provider prompts;
- matched accuracy/cost/latency evaluation;
- adversarial disagreement cases;
- human-review impact measurement;
- enable only after deterministic baseline superiority or complementarity is proven.

## Claim boundary

Supported:

> Session 14 Plus v1 contains a separately versioned graph with capability-authorized routing, sanitized deterministic context projection, bounded Energy-Aware estimate competition, preserved human authority, and remote deterministic plus real-PostgreSQL lifecycle evidence.

Blocked:

- Plus is the current production graph;
- context compaction is lossless;
- competition improves estimate accuracy;
- Kimi K3 or GPT-5.6 is operational;
- any provider is universally superior;
- Session 14 Plus is production-ready;
- protected coursework branches have been merged or replaced.
