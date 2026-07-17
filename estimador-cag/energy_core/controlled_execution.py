from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, model_validator

from energy_core.models import EnergyModel, EvidenceRecord

CommandRisk = Literal["low", "medium", "high", "denied"]
ExecutionDisposition = Literal["allow_fake", "human_required", "deny"]
ExecutionMode = Literal["dry_run", "fake"]

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
]
_SHELL_META = ("&&", "||", ";", "|", ">", "<", "`", "$(", "\n", "\r", "\x00")


class CommandProposal(EnergyModel):
    proposal_id: str = Field(min_length=1, max_length=160)
    executable: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    arguments: list[str] = Field(default_factory=list, max_length=64)
    working_directory: str = Field(default=".", min_length=1, max_length=500)
    declared_paths: list[str] = Field(default_factory=list, max_length=64)
    requested_mode: ExecutionMode = "dry_run"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_output_chars: int = Field(default=12_000, ge=128, le=100_000)
    environment_names: list[str] = Field(default_factory=list, max_length=32)
    rollback_summary: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_arguments(self) -> CommandProposal:
        if any(not isinstance(value, str) for value in self.arguments):
            raise ValueError("arguments must be strings")
        if len(set(self.environment_names)) != len(self.environment_names):
            raise ValueError("environment_names must be unique")
        return self


class CommandPolicy(EnergyModel):
    policy_id: str = "eacode-controlled-execution"
    version: str = "1.0.0"
    allowed_executables: list[str] = Field(
        default_factory=lambda: ["pytest", "ruff", "python", "python3", "uv"]
    )
    human_required_executables: list[str] = Field(default_factory=lambda: ["git"])
    denied_executables: list[str] = Field(
        default_factory=lambda: [
            "bash",
            "cmd",
            "curl",
            "del",
            "mkfs",
            "powershell",
            "pwsh",
            "reboot",
            "rm",
            "rmdir",
            "scp",
            "sh",
            "shutdown",
            "ssh",
            "sudo",
            "wget",
            "zsh",
        ]
    )
    denied_git_subcommands: list[str] = Field(
        default_factory=lambda: [
            "branch",
            "checkout",
            "cherry-pick",
            "clean",
            "commit",
            "merge",
            "push",
            "rebase",
            "reset",
            "restore",
            "switch",
        ]
    )
    environment_allowlist: list[str] = Field(
        default_factory=lambda: ["PYTHONPATH", "PYTHONUNBUFFERED"]
    )
    max_timeout_seconds: int = Field(default=120, ge=1, le=300)
    max_output_chars: int = Field(default=20_000, ge=128, le=100_000)


class ExecutionPlan(EnergyModel):
    plan_id: str
    proposal_id: str
    policy_id: str
    policy_version: str
    repository_root: str
    working_directory: str
    executable: str
    arguments: list[str]
    risk: CommandRisk
    disposition: ExecutionDisposition
    requires_human_authorization: bool
    reasons: list[str] = Field(default_factory=list)
    timeout_seconds: int
    max_output_chars: int
    environment_names: list[str] = Field(default_factory=list)
    declared_paths: list[str] = Field(default_factory=list)
    execution_mode: ExecutionMode
    plan_hash: str
    rollback_summary: str | None = None
    execution_performed: bool = False


class FakeToolResult(EnergyModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = Field(default=0, ge=0)


class ExecutionEvidence(EnergyModel):
    schema_version: str = "1.0.0"
    evidence_id: str
    run_id: str
    proposal_id: str
    plan_hash: str
    status: Literal["pass", "fail", "missing", "conflict"]
    summary: str
    execution_mode: ExecutionMode
    execution_performed: bool = False
    adapter_invoked: bool = False
    exit_code: int | None = None
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    output_truncated: bool = False
    redaction_status: Literal["not_required", "redacted", "not_redacted", "unknown"] = (
        "not_required"
    )
    artifact_hash: str | None = None
    duration_ms: int | None = None
    rollback_available: bool = False
    trust_classification: Literal["trusted", "untrusted", "unknown"] = "trusted"
    policy_reasons: list[str] = Field(default_factory=list)

    def to_evidence_record(self) -> EvidenceRecord:
        return EvidenceRecord(
            schema_version=self.schema_version,
            evidence_id=self.evidence_id,
            run_id=self.run_id,
            type="controlled_execution",
            status=self.status,
            summary=self.summary,
            trusted=self.trust_classification == "trusted",
            trust_classification=self.trust_classification,
            provenance={
                "proposal_id": self.proposal_id,
                "execution_mode": self.execution_mode,
                "adapter_invoked": self.adapter_invoked,
                "execution_performed": self.execution_performed,
                "policy_reasons": list(self.policy_reasons),
            },
            redaction_status=self.redaction_status,
            command_hash=self.plan_hash,
            artifact_hash=self.artifact_hash,
            exit_code=self.exit_code,
        )


class ToolPort(Protocol):
    def invoke(self, plan: ExecutionPlan) -> FakeToolResult:
        """Return deterministic tool output without authorizing the plan."""


class FakeToolAdapter:
    def __init__(self, result: FakeToolResult | None = None) -> None:
        self._result = result or FakeToolResult()
        self.calls = 0

    def invoke(self, plan: ExecutionPlan) -> FakeToolResult:
        if plan.execution_mode != "fake":
            raise ValueError("FakeToolAdapter requires execution_mode=fake.")
        if plan.disposition != "allow_fake":
            raise PermissionError("Denied or human-gated plans must not reach the adapter.")
        self.calls += 1
        return self._result


def build_execution_plan(
    proposal: CommandProposal,
    *,
    repository_root: str | Path,
    policy: CommandPolicy | None = None,
) -> ExecutionPlan:
    """Build a deterministic, non-executing plan inside a bounded repository root."""

    effective_policy = policy or CommandPolicy()
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository_root must be a directory")
    working_directory = _resolve_within(root, root, proposal.working_directory, must_exist=True)
    if not working_directory.is_dir():
        raise ValueError("working_directory must resolve to a directory")

    reasons: list[str] = []
    risk: CommandRisk = "low"
    executable = proposal.executable.lower()

    if executable in effective_policy.denied_executables:
        reasons.append(f"executable_denied:{executable}")
        risk = "denied"
    elif executable in effective_policy.human_required_executables:
        risk = "high"
        reasons.append(f"executable_requires_human:{executable}")
    elif executable not in effective_policy.allowed_executables:
        reasons.append(f"executable_not_allowlisted:{executable}")
        risk = "denied"
    elif executable in {"python", "python3", "uv"}:
        risk = "medium"
        reasons.append(f"general_runtime:{executable}")

    argument_tokens = [value.strip() for value in proposal.arguments if value.strip()]
    if executable == "git" and argument_tokens:
        subcommand = argument_tokens[0].lower()
        if subcommand in effective_policy.denied_git_subcommands:
            reasons.append(f"git_subcommand_denied:{subcommand}")
            risk = "denied"

    for argument in proposal.arguments:
        if any(marker in argument for marker in _SHELL_META):
            reasons.append("shell_metacharacter_denied")
            risk = "denied"
            break

    resolved_paths: list[str] = []
    for raw_path in [*proposal.declared_paths, *_path_like_arguments(proposal.arguments)]:
        resolved = _resolve_within(root, working_directory, raw_path, must_exist=False)
        resolved_paths.append(resolved.relative_to(root).as_posix())

    unknown_environment = sorted(
        set(proposal.environment_names) - set(effective_policy.environment_allowlist)
    )
    if unknown_environment:
        reasons.append("environment_not_allowlisted:" + ",".join(unknown_environment))
        risk = "denied"

    if proposal.timeout_seconds > effective_policy.max_timeout_seconds:
        reasons.append("timeout_exceeds_policy")
        risk = "denied"
    if proposal.max_output_chars > effective_policy.max_output_chars:
        reasons.append("output_budget_exceeds_policy")
        risk = "denied"

    if risk == "denied":
        disposition: ExecutionDisposition = "deny"
    elif risk == "high":
        disposition = "human_required"
    else:
        disposition = "allow_fake"

    plan_payload = {
        "proposal_id": proposal.proposal_id,
        "policy_id": effective_policy.policy_id,
        "policy_version": effective_policy.version,
        "repository_root": str(root),
        "working_directory": str(working_directory),
        "executable": executable,
        "arguments": list(proposal.arguments),
        "risk": risk,
        "disposition": disposition,
        "reasons": sorted(set(reasons)),
        "timeout_seconds": proposal.timeout_seconds,
        "max_output_chars": proposal.max_output_chars,
        "environment_names": sorted(proposal.environment_names),
        "declared_paths": sorted(set(resolved_paths)),
        "execution_mode": proposal.requested_mode,
        "rollback_summary": proposal.rollback_summary,
    }
    plan_hash = _hash_payload(plan_payload)
    return ExecutionPlan(
        plan_id=f"plan-{plan_hash[:16]}",
        requires_human_authorization=disposition == "human_required",
        plan_hash=plan_hash,
        execution_performed=False,
        **plan_payload,
    )


def review_execution(
    proposal: CommandProposal,
    *,
    repository_root: str | Path,
    run_id: str,
    policy: CommandPolicy | None = None,
    adapter: ToolPort | None = None,
) -> tuple[ExecutionPlan, ExecutionEvidence]:
    """Plan a command and produce dry-run or deterministic fake evidence."""

    plan = build_execution_plan(
        proposal,
        repository_root=repository_root,
        policy=policy,
    )
    if plan.disposition == "deny":
        return plan, _non_execution_evidence(
            plan,
            run_id=run_id,
            status="fail",
            summary="Execution plan denied by deterministic command policy.",
        )
    if plan.disposition == "human_required":
        return plan, _non_execution_evidence(
            plan,
            run_id=run_id,
            status="missing",
            summary="Execution plan requires a separate human authorization record.",
        )
    if plan.execution_mode == "dry_run":
        return plan, _non_execution_evidence(
            plan,
            run_id=run_id,
            status="pass",
            summary="Dry-run plan validated; no tool adapter was invoked.",
        )

    tool = adapter or FakeToolAdapter()
    result = tool.invoke(plan)
    stdout, stdout_redacted = _redact(result.stdout)
    stderr, stderr_redacted = _redact(result.stderr)
    stdout, stdout_truncated = _truncate(stdout, plan.max_output_chars)
    stderr, stderr_truncated = _truncate(stderr, plan.max_output_chars)
    output_truncated = stdout_truncated or stderr_truncated
    redacted = stdout_redacted or stderr_redacted
    artifact_payload = {
        "exit_code": result.exit_code,
        "stdout_excerpt": stdout,
        "stderr_excerpt": stderr,
        "duration_ms": result.duration_ms,
    }
    status = "pass" if result.exit_code == 0 else "fail"
    return plan, ExecutionEvidence(
        evidence_id=f"execution-{plan.plan_hash[:16]}",
        run_id=run_id,
        proposal_id=plan.proposal_id,
        plan_hash=plan.plan_hash,
        status=status,
        summary=(
            "Deterministic fake tool evidence recorded."
            if status == "pass"
            else "Deterministic fake tool reported failure."
        ),
        execution_mode=plan.execution_mode,
        execution_performed=False,
        adapter_invoked=True,
        exit_code=result.exit_code,
        stdout_excerpt=stdout,
        stderr_excerpt=stderr,
        output_truncated=output_truncated,
        redaction_status="redacted" if redacted else "not_required",
        artifact_hash=_hash_payload(artifact_payload),
        duration_ms=result.duration_ms,
        rollback_available=bool((plan.rollback_summary or "").strip()),
        trust_classification="trusted",
        policy_reasons=list(plan.reasons),
    )


def _non_execution_evidence(
    plan: ExecutionPlan,
    *,
    run_id: str,
    status: Literal["pass", "fail", "missing", "conflict"],
    summary: str,
) -> ExecutionEvidence:
    return ExecutionEvidence(
        evidence_id=f"execution-{plan.plan_hash[:16]}",
        run_id=run_id,
        proposal_id=plan.proposal_id,
        plan_hash=plan.plan_hash,
        status=status,
        summary=summary,
        execution_mode=plan.execution_mode,
        execution_performed=False,
        adapter_invoked=False,
        redaction_status="not_required",
        rollback_available=bool((plan.rollback_summary or "").strip()),
        trust_classification="trusted",
        policy_reasons=list(plan.reasons),
    )


def _resolve_within(
    root: Path,
    base: Path,
    raw_value: str,
    *,
    must_exist: bool,
) -> Path:
    value = Path(raw_value)
    candidate = value if value.is_absolute() else base / value
    try:
        resolved = candidate.resolve(strict=must_exist)
    except FileNotFoundError as exc:
        raise ValueError(f"Path does not exist: {raw_value}") from exc
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes repository root: {raw_value}")
    return resolved


def _path_like_arguments(arguments: list[str]) -> list[str]:
    values: list[str] = []
    for argument in arguments:
        candidate = argument.split("=", 1)[1] if "=" in argument else argument
        if candidate.startswith(("http://", "https://")):
            continue
        if candidate.startswith((".", "/", "\\")) or "/" in candidate or "\\" in candidate:
            values.append(candidate)
    return values


def _redact(value: str) -> tuple[str, bool]:
    redacted = value
    changed = False
    for pattern in _SECRET_PATTERNS:
        updated = pattern.sub("[REDACTED]", redacted)
        changed = changed or updated != redacted
        redacted = updated
    return redacted, changed


def _truncate(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    suffix = "\n...[TRUNCATED]"
    keep = max(0, limit - len(suffix))
    return value[:keep] + suffix, True


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
