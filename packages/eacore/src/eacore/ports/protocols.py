from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, TypeVar

from eacore.contracts import (
    CandidateRef,
    ConstraintObservation,
    CriticFindingEnvelope,
    DecisionEnvelope,
    EnergySnapshot,
    EvidenceRef,
    LedgerRecord,
)

CandidateT = TypeVar("CandidateT")


class ConstraintEvaluator(Protocol[CandidateT]):
    def evaluate(
        self, candidate: CandidateT, evidence: Sequence[EvidenceRef]
    ) -> Sequence[ConstraintObservation]: ...


class DecisionPolicy(Protocol):
    def decide(
        self,
        *,
        candidate: CandidateRef,
        energy: EnergySnapshot,
        findings: Sequence[CriticFindingEnvelope],
        evidence: Sequence[EvidenceRef],
    ) -> DecisionEnvelope: ...


class LedgerStore(Protocol):
    def append(self, record: LedgerRecord) -> bool: ...
    def read_all(self) -> Sequence[LedgerRecord]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
