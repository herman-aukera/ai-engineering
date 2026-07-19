# CLAUDE.md — EACORE Working Instructions

## Scope

You are working inside the EACORE neutral-kernel incubator.

EACORE may own neutral contracts, compatibility rules, deterministic energy
arithmetic, transition invariants, references, audit envelopes, documentation,
and test fixtures.

EACORE must not own provider SDK clients, credentials, product prompts,
LangGraph topology, FastAPI, Streamlit, retrieval, shell execution, repository
mutation, product decision enums, product weights, or product UI.

## Portfolio definitions

- EACODE is an Energy-Aware coding gateway/service. It may sit between model
  providers and Claude Code, Cline, Aider, IDEs, or local clients. Its coding
  critics and deterministic Boss evaluate, repair, reject, escalate, authorize,
  and audit coding proposals. It owns command and repository safety.
- EACHAT is an Energy-Aware general-purpose chat product. It generates or
  receives answer candidates, runs parallel critics, calculates constraint
  energy, repairs when useful, and renders a user-facing Energy Card.
- Session 13 Plus and later coursework must complete mandatory teacher
  requirements first and prove them. Extras are allowed only as bounded,
  reversible, separately evidenced slices.
- EACORE is documentation-first and extraction-gated. Similar names are not
  sufficient reason to share runtime code.

## Provider policy

Default portfolio preference:

1. DeepSeek for default cost/performance.
2. Kimi K3 for frontier open-model work.
3. GPT-5.6 for premium reference, difficult escalation, or comparative evals.

Never hardcode an unverified model identifier or capability.

Use a capability registry with:

- provider;
- exact model ID;
- supported modalities;
- supported reasoning efforts;
- context length;
- tool support;
- structured-output support;
- pricing snapshot and effective date;
- availability and access status;
- provider-session compatibility;
- deprecation date.

Normalized user selectors:

- provider: auto, deepseek, kimi, openai;
- execution profile: instant, balanced, max;
- reasoning profile: minimal, medium, max;
- context profile: minimal, medium, max.

Current verified mappings:

- DeepSeek instant: V4 Flash, non-thinking.
- DeepSeek balanced: V4 Flash, thinking, high effort.
- DeepSeek max: V4 Pro, thinking, max effort.
- Kimi K3: max effort only at launch. Low/high are future capabilities until
  verified as available.
- GPT-5.6 instant: Luna.
- GPT-5.6 balanced: Terra, normally medium effort.
- GPT-5.6 max: Sol, normally max effort.
- GPT-5.6 ultra is an explicit multi-agent mode and must not be silently mapped
  from max.

Unsupported combinations must produce one explicit result:

- exact;
- repaired with a visible explanation;
- fallback with user/policy permission;
- rejected.

## Context compaction

Never use a free-form summary as the only memory.

Preserve a structured compaction record containing:

- objective;
- accepted decisions;
- hard constraints;
- current repository/product state;
- evidence references;
- unresolved tasks;
- active risks;
- recent raw-turn window;
- provider/model/session identity;
- compaction profile;
- token counts before/after;
- summary version and hash;
- rollback and next action.

Do not switch providers or models mid-session without an explicit compatibility
handoff. For Kimi K3, prefer a fresh session because its current release expects
preserved thinking history.

## Multi-agent rule

Use multiple agents only when work can be decomposed into independent,
evidence-producing subproblems and a deterministic aggregator can resolve them.

Good uses:

- EACODE: specification, tests, security, architecture, rollback, and diff-scope
  critics;
- EACHAT: grounding, safety, instruction-following, completeness, consistency,
  and usefulness critics;
- coursework: parallel nodes, bounded retries, critic/Boss orchestration, and
  human gates;
- evaluation: compare provider candidates under identical constraints.

Do not use multi-agent orchestration for simple requests, as theatre, or when
the subagents share the same unsupported assumption.

## Engineering rules

- Inspect repository state before implementation.
- Write a red test before shared runtime changes.
- Keep provider integrations product-local until at least two products prove
  equivalent contracts.
- Preserve deterministic policy authority.
- Do not expose hidden reasoning.
- Do not print or persist API keys.
- Do not merge the EACORE draft PR.
- Do not modify EACHAT, EACODE, Session 13 Plus, or main from this branch.
