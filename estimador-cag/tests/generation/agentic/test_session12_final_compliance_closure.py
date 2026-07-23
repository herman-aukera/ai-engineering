from pathlib import Path


def test_session12_compliance_doc_records_final_closure_status():
    content = Path("docs/session12_task12_compliance.md").read_text(encoding="utf-8")

    required_fragments = [
        "Final compliance closure",
        "Complex transcript evidence is covered",
        "sample_transcript_complex",
        "four components",
        "two search_budgets calls",
        "Retrieval bridge is covered with injected service",
        "Exact OpenAI Responses API manual loop is implemented",
        "Session 11 live Quality Lab UI diagnostics remain optional",
        "Task 12 validate_estimate extra is covered",
        "Remote CI green observed for 97c0630",
        "Devcontainer validation observed green",
        "Live provider smoke observed green",
        "Model variance is integration evidence, not benchmark evidence",
    ]

    for fragment in required_fragments:
        assert fragment in content


def test_session12_final_closure_does_not_overclaim_model_quality():
    content = Path("docs/session12_task12_compliance.md").read_text(encoding="utf-8")

    forbidden_claims = [
        "model comparison proves quality superiority",
        "Quality Lab UI diagnostics are implemented",
    ]

    for fragment in forbidden_claims:
        assert fragment not in content
