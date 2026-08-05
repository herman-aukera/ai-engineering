"""Deterministic EACODE beta journey with server-owned authority boundaries."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field

from energy_core.coding_agent import CodingProposal
from energy_core.models import EnergyModel
from energy_core.semantic_jury import (
    ActionGovernor,
    DeterministicHardGateResult,
    GovernorDecision,
    HardGateFinding,
    JuryResult,
    SemanticJudgeResult,
    SemanticJury,
)

TimelineType = Literal[
    "proposal",
    "hard_gate",
    "jury",
    "repair",
    "authorization",
    "execution",
    "rollback",
    "reevaluation",
]
AuthorizationSource = Literal["none", "server_session_receipt"]

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
_TEST_WEAKENING_PATTERNS = (
    "pytest.skip",
    "@unittest.skip",
    "@pytest.mark.skip",
    "assert true",
)
_ALLOWED_EXECUTABLES = {"git", "pytest", "python", "python3", "ruff", "uv"}
_ALLOWED_GIT_SUBCOMMANDS = {"diff", "rev-parse", "status"}
_HUMAN_REVIEW_PREFIXES = (
    ".github/workflows/",
    "deploy/",
    "infra/",
    "migrations/",
)


class RepairRecord(EnergyModel):
    revision: int = Field(ge=1)
    reason: str
    patch_before: str
    patch_after: str


class AuthorizationRecord(EnergyModel):
    proposal_id: str
    authorized: bool
    actor: str | None = None
    scope: tuple[tuple[str, ...], ...]
    authorization_id: str | None = None
    source: AuthorizationSource = "none"


class DemoExecutionEvidence(EnergyModel):
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    sanitized: bool
    execution_performed: bool
    mode: Literal["simulated"] = "simulated"


class RollbackState(EnergyModel):
    available: bool
    performed: bool = False
    summary: str


class TimelineRecord(EnergyModel):
    sequence: int = Field(ge=1)
    event_type: TimelineType
    summary: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class BetaDemoResult(EnergyModel):
    proposal: CodingProposal
    effective_proposal: CodingProposal
    hard_gate: DeterministicHardGateResult
    initial_jury: JuryResult
    initial_decision: GovernorDecision
    repair_history: tuple[RepairRecord, ...]
    authorization: AuthorizationRecord
    execution: DemoExecutionEvidence
    rollback: RollbackState
    final_jury: JuryResult
    final_decision: GovernorDecision
    timeline: tuple[TimelineRecord, ...]


def evaluate_beta_hard_gates(proposal: CodingProposal) -> DeterministicHardGateResult:
    """Evaluate concrete proposal content; an empty finding set is never used as proof."""

    findings: list[HardGateFinding] = []

    def add(
        finding_id: str,
        constraint: str,
        passed: bool,
        summary: str,
        evidence_refs: tuple[str, ...],
    ) -> None:
        findings.append(
            HardGateFinding(
                finding_id=finding_id,
                constraint=constraint,
                status="pass" if passed else "fail",
                summary=summary,
                evidence_refs=evidence_refs,
            )
        )

    add(
        "changed-files-present",
        "proposal must identify at least one changed file",
        bool(proposal.changed_files),
        "Changed-file scope is present." if proposal.changed_files else "No changed files were declared.",
        ("proposal.changed_files",),
    )

    normalized_paths = tuple(path.replace("\\", "/") for path in proposal.changed_files)
    safe_paths = all(
        path
        and not path.startswith("/")
        and not re.match(r"^[A-Za-z]:/", path)
        and ".." not in path.split("/")
        for path in normalized_paths
    )
    add(
        "changed-files-safe",
        "changed files must be repository-relative and traversal-free",
        safe_paths,
        "Changed paths are repository-relative."
        if safe_paths
        else "An absolute or traversal path was proposed.",
        ("proposal.changed_files",),
    )

    diff_size_ok = len(proposal.patch.encode("utf-8")) <= 20_000
    add(
        "bounded-diff",
        "proposal patch must remain within the deterministic beta size budget",
        diff_size_ok,
        "Patch is within the 20 KB beta budget."
        if diff_size_ok
        else "Patch exceeds the 20 KB beta budget.",
        ("proposal.patch",),
    )

    secret_free = not any(pattern.search(proposal.patch) for pattern in _SECRET_PATTERNS)
    add(
        "secret-hygiene",
        "proposal patch must not contain likely credentials or private keys",
        secret_free,
        "No credential-shaped material was detected."
        if secret_free
        else "Credential-shaped material was detected.",
        ("proposal.patch",),
    )

    lowered_patch = proposal.patch.lower()
    tests_not_weakened = not any(
        marker in lowered_patch for marker in _TEST_WEAKENING_PATTERNS
    )
    add(
        "test-integrity",
        "proposal must not weaken tests through skip or tautological assertions",
        tests_not_weakened,
        "No deterministic test-weakening marker was detected."
        if tests_not_weakened
        else "A deterministic test-weakening marker was detected.",
        ("proposal.patch",),
    )

    commands_safe = all(_command_is_allowed(command) for command in proposal.proposed_commands)
    add(
        "command-allowlist",
        "all proposed commands must use the bounded read/test allowlist",
        commands_safe,
        "All proposed commands are within the beta allowlist."
        if commands_safe
        else "At least one proposed command is outside the beta allowlist.",
        ("proposal.proposed_commands",),
    )

    human_review_required = any(
        path.startswith(prefix)
        for path in normalized_paths
        for prefix in _HUMAN_REVIEW_PREFIXES
    )
    return DeterministicHardGateResult(
        candidate_id=proposal.proposal_id,
        findings=tuple(findings),
        human_review_required=human_review_required,
    )


def evaluate_beta_semantic_jury(proposal: CodingProposal) -> JuryResult:
    """Produce two independently identified deterministic rubric observations."""

    issues: list[str] = []
    if "todo" in proposal.patch.lower():
        issues.append("placeholder_remains")
    if not proposal.proposed_commands:
        issues.append("validation_evidence_missing")
    if proposal.spec_id.lower().startswith(("stale:", "deprecated:")):
        issues.append("stale_spec_reference")

    disposition = "repair" if issues else "accept"
    summary = (
        "Repair required: " + ", ".join(issues)
        if issues
        else "Proposal is coherent with the deterministic beta rubric."
    )
    results = (
        SemanticJudgeResult(
            judge_id="beta-rubric-structure",
            provider="deterministic-ruleset",
            model="structure-v2",
            disposition=disposition,
            summary=summary,
            evidence_refs=("proposal.patch", "proposal.proposed_commands"),
        ),
        SemanticJudgeResult(
            judge_id="beta-rubric-evidence",
            provider="deterministic-evidence-policy",
            model="evidence-v2",
            disposition=disposition,
            summary=summary,
            evidence_refs=("proposal.spec_id", "proposal.proposed_commands"),
        ),
    )
    return SemanticJury().aggregate(results)


class BetaDemoRunner:
    """Prepare and execute a deterministic journey without accepting client authority."""

    def prepare(self, proposal: CodingProposal) -> BetaDemoResult:
        timeline: list[TimelineRecord] = [
            TimelineRecord(
                sequence=1,
                event_type="proposal",
                summary="Provider-neutral coding proposal received; no execution capability attached.",
            )
        ]
        hard_gate = evaluate_beta_hard_gates(proposal)
        timeline.append(
            TimelineRecord(
                sequence=2,
                event_type="hard_gate",
                summary=(
                    "Deterministic hard gates passed."
                    if hard_gate.passed
                    else "Deterministic hard gates rejected the proposal."
                ),
                evidence_refs=tuple(finding.finding_id for finding in hard_gate.findings),
            )
        )

        initial_jury = evaluate_beta_semantic_jury(proposal)
        timeline.append(
            TimelineRecord(
                sequence=3,
                event_type="jury",
                summary="Two independently identified rubric judges produced semantic evidence.",
                evidence_refs=tuple(result.judge_id for result in initial_jury.results),
            )
        )
        initial_decision = ActionGovernor().decide(
            hard_gate=hard_gate,
            jury=initial_jury,
        )

        effective_proposal = proposal
        repairs: tuple[RepairRecord, ...] = ()
        if hard_gate.passed and initial_decision.disposition == "repair":
            repaired_patch = _repair_patch(proposal.patch)
            if repaired_patch != proposal.patch:
                effective_proposal = proposal.model_copy(update={"patch": repaired_patch})
                repairs = (
                    RepairRecord(
                        revision=1,
                        reason="Replace deterministic placeholder with a concrete safe value.",
                        patch_before=proposal.patch,
                        patch_after=repaired_patch,
                    ),
                )
                timeline.append(
                    TimelineRecord(
                        sequence=4,
                        event_type="repair",
                        summary="A bounded repair produced a new effective proposal revision.",
                        evidence_refs=("repair-1",),
                    )
                )

        effective_jury = evaluate_beta_semantic_jury(effective_proposal)
        pending_decision = _pending_decision(
            initial_decision=initial_decision,
            effective_jury=effective_jury,
            hard_gate=hard_gate,
        )
        return BetaDemoResult(
            proposal=proposal,
            effective_proposal=effective_proposal,
            hard_gate=hard_gate,
            initial_jury=initial_jury,
            initial_decision=initial_decision,
            repair_history=repairs,
            authorization=AuthorizationRecord(
                proposal_id=proposal.proposal_id,
                authorized=False,
                actor=None,
                scope=effective_proposal.proposed_commands,
                authorization_id=None,
                source="none",
            ),
            execution=DemoExecutionEvidence(
                command=_primary_command(effective_proposal),
                exit_code=None,
                stdout="",
                stderr="",
                sanitized=True,
                execution_performed=False,
            ),
            rollback=RollbackState(
                available=bool(effective_proposal.changed_files),
                summary=(
                    "Simulated rollback can restore the pre-proposal snapshot."
                    if effective_proposal.changed_files
                    else "No changed-file snapshot exists."
                ),
            ),
            final_jury=effective_jury,
            final_decision=pending_decision,
            timeline=tuple(timeline),
        )

    def validate_for_authorization(self, result: BetaDemoResult) -> None:
        if not result.hard_gate.passed:
            raise PermissionError("A hard-rejected proposal cannot be authorized.")
        if result.execution.execution_performed:
            raise PermissionError("The proposal has already been executed.")
        if result.final_jury.recommended_disposition != "accept":
            raise PermissionError("The effective proposal still requires repair.")
        if result.authorization.authorized:
            raise PermissionError("The proposal is already authorized.")

    def authorization_scope(self, result: BetaDemoResult) -> tuple[tuple[str, ...], ...]:
        self.validate_for_authorization(result)
        return result.effective_proposal.proposed_commands

    def execute(
        self,
        result: BetaDemoResult,
        *,
        authorization_id: str,
        actor: str,
    ) -> BetaDemoResult:
        self.validate_for_authorization(result)
        if not authorization_id:
            raise ValueError("authorization_id is required.")
        if not actor:
            raise ValueError("actor is required.")

        timeline = list(result.timeline)
        timeline.append(
            TimelineRecord(
                sequence=len(timeline) + 1,
                event_type="authorization",
                summary="A server-verified operator session consumed a one-time authorization receipt.",
                evidence_refs=(authorization_id,),
            )
        )

        execution = DemoExecutionEvidence(
            command=_primary_command(result.effective_proposal),
            exit_code=0,
            stdout="Simulated bounded command completed; output sanitized.",
            stderr="",
            sanitized=True,
            execution_performed=True,
        )
        timeline.append(
            TimelineRecord(
                sequence=len(timeline) + 1,
                event_type="execution",
                summary="Bounded execution was simulated after server-owned authorization.",
                evidence_refs=("simulated-exit-0",),
            )
        )
        timeline.append(
            TimelineRecord(
                sequence=len(timeline) + 1,
                event_type="rollback",
                summary="Rollback snapshot remains available for the effective proposal.",
                evidence_refs=("rollback-snapshot",),
            )
        )

        final_hard_gate = evaluate_beta_hard_gates(result.effective_proposal)
        final_jury = evaluate_beta_semantic_jury(result.effective_proposal)
        final_decision = ActionGovernor().decide(
            hard_gate=final_hard_gate,
            jury=final_jury,
        )
        timeline.append(
            TimelineRecord(
                sequence=len(timeline) + 1,
                event_type="reevaluation",
                summary="The deterministic governor reevaluated the effective proposal and execution evidence.",
                evidence_refs=("simulated-exit-0", *tuple(r.judge_id for r in final_jury.results)),
            )
        )
        return result.model_copy(
            update={
                "authorization": AuthorizationRecord(
                    proposal_id=result.proposal.proposal_id,
                    authorized=True,
                    actor=actor,
                    scope=result.effective_proposal.proposed_commands,
                    authorization_id=authorization_id,
                    source="server_session_receipt",
                ),
                "execution": execution,
                "final_jury": final_jury,
                "final_decision": final_decision,
                "timeline": tuple(timeline),
            }
        )


def _command_is_allowed(command: tuple[str, ...]) -> bool:
    if not command:
        return False
    executable = command[0].lower()
    if executable not in _ALLOWED_EXECUTABLES:
        return False
    if executable == "git":
        return len(command) >= 2 and command[1].lower() in _ALLOWED_GIT_SUBCOMMANDS
    dangerous_tokens = {"--privileged", "--no-preserve-root", "/dev/sda", "sudo"}
    return not any(token.lower() in dangerous_tokens for token in command[1:])


def _repair_patch(patch: str) -> str:
    repaired = re.sub(r"(?i)(['\"])todo\1", lambda match: f"{match.group(1)}ok{match.group(1)}", patch)
    return repaired


def _primary_command(proposal: CodingProposal) -> tuple[str, ...]:
    return proposal.proposed_commands[0] if proposal.proposed_commands else ()


def _pending_decision(
    *,
    initial_decision: GovernorDecision,
    effective_jury: JuryResult,
    hard_gate: DeterministicHardGateResult,
) -> GovernorDecision:
    if initial_decision.disposition == "reject":
        return initial_decision
    if effective_jury.recommended_disposition != "accept":
        return GovernorDecision(
            disposition="repair",
            reason="The effective proposal still has unresolved semantic defects.",
        )
    return GovernorDecision(
        disposition="escalate",
        human_review_required=True,
        reason=(
            "Server-owned operator authorization and execution evidence are required."
            if not hard_gate.human_review_required
            else "Protected-surface change requires explicit operator authorization."
        ),
    )
