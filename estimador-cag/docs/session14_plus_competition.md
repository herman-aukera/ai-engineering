# Session 14 Plus — Bounded Candidate Competition

## Slice

`14P-3`

## Purpose

Add the teacher-deferred conservative/aggressive competition pattern without allowing model agents to control arithmetic, privileges, or acceptance.

## Flow

```text
estimate_generator
→ candidate_competition
   ├─ baseline candidate
   ├─ aggressive / delivery-optimized candidate
   ├─ conservative / risk-buffered candidate
   ├─ deterministic synthesis
   └─ constraint-energy assessment
→ supervisor
→ coherence_validator
→ human review when required
```

## Deterministic policy

- aggressive hours apply a bounded discount and never cross a known lower evidence bound;
- conservative hours apply a bounded buffer and respect a known upper evidence bound;
- synthesis weight moves toward the conservative candidate as average confidence falls;
- material divergence is measured against baseline total hours;
- missing component hours are hard missing evidence;
- material divergence is a hard conflict;
- low average confidence is a soft energy penalty;
- Python selects synthesized output only when hard constraints pass;
- otherwise baseline arithmetic is retained and human review is mandatory.

## Session 13 Plus integration

The node reuses the V3 Energy-Aware foundation:

- stable candidate fingerprints;
- typed constraint observations;
- deterministic energy calculation;
- hard-blocking missing/conflict semantics;
- safe reason codes.

## State evidence

- `plus_competition_completed`
- `plus_competition_policy_version`
- four immutable candidate projections
- typed competition assessment
- energy snapshot
- selected candidate identity
- divergence ratio and threshold
- review disposition
- sanitized domain trace event

## Authority boundary

The competition node has no tools and makes no provider calls. It cannot approve human review, change privileges, alter evidence, or invent source hours.

## Claim boundary

This proves bounded deterministic candidate competition and graph integration. It does not prove that conservative/aggressive LLM personas improve estimation quality. A matched evaluation is required before enabling model-generated competing candidates.
