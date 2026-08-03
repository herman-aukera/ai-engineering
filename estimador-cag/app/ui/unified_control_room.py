"""Streamlit Control Room for the consolidated Session 13 + 14 Plus graph."""

from __future__ import annotations

import os
from typing import Any, Literal
from uuid import uuid4

import httpx
import streamlit as st

ReviewAction = Literal["approve", "adjust", "reject"]


def normalize_backend_url(value: str) -> str:
    """Return a stable backend base URL without a trailing slash."""

    normalized = value.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("backend URL must use http or https")
    return normalized


def unified_control_url(base_url: str) -> str:
    return f"{normalize_backend_url(base_url)}/api/v1/estimate/graph/unified/control"


def unified_readiness_url(base_url: str) -> str:
    return f"{normalize_backend_url(base_url)}/api/v1/estimate/graph/unified/readiness"


def unified_resume_url(base_url: str, estimation_id: str) -> str:
    normalized_id = estimation_id.strip()
    if not normalized_id:
        raise ValueError("estimation_id must not be blank")
    return (
        f"{normalize_backend_url(base_url)}"
        f"/api/v1/estimate/graph/unified/control/{normalized_id}/resume"
    )


def build_review_payload(
    *,
    action: ReviewAction,
    expected_revision: int,
    actor: str,
    reason: str | None,
    adjustments: list[dict[str, object]] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    """Build the exact persisted Session 14 decision contract."""

    normalized_actor = actor.strip()
    if not normalized_actor:
        raise ValueError("actor must not be blank")
    if expected_revision < 1:
        raise ValueError("expected_revision must be positive")
    normalized_reason = reason.strip() if isinstance(reason, str) else None
    if action == "reject" and not normalized_reason:
        raise ValueError("reject requires a reason")
    if action == "adjust" and not adjustments:
        raise ValueError("adjust requires at least one adjustment")
    return {
        "action": action,
        "expected_revision": expected_revision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "adjustments": adjustments or [],
        "idempotency_key": idempotency_key or f"control-{uuid4()}",
    }


def candidate_rows(projection: dict[str, Any]) -> list[dict[str, object]]:
    """Flatten candidates without exposing source state or model content."""

    raw_candidates = projection.get("competition_candidates", [])
    if not isinstance(raw_candidates, list):
        return []
    rows: list[dict[str, object]] = []
    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            continue
        rows.append(
            {
                "variant": candidate.get("variant"),
                "candidate_id": candidate.get("candidate_id"),
                "total_hours": candidate.get("total_hours"),
                "fingerprint": candidate.get("fingerprint"),
            }
        )
    return rows


def route_rows(projection: dict[str, Any]) -> list[dict[str, object]]:
    raw_events = projection.get("route_events", [])
    if not isinstance(raw_events, list):
        return []
    return [
        {
            "sequence": event.get("sequence"),
            "destination": event.get("destination"),
            "reason_code": event.get("reason_code"),
            "summary": event.get("summary"),
        }
        for event in raw_events
        if isinstance(event, dict)
    ]


def _request_json(
    method: Literal["GET", "POST"],
    url: str,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, Any]:
    with httpx.Client(timeout=120.0) as client:
        response = client.request(method, url, json=payload)
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"backend returned {response.status_code}: {detail}")
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("backend response must be a JSON object")
    return data


def _render_projection(projection: dict[str, Any]) -> None:
    columns = st.columns(4)
    columns[0].metric("Status", projection.get("status", "unknown"))
    columns[1].metric("Phase", projection.get("unified_phase", "unknown"))
    columns[2].metric(
        "Human review",
        projection.get("human_review_status", "unknown"),
    )
    columns[3].metric(
        "Revision",
        projection.get("human_review_revision", 0),
    )

    st.caption(
        f"Thread: {projection.get('thread_id', 'unknown')} · "
        f"Graph: {projection.get('graph_version', 'unknown')}"
    )

    st.subheader("Supervisor route ledger")
    routes = route_rows(projection)
    st.dataframe(routes, use_container_width=True) if routes else st.info(
        "No route events yet."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Critic")
        st.json(projection.get("critic_report", {}), expanded=False)
        st.subheader("Reliability")
        st.json(projection.get("reliability_report", {}), expanded=False)
    with right:
        st.subheader("Boss recommendation")
        st.json(projection.get("boss_decision", {}), expanded=False)
        st.subheader("Proposal")
        st.json(projection.get("proposal", {}), expanded=False)

    st.subheader("Energy-Aware candidate competition")
    candidates = candidate_rows(projection)
    st.dataframe(candidates, use_container_width=True) if candidates else st.info(
        "No competition candidates yet."
    )
    st.json(projection.get("competition_assessment", {}), expanded=False)

    st.subheader("Provider and context integrity")
    provider_column, context_column = st.columns(2)
    with provider_column:
        st.json(
            projection.get("authorized_capabilities", {}),
            expanded=False,
        )
    with context_column:
        st.json(
            {
                "detail": projection.get("context_detail"),
                "context_id": projection.get("context_id"),
                "fingerprint": projection.get("context_fingerprint"),
                "source_revision": projection.get("context_source_revision"),
                "evidence_refs": projection.get("context_evidence_refs", []),
            },
            expanded=False,
        )


def main() -> None:
    st.set_page_config(
        page_title="Unified Energy-Aware Control Room",
        layout="wide",
    )
    st.title("Session 13 + 14 Plus — Unified Control Room")
    st.caption(
        "Critics recommend, the deterministic supervisor routes, and only the "
        "persisted human gate can approve, adjust, or reject."
    )

    default_backend = os.getenv("ESTIMADOR_BACKEND_URL", "http://localhost:8000")
    backend_url = st.sidebar.text_input("Backend URL", value=default_backend)

    try:
        readiness = _request_json("GET", unified_readiness_url(backend_url))
    except Exception as exc:
        st.sidebar.error(str(exc))
    else:
        st.sidebar.success(
            "Unified runtime ready" if readiness.get("ready") else "Runtime unavailable"
        )
        st.sidebar.json(readiness, expanded=False)

    transcript = st.text_area(
        "Source request",
        height=180,
        help=(
            "This input is sent to the backend but is not returned in the "
            "Control Room projection or persisted telemetry."
        ),
    )
    if st.button("Start unified estimation", type="primary"):
        if not transcript.strip():
            st.error("Provide a source request before starting.")
        else:
            try:
                projection = _request_json(
                    "POST",
                    unified_control_url(backend_url),
                    payload={"transcript": transcript},
                )
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state["unified_projection"] = projection
                st.session_state["source_request"] = transcript

    projection = st.session_state.get("unified_projection")
    if not isinstance(projection, dict):
        st.info("Start an estimation to inspect the sanitized control plane.")
        return

    _render_projection(projection)

    if projection.get("execution_status") != "awaiting_human_review":
        return

    st.subheader("Persisted human decision")
    action = st.selectbox("Action", ["approve", "adjust", "reject"])
    actor = st.text_input("Actor", value="control-room-reviewer")
    reason = st.text_area("Reason")
    adjustments_json = st.text_area(
        "Adjustments JSON",
        value="[]",
        disabled=action != "adjust",
    )
    if st.button("Submit human decision"):
        try:
            import json

            adjustments = json.loads(adjustments_json)
            if not isinstance(adjustments, list):
                raise ValueError("adjustments JSON must be a list")
            payload = build_review_payload(
                action=action,
                expected_revision=int(
                    projection.get("human_review_revision", 0)
                ),
                actor=actor,
                reason=reason,
                adjustments=adjustments,
            )
            refreshed = _request_json(
                "POST",
                unified_resume_url(
                    backend_url,
                    str(projection.get("estimation_id", "")),
                ),
                payload=payload,
            )
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["unified_projection"] = refreshed
            st.rerun()


if __name__ == "__main__":
    main()
