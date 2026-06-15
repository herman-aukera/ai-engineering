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

MODE_OPTIONS = {
    "Chat lite": "chat_lite",
    "Research": "research",
    "Project": "project",
    "Tutor": "tutor",
}

EXECUTION_OPTIONS = {
    "Live provider draft, DeepSeek primary with Kimi fallback": "/energy-chat/chat/live",
    "Deterministic CI-safe draft": "/energy-chat/chat",
}


def backend_url() -> str:
    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{backend_url()}{path}",
        json=payload,
        timeout=BACKEND_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


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
        st.metric("Hard constraints", "passed" if card.get("hard_constraints_passed") else "failed")

    st.markdown("#### Evidence")
    st.json(card.get("evidence") or [])

    caveats = card.get("remaining_caveats") or []
    if caveats:
        st.markdown("#### Caveats")
        st.json(caveats)


def render_chat_result(result: dict[str, Any]) -> None:
    render_energy_card(result.get("energy_card"))

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
        st.code(backend_url())
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
                    "/energy-chat/benchmark/deepseek-energy-aware",
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
        st.warning("Measurement-only output. This is not a validated quality-improvement claim.")
        st.json(result)


if __name__ == "__main__":
    main()
