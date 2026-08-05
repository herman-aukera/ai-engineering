"""Evidence-driven release and production-readiness audit for EACHAT."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimStatus = Literal["allowed", "blocked", "blocked_missing_evidence"]


class ClaimBoundary(BaseModel):
    """One claim and the exact evidence required to make it."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    status: ClaimStatus = "blocked_missing_evidence"
    required_evidence: list[str] = Field(default_factory=list)
    current_evidence: list[str] = Field(default_factory=list)
    notes: str = ""


class ReleaseEvidence(BaseModel):
    """Observed release facts supplied by CI, smoke tests, and deployment checks."""

    model_config = ConfigDict(extra="forbid")

    exact_head_ci_green: bool = False
    deterministic_tests_passing: bool = False
    process_local_replay_proven: bool = False
    human_resume_proven: bool = False
    postgres_restart_proven: bool = False
    postgres_redaction_retention_proven: bool = False
    browser_contract_tests_passing: bool = False
    browser_smoke_proven: bool = False
    live_provider_smoke_proven: bool = False
    fixed_corpus_quality_benchmark_proven: bool = False
    context_compaction_runtime_proven: bool = False
    multi_agent_runtime_proven: bool = False
    auto_routing_calibrated: bool = False
    kimi_superiority_benchmark_proven: bool = False
    secrets_scan_clean: bool = False
    docker_config_exists: bool = False
    security_review_complete: bool = False
    deployment_health_proven: bool = False


class ReleaseAudit(BaseModel):
    """Release audit whose allowed claims derive only from supplied evidence."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    evidence: ReleaseEvidence = Field(default_factory=ReleaseEvidence)
    claims: list[ClaimBoundary] = Field(default_factory=list)
    deployment_ready: bool = False
    ci_green: bool = False
    deterministic_tests_passing: bool = False
    secrets_scan_clean: bool = False
    limitations: list[str] = Field(default_factory=list)


def _claim(
    *,
    claim_id: str,
    claim_text: str,
    allowed: bool,
    required_evidence: list[str],
    current_evidence: list[str],
    notes: str = "",
) -> ClaimBoundary:
    return ClaimBoundary(
        claim_id=claim_id,
        claim_text=claim_text,
        status="allowed" if allowed else "blocked_missing_evidence",
        required_evidence=[] if allowed else required_evidence,
        current_evidence=current_evidence if allowed else [],
        notes=notes,
    )


def build_release_audit(
    branch: str,
    commit_sha: str,
    *,
    evidence: ReleaseEvidence | None = None,
) -> ReleaseAudit:
    """Build claim boundaries from observed evidence instead of repository folklore."""

    observed = evidence or ReleaseEvidence()
    deterministic_core = (
        observed.exact_head_ci_green and observed.deterministic_tests_passing
    )
    postgres_complete = (
        observed.postgres_restart_proven
        and observed.postgres_redaction_retention_proven
    )
    readiness = check_deployment_readiness(
        exact_head_ci_green=observed.exact_head_ci_green,
        deterministic_tests_passing=observed.deterministic_tests_passing,
        secrets_scan_clean=observed.secrets_scan_clean,
        docker_config_exists=observed.docker_config_exists,
        postgres_restart_proven=observed.postgres_restart_proven,
        browser_smoke_proven=observed.browser_smoke_proven,
        live_provider_smoke_proven=observed.live_provider_smoke_proven,
        security_review_complete=observed.security_review_complete,
        deployment_health_proven=observed.deployment_health_proven,
    )

    claims = [
        _claim(
            claim_id="graph_backed_api",
            claim_text=(
                "EACHAT exposes a deterministic graph-backed V2 API with typed "
                "Energy Card and Decision Ledger projections."
            ),
            allowed=deterministic_core,
            required_evidence=[
                "Exact-head remote CI success",
                "Deterministic full-suite success",
            ],
            current_evidence=[
                "Exact-head CI evidence supplied",
                "Deterministic regression evidence supplied",
            ],
        ),
        _claim(
            claim_id="checkpoint_replay",
            claim_text=(
                "EACHAT supports thread-isolated checkpoint replay without another "
                "graph or provider execution."
            ),
            allowed=observed.process_local_replay_proven,
            required_evidence=["Replay idempotency and no-second-call integration proof"],
            current_evidence=["Process-local replay integration evidence supplied"],
        ),
        _claim(
            claim_id="human_gates",
            claim_text=(
                "EACHAT supports typed, revision-guarded human interrupt and resume."
            ),
            allowed=observed.human_resume_proven,
            required_evidence=["Interrupt, stale-revision, and resume integration proof"],
            current_evidence=["Human interrupt/resume evidence supplied"],
            notes=(
                "The current actions are clarify_response and escalate_response; "
                "authoritative approve/adjust/reject policy is not implemented."
            ),
        ),
        _claim(
            claim_id="postgresql_persistence",
            claim_text=(
                "EACHAT supports PostgreSQL checkpoint restart, resume, redaction, "
                "and retention."
            ),
            allowed=postgres_complete,
            required_evidence=[
                "Checkpoint reopen and resume after process replacement",
                "Persisted redaction and retention execution",
            ],
            current_evidence=[
                "PostgreSQL restart evidence supplied",
                "PostgreSQL redaction and retention evidence supplied",
            ],
        ),
        _claim(
            claim_id="browser_product_contract",
            claim_text=(
                "EACHAT serves a same-origin V2 chat product client wired to graph, "
                "thread, replay, state, and human-response endpoints."
            ),
            allowed=observed.browser_contract_tests_passing,
            required_evidence=["Browser-client route and endpoint contract tests"],
            current_evidence=["Browser product contract-test evidence supplied"],
            notes="This claim does not replace a real browser smoke test.",
        ),
        _claim(
            claim_id="context_compaction_runtime",
            claim_text="EACHAT executes context compaction in the active graph runtime.",
            allowed=observed.context_compaction_runtime_proven,
            required_evidence=[
                "Runtime compaction node execution",
                "Drift and source-range tests",
                "Checkpointed compacted-context evidence",
            ],
            current_evidence=["Context-compaction runtime evidence supplied"],
            notes="Milestone 18 currently provides contract scaffolding only.",
        ),
        _claim(
            claim_id="multi_agent_runtime",
            claim_text=(
                "EACHAT executes bounded committee or adaptive multi-agent orchestration."
            ),
            allowed=observed.multi_agent_runtime_proven,
            required_evidence=[
                "Real committee or adaptive graph topology",
                "Budget enforcement and adjudication tests",
                "Execution trace from the active runtime",
            ],
            current_evidence=["Multi-agent runtime evidence supplied"],
            notes="Milestone 18 currently provides budget contract scaffolding only.",
        ),
        _claim(
            claim_id="live_provider_quality",
            claim_text="EACHAT measurably improves live-provider answer quality.",
            allowed=(
                observed.live_provider_smoke_proven
                and observed.fixed_corpus_quality_benchmark_proven
            ),
            required_evidence=[
                "Credentialed live-provider smoke",
                "Matched fixed-corpus baseline and EACHAT benchmark",
                "Predeclared quality rubric and limitations",
            ],
            current_evidence=[
                "Live-provider smoke evidence supplied",
                "Fixed-corpus quality benchmark evidence supplied",
            ],
        ),
        _claim(
            claim_id="production_ready",
            claim_text="EACHAT is production-ready and health-checked in deployment.",
            allowed=readiness["ready"],
            required_evidence=[
                "Exact-head CI and deterministic regression",
                "Secrets scan and reviewed container configuration",
                "PostgreSQL restart proof",
                "Real browser smoke",
                "Credentialed live-provider smoke",
                "Security review",
                "Deployed health check",
            ],
            current_evidence=["Every production-readiness gate supplied"],
        ),
        _claim(
            claim_id="kimi_k3_best",
            claim_text="Kimi K3 is objectively the best provider for EACHAT.",
            allowed=observed.kimi_superiority_benchmark_proven,
            required_evidence=[
                "Matched cross-provider benchmark",
                "Repeated runs and statistical analysis",
            ],
            current_evidence=["Kimi superiority benchmark evidence supplied"],
        ),
        _claim(
            claim_id="auto_routing_superior",
            claim_text="Automatic provider routing improves cost or quality.",
            allowed=observed.auto_routing_calibrated,
            required_evidence=[
                "Calibrated routing evaluation",
                "Cost-quality frontier comparison",
            ],
            current_evidence=["Automatic routing calibration evidence supplied"],
        ),
    ]
    blocked = [claim.claim_id for claim in claims if claim.status != "allowed"]
    return ReleaseAudit(
        audit_id=f"release-audit-{commit_sha[:12]}",
        branch=branch,
        commit_sha=commit_sha,
        evidence=observed,
        claims=claims,
        deployment_ready=readiness["ready"],
        ci_green=observed.exact_head_ci_green,
        deterministic_tests_passing=observed.deterministic_tests_passing,
        secrets_scan_clean=observed.secrets_scan_clean,
        limitations=[f"Blocked claim: {claim_id}" for claim_id in blocked],
    )


def check_deployment_readiness(
    *,
    exact_head_ci_green: bool = False,
    deterministic_tests_passing: bool = False,
    secrets_scan_clean: bool = False,
    docker_config_exists: bool = False,
    postgres_restart_proven: bool = False,
    browser_smoke_proven: bool = False,
    live_provider_smoke_proven: bool = False,
    security_review_complete: bool = False,
    deployment_health_proven: bool = False,
) -> dict[str, bool]:
    """Require every production gate; deterministic CI alone is insufficient."""

    gates = {
        "exact_head_ci_green": exact_head_ci_green,
        "deterministic_tests_passing": deterministic_tests_passing,
        "secrets_scan_clean": secrets_scan_clean,
        "docker_config_exists": docker_config_exists,
        "postgres_restart_proven": postgres_restart_proven,
        "browser_smoke_proven": browser_smoke_proven,
        "live_provider_smoke_proven": live_provider_smoke_proven,
        "security_review_complete": security_review_complete,
        "deployment_health_proven": deployment_health_proven,
    }
    return {**gates, "ready": all(gates.values())}
