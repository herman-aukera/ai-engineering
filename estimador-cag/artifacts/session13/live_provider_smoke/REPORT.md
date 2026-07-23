# Session 06 CAG stress report

This report is generated from `evals/stress/results.csv`. It measures the existing CAG baseline; it does not optimize prompts, memory limits, provider strategy, or attachment limits.

## Summary table

| scenario | rows | p50 latency ms | p95 latency ms | accumulated cost usd | exact hit rate | semantic hit rate | fact recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| contradiction | 6 | 12526.0 | 44457.0 | 0.016833 | 0.00% | 0.00% | 0.00% |
| growing | 6 | 10215.0 | 12202.0 | 0.011042 | 0.00% | 0.00% | 0.00% |
| pivot | 6 | 9263.5 | 12298.0 | 0.010982 | 0.00% | 0.00% | 0.00% |

## Curve 1: latency vs tokens

| tokens_in bucket | rows | p50 latency ms | p95 latency ms |
| --- | --- | --- | --- |
| 1000-1999 | 3 | 12202.0 | 12298.0 |
| 2000-2999 | 9 | 9646.0 | 19703.0 |
| 3000-3999 | 6 | 10065.5 | 44457.0 |

## Curve 2: cumulative cost vs turn

| turn | average turn cost usd | cumulative average cost usd |
| --- | --- | --- |
| 1 | 0.00240967 | 0.00240967 |
| 2 | 0.00190778 | 0.00431744 |

## Curve 3: recall vs N

| N | rows | fact recall |
| --- | --- | --- |
| 1 | 9 | 0.00% |

## Reading

The most important quantitative claim in this run is: at turn N=1, fact recall is 0.00%. Another cost claim is: turn 2 average cost is 0.79 times turn 1 average cost. These claims are intentionally mechanical and reproducible from the CSV, so they can be challenged directly during the live review.

Latency should be read together with `tokens_in` and `attachments_total_chars`, not in isolation. When the 100 KB synthetic attachments are used, extraction and prompt inflation can dominate the turn even if the model path is deterministic. For a live provider run, this same curve is the early warning line for the moment where CAG stops being cheap enough and RAG becomes architecturally attractive.

## Limitations

If `STRESS_FAKE_PROVIDER=true` was used on the backend, token, cost, and latency numbers are deterministic local smoke values, not live provider economics. The runner and observation contract are still valid; rerun against live keys before using the report as a production benchmark.
