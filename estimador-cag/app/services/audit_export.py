"""Sanitized export packet for reviewer-facing estimation audit evidence."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


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
        "domain_trace": deepcopy(state.get("trace_events", [])),
        "limitations": list(limitations or []),
    }
