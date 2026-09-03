from __future__ import annotations

import json
from pathlib import Path

GOLDEN = Path("evals/energy_chat/final_project_golden.json")


def _cases() -> list[dict[str, object]]:
    payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.1.0"
    return payload["cases"]


def test_final_project_golden_set_covers_all_required_categories() -> None:
    cases = _cases()
    case_ids = {str(case["case_id"]) for case in cases}

    assert len(cases) == 11
    assert len(case_ids) == 11
    assert {
        "spring-health-503",
        "spring-config-startup",
        "postgres-connections",
        "postgres-locks",
        "docker-logs",
        "docker-network",
        "cross-domain-health-db",
        "version-source-conflict",
        "insufficient-evidence-root-cause",
        "l3-source-patch",
        "unsupported-kubernetes",
    } == case_ids


def test_every_golden_case_declares_expected_sources_and_disposition() -> None:
    for case in _cases():
        assert isinstance(case["query"], str) and str(case["query"]).strip()
        assert isinstance(case["expected_source_ids"], list)
        assert case["expected_disposition"] in {
            "accept",
            "repair",
            "clarify",
            "reject",
            "refuse",
            "escalate",
        }


def test_version_source_conflict_requires_clarification() -> None:
    case = next(
        case for case in _cases() if case["case_id"] == "version-source-conflict"
    )

    assert case["expected_disposition"] == "clarify"
    assert "Spring Boot 2.7.18" in str(case["query"])
    assert "spring_boot_actuator_endpoints" in case["expected_source_ids"]
