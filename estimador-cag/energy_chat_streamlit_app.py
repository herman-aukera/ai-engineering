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
ENERGY_CHAT_BENCHMARK_PATH = "/energy-chat/benchmark/deepseek-energy-aware"
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


def build_energy_chat_benchmark_url() -> str:
    """Build the measurement-only benchmark endpoint URL."""

    return f"{get_backend_url()}{ENERGY_CHAT_BENCHMARK_PATH}"


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


def build_energy_chat_benchmark_payload(run_id: str | None = None) -> dict[str, Any]:
    """Build a small fixed benchmark payload for the browser demo."""

    payload: dict[str, Any] = {
        "tier": "flash",
        "cases": [
            {
                "case_id": "scoped_release_answer",
                "user_message": "Should this answer stay scoped to the current validated slice?",
            },
            {
                "case_id": "scope_creep_answer",
                "user_message": "Review a plan that tries to skip gates and add future work.",
            },
        ],
    }
    if run_id:
        payload["run_id"] = run_id
    return payload


def post_energy_chat_evaluation_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Send an Energy Aware Chat evaluation request to the backend."""

    response = requests.post(
        build_energy_chat_evaluate_url(),
        json=payload,
        timeout=(BACKEND_CONNECT_TIMEOUT_SECONDS, BACKEND_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return response.json()


def post_energy_chat_benchmark_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Send a measurement-only benchmark request to the backend."""

    response = requests.post(
        build_energy_chat_benchmark_url(),
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


def extract_findings(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return critic findings from the current or legacy response shape."""

    findings = result.get("findings")
    if isinstance(findings, list):
        return [item for item in findings if isinstance(item, dict)]

    score = result.get("score")
    if isinstance(score, dict):
        score_findings = score.get("findings")
        if isinstance(score_findings, list):
            return [item for item in score_findings if isinstance(item, dict)]
    return []


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
    render_findings(extract_findings(result))

    with st.expander("Raw evaluation result"):
        st.json(result)


def summarize_benchmark_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract compact benchmark summary metrics for Streamlit rendering."""

    return {
        "run_id": result.get("run_id", "unknown"),
        "cases_total": result.get("cases_total", 0),
        "accepted_baseline": result.get("accepted_baseline", 0),
        "accepted_after_repair": result.get("accepted_after_repair", 0),
        "repairs_attempted": result.get("repairs_attempted", 0),
        "hard_rejects": result.get("hard_rejects", 0),
        "claim_status": (result.get("metadata") or {}).get(
            "claim_status",
            "measurement_only_no_quality_claim",
        ),
    }


def benchmark_case_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten benchmark case results into UI-friendly rows."""

    rows: list[dict[str, Any]] = []
    for item in result.get("results") or []:
        if not isinstance(item, dict):
            continue
        case = item.get("case") or {}
        baseline_eval = item.get("baseline_evaluation") or {}
        baseline_decision = (baseline_eval.get("decision") or {}).get("decision", "unknown")
        baseline_energy = (baseline_eval.get("score") or {}).get("total_energy", "unknown")
        rows.append(
            {
                "case_id": case.get("case_id", "unknown"),
                "baseline_decision": baseline_decision,
                "final_decision": item.get("final_decision", "unknown"),
                "baseline_energy": baseline_energy,
                "final_energy": item.get("final_energy", "unknown"),
                "energy_delta_after_repair": item.get(
                    "energy_delta_after_repair",
                    "unknown",
                ),
                "accepted_after_repair": item.get("accepted_after_repair", False),
            }
        )
    return rows


def render_benchmark_result(result: dict[str, Any]) -> None:
    """Render measurement-only benchmark output for a human demo."""

    summary = summarize_benchmark_result(result)
    st.subheader("Measurement-only benchmark summary")
    st.caption("This panel records measurements only. It does not claim improvement.")

    col_cases, col_baseline, col_after, col_repairs = st.columns(4)
    with col_cases:
        st.metric("Cases", summary["cases_total"])
    with col_baseline:
        st.metric("Accepted baseline", summary["accepted_baseline"])
    with col_after:
        st.metric("Accepted after repair", summary["accepted_after_repair"])
    with col_repairs:
        st.metric("Repairs attempted", summary["repairs_attempted"])

    st.caption(f"Claim status: {summary['claim_status']}")
    rows = benchmark_case_rows(result)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("No benchmark case rows returned.")

    with st.expander("Raw benchmark result"):
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
        "Deterministic evaluator, FastAPI endpoint, Streamlit Energy Card, "
        "one-pass repair seam, and measurement-only benchmark harness."
    )

    with st.sidebar:
        st.subheader("Backend")
        st.code(get_backend_url())
        st.caption("Set ESTIMADOR_BACKEND_URL when running outside localhost.")
        st.subheader("Scope")
        st.markdown("- deterministic evaluator")
        st.markdown("- FastAPI evaluation endpoint")
        st.markdown("- one-pass deterministic repair")
        st.markdown("- measurement-only benchmark harness")
        st.markdown("- no RAG yet")
        st.markdown("- no improvement claim yet")

    evaluate_tab, benchmark_tab = st.tabs(
        ["Evaluate answer", "Benchmark harness"],
    )

    with evaluate_tab:
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
        else:
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
                except requests.RequestException as exc:
                    st.error(f"Could not reach backend: {exc}")
                else:
                    render_evaluation_result(result)
                    with st.expander("Request payload"):
                        st.json(payload)

    with benchmark_tab:
        st.write(
            "Run a tiny measurement-only benchmark through the API. Normal tests "
            "use fake providers; live provider quality is not claimed here."
        )
        benchmark_run_id = st.text_input(
            "Benchmark run ID",
            value="streamlit-demo-001",
        )
        benchmark_submitted = st.button("Run measurement benchmark")
        if benchmark_submitted:
            payload = build_energy_chat_benchmark_payload(run_id=benchmark_run_id)
            with st.spinner("Running measurement-only benchmark..."):
                try:
                    benchmark_result = post_energy_chat_benchmark_request(payload)
                except requests.HTTPError as exc:
                    response_text = exc.response.text if exc.response is not None else str(exc)
                    st.error(f"Backend returned an error: {response_text}")
                except requests.RequestException as exc:
                    st.error(f"Could not reach backend: {exc}")
                else:
                    render_benchmark_result(benchmark_result)
                    with st.expander("Benchmark request payload"):
                        st.json(payload)


if __name__ == "__main__":
    main()
