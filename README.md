# AI Engineering Coursework

This repository contains the LIDR AI Engineering coursework.

## Current submission

Active project:

```text
estimador-cag/
```

Current branch:

```text
gg-pre-session-06-cag-stress-test
```

Current deliverable:

```text
Session 06 — CAG stress test baseline
```

## What this branch delivers

This branch adds a measurable stress baseline for the existing CAG system.

The goal is not to implement RAG yet. The goal is to measure where the current Cache Augmented Generation approach starts to degrade under longer conversations, larger attachments, and repeated load.

## Required deliverables

```text
estimador-cag/evals/stress/REPORT.md
estimador-cag/evals/stress/results.csv
```

The committed deterministic stress run contains 900 data rows plus a header.

```text
3 scenarios × 5 attachment sizes × 3 repeats × 20 turns = 900 rows
```

A bounded live provider smoke was also run locally with DeepSeek.

```text
3 scenarios × 5 attachment sizes × 3 repeats × 2 turns = 90 rows
```

The live smoke was kept as local validation evidence. It is not committed because the required deliverable is the report and CSV in evals/stress/.

## Main Session 06 additions

```text
estimador-cag/evals/stress/scenarios.py
estimador-cag/evals/stress/metrics.py
estimador-cag/evals/stress/run.py
estimador-cag/evals/stress/fixtures/build_pdfs.py
estimador-cag/evals/stress/results.csv
estimador-cag/evals/stress/REPORT.md
```

The stress runner measures:

* latency vs tokens
* cumulative cost vs turn
* fact recall vs conversation length
* attachment size impact
* cache hit kind
* tier used
* per turn token and cost metadata

## Instrumentation

Each conversational estimate exposes a turn_observed object with:

```text
turn_index
session_id
enriched_transcript_chars
attachments_total_chars
messages_in_window
anchors_count
summary_chars
tokens_in
tokens_out
cost_usd
latency_ms
cache_hit_kind
last_resolved_tier
```

## Validation

Local validation completed:

```text
ruff clean
py_compile clean
232 pytest tests passed
```

GitHub Actions normal CI is green.

Normal CI uses dummy provider keys for deterministic test execution. Real provider validation is available through the manual workflow:

```text
Live provider smoke - Estimador CAG
```

That workflow uses GitHub Actions repository secrets:

```text
DEEPSEEK_API_KEY
KIMI_API_KEY
```

## Repository map

```text
.
├── estimador-cag/      Active estimator project
├── docs/               Shared notes and sample files
├── scripts/            Helper scripts
├── docker-compose.yml  Root compose file
└── README.md           Current repository review guide
```

The old duplicate estimator/ project folder has been removed from this branch.

## Run the active project

```bash
cd /workspaces/ai-engineering

docker compose up -d redis

cd estimador-cag
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Run the mandatory stress runner

With the backend running:

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run python -m evals.stress.run \
  --http http://localhost:8000 \
  --scenarios growing,pivot,contradiction \
  --attachment-sizes 0,5,20,50,100 \
  --repeats 3 \
  --output evals/stress/results.csv
```

## Run local gates

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check app evals tests
uv run python -m py_compile $(find app tests evals -name '*.py' -type f 2>/dev/null)
DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
```

## Notes

The committed full stress report is deterministic by design to avoid 900 live LLM calls. A smaller live DeepSeek smoke was run locally to verify the real provider path.
