# Session 11 RAGAS Baseline

Status: committed live OpenAI baseline

## Scope

This report is the Session 11 generation-quality baseline. It uses the deterministic RAGAS sample contract derived from the Session 10 golden set and the committed live OpenAI RAGAS result JSON.

Official baseline configuration:

- Judge provider: openai
- Official baseline: True
- Chat judge model: gpt-4o-mini
- Embedding model: text-embedding-3-small
- Sample count: 5
- Isolated scorer profile: ragas==0.1.21, datasets==5.0.0, langchain-community==0.2.19, langchain-openai

## Metrics table

| query | faithfulness | answer_relevancy | context_precision | context_recall |
| --- | ---: | ---: | ---: | ---: |
| Q1 | 1.000 | 0.273 | 1.000 | 1.000 |
| Q2 | 1.000 | 0.322 | 1.000 | 1.000 |
| Q3 | 1.000 | 0.282 | 1.000 | 1.000 |
| Q4 | 1.000 | 0.243 | 1.000 | 1.000 |
| Q5 | 1.000 | 0.488 | 1.000 | 1.000 |
| average | 1.000 | 0.322 | 1.000 | 1.000 |

## Citation verification summary

- Line-level source references are part of the estimate schema.
- Grounded lines require real source references.
- Unsupported lines must be marked as insufficient/no-data instead of inventing hours.
- The planted dangling citation demo verifies that a cited chunk id not present in the retrieved context is detected as a quality failure.

Committed evidence:

- `tests/test_session11_citation_verification.py`
- `tests/test_session11_dangling_demo.py`
- `scripts/demo_verify_citations_s11.py`
- `evals/session11_generation/ragas_results_openai_s11.json`

## Suspicious-number note

The most suspicious result is that faithfulness, context precision, and context recall are all effectively perfect while answer_relevancy is much lower. This likely happens because the deterministic answer is tightly grounded in the retrieved source text, but its wording is short and component-centric rather than naturally answering the query as a user-facing estimate. The numbers should be treated as a baseline for the wired pipeline, not as proof of production-grade generation quality.

## Known limitations

- The corpus and golden set are small, so the metrics are course-scale baseline evidence.
- DeepSeek and Kimi judge dry-runs are supported, but live comparison scoring hit provider API limits around multi-completion requests from the RAGAS/LangChain stack.
- The official submitted baseline is OpenAI because the task requires OpenAI embeddings with `text-embedding-3-small`.

## Reproduction commands

Dry-run contract:

    uv run python evals/session11_generation/run_ragas_s11.py --dry-run --judge-provider openai

Live OpenAI baseline with isolated RAGAS profile:

    uv run --no-project --with "ragas==0.1.21" --with "datasets==5.0.0" --with "langchain-community==0.2.19" --with "langchain-openai" python evals/session11_generation/run_ragas_s11.py --live --judge-provider openai --output-path evals/session11_generation/ragas_results_openai_s11.json
