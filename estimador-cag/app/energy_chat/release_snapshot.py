"""Release snapshot helpers for Energy Aware Chat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SnapshotStatus = Literal["green", "yellow", "red"]
BRANCH_NAME = "gg-finalproject-energy-aware-chat"
WORKFLOW_NAME = "Energy Aware Chat CI"
CLAIM_TOKEN = "measurement_only_no_quality_claim"


@dataclass(frozen=True)
class GateSnapshot:
    """One validation gate snapshot."""

    name: str
    status: SnapshotStatus
    summary: str
    ref: str


@dataclass(frozen=True)
class ReleaseSnapshot:
    """One release snapshot for a branch commit."""

    branch: str
    commit_sha: str
    focused_tests: int
    full_tests: int
    gates: tuple[GateSnapshot, ...]
    claim_token: str = CLAIM_TOKEN
    workflow: str = WORKFLOW_NAME

    @property
    def status(self) -> SnapshotStatus:
        """Aggregate status from gate snapshots."""

        if any(gate.status == "red" for gate in self.gates):
            return "red"
        if all(gate.status == "green" for gate in self.gates):
            return "green"
        return "yellow"

    @property
    def short_sha(self) -> str:
        """Return a compact commit identifier."""

        return self.commit_sha[:7]


def build_release_snapshot(
    *,
    commit_sha: str,
    focused_tests: int,
    full_tests: int,
    local_status: SnapshotStatus,
    ci_status: SnapshotStatus,
    local_ref: str,
    ci_ref: str,
    branch: str = BRANCH_NAME,
    workflow: str = WORKFLOW_NAME,
) -> ReleaseSnapshot:
    """Build a release snapshot from already observed gate evidence."""

    return ReleaseSnapshot(
        branch=branch,
        commit_sha=commit_sha,
        focused_tests=focused_tests,
        full_tests=full_tests,
        workflow=workflow,
        gates=(
            GateSnapshot(
                name="local gate",
                status=local_status,
                summary=f"{focused_tests} focused tests and {full_tests} full tests passed",
                ref=local_ref,
            ),
            GateSnapshot(
                name="ci gate",
                status=ci_status,
                summary=f"{workflow} completed for the exact commit",
                ref=ci_ref,
            ),
        ),
    )


def build_release_snapshot_markdown(snapshot: ReleaseSnapshot) -> str:
    """Render a compact release snapshot as Markdown."""

    lines = [
        "# Energy Aware Chat release snapshot",
        "",
        f"- Branch: `{snapshot.branch}`",
        f"- Commit: `{snapshot.commit_sha}`",
        f"- Status: `{snapshot.status}`",
        f"- Workflow: `{snapshot.workflow}`",
        f"- Claim token: `{snapshot.claim_token}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Ref | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for gate in snapshot.gates:
        summary = gate.summary.replace("|", "\\|")
        lines.append(f"| {gate.name} | {gate.status} | {gate.ref} | {summary} |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This snapshot records validation evidence for the current demo artifact. ",
            "It is not a replacement for a later production release checklist.",
        ]
    )
    return "\n".join(lines) + "\n"
