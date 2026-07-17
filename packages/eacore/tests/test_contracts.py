from datetime import datetime, timezone
import math

import pytest
from pydantic import ValidationError

from eacore.contracts import (
    ConstraintObservation,
    EnergySnapshot,
    EvidenceRef,
    ObservationStatus,
    RedactionStatus,
    Sensitivity,
    TrustClass,
    UnsupportedMajorVersionError,
    VerificationStatus,
    VersionIdentity,
)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        VersionIdentity(
            contract_name="candidate-ref",
            contract_version="0.1.0",
            schema_version="1.0.0",
            surprise=True,
        )


def test_missing_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        VersionIdentity(contract_name="candidate-ref", contract_version="0.1.0")


def test_unsupported_major_fails_closed() -> None:
    version = VersionIdentity(
        contract_name="candidate-ref", contract_version="0.1.0", schema_version="2.0.0"
    )
    with pytest.raises(UnsupportedMajorVersionError):
        version.require_supported_major(1)


def test_non_finite_energy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnergySnapshot(
            energy_snapshot_id="e",
            candidate_id="c",
            policy_ref="p",
            energy_before=0,
            energy_after=math.nan,
            energy_delta=math.nan,
            components=(),
        )


def test_passing_observation_cannot_add_penalty() -> None:
    with pytest.raises(ValidationError):
        ConstraintObservation(
            observation_id="o",
            constraint_id="c",
            status=ObservationStatus.PASS,
            penalty=1,
            summary="pass",
        )


def test_evidence_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            evidence_id="e",
            evidence_kind="test",
            source_ref="artifact:test",
            producer="pytest",
            recorded_at=datetime(2026, 7, 17),
            trust_classification=TrustClass.TRUSTED,
            verification_status=VerificationStatus.VERIFIED,
            sensitivity=Sensitivity.INTERNAL,
            redaction_status=RedactionStatus.REFERENCE_ONLY,
        )


def test_evidence_accepts_utc() -> None:
    evidence = EvidenceRef(
        evidence_id="e",
        evidence_kind="test",
        source_ref="artifact:test",
        producer="pytest",
        recorded_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
        trust_classification=TrustClass.TRUSTED,
        verification_status=VerificationStatus.VERIFIED,
        sensitivity=Sensitivity.INTERNAL,
        redaction_status=RedactionStatus.REFERENCE_ONLY,
    )
    assert evidence.recorded_at.tzinfo is not None
