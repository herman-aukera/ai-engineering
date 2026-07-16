"""Read-only dashboard for legacy-versus-graph shadow rollout evidence.

Run with:

    uv run streamlit run app/ui/shadow_dashboard.py
"""

from __future__ import annotations

import statistics
from typing import Any

import requests
import streamlit as st

from app.ui.graph_inspector import (
    BACKEND_CONNECT_TIMEOUT_SECONDS,
    BACKEND_READ_TIMEOUT_SECONDS,
    get_backend_url,
)

SHADOW_COMPARISONS_PATH = "/api/v1/estimate/graph/shadow/comparisons"


def build_shadow_comparisons_url() -> str:
    return f"{get_backend_url()}{SHADOW_COMPARISONS_PATH}"


def get_shadow_comparisons(*, limit: int = 100) -> dict[str, Any]:
    response = requests.get(
        build_shadow_comparisons_url(),
        params={"limit": limit},
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("shadow comparison response must be a JSON object")
    return payload


def summarize_shadow_comparisons(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [item for item in comparisons if item.get("status") == "completed"]
    failed = [item for item in comparisons if item.get("status") == "failed"]
    latency_deltas = [
        float(item["latency_delta_ms"])
        for item in completed
        if isinstance(item.get("latency_delta_ms"), (int, float))
    ]
    cost_deltas = [
        float(item["cost_delta_eur"])
        for item in completed
        if isinstance(item.get("cost_delta_eur"), (int, float))
    ]
    review_results = [
        bool(item["shadow_review_required"])
        for item in completed
        if item.get("shadow_review_required") is not None
    ]
    return {
        "total": len(comparisons),
        "completed": len(completed),
        "failed": len(failed),
        "success_rate_pct": (
            round((len(completed) / len(comparisons)) * 100, 1)
            if comparisons
            else None
        ),
        "median_latency_delta_ms": (
            round(statistics.median(latency_deltas), 1)
            if latency_deltas
            else None
        ),
        "median_cost_delta_eur": (
            round(statistics.median(cost_deltas), 2)
            if cost_deltas
            else None
        ),
        "graph_review_rate_pct": (
            round((sum(review_results) / len(review_results)) * 100, 1)
            if review_results
            else None
        ),
    }


def _metric_value(value: object, *, suffix: str = "") -> str:
    if value is None:
        return "unknown"
    return f"{value}{suffix}"


def render_shadow_dashboard(payload: dict[str, Any]) -> None:
    raw_comparisons = payload.get("comparisons")
    comparisons = (
        [item for item in raw_comparisons if isinstance(item, dict)]
        if isinstance(raw_comparisons, list)
        else []
    )
    summary = summarize_shadow_comparisons(comparisons)

    total_col, success_col, latency_col, cost_col, review_col = st.columns(5)
    total_col.metric("Comparisons", summary["total"])
    success_col.metric(
        "Shadow success",
        _metric_value(summary["success_rate_pct"], suffix="%"),
    )
    latency_col.metric(
        "Median latency delta",
        _metric_value(summary["median_latency_delta_ms"], suffix=" ms"),
    )
    cost_col.metric(
        "Median cost delta",
        _metric_value(summary["median_cost_delta_eur"], suffix=" EUR"),
    )
    review_col.metric(
        "Graph review rate",
        _metric_value(summary["graph_review_rate_pct"], suffix="%"),
    )

    if not comparisons:
        st.info(
            "No shadow evidence yet. Set GRAPH_ROLLOUT_MODE=shadow and exercise "
            "the conversational session estimate route."
        )
        return

    st.markdown("### Comparison ledger")
    st.dataframe(comparisons, use_container_width=True, hide_index=True)

    failures = [item for item in comparisons if item.get("status") == "failed"]
    if failures:
        st.markdown("### Shadow failures")
        st.dataframe(
            [
                {
                    "comparison_id": item.get("comparison_id"),
                    "session_id": item.get("session_id"),
                    "error_type": item.get("error_type"),
                    "error_message": item.get("error_message"),
                    "shadow_latency_ms": item.get("shadow_latency_ms"),
                }
                for item in failures
            ],
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Graph Shadow Dashboard",
        page_icon="🌓",
        layout="wide",
    )
    st.title("Estimation Control Room — Shadow Rollout")
    st.caption(
        "Legacy remains the served response while graph execution produces sanitized "
        "latency, cost, status, and failure evidence. Transcript content is not stored."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        limit = st.number_input("Comparison limit", min_value=1, max_value=100, value=50)
        refresh = st.button("Refresh evidence", type="primary", use_container_width=True)

    if refresh or "shadow_comparison_payload" not in st.session_state:
        try:
            st.session_state["shadow_comparison_payload"] = get_shadow_comparisons(
                limit=int(limit)
            )
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            st.error(f"Shadow dashboard endpoint returned an error: {detail}")
        except (requests.RequestException, ValueError) as exc:
            st.error(f"Could not load shadow comparison evidence: {exc}")

    payload = st.session_state.get("shadow_comparison_payload")
    if isinstance(payload, dict):
        render_shadow_dashboard(payload)


if __name__ == "__main__":
    main()
