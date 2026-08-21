"""HTTP helpers for estimator ownership that preserve legacy coursework compatibility."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.estimator.ownership_store import (
    EstimationOwnershipError,
    EstimationOwnershipStore,
)
from app.estimator.production_identity import current_actor


def claim_estimation(request: Request, estimation_id: str) -> None:
    actor = current_actor(request)
    store = _store(request)
    if actor is None or store is None:
        return
    try:
        store.claim(estimation_id, actor.owner_id)
    except EstimationOwnershipError as exc:
        raise _ownership_error(exc) from exc


def assert_estimation_owner(request: Request, estimation_id: str) -> None:
    actor = current_actor(request)
    store = _store(request)
    if actor is None or store is None:
        return
    try:
        store.assert_owner(estimation_id, actor.owner_id)
    except EstimationOwnershipError as exc:
        raise _ownership_error(exc) from exc


def authenticated_actor_id(request: Request) -> str | None:
    actor = current_actor(request)
    return None if actor is None else actor.owner_id


def _store(request: Request) -> EstimationOwnershipStore | None:
    return getattr(request.app.state, "estimator_ownership_store", None)


def _ownership_error(exc: EstimationOwnershipError) -> HTTPException:
    if exc.reason_code == "resource_owner_missing":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "estimation_not_found",
                "reason_code": exc.reason_code,
                "detail": "The requested estimation is not available to this actor.",
            },
        )
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "estimation_access_denied",
            "reason_code": exc.reason_code,
            "detail": "The requested estimation belongs to another actor or tenant.",
        },
    )
