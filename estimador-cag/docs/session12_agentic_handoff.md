# Session 12 Agentic Handoff

## Scope

Session 12 adds a deterministic agentic estimation loop and manual live-provider planning evidence.

The implemented path separates three concerns:

1. Provider planning
2. Deterministic local tool execution
3. Sanitized evidence reporting

This keeps normal tests deterministic while still allowing explicit manual provider smoke checks.

## Implemented capabilities

| Area | Evidence |
| --- | --- |
| Strict agent tool contracts | app/generation/agentic/agent_schemas.py and app/generation/agentic/agent_tools.py |
| Deterministic fake provider loop | app/generation/agentic/agent_loop.py |
| Retrieval bridge for search_budgets | app/generation/agentic/retrieval_bridge.py |
| Provider adapter contract | app/generation/agentic/provider_adapters.py |
| OpenAI-compatible planning adapter | app/generation/agentic/provider_adapters.py |
| Manual live-provider planning smoke | scripts/session12_live_provider_smoke.py |
| Provider-plan deterministic execution | scripts/session12_execute_provider_plan.py |
| Executed-plan summary generation | scripts/session12_summarize_executed_provider_plans.py |

## Evidence files

| File | Meaning |
| --- | --- |
| evals/session12_agentic/agent_trace_fake_s12.json | Deterministic fake-provider trace artifact |
| evals/session12_agentic/agent_trace_fake_retrieval_s12.json | Deterministic retrieval-backed trace artifact |
| evals/session12_agentic/session12_live_provider_matrix_summary.md | Sanitized manual live-provider planning summary |
| evals/session12_agentic/session12_executed_provider_plan_summary.md | Sanitized executed provider-plan summary |

## Deterministic local gate

Run from estimador-cag:

    GATE_OK=1
    uv run ruff check --fix scripts tests app || GATE_OK=0
    uv run ruff check scripts tests app || GATE_OK=0
    uv run python -m py_compile scripts/session12_live_provider_smoke.py scripts/session12_execute_provider_plan.py scripts/session12_summarize_executed_provider_plans.py $(find app tests -name '*.py' -type f 2>/dev/null) || GATE_OK=0
    uv run pytest -q tests/generation/agentic/test_executed_provider_plan_summary.py tests/generation/agentic/test_execute_provider_plan.py tests/generation/agentic/test_openai_compatible_provider_adapter.py tests/generation/agentic/test_live_provider_smoke_script.py tests/generation/agentic/test_agent_loop_provider_adapter.py tests/generation/agentic/test_provider_adapters.py tests/generation/agentic/test_retrieval_trace_artifact.py tests/generation/agentic/test_agent_loop_retrieval.py tests/generation/agentic/test_retrieval_bridge.py tests/generation/agentic/test_trace_artifacts.py tests/generation/agentic/test_agent_loop.py tests/generation/agentic/test_agent_tools.py || GATE_OK=0
    uv run python -m json.tool evals/session12_agentic/agent_trace_fake_s12.json >/tmp/agent_trace_fake_s12.pretty.json || GATE_OK=0
    uv run python -m json.tool evals/session12_agentic/agent_trace_fake_retrieval_s12.json >/tmp/agent_trace_fake_retrieval_s12.pretty.json || GATE_OK=0
    git diff --check || GATE_OK=0

    if [ "$GATE_OK" -ne 1 ]; then
      echo "STOP: deterministic Session 12 gate failed."
    else
      echo "Deterministic Session 12 gate passed."
    fi

## Manual live-provider planning smoke

This is opt-in only. It calls real providers and writes local artifacts under /tmp.

    mkdir -p /tmp/session12_live_smoke

    uv run python scripts/session12_live_provider_smoke.py --provider deepseek --tier cheap --live --output-dir /tmp/session12_live_smoke
    uv run python scripts/session12_live_provider_smoke.py --provider deepseek --tier final --live --output-dir /tmp/session12_live_smoke
    uv run python scripts/session12_live_provider_smoke.py --provider kimi --tier cheap --live --output-dir /tmp/session12_live_smoke
    uv run python scripts/session12_live_provider_smoke.py --provider kimi --tier final --live --output-dir /tmp/session12_live_smoke
    uv run python scripts/session12_live_provider_smoke.py --provider openai --tier cheap --live --output-dir /tmp/session12_live_smoke
    uv run python scripts/session12_live_provider_smoke.py --provider openai --tier final --live --output-dir /tmp/session12_live_smoke

## Execute provider plans with deterministic local tools

After live planning artifacts exist:

    mkdir -p /tmp/session12_live_executed

    find /tmp/session12_live_smoke -maxdepth 1 -type f -name '*_plan.json' | sort | while read -r plan; do
      name="$(basename "$plan" .json)"
      uv run python scripts/session12_execute_provider_plan.py --plan-file "$plan" --output-file "/tmp/session12_live_executed/${name}_executed.json"
    done

## Regenerate the sanitized executed-plan summary

    uv run python scripts/session12_summarize_executed_provider_plans.py --input-dir /tmp/session12_live_executed --output-file evals/session12_agentic/session12_executed_provider_plan_summary.md --expected-count 6

## Known limitations

This evidence proves manual live-provider planning plus deterministic local tool execution.

It does not claim remote CI green unless GitHub Actions is observed green for the pushed commit.

It does not claim browser UI proof because no Session 12 UI path was changed or smoked.

It does not claim benchmark quality, model superiority, or production readiness.

Raw provider artifacts and raw executed artifacts are intentionally kept outside the repository.

## Reviewer checklist

1. Read evals/session12_agentic/session12_live_provider_matrix_summary.md.
2. Read evals/session12_agentic/session12_executed_provider_plan_summary.md.
3. Run the deterministic local gate.
4. Optionally rerun manual live-provider planning smoke if provider keys and quota are available.
5. Optionally replay provider plans through deterministic tools.
