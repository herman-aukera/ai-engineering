import json
from pathlib import Path

SESSION11_GOLDEN_PATH = Path("evals/session11_generation/golden_generation_s11.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_session11_generation_golden_cases_have_traceable_ground_truth_sources():
    payload = _load_json(SESSION11_GOLDEN_PATH)

    for case in payload["queries"]:
        sources = case["ground_truth_sources"]

        assert sources
        assert len(sources) == len(case["expected_component_ids"])

        source_component_ids = {
            source["component_id"]
            for source in sources
        }

        assert source_component_ids == set(case["expected_component_ids"])

        for source in sources:
            assert source["budget_id"] in case["relevant_budget_ids"]
            assert source["component_id"] in case["expected_component_ids"]
            assert source["chunk_id"] == f'{source["budget_id"]}::{source["component_id"]}'
            assert source["component_name"]
            assert source["evidence"]
            assert isinstance(source["hours"], int)
            assert source["hours"] > 0
            assert source["complexity"]


def test_session11_generation_ground_truth_mentions_evidence_hours_and_components():
    payload = _load_json(SESSION11_GOLDEN_PATH)

    for case in payload["queries"]:
        ground_truth = case["ground_truth"].lower()

        for source in case["ground_truth_sources"]:
            assert str(source["hours"]) in ground_truth
            assert source["component_id"].lower() in ground_truth
            assert source["component_name"].lower() in ground_truth


def test_session11_generation_golden_payload_declares_evidence_policy():
    payload = _load_json(SESSION11_GOLDEN_PATH)

    assert payload["ground_truth_policy"] == (
        "Ground truth answers are derived from actual budget component evidence "
        "in the current repository corpus."
    )
