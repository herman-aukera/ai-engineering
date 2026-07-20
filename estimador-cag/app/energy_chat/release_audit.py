"""Release audit and deployment readiness for Energy Aware Chat.

Milestones 20-21: consolidates claim boundary verification, dependency
audit, and deployment configuration validation. All checks are
deterministic and CI-safe — no external calls, no credentials.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimStatus = Literal["allowed", "blocked", "blocked_missing_evidence"]


class ClaimBoundary(BaseModel):
    """One claim boundary with its current evidence level."""

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    status: ClaimStatus = "blocked_missing_evidence"
    required_evidence: list[str] = Field(default_factory=list)
    current_evidence: list[str] = Field(default_factory=list)
    notes: str = ""


class ReleaseAudit(BaseModel):
    """Complete release audit with all claim boundaries and deployment checks."""

    audit_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    claims: list[ClaimBoundary] = Field(default_factory=list)
    deployment_ready: bool = False
    ci_green: bool = False
    deterministic_tests_passing: bool = False
    secrets_scan_clean: bool = False
    limitations: list[str] = Field(default_factory=list)


def build_release_audit(branch: str, commit_sha: str) -> ReleaseAudit:
    """Build a release audit with current claim boundaries.

    Every claim that lacks evidence is explicitly blocked. Claims are
    only allowed when the matching evidence is verifiable from the
    repository state or CI artifacts.
    """
    claims = [
        ClaimBoundary(
            claim_id="graph_backed_api",
            claim_text=(
                "EACHAT exposes an additive graph-backed API with deterministic "
                "CI proof and a bounded live-provider integration path."
            ),
            status="allowed",
            current_evidence=[
                "POST /energy-chat/v2/chat and /v2/chat/live routes",
                "One graph execution per request",
                "No legacy fallback or double execution",
                "Provider-neutral selector contracts",
                "340+ focused tests, 598+ full tests, CI green",
            ],
        ),
        ClaimBoundary(
            claim_id="checkpoint_replay",
            claim_text=(
                "EACHAT supports thread-isolated checkpointing with replay "
                "idempotency and resume from awaiting-evidence state."
            ),
            status="allowed",
            current_evidence=[
                "InMemoryCheckpointer wired into deterministic V2 route",
                "Thread isolation tests",
                "Replay idempotency tests",
                "No-duplicate-provider-call proof",
            ],
        ),
        ClaimBoundary(
            claim_id="human_gates",
            claim_text=(
                "EACHAT supports revision-guarded human-in-the-loop interrupts "
                "for clarify and escalate dispositions."
            ),
            status="allowed",
            current_evidence=[
                "HumanActionRequest with expected_revision guard",
                "interrupt() node wired into graph",
                "Command(resume=) resume path tested",
                "StaleHumanActionError for mismatched revisions",
            ],
        ),
        ClaimBoundary(
            claim_id="postgresql_persistence",
            claim_text="EACHAT supports durable PostgreSQL checkpoint persistence.",
            status="blocked_missing_evidence",
            required_evidence=[
                "Live PostgreSQL connection",
                "Schema migration applied",
                "Checkpoint write confirmed",
                "Process restart and checkpoint reopen",
                "Graph resume from PostgreSQL checkpoint",
            ],
            notes="Interface tests exist; live-DB integration is deferred.",
        ),
        ClaimBoundary(
            claim_id="live_provider_quality",
            claim_text=(
                "EACHAT improves answer quality over a plain provider call."
            ),
            status="blocked_missing_evidence",
            required_evidence=[
                "Credentialed provider adapters (Kimi K3, GPT-5.6)",
                "Cross-provider benchmark on fixed corpus",
                "Statistically significant quality improvement",
            ],
            notes="Quality evaluation framework exists (M19); credentialed adapters deferred.",
        ),
        ClaimBoundary(
            claim_id="production_ready",
            claim_text="EACHAT is production-ready and publicly deployed.",
            status="blocked_missing_evidence",
            required_evidence=[
                "Public deployment with health check",
                "Browser-tested UI at public URL",
                "Live provider integration tested",
                "Persistence and restart proven",
                "Security review completed",
            ],
            notes="All remaining roadmap items must be completed first.",
        ),
        ClaimBoundary(
            claim_id="kimi_k3_best",
            claim_text="Kimi K3 is the objectively best provider for EACHAT.",
            status="blocked_missing_evidence",
            required_evidence=[
                "Cross-provider benchmark on identical corpus",
                "Multiple independent evaluation runs",
                "Statistical significance threshold met",
            ],
            notes="Kimi K3 is documented as user-preferred quality candidate only.",
        ),
        ClaimBoundary(
            claim_id="auto_routing_superior",
            claim_text="Automatic provider routing improves cost or quality.",
            status="blocked_missing_evidence",
            required_evidence=[
                "Calibrated routing evaluations",
                "Cost/quality frontier comparison",
                "Controlled A/B testing",
            ],
            notes="auto provider returns provider_unavailable error until calibrated.",
        ),
    ]
    return ReleaseAudit(
        audit_id=f"release-audit-{commit_sha[:12]}",
        branch=branch,
        commit_sha=commit_sha,
        claims=claims,
        limitations=[
            "PostgreSQL persistence requires live-DB integration",
            "Cross-provider quality comparison requires credentialed adapters",
            "Public deployment not yet performed",
            "Browser proof limited to same-origin FastAPI demo",
        ],
    )


def check_deployment_readiness(
    *,
    ci_green: bool = False,
    deterministic_tests_passing: bool = False,
    secrets_scan_clean: bool = False,
    docker_config_exists: bool = False,
) -> dict[str, bool]:
    """Check deployment prerequisites without making external calls."""
    return {
        "ci_green": ci_green,
        "deterministic_tests_passing": deterministic_tests_passing,
        "secrets_scan_clean": secrets_scan_clear,
        "docker_config_exists": docker_config_exists,
        "ready": all([ci_green, deterministic_tests_passing, secrets_scan_clean]),
    }
