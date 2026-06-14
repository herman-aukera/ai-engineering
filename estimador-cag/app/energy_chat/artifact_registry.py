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
        purpose="deterministic evaluator package",
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
        path="scripts/render_energy_chat_release_snapshot.py",
        kind="script",
        purpose="release snapshot renderer",
    ),
)

DOC_ARTIFACTS: tuple[EnergyChatArtifact, ...] = (
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
        path="docs/energy_aware_chat_release_snapshot.md",
        kind="doc",
        purpose="release snapshot guide",
    ),
)


def list_energy_chat_artifacts() -> tuple[EnergyChatArtifact, ...]:
    """Return the canonical reviewer packet artifact list."""

    return CORE_ARTIFACTS + DOC_ARTIFACTS


def artifact_paths() -> tuple[str, ...]:
    """Return artifact paths only, preserving registry order."""

    return tuple(artifact.path for artifact in list_energy_chat_artifacts())
