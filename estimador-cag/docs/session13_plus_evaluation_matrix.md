# Session 13 Plus deterministic evaluation matrix

Run the keyless contract matrix with:

```bash
uv run python -m evals.session13_plus_evaluation_matrix
uv run pytest -q tests/test_session13_plus_evaluation_matrix.py
```

It covers the required happy, evidence-risk, recovery, provider-failure,
tool-runtime, budget, human-review, restart, retrieval-parity, shadow, and
scenario-branch cases. Every row reports status, review requirement, Critic and
Boss outcomes, hours, provenance completeness, tool calls, iterations, latency,
cost, provider/fallback, and checkpoint count.

This is deliberately contract-level, deterministic CI evidence. `latency_ms`
and cost are zero for the local fake and must not be presented as live-provider
measurements. PostgreSQL process restart and browser operation are proven by
their dedicated integration and product-smoke evidence. The separate
credentialed runtime gate in `docs/session13_plus_live_runtime_evidence.md`
proves bounded DeepSeek/Kimi calls and a Logfire export request; this matrix
does not prove those external behaviors.
