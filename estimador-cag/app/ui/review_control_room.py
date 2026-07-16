"""Streamlit control room for durable reviewed Session 13 Plus executions.

Run with:

    uv run streamlit run app/ui/review_control_room.py
"""

from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st

from app.ui.graph_inspector import (
    BACKEND_CONNECT_TIMEOUT_SECONDS,
    BACKEND_READ_TIMEOUT_SECONDS,
    get_backend_url,
    render_graph_inspector,
)

REVIEWED_START_PATH = "/api/v1/estimate/graph/reviewed/start"
REVIEWED_EXECUTION_PATH = "/api/v1/estimate/graph/reviewed/{estimation_id}"
REVIEWED_RESUME_PATH = "/api/v1/estimate/graph/reviewed/{estimation_id}/resume"


def build_reviewed_start_url() -> str:
    return f"{get_backend_url()}{REVIEWED_START_PATH}"


def build_reviewed_execution_url(estimation_id: str) -> str:
    return f"{get_backend_url()}{REVIEWED_EXECUTION_PATH.format(estimation_id=estimation_id)}"


def build_reviewed_resume_url(estimation_id: str) -> str:
    return f"{get_backend_url()}{REVIEWED_RESUME_PATH.format(estimation_id=estimation_id)}"


def _response_json(response: requests.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("reviewed graph response must be a JSON object")
    return payload


def start_reviewed_execution(
    *,
    transcript: str,
    human_review_mode: str,
    estimation_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "transcript": transcript.strip(),
        "human_review_mode": human_review_mode,
    }
    normalized_id = (estimation_id or "").strip()
    if normalized_id:
        payload["estimation_id"] = normalized_id
    response = requests.post(
        build_reviewed_start_url(),
        json=payload,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    return _response_json(response)


def inspect_reviewed_execution(estimation_id: str) -> dict[str, Any]:
    response = requests.get(
        build_reviewed_execution_url(estimation_id.strip()),
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    return _response_json(response)


def resume_reviewed_execution(
    *,
    estimation_id: str,
    decision: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        build_reviewed_resume_url(estimation_id.strip()),
        json=decision,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    return _response_json(response)


def reviewed_response_to_graph_payload(response: dict[str, Any]) -> dict[str, Any]:
    """Flatten the checkpoint-safe state for the existing Graph Inspector renderer."""

    raw_state = response.get("state")
    state = dict(raw_state) if isinstance(raw_state, dict) else {}
    state.update(
        {
            "estimation_id": response.get("estimation_id") or state.get("estimation_id"),
            "thread_id": response.get("thread_id"),
            "graph_version": response.get("graph_version") or state.get("graph_version"),
            "status": response.get("graph_status") or state.get("status"),
            "review_required": response.get("review_required", state.get("review_required")),
        }
    )
    return state


def pending_structure_review(response: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = response.get("interrupts")
    if not isinstance(interrupts, list):
        return None
    for interrupt_payload in interrupts:
        if not isinstance(interrupt_payload, dict):
            continue
        value = interrupt_payload.get("value")
        if isinstance(value, dict) and value.get("gate") == "structure_review":
            return value
    return None


def _parse_json_list(raw_json: str, *, field_name: str) -> list[dict[str, Any]]:
    value = json.loads(raw_json)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must be a JSON array of objects")
    return value


def build_structure_resume_payload(
    *,
    action: str,
    expected_revision: int,
    reason: str | None = None,
    requirements_json: str | None = None,
    components_json: str | None = None,
) -> dict[str, Any]:
    """Build one strict resume value without inventing edits."""

    payload: dict[str, Any] = {
        "action": action,
        "expected_revision": expected_revision,
    }
    normalized_reason = (reason or "").strip()
    if normalized_reason:
        payload["reason"] = normalized_reason

    if action == "edit":
        payload["requirements"] = _parse_json_list(
            requirements_json or "[]",
            field_name="requirements",
        )
        payload["components"] = _parse_json_list(
            components_json or "[]",
            field_name="components",
        )
    return payload


def _request_error_text(exc: requests.HTTPError) -> str:
    if exc.response is None:
        return str(exc)
    try:
        payload = exc.response.json()
    except ValueError:
        return exc.response.text
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return exc.response.text


def _store_response(response: dict[str, Any]) -> None:
    st.session_state["reviewed_graph_response"] = response
    estimation_id = response.get("estimation_id")
    if estimation_id:
        st.session_state["reviewed_estimation_id"] = str(estimation_id)


def _render_review_form(response: dict[str, Any], interrupt_payload: dict[str, Any]) -> None:
    st.markdown("## Human structure gate")
    st.warning(
        "The graph is durably paused. Closing the browser does not approve or discard this review."
    )
    revision = int(interrupt_payload.get("revision", 0))
    requirements = interrupt_payload.get("requirements") or []
    components = interrupt_payload.get("components") or []
    issues = interrupt_payload.get("issues") or []

    structure_col, issue_col = st.columns(2)
    with structure_col:
        st.markdown("### Proposed requirements")
        st.dataframe(requirements, use_container_width=True, hide_index=True)
        st.markdown("### Proposed components")
        st.dataframe(components, use_container_width=True, hide_index=True)
    with issue_col:
        st.markdown("### Structure issues")
        if issues:
            st.dataframe(issues, use_container_width=True, hide_index=True)
        else:
            st.success("No deterministic structure issues were recorded.")

    with st.form("structure_resume_form"):
        action = st.selectbox(
            "Decision",
            options=["approve", "edit", "reject", "regenerate"],
        )
        reason = st.text_area(
            "Reason",
            help="Required for reject and regenerate; retained in checkpoint-safe state.",
        )
        requirements_json = st.text_area(
            "Edited requirements JSON",
            value=json.dumps(requirements, ensure_ascii=False, indent=2),
            height=220,
            disabled=action != "edit",
        )
        components_json = st.text_area(
            "Edited components JSON",
            value=json.dumps(components, ensure_ascii=False, indent=2),
            height=220,
            disabled=action != "edit",
        )
        submitted = st.form_submit_button("Resume persisted graph", type="primary")

    if submitted:
        try:
            decision = build_structure_resume_payload(
                action=action,
                expected_revision=revision,
                reason=reason,
                requirements_json=requirements_json,
                components_json=components_json,
            )
            with st.spinner("Resuming the same checkpoint thread..."):
                resumed = resume_reviewed_execution(
                    estimation_id=str(response["estimation_id"]),
                    decision=decision,
                )
            _store_response(resumed)
            st.rerun()
        except requests.HTTPError as exc:
            st.error(f"Resume failed: {_request_error_text(exc)}")
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            st.error(f"Could not resume reviewed graph: {exc}")


def _render_execution(response: dict[str, Any]) -> None:
    execution_status = response.get("execution_status", "unknown")
    status_col, mode_col, revision_col, next_col = st.columns(4)
    status_col.metric("Execution", execution_status)
    mode_col.metric("Review mode", response.get("human_review_mode", "unknown"))
    revision_col.metric("Review revision", response.get("structure_review_revision", 0))
    next_nodes = response.get("next_nodes") or []
    next_col.metric("Pending nodes", len(next_nodes))

    interrupt_payload = pending_structure_review(response)
    if execution_status == "paused" and interrupt_payload is not None:
        _render_review_form(response, interrupt_payload)

    st.divider()
    render_graph_inspector(reviewed_response_to_graph_payload(response))

    critic_report = (response.get("state") or {}).get("critic_report")
    boss_decision = (response.get("state") or {}).get("boss_decision")
    if critic_report or boss_decision:
        st.markdown("## Review policy")
        critic_col, boss_col = st.columns(2)
        with critic_col:
            st.markdown("### Structured Critic")
            st.json(critic_report or {})
        with boss_col:
            st.markdown("### Deterministic Boss")
            st.json(boss_decision or {})


def main() -> None:
    st.set_page_config(
        page_title="Estimation Control Room",
        page_icon="🎛️",
        layout="wide",
    )
    st.title("Estimation Control Room")
    st.caption(
        "Durable structure review, checkpoint resume, provenance, typed Critic findings, "
        "and deterministic Boss policy. No hidden chain-of-thought is displayed."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        current_id = st.session_state.get("reviewed_estimation_id", "")
        inspect_id = st.text_input("Existing estimation ID", value=current_id)
        if st.button("Reconnect and inspect", use_container_width=True):
            try:
                _store_response(inspect_reviewed_execution(inspect_id))
                st.rerun()
            except requests.HTTPError as exc:
                st.error(_request_error_text(exc))
            except requests.RequestException as exc:
                st.error(str(exc))

        if st.button("Clear local view", use_container_width=True):
            st.session_state.pop("reviewed_graph_response", None)
            st.session_state.pop("reviewed_estimation_id", None)
            st.rerun()

    with st.expander("Start a reviewed estimation", expanded="reviewed_graph_response" not in st.session_state):
        with st.form("reviewed_start_form"):
            transcript = st.text_area(
                "Transcript",
                height=180,
                placeholder="Describe the software project, scope, constraints, and acceptance criteria.",
            )
            review_mode = st.selectbox(
                "Human review mode",
                options=["required", "risk_based", "disabled"],
                index=0,
            )
            optional_id = st.text_input("Stable estimation UUID (optional)")
            submitted = st.form_submit_button("Start checkpointed workflow", type="primary")

        if submitted:
            try:
                with st.spinner("Running until completion or durable review gate..."):
                    response = start_reviewed_execution(
                        transcript=transcript,
                        human_review_mode=review_mode,
                        estimation_id=optional_id,
                    )
                _store_response(response)
                st.rerun()
            except requests.HTTPError as exc:
                st.error(_request_error_text(exc))
            except (requests.RequestException, ValueError) as exc:
                st.error(str(exc))

    response = st.session_state.get("reviewed_graph_response")
    if isinstance(response, dict):
        _render_execution(response)
    else:
        st.info("Start a reviewed estimation or reconnect using an existing estimation ID.")


if __name__ == "__main__":
    main()
