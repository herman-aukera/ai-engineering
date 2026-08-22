from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.energy_chat.identity import SignedSessionCodec
from app.energy_chat.ownership_store import (
    InMemoryResourceOwnershipStore,
    ResourceOwnershipError,
)


def test_signed_session_rejects_tampering_and_expiry() -> None:
    codec = SignedSessionCodec(b"x" * 32)
    token = codec.issue(
        subject="alice",
        tenant_id="tenant-a",
        roles=("member",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    actor = codec.verify(token)
    assert actor.subject == "alice"
    assert actor.tenant_id == "tenant-a"
    assert actor.owner_id == "tenant-a:alice"

    head, payload, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    with pytest.raises(ValueError, match="signature"):
        codec.verify(f"{head}.{payload}.{signature[:-1]}{replacement}")

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


def test_resource_owner_claim_is_idempotent_but_cross_tenant_access_fails() -> None:
    store = InMemoryResourceOwnershipStore()
    store.setup()

    store.claim("conversation", "conversation-1", "tenant-a:alice")
    store.claim("conversation", "conversation-1", "tenant-a:alice")
    store.assert_owner("conversation", "conversation-1", "tenant-a:alice")

    with pytest.raises(ResourceOwnershipError, match="tenant_mismatch"):
        store.assert_owner("conversation", "conversation-1", "tenant-b:bob")

    with pytest.raises(ResourceOwnershipError, match="tenant_mismatch"):
        store.claim("conversation", "conversation-1", "tenant-b:bob")


def test_unknown_resource_fails_closed() -> None:
    store = InMemoryResourceOwnershipStore()
    store.setup()

    with pytest.raises(ResourceOwnershipError, match="resource_owner_missing"):
        store.assert_owner("thread", "thread-unknown", "tenant-a:alice")
