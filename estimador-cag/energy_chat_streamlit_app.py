"""
Streamlit demo for the Energy Aware Chat deterministic evaluator.

LAYER: frontend
RESPONSIBILITY: Let a human paste a user message and draft answer, call the
                FastAPI /energy-chat/evaluate endpoint, and inspect the visible
                Energy Card.
WHY IT EXISTS: Slice 3 gives the Energy Aware Chat core a browser demo without
               adding model calls, RAG, agents, or provider dependencies.
DEPENDS ON: streamlit, requests, FastAPI /energy-chat/evaluate.
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://localhost:8000"
ENERGY_CHAT_EVALUATE_PATH = "/energy-chat/evaluate"
BACKEND_CONNECT_TIMEOUT_SECONDS = 10
BACKEND_READ_TIMEOUT_SECONDS = 120

DEMO_USER_MESSAGE = "Review this release-readiness answer and tell me whether it satisfies the constraints."
DEMO_DRAFT_ANSWER = (
    "The answer is scoped, cites no fabricated sources, names the main caveat, "
    "and the next action is to run the validation gate before claiming success."
)


def get_backend_url() -> str:
    """Return the configured backend base URL without a trailing slash."""

    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def build_energy_chat_evaluate_url() -> str:
    """Build the FastAPI Energy Aware Chat evaluation endpoint URL."""

    return f"{get_backend_url()}{ENERGY_CHAT_EVALUATE_PATH}"


def build_energy_chat_payload(
    user_message: str,
    draft_answer: str,
    mode: str = "chat_lite",
) -> dict[str, Any]:
    """Build the deterministic evaluator request payload used by the demo."""

    return {
        "user_message": user_message,
        "draft_answer": draft_answer,
        "mode": mode,
    }


def post_energy_chat_evaluation_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Send an Energy Aware Chat evaluation request to the backend."""

    response = requests.post(
        build_energy_chat_evaluate_url(),
        json=payload,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return response.json()


def extract_energy_card(result: dict[str, Any]) -> dict[str, Any]:
    """Return the visible Energy Card from the FastAPI evaluation result.

    The backend contract returns the card under `energy_card`. Keep a legacy
    `card` fallback so older local demo payloads do not break while the product
    evolves through early slices.
    """

    card = result.get("energy_card") or result.get("card") or {}
    if isinstance(card, dict):
        return card
    return {}


def format_decision_label(decision: str) -> str:
    """Return a compact human label for an Energy Aware decision."""

    labels = {
        "accept": "✅ accept",
        "repair": "🛠️ repair",
        "reject": "⛔ reject",
        "clarify": "❓ clarify",
    }
    return labels.get(decision, f"⚠️ {decision}")


def render_energy_card(card: dict[str, Any]) -> None:
    """Render the visible Energy Card returned by the evaluator."""

    decision = str(card.get("decision", "unknown"))
    energy = card.get("energy", "unknown")
    hard_constraints_passed = card.get("hard_constraints_passed", False)
    repairs = card.get("repairs", 0)

    st.subheader("Energy Card")
    col_decision, col_energy, col_repairs = st.columns(3)

    with col_decision:
        st.metric("Decision", format_decision_label(decision))

    with col_energy:
        st.metric("Energy", energy)

    with col_repairs:
        st.metric("Repairs", repairs)

    if hard_constraints_passed:
        st.success("Hard constraints passed.")
    else:
        st.error("At least one hard constraint is still blocking acceptance.")

    evidence = card.get("evidence") or []
    caveats = card.get("remaining_caveats") or []

    with st.expander("Evidence refs", expanded=True):
        if evidence:
            for item in evidence:
                st.markdown(f"- {item}")
        else:
            st.caption("No evidence refs returned.")

    with st.expander("Remaining caveats", expanded=bool(caveats)):
        if caveats:
            for item in caveats:
                st.markdown(f"- {item}")
        else:
            st.caption("No remaining caveats returned.")


def render_findings(findings: list[dict[str, Any]]) -> None:
    """Render critic findings as inspectable rows for class/demo review."""

    st.subheader("Critic findings")
    if not findings:
        st.success("No critic findings.")
        return

    st.dataframe(findings, use_container_width=True, hide_index=True)


def render_evaluation_result(result: dict[str, Any]) -> None:
    """Render the deterministic evaluator result for a human demo."""

    render_energy_card(extract_energy_card(result))
    render_findings(result.get("findings") or [])

    with st.expander("Raw evaluation result"):
        st.json(result)


def main() -> None:
    """Render the Energy Aware Chat Streamlit demo."""

    st.set_page_config(
        page_title="Energy Aware Chat Demo",
        page_icon="⚡",
        layout="wide",
    )

    st.title("Energy Aware Chat")
    st.caption(
        "Deterministic Slice 3 demo: paste a user request and draft answer, "
        "then inspect the Energy Card before any model integration exists."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        st.caption("Set ESTIMADOR_BACKEND_URL when running outside localhost.")
        st.subheader("Scope")
        st.markdown("- deterministic evaluator only")
        st.markdown("- no DeepSeek call")
        st.markdown("- no RAG")
        st.markdown("- no repair loop yet")

    with st.form("energy_chat_evaluation_form"):
        user_message = st.text_area(
            "User message",
            value=DEMO_USER_MESSAGE,
            height=160,
        )
        draft_answer = st.text_area(
            "Draft answer candidate",
            value=DEMO_DRAFT_ANSWER,
            height=220,
        )
        mode = st.selectbox("Mode", options=["chat_lite"], index=0)
        submitted = st.form_submit_button("Evaluate answer", type="primary")

    if not submitted:
        st.info("Submit the form to evaluate the draft answer and render an Energy Card.")
        return

    payload = build_energy_chat_payload(
        user_message=user_message,
        draft_answer=draft_answer,
        mode=mode,
    )

    with st.spinner("Evaluating candidate answer..."):
        try:
            result = post_energy_chat_evaluation_request(payload)
        except requests.HTTPError as exc:
            response_text = exc.response.text if exc.response is not None else str(exc)
            st.error(f"Backend returned an error: {response_text}")
            return
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")
            return

    render_evaluation_result(result)

    with st.expander("Request payload"):
        st.json(payload)


if __name__ == "__main__":
    main()
