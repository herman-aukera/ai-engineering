"""FastAPI binding for EACHAT signed actor identity."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from app.energy_chat.identity import ActorContext, SignedSessionCodec


def require_actor(
    request: Request,
    authorization: str | None = Header(default=None),
) -> ActorContext:
    """Authenticate one production request and bind its actor for downstream ownership."""

    signing_key = getattr(request.app.state, "eachat_identity_signing_key", None)
    if not isinstance(signing_key, bytes) or len(signing_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "identity_unavailable", "detail": "Signed identity is not configured."},
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication_required", "detail": "Bearer signed session required."},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        actor = SignedSessionCodec(signing_key).verify(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_session", "detail": "Invalid or expired signed session."},
        ) from exc
    request.state.energy_chat_actor = actor
    return actor


def current_actor(request: Request) -> ActorContext | None:
    """Return authenticated production actor, or None in legacy/coursework applications."""

    actor = getattr(request.state, "energy_chat_actor", None)
    return actor if isinstance(actor, ActorContext) else None
