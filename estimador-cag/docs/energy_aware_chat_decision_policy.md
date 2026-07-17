# Energy Aware Chat decision policy

Decision policy version: `energy-chat-request-policy-1.0.0`

The authoritative disposition is deterministic Python. Providers may generate candidates, but cannot choose a disposition, override hard constraints, declare evidence sufficient, or upgrade release claims.

## Precedence

The complete decider applies this order:

1. `refuse` when a versioned request rule disallows assistance;
2. `escalate` when accountable human authority is required;
3. `reject` when the candidate has a hard-reject violation but the request itself is not disallowed;
4. `clarify` when user intent is materially insufficient;
5. `repair` when violations are reparable and retry budget remains;
6. `escalate` when repair remains required but retry budget is exhausted;
7. `accept` when hard constraints pass and energy is within threshold.

Every outcome records a `policy_rule_id`, reasoning summary, candidate ID, score ID, repairs, and evidence references.

## Request rules

Current refusal rules are deliberately narrow and exact-phrase based:

| Rule ID | Deterministic markers | Result |
|---|---|---|
| `hidden_reasoning_request` | show/reveal your chain of thought | refuse |
| `private_source_request` | use leaked source | refuse |
| `stolen_credentials_request` | use stolen credentials | refuse |

Current human-authority rules:

| Rule ID | Deterministic markers | Result |
|---|---|---|
| `production_authority_required` | authorize production deployment; approve the production release | escalate |
| `policy_override_requires_human` | override policy | escalate |
| `legal_authority_required` | make the final legal decision | escalate |

No model classification is used. Broader safety coverage requires new explicit rules, fixtures, false-positive tests, and a version change.

## Candidate and budget rules

Candidate hard rejects remain `reject`; they do not become request refusals. Vague intent remains `clarify`. Hard-repair violations and energy above the repair threshold remain `repair` while retry budget exists. If the same condition remains when retry budget reaches zero, the result is `escalate` with rule `repair_budget_exhausted`.

## Allowed transitions

| Disposition | Current allowed graph transition |
|---|---|
| accept | end |
| repair | plan repair or finalize repair |
| clarify | end; interrupt/resume is Milestone 12 |
| reject | end |
| refuse | end |
| escalate | end; interrupt/resume is Milestone 12 |

This milestone defines complete disposition semantics, not human-gate resume behavior. Clarification and escalation currently terminate the non-persistent graph with an inspectable outcome.

## Compatibility

The existing evaluator now uses the complete decider. Its prior accept, repair, clarify, and reject rules retain their deterministic thresholds and precedence after request-level rules. A hidden-reasoning request now correctly produces `refuse` rather than conflating request policy with an unusable candidate.
