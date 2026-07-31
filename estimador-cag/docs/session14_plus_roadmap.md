# Session 14 Plus Roadmap

**Working mode:** LIDR coursework + additive portfolio hardening  
**Protected academic branch:** `session-14/pre-work`  
**Plus branch:** `gg-session-14/plus`  
**Plus source head:** `286ed83f3a1133af88a51c9abb88726e4c072261`

## Decision

Session 14 mandatory delivery is frozen. Plus work continues on a separate branch and must not rewrite, merge into, or weaken the submitted branch.

The Plus sequence is:

1. **Provider and context integrity**
   - strict model capability registry;
   - lifecycle-gated route authorization;
   - deterministic context detail (`minimal`, `medium`, `max`);
   - sanitized compacted handoffs;
   - stable fingerprints;
   - stale-context rejection;
   - replay-safe compaction audit.
2. **Graph integration**
   - compact at checkpoint/provider-switch boundaries;
   - preserve authoritative checkpoint and evidence references;
   - expose compaction events without prompts, transcript, hidden reasoning, credentials, or raw provider output.
3. **Bounded competition**
   - conservative and aggressive estimate candidates;
   - deterministic divergence measurement;
   - synthesizer with Python-owned arithmetic;
   - human review for material disagreement;
   - strict cost, latency, route, and tool budgets.
4. **Provider calibration**
   - capability discovery before enablement;
   - matched DeepSeek/Kimi/OpenAI benchmark;
   - no provider-superiority claim without product evidence.
5. **Product evidence**
   - API/UI selector only after contracts are green;
   - PostgreSQL replay proof;
   - hosted traces;
   - rollback and adverse-case evaluation.

## Slice 14P-1 acceptance contract

This first slice is intentionally provider-neutral and deterministic.

Required:

- documented models are not executable merely because they appear in configuration;
- an enabled route must be contract verified or benchmark calibrated;
- every primary route in a `ModelRoutingPlan` must resolve to an enabled capability;
- unsupported output, reasoning effort, or tool requirements fail closed;
- compacted context is a derived projection, not source of truth;
- hard constraints, identity, checkpoint, evidence references, repository state, validation state, next action, rollback boundary, and claim boundary survive compaction;
- transcript, prompts, raw provider output, hidden reasoning, DSNs, tokens, passwords, and secret-like values are rejected;
- equivalent input produces a stable context fingerprint independently of creation time;
- stale compacted context is rejected before resume/provider switching;
- replayed compaction events deduplicate and conflicting IDs fail closed.

## Claim boundary

This slice proves strict contracts and deterministic policy. It does not claim:

- live Kimi K3 or GPT-5.6 availability;
- provider quality superiority;
- graph-integrated context compaction;
- lossless compaction;
- competitive estimators;
- production readiness.
