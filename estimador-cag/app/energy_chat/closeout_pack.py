"""Closeout pack helpers for Energy Aware Chat reviewer handoff."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.energy_chat.artifact_registry import artifact_paths


@dataclass(frozen=True)
class CloseoutSection:
    """One closeout section shown to a reviewer or future maintainer."""

    section_id: str
    title: str
    complete: bool
    summary: str
    evidence: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class CloseoutPack:
    """End-of-day Energy Aware Chat handoff packet."""

    version: str
    project_root: Path
    sections: tuple[CloseoutSection, ...]
    missing_artifacts: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Return whether every closeout section is complete."""

        return not self.missing_artifacts and all(section.complete for section in self.sections)


REQUIRED_CLOSEOUT_ARTIFACTS: tuple[str, ...] = (
    "app/energy_chat/",
    "energy_chat_streamlit_app.py",
    "scripts/validate_energy_chat.sh",
    "scripts/check_energy_chat_ci.sh",
    "docs/energy_aware_chat_reviewer_index.md",
    "docs/energy_aware_chat_final_project_acceptance_matrix.md",
    "docs/energy_aware_chat_final_project_proof_packet.md",
    "docs/energy_aware_chat_demo_command_checklist.md",
    "docs/energy_aware_chat_session17_backlog.md",
    "docs/energy_aware_chat_release_snapshot.md",
)


def _path_exists(project_root: Path, artifact_path: str) -> bool:
    normalized = artifact_path.rstrip("/")
    if artifact_path.startswith("../"):
        return (project_root / artifact_path).resolve().exists()
    return (project_root / normalized).exists()


def _missing_required_artifacts(project_root: Path) -> tuple[str, ...]:
    return tuple(
        artifact
        for artifact in REQUIRED_CLOSEOUT_ARTIFACTS
        if not _path_exists(project_root, artifact)
    )


def _artifact_registry_complete() -> bool:
    paths = set(artifact_paths())
    return all(artifact in paths for artifact in REQUIRED_CLOSEOUT_ARTIFACTS)


def build_energy_chat_closeout_pack(project_root: Path | str) -> CloseoutPack:
    """Build the deterministic closeout packet for the current Energy Chat tree."""

    root = Path(project_root).resolve()
    missing = _missing_required_artifacts(root)
    registry_complete = _artifact_registry_complete()
    no_missing_artifacts = not missing

    sections = (
        CloseoutSection(
            section_id="mvp_status",
            title="MVP status",
            complete=no_missing_artifacts,
            summary="Energy Aware Chat has a deterministic MVP candidate surface.",
            evidence=(
                "app/energy_chat/",
                "docs/energy_aware_chat_final_project_acceptance_matrix.md",
                "docs/energy_aware_chat_final_project_proof_packet.md",
            ),
            next_action="Keep final-project claims tied to deterministic and live-smoke evidence.",
        ),
        CloseoutSection(
            section_id="validation_proof",
            title="Validation proof",
            complete=no_missing_artifacts,
            summary="Local and CI proof commands are explicit and reviewer-runnable.",
            evidence=(
                "scripts/validate_energy_chat.sh",
                "scripts/check_energy_chat_ci.sh",
            ),
            next_action="Run both commands after every EACHAT patch before accepting the branch.",
        ),
        CloseoutSection(
            section_id="reviewer_navigation",
            title="Reviewer navigation",
            complete=registry_complete,
            summary="Reviewer documents are registered in a canonical artifact list.",
            evidence=(
                "docs/energy_aware_chat_reviewer_index.md",
                "scripts/list_energy_chat_artifacts.py",
            ),
            next_action="Use the reviewer index as the first entry point for demos and handoff.",
        ),
        CloseoutSection(
            section_id="scope_boundaries",
            title="Scope boundaries",
            complete=True,
            summary="The branch remains an incubator, not a production-ready claim.",
            evidence=(
                "measurement_only_no_quality_claim",
                "EACHAT remains separate from EACODE and coursework branches.",
            ),
            next_action="Do not merge Chat, Code, Session 08, or Session 09 work in one patch.",
        ),
        CloseoutSection(
            section_id="next_slice",
            title="Next slice",
            complete=True,
            summary="The safest next work is evidence capture, not feature expansion.",
            evidence=(
                "docs/energy_aware_chat_session17_backlog.md",
                "docs/energy_aware_chat_release_snapshot.md",
            ),
            next_action="Pick one evidence or deployment-readiness slice after gates are green.",
        ),
    )

    return CloseoutPack(
        version="1.0.0",
        project_root=root,
        sections=sections,
        missing_artifacts=missing,
    )


def render_energy_chat_closeout_markdown(pack: CloseoutPack) -> str:
    """Render the closeout packet as reviewer-friendly Markdown."""

    lines = [
        "# Energy Aware Chat closeout pack",
        "",
        f"- Version: {pack.version}",
        f"- Project root: `{pack.project_root}`",
        f"- Complete: {pack.complete}",
        f"- Sections: {sum(section.complete for section in pack.sections)}/{len(pack.sections)}",
        "",
        "## Missing artifacts",
        "",
    ]
    if pack.missing_artifacts:
        lines.extend(f"- `{artifact}`" for artifact in pack.missing_artifacts)
    else:
        lines.append("- none")

    lines.extend(["", "## Sections", ""])
    for section in pack.sections:
        lines.extend(
            [
                f"### {section.title}",
                "",
                f"- Id: `{section.section_id}`",
                f"- Complete: {section.complete}",
                f"- Summary: {section.summary}",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - `{evidence}`" for evidence in section.evidence)
        lines.extend(
            [
                f"- Next action: {section.next_action}",
                "",
            ]
        )

    lines.extend(
        [
            "## Non claims",
            "",
            "- This closeout pack does not prove production readiness.",
            "- This closeout pack does not prove quality improvement over DeepSeek.",
            "- This closeout pack does not replace local validation or exact-commit CI proof.",
        ]
    )
    return "\n".join(lines) + "\n"
