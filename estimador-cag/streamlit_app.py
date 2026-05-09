"""
LAYER: streamlit (frontend)
RESPONSIBILITY: Conversational UI for the CAG estimator.
WHY IT EXISTS: Session 3 Nivel 1+2+3. Non-technical users can paste
               meeting transcriptions and see estimations in real time.
DEPENDS ON: app.services.llm_service (estimate, estimate_stream),
            app.context.examples (ESTIMATION_EXAMPLES),
            app.middleware.logging (get_last_metrics)
"""

import hashlib
from datetime import UTC, datetime

import streamlit as st
from dotenv import load_dotenv

from app.context.examples import ESTIMATION_EXAMPLES
from app.middleware.logging import get_last_metrics
from app.services.llm_service import build_system_prompt, estimate, estimate_stream

load_dotenv()

st.set_page_config(
    page_title="LIDR Estimador CAG",
    page_icon="💬",
    layout="wide",
)

# Streamlit reruns this file from top to bottom whenever a widget changes.
# Anything that must survive reruns belongs in st.session_state.
if "messages" not in st.session_state:
    st.session_state.messages = []

if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = []

if "streaming_cache" not in st.session_state:
    st.session_state.streaming_cache = {}

st.title("💬 LIDR Estimador CAG")
st.caption("Context-Augmented Generation para estimacion de software")

def make_streaming_cache_key(transcription: str, tier: str) -> str:
    """
    LAYER: streamlit frontend cache
    RESPONSIBILITY: Build a deterministic key for Streamlit streaming responses.
    WHY IT EXISTS: estimate_stream yields tokens and is not covered by the backend
    exact cache decorator, so the UI needs a tiny local cache for repeated demos.
    DEPENDS_ON: hashlib
    """
    raw = f"{tier}::{transcription}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# --- NIVEL 3: Sidebar with CAG visibility and local call history ---
with st.sidebar:
    st.header("Contexto CAG")

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
            "backup_pro puede ser inestable hasta completar LiteLLM."
        ),
    )

    st.subheader("Metricas ultima llamada")

    if st.session_state.metrics_history:
        latest_metrics = st.session_state.metrics_history[-1]
        st.json(latest_metrics)
    else:
        backend_metrics = get_last_metrics()
        if backend_metrics:
            st.json(backend_metrics)
        else:
            st.info("Aun no hay llamadas")

    if st.session_state.metrics_history:
        with st.expander("Historial de llamadas", expanded=False):
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

        if st.button("Limpiar historial de metricas"):
            st.session_state.metrics_history = []
            st.rerun()

# --- NIVEL 1: Chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Input ---
if prompt := st.chat_input("Pega aqui la transcripcion de la reunion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        result = None
        cache_hit = False

        if use_streaming:
            cache_key = make_streaming_cache_key(prompt, tier)

            if cache_key in st.session_state.streaming_cache:
                full_response = st.session_state.streaming_cache[cache_key]
                cache_hit = True
                st.markdown(full_response)
            else:
                full_response = st.write_stream(estimate_stream(prompt, tier=tier))
                st.session_state.streaming_cache[cache_key] = full_response
        else:
            result = estimate(prompt, tier=tier)
            full_response = result["estimation"]
            cache_hit = result.get("cached", False)
            st.markdown(full_response)

    call_metrics = {
        "timestamp": datetime.now(UTC).isoformat(),
        "mode": "streamlit_streaming" if use_streaming else "streamlit_sync",
        "tier": tier,
        "output_chars": len(full_response),
        "cached": cache_hit,
        "note": (
            "Streamlit uses a local exact cache for streaming demos. "
            "Backend /metrics is updated by API calls."
        ),
    }

    st.session_state.metrics_history.append(call_metrics)
    st.session_state.metrics_history = st.session_state.metrics_history[-20:]

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )

    # Force one clean rerun so the sidebar updates immediately after the call.
    st.rerun()
