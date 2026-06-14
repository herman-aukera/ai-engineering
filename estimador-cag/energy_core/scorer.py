from __future__ import annotations

from collections.abc import Iterable

from energy_core.models import Violation


def total_energy(violations: Iterable[Violation]) -> int:
    return sum(violation.penalty for violation in violations)


def hard_reject_ids(violations: Iterable[Violation]) -> list[str]:
    return [
        violation.violation_id
        for violation in violations
        if violation.constraint_type == "hard_reject"
    ]


def hard_repair_ids(violations: Iterable[Violation]) -> list[str]:
    return [
        violation.violation_id
        for violation in violations
        if violation.constraint_type == "hard_repair"
    ]


def soft_ids(violations: Iterable[Violation]) -> list[str]:
    return [violation.violation_id for violation in violations if violation.constraint_type == "soft"]


def missing_evidence_ids(violations: Iterable[Violation]) -> list[str]:
    return [
        violation.violation_id
        for violation in violations
        if violation.violation_id == "missing_required_evidence"
    ]
