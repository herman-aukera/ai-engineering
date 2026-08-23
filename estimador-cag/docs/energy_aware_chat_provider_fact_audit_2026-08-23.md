# EACHAT provider fact audit — 2026-08-23

Status: current official-source record for provider catalog `2.1.0`.

This audit supersedes the temporal provider facts in
`energy_aware_chat_provider_fact_audit_2026-07-21.md`. The July 21 document
remains historical evidence; it must not be used as current pricing,
availability, or model-limit authority.

Adapter code remains **live-unproven** until dedicated credentialed smoke
evidence exists. This document verifies published provider facts, not live
credential success or model quality.

## Freshness contract

Temporal provider facts are verified on `2026-08-23` and must be re-audited no
later than `2026-09-22`.

The executable catalog exposes:

- `CATALOG_VERIFIED_AT = "2026-08-23"`;
- `CATALOG_REVIEW_BY = "2026-09-22"`;
- `CATALOG_MAX_AGE_DAYS = 30`;
- `assert_catalog_fresh(...)`, which fails closed after the review window.

The normal deterministic test suite calls the freshness guard using the CI
calendar date. Therefore a source-perfect but expired provider catalog cannot
remain silently GREEN. The guard does **not** claim that vendor facts cannot
change sooner; material vendor changes still require an immediate source
refresh.

## Surface separation

| Provider | Surface | Model IDs | EACHAT eligibility |
| --- | --- | --- | --- |
| DeepSeek | OpenAI-compatible product API | `deepseek-v4-flash`, `deepseek-v4-pro` | eligible |
| Kimi Platform | OpenAI-compatible product API | `kimi-k3` | eligible |
| Kimi Code | coding membership API | `k3`, `kimi-for-coding` | not eligible as EACHAT product credentials |
| OpenAI | Responses API | `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol` | eligible, GA/current API models |

The coding model used to implement EACHAT is not evidence that EACHAT has a
product-runtime credential or entitlement for that provider.

## DeepSeek — verified 2026-08-23

Official source:

```text
https://api-docs.deepseek.com/quick_start/pricing
```

Published current facts retained in the catalog:

- base URL `https://api.deepseek.com`;
- model IDs `deepseek-v4-flash` and `deepseek-v4-pro`;
- 1,000,000-token context;
- maximum 384,000 output tokens;
- tool calls and JSON output;
- thinking and non-thinking operation;
- prompt caching.

Current prices per million tokens:

| Model | Input cache miss | Cached input | Output |
| --- | ---: | ---: | ---: |
| V4 Flash | $0.14 | $0.0028 | $0.28 |
| V4 Pro | $0.435 | $0.003625 | $0.87 |

## Kimi Platform — verified 2026-08-23

Official sources:

```text
https://platform.kimi.ai/docs/guide/kimi-k3-quickstart
https://platform.kimi.ai/
```

Published current facts retained in the catalog:

- model ID `kimi-k3`;
- base URL `https://api.moonshot.ai/v1`;
- 1,000,000-token context;
- `max_completion_tokens` defaults to 131,072 and can be set up to 1,048,576;
- reasoning effort `low`, `high`, or `max`;
- image and video input;
- streaming;
- strict structured output;
- tools and automatic context caching;
- minimum successful top-up of USD 1 for K3 access.

Current prices per million tokens:

| Input | Cached input | Output |
| ---: | ---: | ---: |
| $3.00 | $0.30 | $15.00 |

## Kimi Code — verified 2026-08-23

Official source:

```text
https://www.kimi.com/code/docs/en/kimi-code/models.html
```

Kimi Code remains a distinct membership surface and is not accepted as an
EACHAT product-runtime credential.

Current published boundaries represented by the catalog:

- `k3` = Kimi K3, available to Moderato and above;
- up-to-1M K3 context requires Allegretto or above;
- K3 reasoning supports `low`, `high`, and `max`;
- `kimi-for-coding` = Kimi K2.7 Code;
- K2.7 Code uses a 256K context window and Thinking ON;
- K2.7 Code is available to all Kimi Code members.

Kimi's docs also expose additional model IDs such as `k3-256k` and
`kimi-for-coding-highspeed`. They are intentionally not EACHAT product models;
the catalog is an allowlist, not an attempt to mirror every vendor SKU.

## OpenAI GPT-5.6 — refreshed 2026-08-23

Official sources:

```text
https://openai.com/index/gpt-5-6/
https://developers.openai.com/api/docs/models
https://developers.openai.com/api/docs/models/compare
```

The July 21 snapshot represented the limited-preview state. That is no longer
current. OpenAI moved the GPT-5.6 family to general availability on July 9 and
subsequently changed pricing.

Current published API facts represented by catalog `2.1.0`:

- `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol` are current API models;
- 1,050,000-token context window;
- 128,000 maximum output tokens;
- text and image input, text output;
- reasoning effort values `none`, `low`, `medium`, `high`, `xhigh`, and `max`;
- tools, structured outputs, streaming, and prompt caching.

Current prices per million tokens:

| Model | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| `gpt-5.6-luna` | $0.20 | $0.02 | $1.20 |
| `gpt-5.6-terra` | $2.00 | $0.20 | $12.00 |
| `gpt-5.6-sol` | $4.00 | $0.40 | $20.00 |

The Sol price is a temporal reduction announced on 2026-08-21. It must be
rechecked before the catalog review deadline or immediately if OpenAI changes
it earlier.

## Deterministic product mapping

The product's stable effort selector remains independent from changing vendor
names:

- DeepSeek: `fast` -> V4 Flash non-thinking; `balanced` -> V4 Flash thinking;
  `max` -> V4 Pro thinking.
- Kimi: all three profiles use K3 with product-controlled
  `reasoning_effort=low/high/max`.
- OpenAI: `fast` -> Luna; `balanced` -> Terra; `max` -> Sol with max reasoning.

These are **product routing decisions**, not vendor quality claims.

## Adapter and evidence boundary

Implemented and keyless-tested:

- provider-neutral candidate transport contract;
- Kimi Platform and OpenAI adapter boundaries;
- deterministic effort mapping;
- sentinel credential rejection;
- no adapter-internal provider fallback;
- requested/served provider and model metrics;
- fake transport injection for CI;
- source-dated capability allowlist;
- fail-closed temporal freshness deadline.

Not yet proven:

- successful current-head live Kimi Platform call;
- successful current-head GPT-5.6 Responses API call;
- successful current-head DeepSeek call through the catalog transport;
- provider quality superiority;
- calibrated `auto` routing;
- future vendor pricing or availability beyond the verification window.

Normal blocking CI remains external-provider-free. Credentialed smoke tests
require explicit secrets, bounded spend, sanitized fixtures, and a separate
evidence gate.
