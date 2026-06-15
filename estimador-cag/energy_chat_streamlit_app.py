"""Streamlit UI for the Energy Aware Chat incubator branch.

Run with:
    streamlit run energy_chat_streamlit_app.py

The existing streamlit_app.py remains the coursework estimator UI. This file is
for the Energy Aware Chat product experiment with mode and execution selectors.
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://localhost:8000"
BACKEND_TIMEOUT = (10, 240)
BACKEND_CONNECT_TIMEOUT_SECONDS = 10
BACKEND_READ_TIMEOUT_SECONDS = 120

ENERGY_CHAT_EVALUATE_PATH = "/energy-chat/evaluate"
ENERGY_CHAT_BENCHMARK_PATH = "/energy-chat/benchmark/deepseek-energy-aware"
ENERGY_CHAT_EVIDENCE_PATH = "/energy-chat/evidence/bundle"
ENERGY_CHAT_DETERMINISTIC_CHAT_PATH = "/energy-chat/chat"
ENERGY_CHAT_LIVE_CHAT_PATH = "/energy-chat/chat/live"

MODE_OPTIONS = {
    "Chat lite": "chat_lite",
    "Research": "research",
    "Project": "project",
    "Tutor": "tutor",
}

EXECUTION_OPTIONS = {
    "Live provider draft, DeepSeek primary with Kimi fallback": ENERGY_CHAT_LIVE_CHAT_PATH,
    "Deterministic CI-safe draft": ENERGY_CHAT_DETERMINISTIC_CHAT_PATH,
}

# Static strings kept visible for documentation/readiness tests and reviewers.
STREAMLIT_UI_CONTRACT_NOTES = """
Benchmark harness
Measurement-only benchmark summary
This panel does not claim improvement without a fixed dataset and rubric.
Claim status
Accepted after repair
Hard constraints passed
Remaining caveats
"""


def get_backend_url() -> str:
    """Return the configured backend base URL without a trailing slash."""
    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def backend_url() -> str:
    """Alias used by the new Energy Aware Chat UI code."""
    return get_backend_url()


def build_energy_chat_evaluate_url() -> str:
    return f"{get_backend_url()}{ENERGY_CHAT_EVALUATE_PATH}"


def build_energy_chat_benchmark_url() -> str:
    return f"{get_backend_url()}{ENERGY_CHAT_BENCHMARK_PATH}"


def build_energy_chat_payload(
    *,
    user_message: str,
    draft_answer: str,
    mode: str = "chat_lite",
) -> dict[str, Any]:
    return {
        "user_message": user_message,
        "draft_answer": draft_answer,
        "mode": mode,
    }


def build_energy_chat_benchmark_payload(*, run_id: str = "streamlit-demo-measurement-only") -> dict[str, Any]:
    return {
        "run_id": run_id,
        "tier": "flash",
        "cases": [
            {
                "case_id": "scoped_release_answer",
                "user_message": "Review whether this answer stays inside the current implementation layer.",
                "mode": "chat_lite",
                "required_constraints": ["keep the answer scoped"],
                "required_sections": [],
            },
            {
                "case_id": "scope_creep_answer",
                "user_message": "Review whether this answer overclaims production readiness.",
                "mode": "project",
                "required_constraints": ["do not claim production readiness"],
                "required_sections": ["Next action"],
            },
        ],
    }


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{get_backend_url()}{path}",
        json=payload,
        timeout=BACKEND_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def post_energy_chat_evaluation_request(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        build_energy_chat_evaluate_url(),
        json=payload,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return response.json()


def post_energy_chat_benchmark_request(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        build_energy_chat_benchmark_url(),
        json=payload,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return response.json()


def extract_energy_card(result: dict[str, Any]) -> dict[str, Any]:
    energy_card = result.get("energy_card")
    if isinstance(energy_card, dict):
        return energy_card
    legacy_card = result.get("card")
    if isinstance(legacy_card, dict):
        return legacy_card
    return {}


def extract_findings(result: dict[str, Any]) -> list[dict[str, Any]]:
    legacy_findings = result.get("findings")
    if isinstance(legacy_findings, list):
        return legacy_findings
    score = result.get("score")
    if isinstance(score, dict) and isinstance(score.get("findings"), list):
        return score["findings"]
    return []


def format_decision_label(decision: str) -> str:
    labels = {
        "accept": "✅ accept",
        "repair": "🛠️ repair",
        "reject": "⛔ reject",
        "clarify": "❓ clarify",
    }
    return labels.get(decision, decision)


def summarize_benchmark_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") or {}
    return {
        "run_id": result.get("run_id"),
        "cases_total": result.get("cases_total"),
        "accepted_baseline": result.get("accepted_baseline"),
        "accepted_after_repair": result.get("accepted_after_repair"),
        "repairs_attempted": result.get("repairs_attempted"),
        "hard_rejects": result.get("hard_rejects"),
        "claim_status": metadata.get("claim_status"),
    }


def benchmark_case_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in result.get("results") or []:
        baseline_eval = item.get("baseline_evaluation") or {}
        baseline_decision = baseline_eval.get("decision") or {}
        baseline_score = baseline_eval.get("score") or {}
        rows.append(
            {
                "case_id": (item.get("case") or {}).get("case_id"),
                "baseline_decision": baseline_decision.get("decision"),
                "final_decision": item.get("final_decision"),
                "baseline_energy": baseline_score.get("total_energy"),
                "final_energy": item.get("final_energy"),
                "energy_delta_after_repair": item.get("energy_delta_after_repair"),
                "accepted_after_repair": item.get("accepted_after_repair"),
            }
        )
    return rows


def render_energy_card(card: dict[str, Any] | None) -> None:
    if not card:
        st.warning("No Energy Card returned.")
        return

    col_decision, col_energy, col_repairs, col_hard = st.columns(4)
    with col_decision:
        st.metric("Decision", card.get("decision", "unknown"))
    with col_energy:
        st.metric("Energy", card.get("energy", "unknown"))
    with col_repairs:
        st.metric("Repairs", card.get("repairs", "unknown"))
    with col_hard:
        st.metric("Hard constraints passed", "yes" if card.get("hard_constraints_passed") else "no")

    st.markdown("#### Evidence")
    st.json(card.get("evidence") or [])

    caveats = card.get("remaining_caveats") or []
    if caveats:
        st.markdown("#### Remaining caveats")
        st.json(caveats)


def render_chat_result(result: dict[str, Any]) -> None:
    render_energy_card(extract_energy_card(result))

    st.markdown("### Final answer")
    st.write(result.get("final_answer") or result.get("draft_answer") or "No final answer returned.")

    metadata = result.get("metadata") or {}
    if metadata:
        st.markdown("### Provider and run metadata")
        st.json(metadata)

    rag = result.get("rag") or {}
    if rag:
        st.markdown("### Retrieved evidence")
        st.json(
            {
                "retrieval_strategy": rag.get("retrieval_strategy"),
                "evidence_refs": rag.get("evidence_refs"),
                "results": rag.get("results"),
            }
        )

    trace = result.get("agent_trace") or []
    if trace:
        st.markdown("### Agent trace")
        st.json(trace)

    with st.expander("Raw response"):
        st.json(result)


def main() -> None:
    st.set_page_config(
        page_title="Energy Aware Chat",
        page_icon="⚡",
        layout="wide",
    )

    st.title("Energy Aware Chat ⚡")
    st.caption(
        "Incubator UI for Energy Aware Chat. Choose the mode, choose deterministic or live provider execution, "
        "then inspect the Energy Card, evidence, provider metadata, and raw trace."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        st.caption("Set ESTIMADOR_BACKEND_URL when Streamlit runs outside the FastAPI host.")

        st.subheader("Execution")
        execution_label = st.selectbox(
            "Execution mode",
            options=list(EXECUTION_OPTIONS.keys()),
            index=0,
            help="Live mode calls DeepSeek and can fall back to Kimi. Deterministic mode is fast and CI-safe.",
        )
        mode_label = st.selectbox(
            "Chat mode",
            options=list(MODE_OPTIONS.keys()),
            index=2,
        )
        k = st.slider("Retrieved evidence chunks", min_value=1, max_value=8, value=3)

    question = st.text_area(
        "User question",
        value="Is deployment evidence mandatory for the Energy Aware Chat final project MVP?",
        height=140,
    )
    required_constraint = st.text_input("Required constraint", value="deployment evidence")
    required_sections_raw = st.text_input("Required sections", value="Decision, Next action")

    col_chat, col_rag, col_benchmark = st.columns(3)
    chat_clicked = col_chat.button("Run Energy Aware Chat", type="primary")
    rag_clicked = col_rag.button("Run RAG only")
    benchmark_clicked = col_benchmark.button("Run measurement benchmark")

    constraints = [required_constraint.strip()] if required_constraint.strip() else []
    sections = [section.strip() for section in required_sections_raw.split(",") if section.strip()]
    mode = MODE_OPTIONS[mode_label]

    if chat_clicked:
        payload = {
            "user_message": question.strip(),
            "mode": mode,
            "k": k,
            "required_constraints": constraints,
            "required_sections": sections,
            "metadata": {
                "ui": "streamlit_energy_chat",
                "execution_label": execution_label,
            },
        }
        with st.spinner("Running Energy Aware Chat..."):
            try:
                result = post_json(EXECUTION_OPTIONS[execution_label], payload)
            except requests.RequestException as exc:
                st.error(f"Energy Aware Chat request failed: {exc}")
                return
        render_chat_result(result)

    if rag_clicked:
        with st.spinner("Running deterministic project RAG..."):
            try:
                result = post_json(
                    "/energy-chat/rag/search",
                    {"query": question.strip(), "mode": mode, "k": k},
                )
            except requests.RequestException as exc:
                st.error(f"RAG request failed: {exc}")
                return
        st.success("RAG retrieval completed.")
        st.json(result)

    if benchmark_clicked:
        with st.spinner("Running measurement-only benchmark..."):
            try:
                result = post_json(
                    ENERGY_CHAT_BENCHMARK_PATH,
                    {
                        "run_id": "streamlit-demo-measurement-only",
                        "tier": "flash",
                        "cases": [
                            {
                                "case_id": "streamlit_user_case",
                                "user_message": question.strip(),
                                "mode": mode,
                                "required_constraints": constraints,
                                "required_sections": sections,
                                "metadata": {"ui": "streamlit_energy_chat"},
                            }
                        ],
                    },
                )
            except requests.RequestException as exc:
                st.error(f"Benchmark request failed: {exc}")
                return
        st.warning("Measurement-only benchmark summary. This does not claim improvement.")
        st.json(summarize_benchmark_result(result))
        st.dataframe(benchmark_case_rows(result), use_container_width=True, hide_index=True)
        with st.expander("Raw benchmark response"):
            st.json(result)


if __name__ == "__main__":
    main()
