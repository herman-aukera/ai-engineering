# EACHAT Final Project — Evaluation Guide

Status: deterministic implementation + LIVE-READY external evaluation.

## Golden set

`evals/energy_chat/final_project_golden.json` contains 11 fixed cases spanning supported Spring Boot/PostgreSQL/Docker support, cross-domain diagnosis, insufficient evidence, version conflict, L3 escalation and unsupported Kubernetes scope.

## Layer 1 — deterministic regressions

```bash
cd estimador-cag
DEEPSEEK_API_KEY=test KIMI_API_KEY=test OPENAI_API_KEY=test \
uv run pytest -q tests/test_eachat_final_project_*.py
```

This proves contracts and policy behavior without paid calls. It does not prove real-source acquisition or live answer quality.

## Layer 2 — persisted pgvector retrieval

After real ingestion:

```bash
cd estimador-cag
uv run python evals/energy_chat/final_project_eval.py --k 5
```

The report measures retrieval hit@5 only and writes `evals/energy_chat/final_project_retrieval_report.json` by default.

## Layer 3 — full live system

```bash
cd estimador-cag
uv run python evals/energy_chat/final_project_system_eval.py \
  --live \
  --provider openai \
  --effort balanced \
  --strict
```

The default timestamped report is written under `evals/energy_chat/results/`. It records no prompt or answer bodies.

Directly measured aggregates include:

- disposition accuracy
- clarification accuracy
- escalation accuracy
- retrieval hit@5 from graph-retained evidence
- evidence-reference and answer presence
- error rate
- mean/p95 latency
- provider calls
- mean/total estimated cost

`unsupported_claim_rate` is intentionally not fabricated. It remains unmeasured without a fixed semantic judge/manual rubric.

The live workflow uses `--strict`, so any disposition mismatch makes the proof run fail
even when provider calls themselves succeed.

## Monitoring evidence

During API/demo execution inspect authenticated:

```text
/energy-chat/v2/monitoring
/energy-chat/v2/monitoring/dashboard
```

The rolling monitor reports request/success/error count, error rate, mean/p95 wall latency, provider cost/request, provider calls and dispositions.

## Recommended submission evidence

For the exact final SHA retain:

1. green deterministic CI URL;
2. live RAG workflow URL;
3. ingestion artifact;
4. retrieval report;
5. one-answer live smoke artifact;
6. full 11-case live evaluation artifact;
7. monitoring screenshot during the 2–3 minute demo;
8. public URL or video link required by the assignment.

Do not merge deterministic and live evidence into a single claim. A green unit-test run is not a live-provider result, and a live smoke of one question is not the 11-case evaluation.
