"""FastAPI binding for signed estimator actor identity."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from app.estimator.identity import ActorContext, SignedSessionCodec


def require_actor(
    request: Request,
    authorization: str | None = Header(default=None),
) -> ActorContext:
    signing_key = getattr(request.app.state, "estimator_identity_signing_key", None)
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
    try:
        actor = SignedSessionCodec(signing_key).verify(
            authorization.removeprefix("Bearer ").strip()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_session", "detail": "Invalid or expired signed session."},
        ) from exc
    request.state.estimator_actor = actor
    return actor


def current_actor(request: Request) -> ActorContext | None:
    actor = getattr(request.state, "estimator_actor", None)
    return actor if isinstance(actor, ActorContext) else None
