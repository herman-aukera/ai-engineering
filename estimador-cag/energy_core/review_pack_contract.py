from __future__ import annotations

REVIEW_PACK_ARTIFACT_FILES = (
    "README.md",
    "reviewer_snapshot.md",
    "nightly_status.md",
    "release_readiness.md",
    "package_manifest.md",
    "export_plan.md",
    "command_catalog.md",
    "critic_coverage.md",
    "ledger_integrity.md",
    "candidate_readiness.md",
    "review_gap_register.md",
    "acceptance_trace.md",
    "demo_walkthrough.md",
    "course_boundary.md",
)


def get_review_pack_artifact_files() -> tuple[str, ...]:
    """Return generated review pack filenames without rendering their content."""

    return REVIEW_PACK_ARTIFACT_FILES
