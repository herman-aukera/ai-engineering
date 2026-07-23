import json
from pathlib import Path

from app.generation.agentic.agent_loop import run_agent_loop
from app.generation.agentic.agent_schemas import AgentRunRequest
from app.generation.agentic.trace_artifacts import build_trace_artifact, write_trace_artifact

TRANSCRIPT_PATH = Path("evals/session12_agentic/sample_transcript_complex.txt")


def test_build_trace_artifact_contains_agent_loop_evidence():
    transcript = TRANSCRIPT_PATH.read_text()
    result = run_agent_loop(
        AgentRunRequest(
            transcript=transcript,
            provider="fake",
            max_iterations=8,
        )
    )

    artifact = build_trace_artifact(
        scenario_id="sample_transcript_complex",
        request_provider="fake",
        result=result,
    )

    assert artifact["schema_version"] == "session12.agent_trace.v1"
    assert artifact["scenario_id"] == "sample_transcript_complex"
    assert artifact["provider"] == "fake"
    assert artifact["terminated"] is True
    assert artifact["estimate"]["total_hours"] > 0
    assert artifact["validation"]["valid"] is True

    trace = artifact["trace"]
    assert trace[-1]["role"] == "final"

    tool_calls = [item for item in trace if item["role"] == "function_call"]
    tool_outputs = [item for item in trace if item["role"] == "function_call_output"]

    assert len(tool_calls) >= 4
    assert {item["call_id"] for item in tool_calls} == {
        item["call_id"] for item in tool_outputs
    }


def test_write_trace_artifact_creates_pretty_json(tmp_path):
    transcript = TRANSCRIPT_PATH.read_text()
    result = run_agent_loop(
        AgentRunRequest(
            transcript=transcript,
            provider="fake",
            max_iterations=8,
        )
    )

    output_path = tmp_path / "agent_trace_fake_s12.json"

    write_trace_artifact(
        output_path=output_path,
        scenario_id="sample_transcript_complex",
        request_provider="fake",
        result=result,
    )

    payload = json.loads(output_path.read_text())

    assert payload["schema_version"] == "session12.agent_trace.v1"
    assert payload["trace"][0]["role"] == "reasoning"
    assert output_path.read_text().endswith("\n")
