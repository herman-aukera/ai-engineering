"""HTTP helpers that apply durable ownership only in the production composition root."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.energy_chat.ownership_store import ResourceOwnershipError, ResourceOwnershipStore
from app.energy_chat.production_identity import current_actor


def claim_resource(request: Request, resource_type: str, resource_id: str) -> None:
    actor = current_actor(request)
    store = _store(request)
    if actor is None or store is None:
        return
    try:
        store.claim(resource_type, resource_id, actor.owner_id)
    except ResourceOwnershipError as exc:
        raise _ownership_error(exc) from exc


def assert_resource_owner(request: Request, resource_type: str, resource_id: str) -> None:
    actor = current_actor(request)
    store = _store(request)
    if actor is None or store is None:
        return
    try:
        store.assert_owner(resource_type, resource_id, actor.owner_id)
    except ResourceOwnershipError as exc:
        raise _ownership_error(exc) from exc


def delete_resource_owner(request: Request, resource_type: str, resource_id: str) -> None:
    actor = current_actor(request)
    store = _store(request)
    if actor is None or store is None:
        return
    try:
        store.delete(resource_type, resource_id, actor.owner_id)
    except ResourceOwnershipError as exc:
        raise _ownership_error(exc) from exc


def _store(request: Request) -> ResourceOwnershipStore | None:
    return getattr(request.app.state, "energy_chat_ownership_store", None)


def _ownership_error(exc: ResourceOwnershipError) -> HTTPException:
    if exc.reason_code == "resource_owner_missing":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "resource_not_found",
                "reason_code": exc.reason_code,
                "detail": "The requested resource is not available to this actor.",
            },
        )
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "resource_access_denied",
            "reason_code": exc.reason_code,
            "detail": "The requested resource is owned by another actor or tenant.",
        },
    )
