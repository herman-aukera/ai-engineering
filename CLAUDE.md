# Claude Code project memory — EACHAT branch

This file is branch-scoped to the `EACHAT` incubator. Verify the current branch, remote head and clean working tree before editing. Stop when the checkout is not `EACHAT` or is divergent.

## Product and portfolio context

Read these files before implementation:

@docs/ENERGY_AWARE_PORTFOLIO_README.md
@estimador-cag/ENERGY_AWARE_PROVIDER_ROUTING_README.md
@estimador-cag/docs/energy_aware_chat_provider_context_spec.md
@estimador-cag/docs/energy_aware_chat_milestone_10_provider_context_addendum.md
@estimador-cag/docs/energy_aware_chat_sdd.md
@estimador-cag/docs/energy_aware_chat_architecture.md
@estimador-cag/docs/energy_aware_chat_state_contract.md
@estimador-cag/docs/energy_aware_chat_milestone_10_graph_api_spec.md
@estimador-cag/docs/energy_aware_chat_cross_project_learning_register.md

## Product boundary

EACHAT is a general-purpose Energy Aware Chat product. It owns chat interpretation, evidence routing, candidate generation, critics, energy scoring, deterministic decisions, bounded repair, clarification, refusal, escalation, Decision Ledger, Energy Cards, chat API, persistence roadmap, UI and chat evaluations.

EACHAT does not own shell execution, repository mutation, patch application, IDE adapters or EACODE rollback mechanics.

EACODE is a separate coding-governance product intended to sit between coding clients and model providers. Session 13 Plus is coursework and architecture inspiration. EACORE remains documentation/contracts until two products justify runtime extraction.

Do not modify `EACODE`, `gg-session-13/plus`, `main` or `finalproject-GGC` while implementing EACHAT.

## Current task

All 21 implementation milestones are complete. The exact-head product path includes deterministic regression, PostgreSQL, browser, security/dependency, durable-memory, fixed-quality, and container-restart gates. Remaining work is external evidence: credentialed provider smoke, matched live quality comparison, public deployment, real-user telemetry, and a human release decision. See `estimador-cag/docs/energy_aware_chat_current_audit.md` for the current evidence boundary.

```text
POST /energy-chat/v2/chat        — deterministic, owns execution profile, checkpointed
POST /energy-chat/v2/chat/live   — live bounded, owns execution profile, bounded provider
POST /energy-chat/v2/demo        — V2 browser demo (served by FastAPI)
```

**Implemented capabilities:** graph-backed API, application-lifetime and PostgreSQL checkpointing with authoritative replay/resume, revision-guarded human gates, durable encrypted conversation memory, observability spans/metrics, evidence body hashing and citation validation, XSS-safe V2 browser demo, provider capability catalog and bounded adapters, runtime context compaction, bounded committee/adaptive orchestration, fixed-corpus evaluation, container restart proof, and evidence-gated release claims.

## Model and selector policy

Stable product selectors:

```text
provider: auto | deepseek | kimi | openai
effort: fast | balanced | max
context: minimal | balanced | max
orchestration: single | critic | committee | adaptive
```

Current policy:

- DeepSeek is the cost-effective default.
- Kimi K3 is the user-preferred quality candidate, not an objectively proven best model.
- GPT-5.6 is the premium option.
- The normal Energy Aware graph corresponds to the `critic` concept; do not claim committee/adaptive execution unless separately implemented.
- Reasoning effort and context compaction are independent.

Do not guess Kimi K3 API model IDs or parameters. The public release is confirmed, but adapter implementation requires account-visible API verification. OpenAI GPT-5.6 uses Luna/Terra/Sol capability tiers; map them through provider adapters rather than accepting arbitrary user model IDs.

Claude Code may itself be running through DeepSeek. That implementation backend is separate from the EACHAT product runtime. Never infer that the product has a provider integration merely because Claude Code used that provider to write code.

## Engineering rules

- Repository state, tests, CI and current command output outrank this file.
- Use TDD and the smallest coherent slice.
- No `set -e` or `set -euo pipefail` in user-pasteable commands.
- Do not commit on failed gates.
- Deterministic CI makes zero external provider calls.
- Credentialed provider smoke is manual, bounded and sanitized.
- No secrets, raw environment dumps, hidden chain-of-thought, raw provider transcripts or sensitive evidence bodies in code, state, logs, fixtures, docs or responses.
- Models propose candidates/observations; deterministic Python owns hard constraints, evidence sufficiency, budgets, authoritative energy and terminal disposition.
- Every fallback or escalation is explicit and ledgered.
- Do not label Kimi K3 “best,” auto-routing “better,” multi-agent “superior,” or compaction “context-rot proof” without controlled benchmark evidence.
- Do not merge, rebase, reset, force-push or amend unless the user explicitly authorizes a verified recovery operation.

## Milestone 10 stop conditions

Stop and report instead of broadening scope when:

- branch, remote or working tree differs from the expected clean EACHAT state;
- the base graph/API specifications conflict;
- a provider adapter would require guessed model metadata;
- normal tests would require real credentials;
- implementation would silently change legacy routes;
- context or orchestration selectors would claim behavior not implemented;
- a gate fails.

## Required final report

Report:

- branch and before/after SHA;
- files changed;
- red tests and expected failures;
- implementation summary;
- focused and full gate results;
- provider calls made (expected zero for deterministic validation);
- secrets scan;
- docs updated;
- known limitations;
- exact next milestone.
