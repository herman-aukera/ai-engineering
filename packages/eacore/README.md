# EACORE 0.1 — Neutral Kernel

EACORE is a framework-neutral Python package and architecture layer for strict
Energy-Aware contracts, deterministic energy arithmetic, universal transition
invariants, canonical serialization, integrity helpers, append-only reference
ledgers, and cross-product design agreements.

It deliberately does **not** contain LangGraph, FastAPI, Streamlit, provider
SDKs, retrieval, shell execution, repository mutation, product policies, or
product-specific decision enums.

## Portfolio role

EACORE is the optional common layer between:

- **EACODE** — a local coding gateway that can evaluate and repair model output
  before returning it to Claude Code, Cline, Aider, IDEs, or other coding clients;
- **EACHAT** — an Energy-Aware general-purpose chat product with candidate
  generation, parallel critics, deterministic Boss decisions, repair, evidence,
  provider selection, context compaction, and an Energy Card;
- **Session 13 Plus and later coursework** — the learning and evaluation
  laboratory where mandatory requirements are completed first, then improved
  through bounded, evidence-backed extras;
- **EACORE** — shared contracts, architectural decisions, compatibility
  fixtures, and documentation only where reuse is proven. Shared code is
  optional rather than forced.

## Boundary

```text
product request
→ product-owned provider selector and adapter
→ product candidate
→ product-owned critics and policy
→ EACORE references, observations, energy arithmetic, and audit envelopes
→ product-owned Boss decision and repair loop
→ product graph/API/UI/tool action
```

Provider clients, credentials, model prompts, routing weights, product-specific
fallbacks, and execution remain product-owned.

## Multi-provider direction

The documented provider policy is:

| Provider | Portfolio role | Current preferred models |
|---|---|---|
| DeepSeek | Default cost/performance route | `deepseek-v4-flash`, `deepseek-v4-pro` |
| Kimi | Frontier open-model route | `kimi-k3` |
| OpenAI | Premium reference and escalation route | GPT-5.6 Luna, Terra, Sol |

The user-facing selector is normalized rather than exposing invalid combinations:

- provider: `auto`, `deepseek`, `kimi`, `openai`;
- execution profile: `instant`, `balanced`, `max`;
- reasoning profile: `minimal`, `medium`, `max`;
- context profile: `minimal`, `medium`, `max`.

Every product must resolve these values against a versioned provider-capability
registry. Unsupported combinations must be repaired transparently, routed only
with permission, or rejected. They must never be silently invented.

Kimi K3 launched with max reasoning effort. Moonshot announced low and high
effort for later updates; they are not treated as available until capability
discovery or verified configuration proves them.

See:

- `docs/PROVIDER_ROUTING_CONTEXT_COMPACTION_AND_MULTI_AGENT.md`
- `specs/0002-provider-routing-context-compaction/SPEC.md`
- `CLAUDE.md`

## Context compaction

All products should use structured, versioned compaction to limit context rot.
Compaction preserves:

- accepted decisions and invariants;
- current product and branch state;
- evidence references;
- unresolved work and risks;
- recent raw turns;
- provider/model/session identity;
- rollback and next action;
- summary provenance, version, and hash.

A provider switch must normally start a new model session or a compatibility
handoff. This is especially important for Kimi K3 because Moonshot warns that
switching into K3 mid-session without preserved thinking history can destabilize
generation quality.

## Install for development

    python -m pip install -e ".[dev]"
    python -m pytest

## Claim boundary

EACORE 0.1 is a neutral-kernel incubator. It does not claim that Session 13
Plus, EACHAT, or EACODE already consume this package. Provider routing, context
compaction, and multi-agent orchestration are documented in Spec 0002 but are
not yet implemented as shared runtime code.
