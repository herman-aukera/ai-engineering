"""Sanitized export packet for reviewer-facing estimation audit evidence."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def _sanitize_trace_events(raw_events: object) -> list[dict[str, object]]:
    """Allow-list trace data and remove source-input field names."""
    if not isinstance(raw_events, list):
        return []

    sanitized: list[dict[str, object]] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, Mapping):
            continue
        state_delta_keys = [
            str(key)
            for key in raw_event.get("state_delta_keys", [])
            if isinstance(key, str) and "transcript" not in key.lower()
        ]
        summary = str(raw_event.get("summary", "")).replace("transcript", "source input").replace("Transcript", "Source input")
        sanitized.append(
            {
                "event_type": str(raw_event.get("event_type", "unknown")),
                "node": str(raw_event.get("node", "unknown")),
                "summary": summary,
                "evidence_refs": [
                    str(item)
                    for item in raw_event.get("evidence_refs", [])
                    if isinstance(item, str)
                ],
                "state_delta_keys": state_delta_keys,
            }
        )
    return sanitized


def build_estimation_audit_packet(
    state: Mapping[str, Any],
    *,
    thread_id: str,
    checkpoint_id: str,
    limitations: list[str] | None = None,
) -> dict[str, object]:
    """Build a JSON-safe packet without prompts, transcript bodies, or keys."""

    return {
        "schema_version": "session13.plus.audit.v1",
        "identity": {
            "estimation_id": state.get("estimation_id"),
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "graph_version": state.get("graph_version"),
            "scenario_id": state.get("scenario_id"),
            "parent_estimation_id": state.get("parent_estimation_id"),
            "parent_checkpoint_id": state.get("parent_checkpoint_id"),
        },
        "status": {
            "graph_status": state.get("status"),
            "review_required": bool(state.get("review_required")),
            "structure_review_status": state.get("structure_review_status"),
            "final_review_status": state.get("final_review_status"),
        },
        "final_estimate": deepcopy(state.get("estimate", {})),
        "component_estimates": deepcopy(state.get("component_estimates", [])),
        "provenance": deepcopy(state.get("budget_matches", [])),
        "unresolved_issues": deepcopy(state.get("errors", [])),
        "critic_report": deepcopy(state.get("critic_report", {})),
        "boss_decision": deepcopy(state.get("boss_decision", {})),
        "human_decisions": {
            "structure": deepcopy(state.get("structure_review_record", {})),
            "final": deepcopy(state.get("final_review_record", {})),
            "baseline_overrides": deepcopy(state.get("human_baseline_overrides", [])),
        },
        "execution": {
            "provider": deepcopy(state.get("provider_metadata", {})),
            "budgets": deepcopy(state.get("execution_budgets", {})),
            "metadata": deepcopy(state.get("execution_metadata", {})),
        },
        "domain_trace": _sanitize_trace_events(state.get("trace_events", [])),
        "limitations": list(limitations or []),
    }
