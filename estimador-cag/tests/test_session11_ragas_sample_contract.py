import json
from pathlib import Path

GOLDEN_PATH = Path("evals/session11_generation/golden_generation_s11.json")
RAGAS_SAMPLE_PATH = Path("evals/session11_generation/ragas_sample_s11.json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_session11_ragas_sample_contract_exists_with_expected_metrics():
    payload = _load_json(RAGAS_SAMPLE_PATH)

    assert payload["source"] == "golden_generation_s11.json"
    assert payload["sample_type"] == "deterministic_contract_not_live_score"
    assert payload["metrics"] == [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]
    assert len(payload["samples"]) == 5


def test_session11_ragas_samples_derive_from_evidence_backed_golden_set():
    golden = _load_json(GOLDEN_PATH)
    sample_payload = _load_json(RAGAS_SAMPLE_PATH)

    golden_by_id = {
        case["query_id"]: case
        for case in golden["queries"]
    }

    for sample in sample_payload["samples"]:
        golden_case = golden_by_id[sample["metadata"]["query_id"]]

        assert sample["question"] == golden_case["question"]
        assert sample["ground_truth"] == golden_case["ground_truth"]
        assert sample["metadata"]["expected_component_ids"] == golden_case["expected_component_ids"]
        assert sample["metadata"]["relevant_budget_ids"] == golden_case["relevant_budget_ids"]
        assert sample["metadata"]["ground_truth_sources"] == golden_case["ground_truth_sources"]


def test_session11_ragas_samples_have_ragas_required_fields():
    payload = _load_json(RAGAS_SAMPLE_PATH)

    for sample in payload["samples"]:
        assert set(sample) == {
            "question",
            "answer",
            "contexts",
            "ground_truth",
            "metadata",
        }

        assert sample["question"]
        assert sample["answer"]
        assert sample["contexts"]
        assert sample["ground_truth"]

        assert isinstance(sample["contexts"], list)
        assert all(isinstance(context, str) and context for context in sample["contexts"])


def test_session11_ragas_sample_answer_and_contexts_preserve_source_evidence():
    payload = _load_json(RAGAS_SAMPLE_PATH)

    for sample in payload["samples"]:
        answer = sample["answer"].lower()
        contexts = "\n".join(sample["contexts"]).lower()

        for source in sample["metadata"]["ground_truth_sources"]:
            component_id = source["component_id"].lower()
            component_name = source["component_name"].lower()
            chunk_id = source["chunk_id"].lower()
            evidence = source["evidence"].lower()
            hours = str(source["hours"])

            assert component_id in answer
            assert component_name in answer
            assert chunk_id in answer
            assert hours in answer

            assert component_id in contexts
            assert component_name in contexts
            assert chunk_id in contexts
            assert evidence in contexts
            assert hours in contexts
