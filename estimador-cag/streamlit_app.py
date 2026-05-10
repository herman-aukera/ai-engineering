"""
LAYER: streamlit (frontend)
RESPONSIBILITY: Conversational UI for the CAG estimator.
WHY IT EXISTS: Session 3 Nivel 1+2+3. Non-technical users can paste meeting
               transcriptions and see estimations in real time through the
               FastAPI backend, not by bypassing backend business logic.
DEPENDS_ON: os, hashlib, datetime, requests, streamlit,
            app.context.examples, app.services.llm_service.build_system_prompt

ARCHITECTURE NOTE:
Streamlit is a presentation layer. The production path calls FastAPI:
- POST /api/v1/estimate
- POST /api/v1/estimate/stream
- GET /metrics

This preserves one source of truth for Redis cache, LiteLLM routing, fallback,
metrics, and structured logging.
"""

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime

import requests
import streamlit as st
from dotenv import load_dotenv

from app.context.examples import ESTIMATION_EXAMPLES
from app.services.llm_service import build_system_prompt

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
ESTIMATE_PATH = "/api/v1/estimate"
STREAM_PATH = "/api/v1/estimate/stream"
METRICS_PATH = "/metrics"

st.set_page_config(
    page_title="LIDR Estimador CAG",
    page_icon="💬",
    layout="wide",
)



def get_backend_metrics() -> dict:
    """
    LAYER: streamlit backend client
    RESPONSIBILITY: Fetch current backend metrics from FastAPI.
    WHY IT EXISTS: Keeps Streamlit metrics aligned with the backend source of truth.
    DEPENDS_ON: requests, BACKEND_URL, METRICS_PATH
    """
    response = requests.get(f"{BACKEND_URL}{METRICS_PATH}", timeout=10)
    response.raise_for_status()
    return response.json()


def request_estimate(transcription: str, tier: str) -> dict:
    """
    LAYER: streamlit backend client
    RESPONSIBILITY: Call FastAPI synchronous estimation endpoint.
    WHY IT EXISTS: Ensures Streamlit uses Redis, LiteLLM, fallback, metrics,
                   and logging through the same backend path as every client.
    DEPENDS_ON: requests, BACKEND_URL, ESTIMATE_PATH
    """
    response = requests.post(
        f"{BACKEND_URL}{ESTIMATE_PATH}",
        json={"transcription": transcription, "tier": tier},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()



def parse_sse_data_line(line: str) -> str:
    """
    LAYER: streamlit backend client
    RESPONSIBILITY: Parse one Server Sent Events data line without destroying tokens.
    WHY IT EXISTS: SSE uses "data:" plus an optional separator space, but LLM tokens
                   may intentionally start with a space. Removing all leading spaces
                   glues streamed words together.
    DEPENDS_ON: str
    """
    value = line.removeprefix("data:")
    if value.startswith(" "):
        return value[1:]
    return value


def stream_estimate(transcription: str, tier: str) -> Iterator[str]:
    """
    LAYER: streamlit backend client
    RESPONSIBILITY: Consume FastAPI Server Sent Events and yield visible tokens.
    WHY IT EXISTS: Preserves streaming UX while keeping provider details in FastAPI.
    DEPENDS_ON: requests, BACKEND_URL, STREAM_PATH
    """
    with requests.post(
        f"{BACKEND_URL}{STREAM_PATH}",
        json={"transcription": transcription, "tier": tier},
        stream=True,
        timeout=120,
    ) as response:
        response.raise_for_status()

        event = None
        data_lines: list[str] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            line = raw_line or ""

            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
                continue

            if line.startswith("data:"):
                data_lines.append(parse_sse_data_line(line))
                continue

            if line == "":
                if event == "token" and data_lines:
                    yield "\n".join(data_lines)
                elif event == "error" and data_lines:
                    payload = "\n".join(data_lines)
                    try:
                        detail = json.loads(payload).get("detail", payload)
                    except json.JSONDecodeError:
                        detail = payload
                    raise RuntimeError(f"Backend stream error: {detail}")

                event = None
                data_lines = []


if "messages" not in st.session_state:
    st.session_state.messages = []

if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = []
st.title("💬 LIDR Estimador CAG")
st.caption("Context-Augmented Generation para estimacion de software")

with st.sidebar:
    st.header("Contexto CAG")
    st.caption(f"Backend: `{BACKEND_URL}`")

    with st.expander("Ver System Prompt"):
        st.code(build_system_prompt(), language="markdown")

    st.subheader("Ejemplos inyectados")
    for i, ex in enumerate(ESTIMATION_EXAMPLES, 1):
        summary = ex.get("meeting_summary", "")[:50]
        with st.expander(f"Ejemplo {i}: {summary}..."):
            st.markdown(f"**Transcripcion:**\n{ex.get('meeting_summary', '')}")
            st.markdown(f"**Estimacion:**\n{ex.get('estimation', '')}")

    st.divider()

    use_streaming = st.checkbox("Usar streaming (Nivel 2)", value=True)

    tier = st.selectbox(
        "Modelo",
        options=["flash", "pro", "backup", "backup_pro"],
        index=0,
        key="selected_tier",
        help=(
            "flash/pro usan DeepSeek. backup/backup_pro usan Kimi. "
            "backup_pro debe considerarse no confiable hasta verificar salida visible."
        ),
    )

    st.subheader("Metricas backend")

    try:
        backend_metrics = get_backend_metrics()
    except Exception as exc:
        st.warning(f"No se pudieron leer metricas del backend: {exc}")
        backend_metrics = {}

    if backend_metrics:
        st.json(backend_metrics)
    else:
        st.info("Aun no hay llamadas backend")

    if st.session_state.metrics_history:
        with st.expander("Historial UI local", expanded=False):
            for idx, item in enumerate(
                reversed(st.session_state.metrics_history[-10:]),
                start=1,
            ):
                label = (
                    f"#{idx} | {item['tier']} | {item['mode']} | "
                    f"{item['output_chars']} chars"
                )
                with st.expander(label):
                    st.json(item)

        if st.button("Limpiar historial UI"):
            st.session_state.metrics_history = []
            st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Pega aqui la transcripcion de la reunion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        result = None
        cache_hit = False

        if use_streaming:
            full_response = st.write_stream(stream_estimate(prompt, tier=tier))
            cache_hit = False
        else:
            result = request_estimate(prompt, tier=tier)
            full_response = result["estimation"]
            cache_hit = result.get("cached", False)
            st.markdown(full_response)

    call_metrics = {
        "timestamp": datetime.now(UTC).isoformat(),
        "mode": "backend_streaming" if use_streaming else "backend_sync",
        "tier": tier,
        "output_chars": len(full_response),
        "cached": cache_hit,
        "backend_url": BACKEND_URL,
        "note": (
            "Streamlit calls FastAPI. Backend /metrics is the source of truth "
            "for Redis, LiteLLM, fallback, and request observability."
        ),
    }

    if result:
        call_metrics["backend_result"] = {
            "model": result.get("model"),
            "provider": result.get("provider"),
            "cache_backend": result.get("cache_backend"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
        }

    st.session_state.metrics_history.append(call_metrics)
    st.session_state.metrics_history = st.session_state.metrics_history[-20:]

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )

    st.rerun()
