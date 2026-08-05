import json
from pathlib import Path

from app.energy_chat.artifact_registry import artifact_paths

ACCEPTANCE_MATRIX = Path(
    "docs/energy_aware_chat_final_project_acceptance_matrix.md"
).read_text(encoding="utf-8")
DEPLOYMENT_RUNBOOK = Path(
    "docs/energy_aware_chat_deployment_readiness_runbook.md"
).read_text(encoding="utf-8")
LIVE_PROVIDER_TEMPLATE = Path(
    "docs/energy_aware_chat_live_provider_evidence_template.md"
).read_text(encoding="utf-8")
LIVE_PROVIDER_WORKFLOW = Path(
    "../.github/workflows/eachat-live-provider-smoke.yml"
).read_text(encoding="utf-8")
LIVE_PROVIDER_EVIDENCE = json.loads(
    Path("evals/energy_chat/live_provider_smoke_deepseek_2026-08-05.json").read_text(
        encoding="utf-8"
    )
)
DEMO_RECORDING_PACKET = Path(
    "docs/energy_aware_chat_mvp_demo_recording_packet.md"
).read_text(encoding="utf-8")
REVIEWER_INDEX = Path("docs/energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)
EXPORT_MANIFEST = Path("scripts/export_energy_chat_manifest.sh").read_text(
    encoding="utf-8"
)


MILESTONE_DOCS = [
    "docs/energy_aware_chat_final_project_acceptance_matrix.md",
    "docs/energy_aware_chat_deployment_readiness_runbook.md",
    "docs/energy_aware_chat_live_provider_evidence_template.md",
    "docs/energy_aware_chat_mvp_demo_recording_packet.md",
]


def test_acceptance_matrix_maps_final_project_requirements_to_evidence() -> None:
    required_fragments = [
        "finalproject-GGC",
        "User-facing AI service",
        "RAG pipeline",
        "Agent layer",
        "Documented evals",
        "Deployment evidence",
        "DeepSeek-to-Kimi fallback seam",
        "measurement_only_no_quality_claim",
        "production-ready",
        "vector database RAG grounding",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in ACCEPTANCE_MATRIX


def test_deployment_runbook_keeps_public_deployment_claim_blocked() -> None:
    required_fragments = [
        "bash scripts/start_energy_chat.sh",
        "docker compose -f docker-compose.energy-chat.yml up --build",
        "DEEPSEEK_API_KEY",
        "KIMI_API_KEY",
        "public deployment is already live",
        "production readiness",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in DEPLOYMENT_RUNBOOK


def test_live_provider_document_records_bounded_sanitized_evidence() -> None:
    required_fragments = [
        "EACHAT - Live Provider Smoke",
        "single_provider_live_smoke",
        "fallback_used",
        "credential_recorded",
        "A bounded DeepSeek V4 Flash live integration smoke passed",
        "quality improvement over plain DeepSeek",
        "live_provider_smoke_deepseek_2026-08-05.json",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in LIVE_PROVIDER_TEMPLATE


def test_live_provider_workflow_enforces_exact_requested_profile() -> None:
    required_fragments = [
        'PYTHONPATH: "."',
        "EXPECTED_HEAD_SHA",
        "provider_call_count",
        "REQUESTED_PROVIDER",
        "REQUESTED_EFFORT",
        "payload['requested_provider'] == os.environ['REQUESTED_PROVIDER']",
        "payload['effort'] == os.environ['REQUESTED_EFFORT']",
        "payload['fallback_used'] is False",
        "payload['credential_recorded'] is False",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in LIVE_PROVIDER_WORKFLOW


def test_deepseek_live_evidence_preserves_claim_boundary() -> None:
    assert LIVE_PROVIDER_EVIDENCE["schema_version"] == 1
    assert LIVE_PROVIDER_EVIDENCE["evidence_type"] == "single_provider_live_smoke"
    assert LIVE_PROVIDER_EVIDENCE["status"] == "success"
    assert LIVE_PROVIDER_EVIDENCE["requested_provider"] == "deepseek"
    assert LIVE_PROVIDER_EVIDENCE["provider"] == "deepseek"
    assert LIVE_PROVIDER_EVIDENCE["effort"] == "balanced"
    assert LIVE_PROVIDER_EVIDENCE["provider_call_count"] == 1
    assert LIVE_PROVIDER_EVIDENCE["fallback_used"] is False
    assert LIVE_PROVIDER_EVIDENCE["answer_body_recorded"] is False
    assert LIVE_PROVIDER_EVIDENCE["prompt_body_recorded"] is False
    assert LIVE_PROVIDER_EVIDENCE["credential_recorded"] is False
    assert "quality improvement over plain DeepSeek" in LIVE_PROVIDER_EVIDENCE[
        "claims_blocked"
    ]
    assert "production readiness" in LIVE_PROVIDER_EVIDENCE["claims_blocked"]


def test_demo_recording_packet_covers_mvp_routes_and_non_claims() -> None:
    required_fragments = [
        "2 to 3 minutes",
        "POST /energy-chat/evaluate",
        "POST /energy-chat/rag/search",
        "POST /energy-chat/chat",
        "Energy Card",
        "DeepSeek and Kimi are wired through a fallback seam",
        "vector database RAG",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in DEMO_RECORDING_PACKET


def test_milestone_docs_are_reviewer_packet_artifacts() -> None:
    paths = artifact_paths()

    for doc_path in MILESTONE_DOCS:
        assert doc_path in paths
        assert doc_path in REVIEWER_INDEX
        assert doc_path in EXPORT_MANIFEST
