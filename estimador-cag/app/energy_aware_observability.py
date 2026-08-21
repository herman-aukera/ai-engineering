"""Provider-neutral operational event envelope for Energy-Aware products."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "energy-aware.protocol.v1"
EVENT_SCHEMA_VERSION = "energy-aware.event.v1"
_REASON_CODE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SENSITIVE_KEYS = frozenset(
    {"authorization", "cookie", "password", "secret", "token", "api_key", "prompt", "transcript"}
)


@dataclass(frozen=True)
class OperationalEvent:
    product: str
    event_type: str
    outcome: str
    reason_code: str
    request_id: str
    duration_ms: int
    resource_id: str | None = None
    policy_version: str | None = None
    contract_version: str = PROTOCOL_VERSION
    attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _REASON_CODE.fullmatch(self.reason_code):
            raise ValueError("reason_code must be stable lower_snake_case with a domain/condition")
        if not _ID.fullmatch(self.request_id):
            raise ValueError("request_id has an invalid shape")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        normalized_keys = {key.casefold() for key in self.attributes}
        if normalized_keys & _SENSITIVE_KEYS:
            raise ValueError("operational event attributes contain a sensitive key")

    def as_dict(self) -> dict[str, object]:
        return {
            "event_schema_version": EVENT_SCHEMA_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "product": self.product,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "request_id": self.request_id,
            "duration_ms": self.duration_ms,
            "resource_id": self.resource_id,
            "policy_version": self.policy_version,
            "contract_version": self.contract_version,
            "attributes": dict(sorted(self.attributes.items())),
        }


def safe_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if candidate and _ID.fullmatch(candidate):
        return candidate
    return f"request-{uuid.uuid4().hex}"


async def observe_http_request(
    request: Any,
    call_next: Callable[[Any], Awaitable[Any]],
    *,
    product: str,
    logger: logging.Logger,
) -> Any:
    """Emit one safe request-completion event without bodies, prompts or credentials."""

    request_id = safe_request_id(request.headers.get("X-Request-ID"))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            json.dumps(
                OperationalEvent(
                    product=product,
                    event_type="http_request",
                    outcome="error",
                    reason_code="request_internal_error",
                    request_id=request_id,
                    duration_ms=duration_ms,
                    attributes={"method": request.method, "path": request.url.path},
                ).as_dict(),
                sort_keys=True,
            )
        )
        raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code < 400:
        outcome, reason_code = "success", "request_completed"
    elif response.status_code in {401, 403}:
        outcome, reason_code = "denied", "request_identity_denied"
    elif response.status_code == 409:
        outcome, reason_code = "conflict", "request_state_conflict"
    elif response.status_code == 503:
        outcome, reason_code = "unavailable", "runtime_not_ready"
    else:
        outcome, reason_code = "error", "request_http_error"

    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            OperationalEvent(
                product=product,
                event_type="http_request",
                outcome=outcome,
                reason_code=reason_code,
                request_id=request_id,
                duration_ms=duration_ms,
                attributes={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code),
                },
            ).as_dict(),
            sort_keys=True,
        )
    )
    return response
