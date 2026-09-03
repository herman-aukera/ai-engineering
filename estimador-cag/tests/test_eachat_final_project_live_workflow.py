from pathlib import Path

WORKFLOW = Path("../.github/workflows/final-project-live-rag.yml").read_text(
    encoding="utf-8"
)
RUNBOOK = Path("docs/final_project/LIVE_PROOF_RUNBOOK.md").read_text(encoding="utf-8")


def test_live_rag_workflow_is_manual_exact_head_and_uses_pinned_postgres() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "EXPECTED_HEAD_SHA: ${{ github.sha }}" in WORKFLOW
    assert 'ref: ${{ env.EXPECTED_HEAD_SHA }}' in WORKFLOW
    assert (
        "postgres:16@sha256:e17e86066e5ef83e0952a9347f5c792b7ece00972e2aa787a6986f471b3dd3d5"
        in WORKFLOW
    )


def test_live_rag_workflow_executes_real_ingestion_retrieval_and_bounded_answer() -> None:
    required = (
        "scripts/ingest_eachat_support_rag.py",
        "evals/energy_chat/final_project_eval.py",
        "scripts/smoke_eachat_final_project_live.py",
        "EACHAT_SUPPORT_RAG_ENABLED: \"true\"",
        "EACHAT_SUPPORT_EMBEDDING_API_KEY: ${{ secrets.OPENAI_API_KEY }}",
        "--provider \"${{ inputs.provider }}\"",
        "--effort \"${{ inputs.effort }}\"",
        "final-project-live-rag-${{ inputs.provider }}-${{ inputs.effort }}",
    )
    for item in required:
        assert item in WORKFLOW


def test_live_rag_workflow_keeps_secrets_out_of_evidence_artifacts() -> None:
    assert "Reject secrets from evidence artifacts" in WORKFLOW
    assert "answer_body_recorded" in Path(
        "scripts/smoke_eachat_final_project_live.py"
    ).read_text(encoding="utf-8")
    assert "prompt_body_recorded" in Path(
        "scripts/smoke_eachat_final_project_live.py"
    ).read_text(encoding="utf-8")
    assert "credential_recorded" in Path(
        "scripts/smoke_eachat_final_project_live.py"
    ).read_text(encoding="utf-8")


def test_runbook_preserves_live_evidence_claim_boundary() -> None:
    assert "deterministic CI must not silently call paid providers" in RUNBOOK
    assert "public deployment URL **or** the required 2–3 minute video" in RUNBOOK
    assert "final-project-ingestion.json" in RUNBOOK
    assert "final-project-retrieval-report.json" in RUNBOOK
    assert "final-project-live-answer.json" in RUNBOOK
