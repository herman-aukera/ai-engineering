"""
LAYER: streamlit (frontend)
RESPONSIBILITY: Conversational UI for the CAG estimator.
WHY IT EXISTS: Session 3 Nivel 1+2+3. Non-technical users can paste
               meeting transcriptions and see estimations in real time.
DEPENDS ON: app.services.llm_service (estimate, estimate_stream),
            app.context.examples (ESTIMATION_EXAMPLES),
            app.middleware.logging (get_last_metrics)
"""


import streamlit as st
from dotenv import load_dotenv

from app.context.examples import ESTIMATION_EXAMPLES
from app.middleware.logging import get_last_metrics
from app.services.llm_service import build_system_prompt, estimate, estimate_stream

load_dotenv()

st.set_page_config(page_title="LIDR Estimador CAG", page_icon="💬")
st.title("💬 LIDR Estimador CAG")
st.caption("Context-Augmented Generation para estimacion de software")

# --- NIVEL 3: Sidebar ---
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

    st.subheader("Metricas ultima llamada")
    metrics = get_last_metrics()
    if metrics:
        st.json(metrics)
    else:
        st.info("Aun no hay llamadas")

# --- NIVEL 1: Chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Input ---
if prompt := st.chat_input("Pega aqui la transcripcion de la reunion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if use_streaming:
            # NIVEL 2: Streaming via st.write_stream
            full_response = st.write_stream(estimate_stream(prompt))
        else:
            result = estimate(prompt)
            full_response = result["estimation"]
            st.markdown(full_response)

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )
