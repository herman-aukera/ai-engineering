"""Standalone read-only control room for Session 13 graph executions.

Run with:

    uv run streamlit run app/ui/graph_inspector.py

The inspector renders checkpoint-safe graph output, provenance, domain events,
and sanitized execution metadata. It never displays hidden chain-of-thought.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://localhost:8000"
GRAPH_ESTIMATE_PATH = "/api/v1/estimate/graph"
BACKEND_CONNECT_TIMEOUT_SECONDS = 10
BACKEND_READ_TIMEOUT_SECONDS = 240
GRAPH_NODE_ORDER = (
    "extract_requirements",
    "classify_components",
    "search_budgets",
    "generate_estimate",
    "validate_and_consolidate",
)


def get_backend_url() -> str:
    """Return the configured FastAPI base URL without a trailing slash."""

    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def build_graph_estimate_url() -> str:
    """Return the additive Session 13 graph endpoint URL."""

    return f"{get_backend_url()}{GRAPH_ESTIMATE_PATH}"


def build_graph_request_payload(
    *,
    transcript: str,
    estimation_id: str | None,
) -> dict[str, str]:
    """Build the strict graph request while omitting an empty identifier."""

    payload = {"transcript": transcript.strip()}
    normalized_id = (estimation_id or "").strip()
    if normalized_id:
        payload["estimation_id"] = normalized_id
    return payload


def post_graph_estimation(
    *,
    transcript: str,
    estimation_id: str | None = None,
) -> dict[str, Any]:
    """Execute or idempotently reopen one graph run through the public API."""

    response = requests.post(
        build_graph_estimate_url(),
        json=build_graph_request_payload(
            transcript=transcript,
            estimation_id=estimation_id,
        ),
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("graph endpoint response must be a JSON object")
    return payload


def parse_graph_payload(raw_json: str) -> dict[str, Any]:
    """Parse a previously captured graph response for offline inspection."""

    payload = json.loads(raw_json)
    if not isinstance(payload, dict):
        raise ValueError("graph inspection payload must be a JSON object")
    return payload


def build_execution_header(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the stable execution facts shown above the inspector."""

    estimate = payload.get("estimate")
    estimate_payload = estimate if isinstance(estimate, dict) else {}
    provider_metadata = payload.get("provider_metadata")
    provider_payload = provider_metadata if isinstance(provider_metadata, dict) else {}
    execution_metadata = payload.get("execution_metadata")
    execution_payload = execution_metadata if isinstance(execution_metadata, dict) else {}

    return {
        "estimation_id": payload.get("estimation_id"),
        "thread_id": payload.get("thread_id"),
        "graph_version": payload.get("graph_version"),
        "status": payload.get("status"),
        "review_required": payload.get("review_required"),
        "provider": provider_payload.get("provider"),
        "model": provider_payload.get("model"),
        "prompt_version": provider_payload.get("prompt_version"),
        "total_hours": estimate_payload.get("total_hours"),
        "total_cost_eur": estimate_payload.get("total_cost_eur"),
        "requirement_count": execution_payload.get("requirement_count"),
        "component_count": execution_payload.get("component_count"),
        "budget_match_count": execution_payload.get("budget_match_count"),
    }


def _trace_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("trace_events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def build_timeline_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a deterministic node timeline from checkpointed domain events."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in _trace_events(payload):
        node = event.get("node")
        if isinstance(node, str) and node:
            grouped[node].append(event)

    ordered_nodes = list(GRAPH_NODE_ORDER)
    ordered_nodes.extend(sorted(node for node in grouped if node not in GRAPH_NODE_ORDER))

    rows: list[dict[str, Any]] = []
    for position, node in enumerate(ordered_nodes, start=1):
        events = grouped.get(node, [])
        last_event = events[-1] if events else {}
        state_keys = sorted(
            {
                str(key)
                for event in events
                for key in (event.get("state_delta_keys") or [])
            }
        )
        evidence_refs = sorted(
            {
                str(reference)
                for event in events
                for reference in (event.get("evidence_refs") or [])
            }
        )
        rows.append(
            {
                "step": position,
                "node": node,
                "status": "completed" if events else "not_observed",
                "event_count": len(events),
                "last_event_type": last_event.get("event_type"),
                "last_summary": last_event.get("summary"),
                "state_keys_changed": ", ".join(state_keys),
                "evidence_refs": ", ".join(evidence_refs),
            }
        )
    return rows


def build_provenance_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Join component estimates with every retained historical source reference."""

    matches_by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    budget_matches = payload.get("budget_matches")
    if isinstance(budget_matches, list):
        for match in budget_matches:
            if not isinstance(match, dict):
                continue
            component_id = match.get("component_id")
            if isinstance(component_id, str):
                matches_by_component[component_id].append(match)

    rows: list[dict[str, Any]] = []
    component_estimates = payload.get("component_estimates")
    if not isinstance(component_estimates, list):
        return rows

    for component in component_estimates:
        if not isinstance(component, dict):
            continue
        component_id = str(component.get("component_id") or "")
        matches = matches_by_component.get(component_id, [])
        source_documents = sorted(
            {
                str(match.get("source_document_id"))
                for match in matches
                if match.get("source_document_id")
            }
        )
        source_chunks = sorted(
            {
                str(match.get("source_chunk_id"))
                for match in matches
                if match.get("source_chunk_id")
            }
        )
        budget_ids = sorted(
            {
                str(match.get("budget_id"))
                for match in matches
                if match.get("budget_id")
            }
        )
        confidence = component.get("confidence")
        confidence_pct = (
            round(float(confidence) * 100)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
            else None
        )
        rows.append(
            {
                "component_id": component_id,
                "component": component.get("name"),
                "hours": component.get("hours"),
                "grounding_status": component.get("grounding_status"),
                "confidence_pct": confidence_pct,
                "derivation_method": component.get("derivation_method"),
                "source_range_low": component.get("source_range_low"),
                "source_range_high": component.get("source_range_high"),
                "reference_count": len(matches),
                "budget_ids": ", ".join(budget_ids),
                "source_documents": ", ".join(source_documents),
                "source_chunks": ", ".join(source_chunks),
                "review_reasons": ", ".join(component.get("review_reasons") or []),
            }
        )
    return rows


def build_graphviz_source(payload: dict[str, Any]) -> str:
    """Render the stable graph topology with observed status in node labels."""

    statuses = {row["node"]: row["status"] for row in build_timeline_rows(payload)}
    lines = ["digraph estimation_graph {", "rankdir=LR;", 'node [shape="box"];']
    previous = "START"
    lines.append('"START" [shape="circle"];')
    for node in GRAPH_NODE_ORDER:
        status = statuses.get(node, "not_observed")
        lines.append(f'"{node}" [label="{node}\\n{status}"];')
        lines.append(f'"{previous}" -> "{node}";')
        previous = node
    lines.append('"END" [shape="doublecircle"];')
    lines.append(f'"{previous}" -> "END";')
    lines.append("}")
    return "\n".join(lines)


def _render_execution_header(payload: dict[str, Any]) -> None:
    header = build_execution_header(payload)
    status_col, review_col, hours_col, cost_col, provider_col = st.columns(5)
    status_col.metric("Status", header.get("status") or "unknown")
    review_col.metric("Review required", "yes" if header.get("review_required") else "no")
    hours_col.metric("Total hours", header.get("total_hours") or "unknown")
    total_cost = header.get("total_cost_eur")
    cost_col.metric("Total cost", f"EUR {total_cost:g}" if isinstance(total_cost, (int, float)) else "unknown")
    provider_label = "/".join(
        value for value in (header.get("provider"), header.get("model")) if value
    )
    provider_col.metric("Provider", provider_label or "deterministic")

    st.caption(
        " | ".join(
            [
                f"estimation_id={header.get('estimation_id') or 'unknown'}",
                f"thread_id={header.get('thread_id') or 'unknown'}",
                f"graph_version={header.get('graph_version') or 'unknown'}",
                f"prompt_version={header.get('prompt_version') or 'unknown'}",
            ]
        )
    )


def render_graph_inspector(payload: dict[str, Any]) -> None:
    """Render one graph response as an auditable read-only control room."""

    _render_execution_header(payload)

    st.markdown("### Graph topology and node timeline")
    st.graphviz_chart(build_graphviz_source(payload), use_container_width=True)
    st.dataframe(build_timeline_rows(payload), use_container_width=True, hide_index=True)

    st.markdown("### Provenance explorer")
    provenance_rows = build_provenance_rows(payload)
    if provenance_rows:
        st.dataframe(provenance_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No component-level provenance was returned.")

    issues = payload.get("errors")
    if isinstance(issues, list) and issues:
        st.markdown("### Structured issues")
        st.dataframe(issues, use_container_width=True, hide_index=True)

    domain_tab, telemetry_tab, checkpoint_tab = st.tabs(
        ["Domain trace", "Telemetry metadata", "Checkpoint-safe payload"]
    )
    with domain_tab:
        st.caption(
            "Domain events summarize decisions, evidence references, and state changes. "
            "They are not hidden chain-of-thought."
        )
        trace_events = _trace_events(payload)
        if trace_events:
            st.dataframe(trace_events, use_container_width=True, hide_index=True)
        else:
            st.info("No domain trace events were returned.")

    with telemetry_tab:
        st.markdown("#### Provider metadata")
        st.json(payload.get("provider_metadata") or {})
        st.markdown("#### Execution metadata")
        st.json(payload.get("execution_metadata") or {})
        st.caption("Hosted spans and latency details remain in Logfire, separate from domain state.")

    with checkpoint_tab:
        st.json(payload)


def main() -> None:
    """Run the standalone Graph Inspector Streamlit application."""

    st.set_page_config(
        page_title="Estimation Graph Inspector",
        page_icon="🧭",
        layout="wide",
    )
    st.title("Estimation Control Room — Graph Inspector")
    st.caption(
        "Inspect graph topology, provenance, structured issues, domain events, and "
        "checkpoint-safe output without exposing hidden reasoning."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        st.caption("Set ESTIMADOR_BACKEND_URL when FastAPI is not on localhost:8000.")

    execute_tab, load_tab = st.tabs(["Execute or reopen", "Load saved JSON"])

    with execute_tab:
        with st.form("graph_execution_form"):
            transcript = st.text_area(
                "Transcript",
                height=180,
                placeholder="Describe the software project and estimation scope.",
            )
            estimation_id = st.text_input(
                "Estimation ID (optional)",
                help="Reuse the same UUID with the identical transcript to reopen a completed thread.",
            )
            submitted = st.form_submit_button("Run graph and inspect", type="primary")

        if submitted:
            try:
                with st.spinner("Executing checkpointed graph..."):
                    st.session_state["graph_inspection_payload"] = post_graph_estimation(
                        transcript=transcript,
                        estimation_id=estimation_id,
                    )
            except requests.HTTPError as exc:
                response_text = exc.response.text if exc.response is not None else str(exc)
                st.error(f"Graph endpoint returned an error: {response_text}")
            except (requests.RequestException, ValueError) as exc:
                st.error(f"Could not inspect graph execution: {exc}")

    with load_tab:
        raw_json = st.text_area(
            "Saved GraphEstimationResponse JSON",
            height=240,
            placeholder='{"estimation_id": "...", "thread_id": "estimate:..."}',
        )
        if st.button("Load saved response"):
            try:
                st.session_state["graph_inspection_payload"] = parse_graph_payload(raw_json)
            except (json.JSONDecodeError, ValueError) as exc:
                st.error(f"Invalid graph response JSON: {exc}")

    payload = st.session_state.get("graph_inspection_payload")
    if isinstance(payload, dict):
        st.divider()
        render_graph_inspector(payload)
    else:
        st.info("Run a graph estimate or load a saved response to open the inspector.")


if __name__ == "__main__":
    main()
