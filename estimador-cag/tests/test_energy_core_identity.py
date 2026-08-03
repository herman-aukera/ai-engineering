from datetime import UTC, datetime, timedelta

import pytest

from energy_core.identity import (
    IdentityProviderConfig,
    LinkedIdentity,
    LocalUser,
    SessionSigner,
)


def test_local_user_keeps_provider_identity_separate() -> None:
    user = LocalUser(
        user_id="user-1",
        display_name="Demo Admin",
        roles=("admin",),
        linked_identities=(
            LinkedIdentity(provider="google", subject="google-subject-1"),
        ),
    )

    assert user.user_id == "user-1"
    assert user.linked_identities[0].subject == "google-subject-1"


def test_backend_session_is_signed_expiring_and_tamper_evident() -> None:
    signer = SessionSigner(b"deterministic-test-key-at-least-32-bytes")
    expires = datetime.now(UTC) + timedelta(minutes=5)
    token = signer.issue(user_id="user-1", roles=("reviewer",), expires_at=expires)

    session = signer.verify(token)
    assert session.user_id == "user-1"
    assert session.roles == ("reviewer",)

    with pytest.raises(ValueError, match="signature"):
        signer.verify(token[:-1] + ("a" if token[-1] != "a" else "b"))


def test_google_oidc_configuration_is_google_first() -> None:
    config = IdentityProviderConfig(
        provider="google",
        client_id="configured-client-id",
        redirect_uri="http://localhost:8000/eacode/auth/google/callback",
        issuer="https://accounts.google.com",
    )
    assert config.readiness == "configured_not_live_verified"


def test_apple_requires_team_key_and_service_identifiers() -> None:
    with pytest.raises(ValueError, match="Apple"):
        IdentityProviderConfig(
            provider="apple",
            client_id="service-id",
            redirect_uri="https://example.test/eacode/auth/apple/callback",
            issuer="https://appleid.apple.com",
        )
