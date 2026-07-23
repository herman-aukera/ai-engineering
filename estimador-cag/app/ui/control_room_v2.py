"""Unified Estimation Control Room V2 over the canonical API."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any
from uuid import uuid4

import pandas as pd
import requests
import streamlit as st

from app.ui.graph_inspector import (
    BACKEND_CONNECT_TIMEOUT_SECONDS,
    BACKEND_READ_TIMEOUT_SECONDS,
    get_backend_url,
)

V2_STAGES = (
    "Context",
    "Reformulation",
    "Structure",
    "Evidence",
    "Estimation",
    "Critic & Boss",
    "Human approval",
    "Audit",
)
STAGE_INDEX = {
    "context": 1,
    "reformulation": 2,
    "structure": 3,
    "evidence": 4,
    "estimation": 5,
    "critic_boss": 6,
    "human_approval": 7,
    "audit": 8,
    "completed": 8,
}
TIMEOUT = (BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS)


def stage_progress(stage: str) -> float:
    return STAGE_INDEX.get(stage, 1) / len(V2_STAGES)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def editor_rows_from_estimation(estimation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module in estimation.get("modules", []):
        for task in module.get("tasks", []):
            estimate = task.get("estimate") or {}
            rows.append(
                {
                    "module_id": module.get("module_id", ""),
                    "module_name": module.get("name", ""),
                    "module_description": module.get("description") or "",
                    "task_id": task.get("task_id", ""),
                    "task_name": task.get("name", ""),
                    "task_description": task.get("description") or "",
                    "category": task.get("category", "uncategorized"),
                    "requirement_ids": ", ".join(task.get("requirement_ids", [])),
                    "hours_low": estimate.get("hours_low"),
                    "hours_expected": estimate.get("hours_expected"),
                    "hours_high": estimate.get("hours_high"),
                    "hourly_rate_eur": estimate.get("hourly_rate_eur", 0),
                    "confidence": estimate.get("confidence", 0),
                }
            )
    return rows


def modules_from_editor_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    modules: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for index, row in enumerate(rows):
        module_id = str(row.get("module_id") or f"module-{index + 1}").strip()
        task_id = str(row.get("task_id") or f"task-{uuid4().hex[:10]}").strip()
        module = modules.setdefault(
            module_id,
            {
                "module_id": module_id,
                "name": str(row.get("module_name") or "Untitled module").strip(),
                "description": str(row.get("module_description") or "").strip() or None,
                "tasks": [],
            },
        )
        expected = _safe_float(row.get("hours_expected"))
        rate = _safe_float(row.get("hourly_rate_eur"))
        module["tasks"].append(
            {
                "task_id": task_id,
                "name": str(row.get("task_name") or "Untitled task").strip(),
                "description": str(row.get("task_description") or "").strip() or None,
                "category": str(row.get("category") or "uncategorized").strip(),
                "requirement_ids": [
                    item.strip()
                    for item in str(row.get("requirement_ids") or "").split(",")
                    if item.strip()
                ],
                "estimate": {
                    "hours_low": _safe_float(row.get("hours_low"), expected),
                    "hours_expected": expected,
                    "hours_high": _safe_float(row.get("hours_high"), expected),
                    "hourly_rate_eur": rate,
                    "confidence": _safe_float(row.get("confidence")),
                },
                "evidence": [],
                "assumptions": [],
                "active_finding_codes": [],
                "review_status": "human_edited",
            }
        )
    result = list(modules.values())
    for module in result:
        module["total_hours"] = round(
            sum(task["estimate"]["hours_expected"] for task in module["tasks"]), 2
        )
        module["total_cost_eur"] = round(
            sum(
                task["estimate"]["hours_expected"]
                * task["estimate"]["hourly_rate_eur"]
                for task in module["tasks"]
            ),
            2,
        )
    return result


def build_structure_action(
    *,
    estimation: dict[str, Any],
    rows: list[dict[str, Any]],
    expected_revision: int,
    reason: str,
) -> dict[str, Any]:
    modules = modules_from_editor_rows(rows)
    clean_modules = [
        {key: value for key, value in module.items() if not key.startswith("total_")}
        for module in modules
    ]
    return {
        "gate": "structure",
        "action": "edit",
        "expected_revision": expected_revision,
        "reason": reason.strip() or None,
        "requirements": estimation.get("requirements", []),
        "modules": clean_modules,
    }


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.request(
        method,
        f"{get_backend_url()}{path}",
        timeout=TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("V2 response must be a JSON object")
    return payload


def _store(payload: dict[str, Any]) -> None:
    st.session_state["v2_response"] = payload
    estimation = payload.get("estimation") or {}
    if estimation.get("estimation_id"):
        st.session_state["v2_estimation_id"] = estimation["estimation_id"]


def _render_header(estimation: dict[str, Any]) -> None:
    stage = str(estimation.get("stage", "context"))
    st.progress(stage_progress(stage))
    active = STAGE_INDEX.get(stage, 1)
    st.caption(
        "  →  ".join(
            f"**{index}. {label}**" if index == active else f"{index}. {label}"
            for index, label in enumerate(V2_STAGES, start=1)
        )
    )
    status_col, hours_col, cost_col, profile_col, thread_col = st.columns(5)
    status_col.metric("Status", estimation.get("execution_status", "unknown"))
    hours_col.metric("Expected hours", estimation.get("total_hours", 0))
    cost_col.metric("Estimated cost", f"€{estimation.get('total_cost_eur', 0):,.2f}")
    profile_col.metric("Profile", estimation.get("execution_policy", {}).get("profile", "-"))
    thread_col.metric("Revision", estimation.get("revision", 0))


def _render_structure_editor(estimation: dict[str, Any]) -> None:
    st.subheader("Structure editor")
    st.caption("Add, remove or edit modules and tasks directly. No JSON editing is required.")
    requirements = estimation.get("requirements", [])
    st.dataframe(requirements, use_container_width=True, hide_index=True)
    rows = editor_rows_from_estimation(estimation)
    edited = st.data_editor(
        pd.DataFrame(rows),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"v2-structure-{estimation.get('estimation_id')}-{estimation.get('revision')}",
    )
    reason = st.text_input("Review reason", value="Reviewed in Control Room V2")
    approve_col, edit_col, reject_col, regenerate_col = st.columns(4)
    estimation_id = estimation["estimation_id"]
    revision = int(estimation.get("revision", 0))
    actions = {
        "approve": approve_col.button("Approve structure", type="primary"),
        "edit": edit_col.button("Save edits & continue"),
        "reject": reject_col.button("Reject"),
        "regenerate": regenerate_col.button("Regenerate"),
    }
    selected = next((name for name, clicked in actions.items() if clicked), None)
    if selected:
        if selected == "edit":
            action = build_structure_action(
                estimation=estimation,
                rows=edited.to_dict("records"),
                expected_revision=revision,
                reason=reason,
            )
        else:
            action = {
                "gate": "structure",
                "action": selected,
                "expected_revision": revision,
                "reason": reason if selected in {"reject", "regenerate"} else None,
            }
        _store(_request("POST", f"/api/v2/estimations/{estimation_id}/actions", json=action))
        st.rerun()


def _render_estimate(estimation: dict[str, Any]) -> None:
    for module in estimation.get("modules", []):
        with st.expander(
            f"{module['name']} · {module.get('total_hours', 0)} h · €{module.get('total_cost_eur', 0):,.2f}",
            expanded=True,
        ):
            st.dataframe(
                [
                    {
                        "Task": task["name"],
                        "Category": task["category"],
                        "Low": (task.get("estimate") or {}).get("hours_low"),
                        "Expected": (task.get("estimate") or {}).get("hours_expected"),
                        "High": (task.get("estimate") or {}).get("hours_high"),
                        "Confidence": (task.get("estimate") or {}).get("confidence"),
                        "Evidence": len(task.get("evidence", [])),
                        "Review": task.get("review_status"),
                    }
                    for task in module.get("tasks", [])
                ],
                use_container_width=True,
                hide_index=True,
            )


def _render_final_gate(estimation: dict[str, Any]) -> None:
    st.subheader("Final human approval")
    actor = st.text_input("Reviewer", value="control-room-reviewer")
    reason = st.text_input("Decision reason", value="Reviewed evidence and policy output.")
    approve, recover, reject = st.columns(3)
    action = None
    if approve.button("Approve final estimate", type="primary"):
        action = "approve"
    elif recover.button("Request selective recovery"):
        action = "request_recovery"
    elif reject.button("Reject final estimate"):
        action = "reject"
    if action:
        payload = {
            "gate": "final",
            "action": action,
            "expected_revision": estimation.get("revision", 0),
            "actor": actor,
            "reason": reason if action != "approve" else None,
        }
        _store(
            _request(
                "POST",
                f"/api/v2/estimations/{estimation['estimation_id']}/actions",
                json=payload,
            )
        )
        st.rerun()


def _render_execution(estimation: dict[str, Any]) -> None:
    _render_header(estimation)
    overview, structure, evidence, policy, history, audit = st.tabs(
        ["Overview", "Structure", "Evidence", "Critic & Boss", "History & scenarios", "Audit"]
    )
    with overview:
        _render_estimate(estimation)
        st.subheader("Execution policy")
        st.json(estimation.get("execution_policy", {}), expanded=False)
    with structure:
        if estimation.get("stage") == "structure":
            _render_structure_editor(estimation)
        else:
            _render_estimate(estimation)
    with evidence:
        for module in estimation.get("modules", []):
            for task in module.get("tasks", []):
                st.markdown(f"**{module['name']} / {task['name']}**")
                st.dataframe(task.get("evidence", []), use_container_width=True, hide_index=True)
    with policy:
        critic, boss = st.columns(2)
        critic.subheader("Typed Critic")
        critic.json(estimation.get("critic_report", {}))
        boss.subheader("Deterministic Boss")
        boss.json(estimation.get("boss_decision", {}))
        if estimation.get("stage") == "human_approval":
            _render_final_gate(estimation)
    with history:
        if st.button("Load checkpoint timeline"):
            payload = _request(
                "GET", f"/api/v2/estimations/{estimation['estimation_id']}/checkpoints"
            )
            st.session_state["v2_history"] = payload
        if st.session_state.get("v2_history"):
            st.dataframe(
                st.session_state["v2_history"].get("checkpoints", []),
                use_container_width=True,
                hide_index=True,
            )
        st.caption("Scenario branching is non-destructive and creates a new estimation identity.")
    with audit:
        if st.button("Build sanitized audit packet"):
            packet = _request("GET", f"/api/v2/estimations/{estimation['estimation_id']}/audit")
            st.session_state["v2_audit"] = packet
        if st.session_state.get("v2_audit"):
            st.json(st.session_state["v2_audit"])
            st.download_button(
                "Download audit packet",
                data=json.dumps(st.session_state["v2_audit"], ensure_ascii=False, indent=2),
                file_name=f"estimation-{estimation['estimation_id']}-audit.json",
                mime="application/json",
            )


def main() -> None:
    st.set_page_config(page_title="Estimation Control Room V2", page_icon="🎛️", layout="wide")
    st.title("Estimation Control Room V2")
    st.caption(
        "One durable estimation workflow: product structure, parallel evidence, typed policy, "
        "human control, checkpoints and audit."
    )
    with st.sidebar:
        st.subheader("Execution")
        st.code(get_backend_url())
        reconnect_id = st.text_input(
            "Estimation ID", value=st.session_state.get("v2_estimation_id", "")
        )
        if st.button("Reconnect", use_container_width=True) and reconnect_id:
            _store(_request("GET", f"/api/v2/estimations/{reconnect_id}"))
            st.rerun()
        if st.button("New estimation", use_container_width=True):
            for key in ("v2_response", "v2_estimation_id", "v2_history", "v2_audit"):
                st.session_state.pop(key, None)
            st.rerun()

    if "v2_response" not in st.session_state:
        with st.form("v2-create"):
            transcript = st.text_area(
                "Project transcript",
                height=220,
                placeholder="Describe scope, constraints and acceptance criteria.",
            )
            profile = st.selectbox(
                "Execution profile",
                ["balanced", "cost_first", "quality_first", "human_controlled"],
                format_func=lambda value: value.replace("_", " ").title(),
            )
            submitted = st.form_submit_button("Start durable estimation", type="primary")
        if submitted:
            with st.spinner("Running until the next durable decision gate..."):
                _store(
                    _request(
                        "POST",
                        "/api/v2/estimations",
                        json={"context": {"transcript": transcript}, "profile": profile},
                    )
                )
            st.rerun()
        return

    response = st.session_state["v2_response"]
    _render_execution(response["estimation"])


if __name__ == "__main__":
    main()
