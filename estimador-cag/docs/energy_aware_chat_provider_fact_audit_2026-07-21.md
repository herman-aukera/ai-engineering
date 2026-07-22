# EACHAT provider fact audit — 2026-07-21

Status: verified source record for Phase 6. Adapter code remains live-unproven until dedicated credentialed smoke evidence exists.

## Surface separation

| Provider | Surface | Model IDs | EACHAT eligibility |
|---|---|---|---|
| DeepSeek | OpenAI-compatible product API | `deepseek-v4-flash`, `deepseek-v4-pro` | eligible |
| Kimi Platform | OpenAI-compatible product API | `kimi-k3` | eligible |
| Kimi Code | Anthropic-compatible coding membership | `k3`, `kimi-for-coding`, `kimi-for-coding-highspeed` | not eligible as EACHAT product credentials |
| OpenAI | Responses API preview | `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol` | eligible, preview |

The coding model used to implement EACHAT is not evidence that EACHAT has a product-runtime adapter for that provider.

## Verified DeepSeek facts

Official source:

```text
https://api-docs.deepseek.com/quick_start/pricing
```

Both V4 Flash and V4 Pro document:

- 1,000,000-token context;
- up to 384,000 output tokens;
- tools, JSON output, streaming, thinking/non-thinking operation;
- prompt caching.

Current prices recorded in the catalog, per million tokens:

| Model | Input cache miss | Cached input | Output |
|---|---:|---:|---:|
| V4 Flash | $0.14 | $0.0028 | $0.28 |
| V4 Pro | $0.435 | $0.003625 | $0.87 |

## Verified Kimi facts

Kimi Platform source:

```text
https://platform.kimi.ai/docs/guide/kimi-k3-quickstart
```

Kimi K3 product API facts:

- model ID `kimi-k3`;
- base URL `https://api.moonshot.ai/v1`;
- 1,000,000-token context;
- maximum output 1,048,576 tokens;
- reasoning effort `low`, `high`, or `max`;
- OpenAI-compatible API;
- $3 input, $0.30 cached input, $15 output per million tokens.

Kimi Code source:

```text
https://www.kimi.com/code/docs/en/kimi-code/models.html
```

Kimi Code is a distinct membership surface. Its IDs are not Kimi Platform API IDs and must not be accepted as arbitrary EACHAT model input.

## Verified OpenAI facts

Official sources:

```text
https://openai.com/index/gpt-5-6/
https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt
```

Preview API IDs and prices, per million tokens:

| Model | Input | Output |
|---|---:|---:|
| `gpt-5.6-luna` | $1.00 | $6.00 |
| `gpt-5.6-terra` | $2.50 | $15.00 |
| `gpt-5.6-sol` | $5.00 | $30.00 |

The cited preview documents do not establish exact context-window or maximum-output values. Those fields remain `null` rather than guessed.

## Adapter claim boundary

Implemented and keyless-tested:

- provider-neutral candidate transport contract;
- separate Kimi Platform and OpenAI adapter boundaries;
- deterministic effort mapping;
- sentinel credential rejection;
- no adapter-internal provider fallback;
- requested/served provider and model metrics;
- fake transport injection for CI.

Not yet proven:

- successful live Kimi Platform call;
- successful live GPT-5.6 Responses API call;
- successful live DeepSeek through the new catalog transport;
- provider quality superiority;
- calibrated `auto` routing.

Normal CI must remain external-provider-free. Credentialed smoke tests require explicit secrets, bounded spend, sanitized fixtures, and a separate evidence gate.
