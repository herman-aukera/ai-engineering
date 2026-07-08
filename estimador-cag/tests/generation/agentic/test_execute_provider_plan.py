import asyncio
import json
import subprocess
import sys
from pathlib import Path

from app.generation.agentic.agent_loop import execute_planned_steps_with_retrieval
from app.generation.agentic.agent_schemas import AgentRunRequest
from app.generation.agentic.provider_adapters import AgentPlannedStep


def test_execute_planned_steps_runs_deterministic_tools():
    planned_steps = [
        AgentPlannedStep(
            kind="reasoning",
            content="Plan the estimate.",
        ),
        AgentPlannedStep(
            kind="function_call",
            content="Call search_budgets.",
            tool_name="search_budgets",
            call_id="call_search",
            arguments={"query": "JWT authentication finance SaaS"},
        ),
        AgentPlannedStep(
            kind="function_call",
            content="Call calculate_estimate.",
            tool_name="calculate_estimate",
            call_id="call_calculate",
            arguments={
                "components": [
                    {
                        "name": "JWT authentication",
                        "complexity": "medium",
                        "reference_hours": 40,
                    },
                    {
                        "name": "Audit logging",
                        "complexity": "low",
                        "reference_hours": 24,
                    },
                ],
                "hourly_rate_eur": 75,
                "contingency_pct": 0.2,
            },
        ),
        AgentPlannedStep(
            kind="function_call",
            content="Call validate_estimate.",
            tool_name="validate_estimate",
            call_id="call_validate",
            arguments={
                "required_component_names": [
                    "JWT authentication",
                    "Audit logging",
                ]
            },
        ),
        AgentPlannedStep(
            kind="final",
            content="Return final estimate.",
        ),
    ]

    result = asyncio.run(
        execute_planned_steps_with_retrieval(
            AgentRunRequest(
                transcript="Client needs JWT authentication and audit logging.",
                provider="deepseek",
                model="deepseek-v4-flash",
            ),
            planned_steps,
        )
    )

    assert result.provider == "deepseek"
    assert result.model == "deepseek-v4-flash"
    assert result.estimate.total_hours == 76.8
    assert result.estimate.total_cost_eur == 5760
    assert result.validation is not None
    assert result.validation.valid is True
    assert result.terminated is True
    assert [item.role for item in result.trace] == [
        "reasoning",
        "function_call",
        "function_call_output",
        "function_call",
        "function_call_output",
        "function_call",
        "function_call_output",
        "final",
    ]


def test_execute_provider_plan_script_reads_plan_and_writes_result(tmp_path):
    plan_path = tmp_path / "cheap_deepseek_plan.json"
    output_path = tmp_path / "cheap_deepseek_executed.json"

    plan_path.write_text(
        json.dumps(
            {
                "schema_version": "session12.live_provider_smoke.v1",
                "provider": "deepseek",
                "tier": "cheap",
                "model": "deepseek-v4-flash",
                "temperature": 0.0,
                "steps": [
                    {"kind": "reasoning", "content": "Plan."},
                    {
                        "kind": "function_call",
                        "content": "Call calculate_estimate.",
                        "tool_name": "calculate_estimate",
                        "call_id": "call_calculate",
                        "arguments": {
                            "components": [
                                {
                                    "name": "JWT authentication",
                                    "complexity": "medium",
                                    "reference_hours": 40,
                                }
                            ],
                            "hourly_rate_eur": 75,
                            "contingency_pct": 0.2,
                        },
                    },
                    {
                        "kind": "function_call",
                        "content": "Call validate_estimate.",
                        "tool_name": "validate_estimate",
                        "call_id": "call_validate",
                        "arguments": {
                            "required_component_names": ["JWT authentication"]
                        },
                    },
                    {"kind": "final", "content": "Done."},
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/session12_execute_provider_plan.py",
            "--plan-file",
            str(plan_path),
            "--output-file",
            str(output_path),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "session12.executed_provider_plan.v1"
    assert payload["provider"] == "deepseek"
    assert payload["tier"] == "cheap"
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["result"]["estimate"]["total_hours"] == 48
    assert payload["result"]["validation"]["valid"] is True
