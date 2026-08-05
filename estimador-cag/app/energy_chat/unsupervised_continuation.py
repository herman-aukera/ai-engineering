"""Unsupervised continuation helpers for Energy Aware Chat.

The continuation pack is a deterministic handoff artifact. It does not execute
providers or expand runtime scope. Its job is to keep the next batch aligned
when work continues without an immediate local reviewer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContinuationSection:
    """One safe continuation section for the next Energy Chat batch."""

    section_id: str
    title: str
    complete: bool
    summary: str
    evidence: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class UnsupervisedContinuationPack:
    """Deterministic handoff packet for continuing Energy Chat safely."""

    version: str
    project_root: Path
    sections: tuple[ContinuationSection, ...]
    missing_artifacts: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Return whether the continuation packet is complete."""

        return not self.missing_artifacts and all(
            section.complete for section in self.sections
        )


REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS: tuple[str, ...] = (
    "scripts/validate_energy_chat.sh",
    "scripts/check_energy_chat_ci.sh",
    "docs/energy_aware_chat_reviewer_index.md",
    "docs/energy_aware_chat_final_project_proof_packet.md",
    "docs/energy_aware_chat_fixed_benchmark_report.md",
    "docs/energy_aware_chat_session17_backlog.md",
    "docs/energy_aware_chat_release_snapshot.md",
    "docs/energy_aware_chat_closeout_pack.md",
)


def _artifact_exists(project_root: Path, artifact: str) -> bool:
    path = project_root / artifact
    if artifact.endswith("/"):
        return path.is_dir()
    return path.exists()


def _missing_artifacts(project_root: Path) -> tuple[str, ...]:
    return tuple(
        artifact
        for artifact in REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS
        if not _artifact_exists(project_root, artifact)
    )


def build_energy_chat_unsupervised_continuation_pack(
    project_root: Path | str,
) -> UnsupervisedContinuationPack:
    """Build the deterministic unsupervised continuation packet."""

    root = Path(project_root).resolve()
    missing = _missing_artifacts(root)
    base_complete = not missing
    sections = (
        ContinuationSection(
            section_id="validated_start_state",
            title="Validated start state",
            complete=base_complete,
            summary="Continue only from a clean local gate and exact commit CI proof.",
            evidence=(
                "scripts/validate_energy_chat.sh",
                "scripts/check_energy_chat_ci.sh",
            ),
            next_action="Run the local gate and exact-commit CI check after every patch.",
        ),
        ContinuationSection(
            section_id="reviewer_navigation",
            title="Reviewer navigation",
            complete=base_complete,
            summary="Reviewer entry points are centralized in the reviewer index and proof packet.",
            evidence=(
                "docs/energy_aware_chat_reviewer_index.md",
                "docs/energy_aware_chat_final_project_proof_packet.md",
            ),
            next_action="Keep new proof artifacts linked from the reviewer index.",
        ),
        ContinuationSection(
            section_id="claim_boundary",
            title="Claim boundary",
            complete=base_complete,
            summary="Benchmark wording remains measurement-only until comparative data exists.",
            evidence=(
                "measurement_only_no_quality_claim",
                "docs/energy_aware_chat_fixed_benchmark_report.md",
            ),
            next_action="Do not claim quality improvement or production readiness.",
        ),
        ContinuationSection(
            section_id="next_safe_slice",
            title="Next safe slice",
            complete=base_complete,
            summary="New class material and product ideas enter through a backlog before runtime code.",
            evidence=(
                "docs/energy_aware_chat_session17_backlog.md",
                "docs/energy_aware_chat_release_snapshot.md",
            ),
            next_action="Pick one evidence, demo, or deployment-readiness slice after validation is green.",
        ),
        ContinuationSection(
            section_id="scope_guards",
            title="Scope guards",
            complete=base_complete,
            summary="Unsupervised work must not mix Energy Chat with Code or coursework branches.",
            evidence=(
                "No Session 08 implementation.",
                "No Session 09 implementation.",
                "No EACODE changes.",
                "No provider calls without an explicit isolated smoke workflow.",
            ),
            next_action="Stop if the next patch would cross a product or coursework boundary.",
        ),
    )
    return UnsupervisedContinuationPack(
        version="1.0.0",
        project_root=root,
        sections=sections,
        missing_artifacts=missing,
    )


def render_energy_chat_unsupervised_continuation_markdown(
    pack: UnsupervisedContinuationPack,
) -> str:
    """Render the continuation packet as Markdown."""

    completed_sections = sum(section.complete for section in pack.sections)
    missing_lines = [f"- `{artifact}`" for artifact in pack.missing_artifacts] or [
        "- none"
    ]
    lines = [
        "# Energy Aware Chat unsupervised continuation pack",
        "",
        f"- Version: {pack.version}",
        f"- Project root: `{pack.project_root}`",
        f"- Complete: {pack.complete}",
        f"- Sections: {completed_sections}/{len(pack.sections)}",
        "- Mode: unsupervised-continuation-safe",
        "",
        "## Missing artifacts",
        "",
        *missing_lines,
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
            "## Non goals",
            "",
            "- This pack does not execute shell actions.",
            "- This pack does not call LLM providers.",
            "- This pack does not mutate benchmark evidence.",
            "- This pack does not authorize Session 08, Session 09, EACODE, or bridge work.",
            "- This pack does not prove production readiness or model-quality improvement.",
        ]
    )
    return "\n".join(lines) + "\n"
