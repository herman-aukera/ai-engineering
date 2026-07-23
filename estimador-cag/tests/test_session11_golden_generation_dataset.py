import json
from pathlib import Path

SESSION10_GOLDEN_PATH = Path("evals/session10_retrieval/golden_retrieval.json")
SESSION11_GOLDEN_PATH = Path("evals/session11_generation/golden_generation_s11.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_session11_generation_golden_set_exists_and_has_five_cases():
    payload = _load_json(SESSION11_GOLDEN_PATH)

    assert payload["source"] == "session10_retrieval/golden_retrieval.json"
    assert payload["metrics"] == [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]
    assert len(payload["queries"]) == 5


def test_session11_generation_golden_cases_extend_session10_queries():
    session10_payload = _load_json(SESSION10_GOLDEN_PATH)
    session11_payload = _load_json(SESSION11_GOLDEN_PATH)

    session10_by_id = {
        item["query_id"]: item
        for item in session10_payload["queries"]
    }

    for case in session11_payload["queries"]:
        source_case = session10_by_id[case["query_id"]]

        assert case["question"] == source_case["query"]
        assert case["intent"] == source_case["intent"]
        assert case["relevant_budget_ids"] == source_case["relevant_budget_ids"]
        assert case["expected_component_ids"] == source_case["expected_component_ids"]


def test_session11_generation_golden_cases_have_reference_answers():
    payload = _load_json(SESSION11_GOLDEN_PATH)

    for case in payload["queries"]:
        assert case["query_id"]
        assert case["question"]
        assert case["ground_truth"]
        assert "hours" in case["ground_truth"].lower()
        assert "source" in case["ground_truth"].lower()
        assert case["answer"] is None
        assert case["contexts"] == []
        assert case["ragas_scores"] is None
