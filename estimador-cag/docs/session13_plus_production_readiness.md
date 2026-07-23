# Session 13 Plus — Provider and Production Readiness

**Branch:** `gg-session-13/plus-production-readiness`  
**Base:** promoted Session 13 Plus stabilization head  
**Working mode:** evidence-gated continuation; PR #10 remains draft and unmerged

## 1. Readiness dimensions

Readiness is not one Boolean. The implementation tracks five independent claims:

| Dimension | Required evidence |
|---|---|
| Deterministic implementation | Ruff, compilation, full deterministic tests, diff and secret gates |
| Live provider reachability | Exact-head calls using repository secrets, sanitized results |
| Provider contract verification | Exact text, structured JSON, and tool calling on the same cases |
| Auto calibration | Complete matched benchmark snapshot for every required provider |
| Deployment readiness | Built production container, initialized PostgreSQL checkpointers, `/health` and `/ready` green |

A green deterministic suite does not imply live reachability. A successful live call does not imply benchmark calibration. A running process does not imply dependency readiness.

## 2. Runtime provider routing

Every leaf graph stage is classified as:

- `model`;
- `deterministic`;
- `retrieval`;
- `human`.

Model-backed stages currently include:

- semantic classification;
- requirement extraction;
- component classification;
- selective recovery;
- human-requested recovery.

One checkpoint-safe `StageRouteDecision` is resolved for every leaf stage. The route is bound through a context variable only during that node invocation. The same bound route controls the shared structured provider and the bounded recovery agent. Non-model stages record truthful routes such as `python`, `pgvector`, or `human_gate` and do not call an LLM.

Route evidence contains provider, model, effort, source, complexity, and stable reason codes. It never contains credentials, raw provider output, or hidden reasoning.

## 3. Common reasoning intent

The product selector remains:

```text
minimal | medium | max
```

Adapters map that intent to provider-supported behavior:

| Provider | Minimal | Medium | Max |
|---|---|---|---|
| DeepSeek | thinking disabled | high | max |
| OpenAI GPT-5.6 | low | medium | max |
| Kimi K3, when product API verifies `k3` | low | high | max |
| Other verified Kimi product models | high | high | high |

Unsupported combinations fail before the network call.

Kimi Code membership model IDs are not assumed to be valid product API model IDs. Product routing uses the Kimi Platform base URL and model catalogue returned to the configured product API key.

## 4. Matched benchmark contract

The live benchmark executes the same three cases for every configured route:

1. exact visible text;
2. exact structured JSON;
3. one typed tool call with exact arguments.

For each route it records:

- provider/model/effort;
- pass/fail by case;
- schema pass rate;
- tool pass rate;
- median latency;
- input/output token counts;
- median cost when provider/LiteLLM metadata supports it;
- sanitized exception type and HTTP status only.

It does not record API keys, private project prompts, complete provider responses, or stack traces.

## 5. Auto policy

`Auto` fails closed without a complete matched snapshot covering DeepSeek, Kimi/Moonshot, and OpenAI.

Once complete:

- `minimal` chooses the cheapest measured contract-passing route above the minimum quality threshold;
- `medium` uses a versioned utility weighting quality, schema/tool reliability, latency, and cost;
- `max` chooses the highest-quality contract-passing route, with cost and latency as deterministic tie-breakers.

A route with missing cost cannot win the cost-first policy. A provider with unavailable credentials, contract failures, or incomplete coverage cannot make `Auto` eligible.

## 6. Operational probes

### `/health`

Liveness only. It indicates that the HTTP process is running.

### `/ready`

Returns HTTP 503 until:

- the mandatory graph runtime is initialized;
- the reviewed graph runtime is initialized;
- at least one non-placeholder provider credential is configured.

The response separately reports:

- configured provider names;
- benchmark snapshot version;
- whether Auto is eligible;
- safe reason codes for failed checks.

No credential, database URL, Redis URL, DSN, or service object is serialized.

## 7. Container gate

The production container:

- uses Python 3.11 slim;
- installs the frozen production dependency set;
- runs as a non-root user;
- starts Uvicorn with proxy headers;
- receives all secrets at runtime;
- excludes tests, artifacts, local environments, and `.env` files from the build context.

The container workflow starts PostgreSQL with pgvector and Redis, launches the exact image, and requires both `/health` and `/ready` to return 200. It also asserts that readiness output contains no secret-bearing fields.

## 8. Rollback

This work remains isolated on PR #16. Rollback is deletion or closure of the readiness branch/PR; the promoted `gg-session-13/plus` head and PR #10 remain unchanged.

Within the runtime, explicit provider selection can be changed without modifying graph topology. `Auto` can be disabled by removing the benchmark snapshot path. The existing deterministic and reviewed graph contracts remain checkpoint compatible.

## 9. Claim boundary

Do not claim these until exact evidence exists:

- all three providers are reachable;
- Kimi K3 is available through the configured product API account;
- the matched benchmark is complete;
- Auto is cheapest or best;
- the container has been deployed to a real target;
- production SLOs, load, backup, recovery, and security review are complete.

The final handoff must report each dimension independently and identify credential/account blockers rather than labelling them code defects.
