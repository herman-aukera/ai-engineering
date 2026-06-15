"""Canonical artifact paths for Energy Aware Chat reviewer packets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnergyChatArtifact:
    """One artifact that belongs to the Energy Aware Chat delivery packet."""

    path: str
    kind: str
    purpose: str


CORE_ARTIFACTS: tuple[EnergyChatArtifact, ...] = (
    EnergyChatArtifact(
        path="app/energy_chat/",
        kind="code",
        purpose="deterministic evaluator, RAG, and agent package",
    ),
    EnergyChatArtifact(
        path="energy_chat_streamlit_app.py",
        kind="ui",
        purpose="human demo interface",
    ),
    EnergyChatArtifact(
        path="demo_payloads/energy_chat/",
        kind="fixture",
        purpose="checked demo request payloads",
    ),
    EnergyChatArtifact(
        path="scripts/validate_energy_chat.sh",
        kind="script",
        purpose="local validation gate",
    ),
    EnergyChatArtifact(
        path="scripts/check_energy_chat_ci.sh",
        kind="script",
        purpose="dedicated workflow proof helper",
    ),
    EnergyChatArtifact(
        path="scripts/smoke_energy_chat_live_provider.py",
        kind="script",
        purpose="manual DeepSeek and Kimi live provider smoke",
    ),
    EnergyChatArtifact(
        path="scripts/start_energy_chat.sh",
        kind="script",
        purpose="local API start command",
    ),
    EnergyChatArtifact(
        path="scripts/render_energy_chat_release_snapshot.py",
        kind="script",
        purpose="release snapshot renderer",
    ),
    EnergyChatArtifact(
        path="scripts/render_energy_chat_closeout_pack.py",
        kind="script",
        purpose="end-of-day closeout pack renderer",
    ),
    EnergyChatArtifact(
        path="Dockerfile.energy-chat",
        kind="deployment",
        purpose="container image for Energy Aware Chat API",
    ),
    EnergyChatArtifact(
        path="docker-compose.energy-chat.yml",
        kind="deployment",
        purpose="local compose deployment path",
    ),
    EnergyChatArtifact(
        path="../.github/workflows/energy-chat-ci.yml",
        kind="workflow",
        purpose="deterministic Energy Aware Chat CI",
    ),
    EnergyChatArtifact(
        path="../.github/workflows/energy-chat-live-provider-smoke.yml",
        kind="workflow",
        purpose="manual live provider smoke with GitHub secrets",
    ),
)

DOC_ARTIFACTS: tuple[EnergyChatArtifact, ...] = (
    EnergyChatArtifact(
        path="docs/energy_aware_chat_examiner_quickstart.md",
        kind="doc",
        purpose="examiner quickstart",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_final_project_acceptance_matrix.md",
        kind="doc",
        purpose="final-project requirement to evidence matrix",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_mvp_upgrade.md",
        kind="doc",
        purpose="MVP upgrade and claim boundary",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_deployment_readiness_runbook.md",
        kind="doc",
        purpose="deployment readiness runbook",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_live_provider_evidence_template.md",
        kind="doc",
        purpose="manual live provider smoke evidence template",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_mvp_demo_recording_packet.md",
        kind="doc",
        purpose="2 to 3 minute MVP demo recording packet",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_final_submission_handoff.md",
        kind="doc",
        purpose="final submission handoff",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_pr_body_draft.md",
        kind="doc",
        purpose="pull request body draft",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_reviewer_index.md",
        kind="doc",
        purpose="reviewer entry point",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_final_project_proof_packet.md",
        kind="doc",
        purpose="final project proof packet",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_actions_filtering.md",
        kind="doc",
        purpose="actions filtering guide",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_demo_evidence_checklist.md",
        kind="doc",
        purpose="demo evidence checklist",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_live_demo_readiness.md",
        kind="doc",
        purpose="demo readiness checklist",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_demo_script.md",
        kind="doc",
        purpose="demo narration script",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_demo_command_checklist.md",
        kind="doc",
        purpose="demo command checklist",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_session17_backlog.md",
        kind="doc",
        purpose="Session 17 intake backlog",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_release_snapshot.md",
        kind="doc",
        purpose="release snapshot guide",
    ),
    EnergyChatArtifact(
        path="docs/energy_aware_chat_closeout_pack.md",
        kind="doc",
        purpose="end-of-day closeout and resume handoff",
    ),
)


def list_energy_chat_artifacts() -> tuple[EnergyChatArtifact, ...]:
    """Return the canonical reviewer packet artifact list."""

    return CORE_ARTIFACTS + DOC_ARTIFACTS


def artifact_paths() -> tuple[str, ...]:
    """Return artifact paths only, preserving registry order."""

    return tuple(artifact.path for artifact in list_energy_chat_artifacts())
