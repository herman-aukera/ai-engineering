from __future__ import annotations

from pathlib import Path
from typing import Any

import energy_chat_streamlit_app as energy_ui

STREAMLIT_SOURCE = Path("energy_chat_streamlit_app.py").read_text(encoding="utf-8")


def test_streamlit_ui_exposes_fixed_benchmark_evidence_panel() -> None:
    assert 'ENERGY_CHAT_FIXED_BENCHMARK_PATH = "/energy-chat/benchmark/fixed"' in STREAMLIT_SOURCE
    assert (
        'ENERGY_CHAT_FIXED_BENCHMARK_REPORT_PATH = "/energy-chat/benchmark/fixed/report"'
        in STREAMLIT_SOURCE
    )
    assert "Fixed deterministic benchmark evidence" in STREAMLIT_SOURCE
    assert "Show fixed benchmark evidence" in STREAMLIT_SOURCE
    assert "does not claim live provider quality improvement" in STREAMLIT_SOURCE


def test_fixed_benchmark_case_rows_flatten_response_shape() -> None:
    rows = energy_ui.fixed_benchmark_case_rows(
        {
            "results": [
                {
                    "case": {"case_id": "fixed-001", "category": "scope"},
                    "baseline_decision": "repair",
                    "baseline_energy": 700,
                    "final_decision": "accept",
                    "final_energy": 0,
                    "energy_delta_after_repair": -700,
                    "accepted_after_repair": True,
                }
            ]
        }
    )

    assert rows == [
        {
            "case_id": "fixed-001",
            "category": "scope",
            "baseline_decision": "repair",
            "baseline_energy": 700,
            "final_decision": "accept",
            "final_energy": 0,
            "energy_delta_after_repair": -700,
            "accepted_after_repair": True,
        }
    ]


def test_get_energy_chat_fixed_benchmark_result_uses_backend(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        text = "# report"

        def raise_for_status(self) -> None:
            captured["raise_for_status_called"] = True

        def json(self) -> dict[str, Any]:
            return {"cases_total": 5}

    def fake_get(url: str, timeout: tuple[int, int]) -> FakeResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(energy_ui.requests, "get", fake_get)
    monkeypatch.setenv("ESTIMADOR_BACKEND_URL", "https://example.test/")

    result = energy_ui.get_energy_chat_fixed_benchmark_result()

    assert result == {"cases_total": 5}
    assert captured == {
        "url": "https://example.test/energy-chat/benchmark/fixed",
        "timeout": (10, 240),
        "raise_for_status_called": True,
    }


def test_get_energy_chat_fixed_benchmark_report_uses_backend(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        text = "# Energy Aware Chat Fixed Benchmark Report"

        def raise_for_status(self) -> None:
            captured["raise_for_status_called"] = True

    def fake_get(url: str, timeout: tuple[int, int]) -> FakeResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(energy_ui.requests, "get", fake_get)
    monkeypatch.setenv("ESTIMADOR_BACKEND_URL", "https://example.test/")

    result = energy_ui.get_energy_chat_fixed_benchmark_report()

    assert result == "# Energy Aware Chat Fixed Benchmark Report"
    assert captured == {
        "url": "https://example.test/energy-chat/benchmark/fixed/report",
        "timeout": (10, 240),
        "raise_for_status_called": True,
    }
