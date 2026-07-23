# Session 12 Live Provider Planning Smoke Summary

Scope: manual opt-in live provider planning smoke.

Evidence level: live provider/manual integration evidence.

| Provider | Tier | Model | Temperature | Step count | Tools |
|---|---|---|---:|---:|---|
| deepseek | cheap | `deepseek-v4-flash` | 0.0 | 5 | search_budgets, calculate_estimate, validate_estimate |
| deepseek | final | `deepseek-v4-pro` | 0.0 | 5 | search_budgets, calculate_estimate, validate_estimate |
| kimi | cheap | `kimi-k2.6` | 1.0 | 5 | search_budgets, calculate_estimate, validate_estimate |
| kimi | final | `kimi-k2.7-code` | 1.0 | 5 | search_budgets, calculate_estimate, validate_estimate |
| openai | cheap | `gpt-5.4-mini` | 0.0 | 5 | search_budgets, calculate_estimate, validate_estimate |
| openai | final | `gpt-5.5` | default | 5 | search_budgets, calculate_estimate, validate_estimate |

Notes:
- These smokes validate live provider planning and JSON normalization.
- They do not execute the full agent loop tools.
- Raw provider artifacts were kept outside the repository in `/tmp/session12_live_smoke`.
- The expected tool sequence is `search_budgets`, `calculate_estimate`, `validate_estimate`.
- `default` means the script intentionally omitted `temperature` because the provider/model rejected explicit non-default values.
