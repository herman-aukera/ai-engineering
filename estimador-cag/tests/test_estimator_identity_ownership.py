from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.estimator.identity import SignedSessionCodec
from app.estimator.ownership_store import (
    EstimationOwnershipError,
    InMemoryEstimationOwnershipStore,
)


def test_estimator_signed_session_rejects_tampering_and_expiry() -> None:
    codec = SignedSessionCodec(b"x" * 32)
    token = codec.issue(
        subject="alice",
        tenant_id="tenant-a",
        roles=("member",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    actor = codec.verify(token)
    assert actor.owner_id == "tenant-a:alice"

    version, payload, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    with pytest.raises(ValueError, match="signature"):
        codec.verify(f"{version}.{payload}.{signature[:-1]}{replacement}")

    now = datetime.now(UTC)
    expired = codec.issue(
        subject="alice",
        tenant_id="tenant-a",
        roles=("member",),
        issued_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=5),
    )
    with pytest.raises(ValueError, match="expired"):
        codec.verify(expired)


def test_estimation_owner_claim_is_idempotent_and_cross_tenant_fails() -> None:
    store = InMemoryEstimationOwnershipStore()
    store.setup()
    store.claim("estimate-1", "tenant-a:alice")
    store.claim("estimate-1", "tenant-a:alice")
    store.assert_owner("estimate-1", "tenant-a:alice")

    with pytest.raises(EstimationOwnershipError, match="tenant_mismatch"):
        store.claim("estimate-1", "tenant-b:bob")
    with pytest.raises(EstimationOwnershipError, match="tenant_mismatch"):
        store.assert_owner("estimate-1", "tenant-b:bob")


def test_unknown_estimation_owner_fails_closed() -> None:
    store = InMemoryEstimationOwnershipStore()
    store.setup()
    with pytest.raises(EstimationOwnershipError, match="resource_owner_missing"):
        store.assert_owner("estimate-unknown", "tenant-a:alice")
