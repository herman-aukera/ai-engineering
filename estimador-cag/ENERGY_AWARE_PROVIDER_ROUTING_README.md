# EACHAT provider routing and context selectors

Status: design contract and implementation roadmap. The current live runtime still uses the existing DeepSeek/Kimi baseline seam; the provider-neutral selector described here is not yet a completed public feature.

## Product intent

EACHAT is a general-purpose Energy Aware Chat application. It should resemble a provider-flexible ChatGPT-style interface while placing a deterministic evidence/constraint engine behind every model candidate:

```text
user request
-> provider/model selection
-> candidate
-> evidence and critic panel
-> energy score
-> accept | repair | clarify | reject | refuse | escalate
-> Decision Ledger and Energy Card
-> safe final answer
```

The model is a candidate generator. It does not own hard constraints, evidence sufficiency, energy, budgets or final disposition.

## Intended selectors

### Provider

```text
auto | deepseek | kimi | openai
```

Current product policy:

- `deepseek`: default cost-effective provider;
- `kimi`: user-preferred quality candidate, targeting Kimi K3 after API capability verification;
- `openai`: premium provider, targeting the GPT-5.6 family;
- `auto`: future energy-aware routing after controlled provider evals exist.

Do not claim Kimi is objectively best before benchmark evidence. Do not silently route to a more expensive provider.

### Effort

```text
fast | balanced | max
```

Intended mapping:

| Provider | Fast | Balanced | Max |
|---|---|---|---|
| DeepSeek | V4 Flash non-thinking | V4 Flash thinking or V4 Pro non-thinking | V4 Pro thinking |
| Kimi | verified K3 fast capability | K3 default capability | verified K3 deep/agentic capability |
| OpenAI | GPT-5.6 Luna | GPT-5.6 Terra, medium effort | GPT-5.6 Sol, max effort |

Kimi K3 API model IDs and supported reasoning parameters must be discovered or allow-listed from official provider metadata. Guessed IDs are forbidden.

### Context

```text
minimal | balanced | max
```

- `minimal`: task brief, hard constraints, pinned facts, unresolved work, recent relevant turns and evidence IDs.
- `balanced`: structured rolling summary plus pinned facts, recent raw turns, evidence and ledger references. Default.
- `max`: larger raw window and hierarchical summaries for difficult long-horizon work.

Reasoning effort and context retention are independent. A user may select fast reasoning with max context or max reasoning with minimal context.

### Orchestration

```text
single | critic | committee | adaptive
```

- `single`: one candidate and deterministic policy.
- `critic`: one candidate plus independent critics; intended normal Energy Aware path.
- `committee`: multiple candidates/specialists plus deterministic adjudication; expensive and bounded.
- `adaptive`: starts cheap and expands only when energy/risk/uncertainty requires it.

## Milestone boundary

Milestone 10 adds the graph-backed API. It must be provider-neutral in its contracts, but it must not expand into three new credentialed provider integrations.

Milestone 10 may add validated selection fields and safe response metadata:

```text
provider_preference
effort_profile
context_profile
orchestration_mode
requested_model_profile
served_model_profile
fallback_used
routing_reason
```

The deterministic route remains keyless. The bounded live route may continue using the existing provider seam. Kimi K3 and GPT-5.6 adapters, model discovery, UI selectors and provider comparison benchmarks belong to later dedicated slices unless the repository already proves a smaller safe implementation.

## Canonical documents

Read:

```text
../docs/ENERGY_AWARE_PORTFOLIO_README.md
docs/energy_aware_chat_provider_context_spec.md
docs/energy_aware_chat_milestone_10_provider_context_addendum.md
docs/energy_aware_chat_milestone_10_graph_api_spec.md
docs/energy_aware_chat_sdd.md
```

Claude Code also reads the branch-scoped repository `CLAUDE.md`.

## Security and CI

- No API keys in state, prompts, docs, fixtures, logs or commits.
- Normal CI uses deterministic/fake providers only.
- Real provider smoke is explicit, manual, bounded and sanitized.
- Provider selection must respect privacy, data residency, modality, tool and cost constraints.
- Every model escalation must be ledgered.

## Current model verification note

As of 2026-07-19, official sources confirm DeepSeek V4 Flash/Pro, the public Kimi K3 release and the GPT-5.6 Luna/Terra/Sol family. Kimi K3 API identifiers and fine-grained modes were not yet established by the documentation audit and therefore remain runtime-discovery requirements rather than hard-coded contracts.
