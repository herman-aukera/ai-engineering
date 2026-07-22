"""One-time fail-closed repair for the final EACHAT merge gates."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one exact marker in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    committee = ROOT / "app/energy_chat/committee_orchestration.py"
    replace_once(
        committee,
        "                violation_count=len(score.violations),\n",
        "                violation_count=len(score.findings),\n",
    )

    checkpoint = ROOT / "app/energy_chat/graph_checkpoint.py"
    replace_once(
        checkpoint,
        "from langgraph.checkpoint.memory import MemorySaver\n\nfrom app.energy_chat.graph_state import EnergyChatGraphState\n",
        "from langgraph.checkpoint.memory import MemorySaver\n"
        "from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer\n\n"
        "from app.energy_chat.checkpoint_strict import STRICT_MSGPACK_ALLOWLIST\n"
        "from app.energy_chat.graph_state import EnergyChatGraphState\n",
    )
    replace_once(
        checkpoint,
        "        self._saver = MemorySaver()\n",
        "        self._saver = MemorySaver(\n"
        "            serde=JsonPlusSerializer(\n"
        "                allowed_msgpack_modules=STRICT_MSGPACK_ALLOWLIST,\n"
        "            )\n"
        "        )\n",
    )

    runner = ROOT / "scripts/run_eachat_fixed_quality.py"
    replace_once(
        runner,
        "import argparse\nfrom pathlib import Path\n\nfrom app.energy_chat.fixed_benchmark import (\n",
        "import argparse\nimport sys\nfrom pathlib import Path\n\n"
        "PROJECT_ROOT = Path(__file__).resolve().parents[1]\n"
        "if str(PROJECT_ROOT) not in sys.path:\n"
        "    sys.path.insert(0, str(PROJECT_ROOT))\n\n"
        "from app.energy_chat.fixed_benchmark import (  # noqa: E402\n",
    )

    api_tests = ROOT / "tests/test_energy_chat_api_v2.py"
    old_orchestration_tests = '''def test_v2_request_rejects_committee_orchestration_mode() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "orchestration_mode": "committee"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_orchestration_mode"


def test_v2_request_rejects_adaptive_orchestration_mode() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "orchestration_mode": "adaptive"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_orchestration_mode"
'''
    new_orchestration_tests = '''def test_v2_request_executes_bounded_deterministic_committee() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Prepare a bounded release recommendation.",
            "orchestration_mode": "committee",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requested_orchestration_mode"] == "committee"
    assert body["resolved_orchestration_mode"] == "committee"
    assert body["orchestration_candidate_count"] == 3
    assert body["served_provider"] == "deterministic_committee"


def test_v2_request_keeps_ordinary_adaptive_request_on_critic() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the bounded deterministic chat path.",
            "orchestration_mode": "adaptive",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requested_orchestration_mode"] == "adaptive"
    assert body["resolved_orchestration_mode"] == "critic"
    assert body["orchestration_candidate_count"] == 1
    assert "ordinary_request" in body["orchestration_reason"]
'''
    replace_once(api_tests, old_orchestration_tests, new_orchestration_tests)

    benchmark_routes = ROOT / "tests/test_energy_chat_fixed_benchmark_routes.py"
    benchmark_routes.write_text(
        '''from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fixed_benchmark_result_route_returns_bounded_quality_evidence() -> None:
    response = client.get("/energy-chat/benchmark/fixed")

    assert response.status_code == 200
    body = response.json()
    assert body["cases_total"] == 5
    assert body["accepted_baseline"] == 0
    assert body["accepted_after_repair"] == 4
    assert body["metadata"]["claim_status"] == (
        "deterministic_fixed_corpus_energy_reduction"
    )
    assert body["metadata"]["claim_scope"] == "committed deterministic corpus only"
    assert body["metadata"]["provider_calls"] == 0
    assert body["metadata"]["quality_claim_allowed"] is True
    assert body["metadata"]["live_provider_quality_proven"] is False
    assert body["average_energy_delta_after_repair"] < 0
    assert body["accepted_hard_reject_exposures"] == 0


def test_fixed_benchmark_report_route_preserves_external_claim_boundary() -> None:
    response = client.get("/energy-chat/benchmark/fixed/report")

    assert response.status_code == 200
    assert "# Energy Aware Chat Fixed Benchmark Report" in response.text
    assert "deterministic_fixed_corpus_energy_reduction" in response.text
    assert "committed deterministic corpus only" in response.text
    assert "does not prove live provider quality improvement" in response.text
    assert "superiority over DeepSeek, Kimi, OpenAI" in response.text
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
