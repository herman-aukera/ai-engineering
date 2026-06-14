"""Deterministic evidence bundle helpers for project and research modes."""

from __future__ import annotations

import re

from app.energy_chat.contracts import (
    EvidenceBundleRequest,
    EvidenceBundleResult,
    EvidenceItem,
    EvidenceKind,
)

PREFIX_KIND_MAP: dict[str, EvidenceKind] = {
    "git:": "git",
    "test:": "test",
    "ci:": "ci",
    "file:": "file",
    "source:": "source",
    "web:": "web",
    "manual:": "manual",
    "cmd:": "cmd",
}

TRUSTED_KINDS: set[EvidenceKind] = {
    "git",
    "test",
    "ci",
    "file",
    "source",
    "web",
    "manual",
    "cmd",
}

PROJECT_STATE_KINDS: set[EvidenceKind] = {
    "git",
    "ci",
    "file",
    "manual",
    "cmd",
}

VALIDATION_KINDS: set[EvidenceKind] = {
    "test",
    "ci",
    "manual",
    "cmd",
}

CURRENT_SOURCE_KINDS: set[EvidenceKind] = {
    "web",
    "source",
    "file",
    "manual",
}


def build_evidence_bundle(request: EvidenceBundleRequest) -> EvidenceBundleResult:
    """Normalize refs and command outputs into a project/research evidence bundle."""

    refs = _deduplicate(
        [
            *_normalize_refs(request.evidence_refs),
            *_refs_from_command_outputs(request.command_outputs),
        ]
    )
    items = [build_evidence_item(ref) for ref in refs]
    trusted_refs = [item.ref for item in items if item.trusted]
    trusted_kinds = {item.source_type for item in items if item.trusted}

    can_support_project_claim = _can_support_project_claim(trusted_kinds)
    can_support_current_claim = bool(trusted_kinds & CURRENT_SOURCE_KINDS)
    missing_required_kinds = _missing_required_kinds(
        mode=request.mode,
        can_support_project_claim=can_support_project_claim,
        can_support_current_claim=can_support_current_claim,
    )

    if missing_required_kinds:
        next_action = "Attach the missing evidence kinds before accepting the claim."
    else:
        next_action = "Use the trusted refs as evidence_refs on the evaluation request."

    return EvidenceBundleResult(
        mode=request.mode,
        evidence_refs=refs,
        trusted_refs=trusted_refs,
        missing_required_kinds=missing_required_kinds,
        items=items,
        can_support_project_claim=can_support_project_claim,
        can_support_current_claim=can_support_current_claim,
        reasoning_summary=_reasoning_summary(
            trusted_kinds=trusted_kinds,
            missing_required_kinds=missing_required_kinds,
        ),
        next_action=next_action,
    )


def build_evidence_item(ref: str) -> EvidenceItem:
    """Build one typed evidence item from a normalized reference string."""

    source_type = _source_type(ref)
    trusted = source_type in TRUSTED_KINDS
    return EvidenceItem(
        ref=ref,
        source_type=source_type,
        trusted=trusted,
        summary=_summary(ref, source_type, trusted),
    )


def _source_type(ref: str) -> EvidenceKind:
    lowered = ref.casefold()
    for prefix, source_type in PREFIX_KIND_MAP.items():
        if lowered.startswith(prefix):
            return source_type
    return "unknown"


def _summary(ref: str, source_type: EvidenceKind, trusted: bool) -> str:
    if not trusted:
        return "Untrusted evidence ref because it uses no supported prefix."
    return f"Trusted {source_type} evidence ref: {ref}"


def _normalize_refs(refs: list[str]) -> list[str]:
    normalized: list[str] = []
    for ref in refs:
        value = ref.strip()
        if value:
            normalized.append(value)
    return normalized


def _refs_from_command_outputs(command_outputs: dict[str, str]) -> list[str]:
    refs: list[str] = []
    for command_name, output in sorted(command_outputs.items()):
        command = command_name.casefold()
        text = output.casefold()
        slug = _slug(command_name)

        if "git" in command and "status" in command and not output.strip():
            refs.append("git:status-clean")
            continue

        if "git" in command and "status" in command:
            if "working tree clean" in text or "nothing to commit" in text:
                refs.append("git:status-clean")
                continue

        if "ruff" in command and "all checks passed" in text:
            refs.append("test:ruff-passed")
            continue

        if ("pytest" in command or "test" in command) and "passed" in text:
            refs.append("test:pytest-passed")
            continue

        if "workflow" in command and ("success" in text or "completed" in text):
            refs.append("ci:workflow-success")
            continue

        if output.strip():
            refs.append(f"cmd:{slug}")
    return refs


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "command-output"


def _can_support_project_claim(trusted_kinds: set[EvidenceKind]) -> bool:
    has_project_state = bool(trusted_kinds & PROJECT_STATE_KINDS)
    has_validation = bool(trusted_kinds & VALIDATION_KINDS)
    return has_project_state and has_validation


def _missing_required_kinds(
    *,
    mode: str,
    can_support_project_claim: bool,
    can_support_current_claim: bool,
) -> list[str]:
    missing: list[str] = []
    if mode == "project" and not can_support_project_claim:
        missing.append("project_state_and_validation_evidence")
    if mode == "research" and not can_support_current_claim:
        missing.append("current_or_source_evidence")
    return missing


def _reasoning_summary(
    *,
    trusted_kinds: set[EvidenceKind],
    missing_required_kinds: list[str],
) -> str:
    if not trusted_kinds:
        return "No trusted evidence refs were attached."
    kinds = ", ".join(sorted(trusted_kinds))
    if missing_required_kinds:
        missing = ", ".join(missing_required_kinds)
        return f"Trusted evidence kinds found: {kinds}; missing: {missing}."
    return f"Trusted evidence kinds found: {kinds}."


def _deduplicate(refs: list[str]) -> list[str]:
    return list(dict.fromkeys(refs))
