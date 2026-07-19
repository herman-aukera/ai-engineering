# Energy-Aware portfolio architecture

Status: architecture and roadmap contract; implementation is product-local and evidence-gated.

Updated: 2026-07-19.

## Portfolio definition

The portfolio contains four related but independent workstreams:

| Workstream | Product responsibility | Boundary |
|---|---|---|
| EACHAT | General-purpose chat with candidate generation, evidence checks, critics, energy scoring, repair, refusal, clarification and escalation | No repository mutation, shell execution or IDE adapter ownership |
| EACODE | A local coding-governance layer between coding clients and model providers; evaluates proposed coding actions, patches and commands before they reach Claude Code, Cline, Aider or another client | No general chat UX ownership |
| EACORE | Shared contracts and architecture extracted only after EACHAT and EACODE independently prove equivalent semantics | May remain documentation-only until runtime extraction is justified |
| LIDR coursework / Session 13 Plus | Coursework implementation that must satisfy every mandatory requirement precisely, then add bounded extras with separate evidence | Domain-specific estimation schemas and arithmetic must not leak into product contracts |

The common design principle is:

```text
candidate -> evidence/constraint critics -> energy score -> deterministic decision
          -> accept | repair | clarify | reject | refuse | escalate
          -> append-only ledger -> safe projection
```

Session 13 multi-agent orchestration is a useful architecture source for the products, but not a package to copy wholesale. The reusable parts are typed shared state, explicit nodes, bounded retries, critic/boss separation, safe audit projections, persistence gates, human revision guards and deterministic routing. Estimation-specific arithmetic, budget schemas and teacher-domain terminology remain coursework-local.

## Provider and model strategy

The products must use a provider-neutral model catalog. User-facing choices are stable capability profiles; provider model IDs remain configuration discovered and verified at runtime.

### User-facing provider choices

| Choice | Product role | Current policy |
|---|---|---|
| `auto` | Energy-aware router chooses within explicit cost, latency, quality and privacy budgets | Recommended future default after routing evals exist |
| `deepseek` | Cost-effective default | Current implementation default; use DeepSeek V4 Flash/Pro according to effort profile |
| `kimi` | User-preferred quality candidate | Kimi K3 is the intended flagship, but “best” is a hypothesis until product benchmarks prove it |
| `openai` | Premium option | GPT-5.6 family; higher budget ceiling and explicit user consent required |

### Common effort selector

Expose one cross-provider selector:

```text
fast | balanced | max
```

Provider adapters translate that stable profile into verified provider capabilities:

| Provider | `fast` | `balanced` | `max` |
|---|---|---|---|
| DeepSeek | V4 Flash, non-thinking | V4 Flash thinking or V4 Pro non-thinking, chosen by policy | V4 Pro thinking |
| Kimi | verified fast K3 capability when the API catalog exposes it | K3 default capability | verified deep-reasoning/agentic K3 capability when exposed |
| OpenAI | GPT-5.6 Luna | GPT-5.6 Terra with medium effort | GPT-5.6 Sol with max effort |

Do not hard-code guessed Kimi K3 API identifiers or reasoning-mode names. The public Kimi K3 release is confirmed, but the product must discover the account-visible model ID and supported parameters through the provider model endpoint or an allow-listed deployment configuration before enabling it.

OpenAI GPT-5.6 uses the current Luna, Terra and Sol capability tiers. Do not use obsolete generic UI labels such as `nano` or `instant` as API model IDs. `ultra` is an optional capability, not part of the common three-level selector, and may be exposed only when the account and endpoint explicitly support it.

### Routing rule

The energy-aware controller, not the provider, owns escalation:

1. Resolve privacy, evidence, modality and tool requirements.
2. Select the cheapest compatible model profile within the user budget.
3. Generate one candidate.
4. Run deterministic critics and compute authoritative energy.
5. Repair on the same profile when safe and within budget.
6. Escalate effort or provider only when unresolved hard constraints, energy, risk or quality policy justify it.
7. Record requested provider, served provider, model, effort, fallback, cost, latency and escalation reason in the decision ledger.
8. Never silently downgrade privacy, evidence or safety requirements.

## Context compaction strategy

Reasoning effort and context compaction are separate selectors.

Expose:

```text
minimal | balanced | max
```

| Context profile | Retained context | Intended use |
|---|---|---|
| `minimal` | current task brief, hard constraints, pinned facts, unresolved decisions, latest relevant turns and evidence IDs | low latency/cost; narrow tasks |
| `balanced` | structured rolling summary, pinned facts, recent raw window, evidence/decision ledger references and unresolved work | default |
| `max` | larger recent raw window, hierarchical summaries, selected source excerpts, complete unresolved-decision history and audit references | difficult long-horizon work; higher cost |

Compaction must be hierarchical, typed and provenance-preserving:

- never summarize away hard constraints, secrets policy, IDs, accepted architecture decisions, failing gates or unresolved questions;
- keep pinned facts separate from generated summaries;
- store summary version, source range, token counts, content hash and creation policy;
- retain exact evidence and ledger references even when prose is compressed;
- preserve a recent raw-message window;
- detect contradiction or summary drift and rebuild from the previous trusted checkpoint;
- never persist hidden chain-of-thought;
- allow user-triggered recompression and rollback to the preceding summary revision.

Product-specific retention:

- EACHAT pins user intent, stable preferences, evidence references, decisions, limitations and open questions.
- EACODE pins repository/branch/SHA, working-tree state, spec constraints, changed files, test/CI evidence, command safety state, rollback point and unresolved failures.
- Session 13 pins graph revision, checkpoint identity, scenario inputs, authoritative calculations, critic/boss findings and human-gate state.

## Multi-agent adoption

Multi-agent orchestration is useful when independent work can reduce risk or latency. It is not the default for every request.

Recommended modes:

```text
single | critic | committee | adaptive
```

- `single`: one candidate plus deterministic policy; cheapest path.
- `critic`: one generator and one or more independent critics; recommended default for meaningful product work.
- `committee`: multiple candidates or specialist agents plus deterministic adjudication; high-value or ambiguous work only.
- `adaptive`: begin single/critic and expand only when energy, risk or uncertainty crosses a threshold.

The boss/adjudicator must not merely be another unconstrained model. Deterministic policy owns hard constraints, budgets, quorum, retry ceilings, evidence sufficiency and terminal disposition.

## Evidence and claim discipline

- Provider marketing is not a product benchmark.
- Kimi K3 may be labelled `quality_candidate` or `user_preferred`; do not label it objectively best until controlled EACHAT/EACODE evals establish that result.
- GPT-5.6 may be labelled `premium`; cost and model availability must come from current provider metadata/configuration.
- Model names, prices, context windows and supported reasoning parameters are temporal facts and must be revalidated before release.
- Deterministic CI uses fake providers only. Credentialed provider smoke tests remain opt-in and sanitized.
- Shared EACORE runtime extraction remains blocked until at least two products prove stable equivalent contracts and compatibility tests.

## Current official model notes

As of 2026-07-19:

- DeepSeek documents V4 Flash and V4 Pro, both with 1M context and thinking/non-thinking support.
- Moonshot AI publicly announces Kimi K3 as a 2.8T-parameter, natively multimodal, 1M-context model aimed at long-horizon coding, knowledge work and deep reasoning. Public API identifiers and mode parameters must still be verified against the account-visible API catalog before implementation.
- OpenAI documents GPT-5.6 Luna, Terra and Sol, with user-selectable effort and premium max/optional ultra capabilities subject to product/account availability.

Official sources:

- https://api-docs.deepseek.com/quick_start/pricing
- https://www.moonshot.ai/
- https://openai.com/index/gpt-5-6/
