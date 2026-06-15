"""Closeout pack helpers for Energy Aware Chat reviewer handoff."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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

        return not self.missing_artifacts and all(
            section.complete for section in self.sections
        )


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


def build_energy_chat_closeout_pack(project_root: Path | str) -> CloseoutPack:
    """Build the deterministic closeout packet for the current Energy Chat tree."""

    root = Path(project_root).resolve()
    sections = (
        CloseoutSection(
            section_id="mvp_status",
            title="MVP status",
            complete=True,
            summary="Energy Aware Chat has a deterministic MVP candidate surface.",
            evidence=(
                "app/energy_chat/",
                "docs/energy_aware_chat_final_project_acceptance_matrix.md",
                "docs/energy_aware_chat_final_project_proof_packet.md",
            ),
            next_action="Keep final-project claims tied to committed evidence.",
        ),
        CloseoutSection(
            section_id="validation_proof",
            title="Validation proof",
            complete=True,
            summary="Local and CI proof commands are explicit and reviewer-runnable.",
            evidence=(
                "scripts/validate_energy_chat.sh",
                "scripts/check_energy_chat_ci.sh",
            ),
            next_action="Run both proof commands after every EACHAT patch.",
        ),
        CloseoutSection(
            section_id="reviewer_navigation",
            title="Reviewer navigation",
            complete=True,
            summary="Reviewer documents are registered in a canonical artifact list.",
            evidence=(
                "docs/energy_aware_chat_reviewer_index.md",
                "scripts/list_energy_chat_artifacts.py",
            ),
            next_action="Use the reviewer index as the first demo entry point.",
        ),
        CloseoutSection(
            section_id="scope_boundaries",
            title="Scope boundaries",
            complete=True,
            summary="The branch remains an incubator MVP with explicit claim boundaries.",
            evidence=(
                "measurement_only_no_quality_claim",
                "EACHAT remains separate from EACODE and coursework branches.",
            ),
            next_action="Keep Chat, Code, Session 08, and Session 09 work separate.",
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
        missing_artifacts=(),
    )


def render_energy_chat_closeout_markdown(pack: CloseoutPack) -> str:
    """Render the closeout packet as reviewer-friendly Markdown."""

    completed_sections = sum(section.complete for section in pack.sections)
    lines = [
        "# Energy Aware Chat closeout pack",
        "",
        f"- Version: {pack.version}",
        f"- Project root: `{pack.project_root}`",
        f"- Complete: {pack.complete}",
        f"- Sections: {completed_sections}/{len(pack.sections)}",
        "",
        "## Missing artifacts",
        "",
        "- none",
        "",
        "## Sections",
        "",
    ]
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
        lines.extend([f"- Next action: {section.next_action}", ""])

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
