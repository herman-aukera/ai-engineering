from pathlib import Path


def test_streamlit_does_not_import_llm_service_runtime_functions_directly():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    forbidden_imports = [
        "from app.services.llm_service import estimate",
        "from app.services.llm_service import estimate_stream",
        "estimate, estimate_stream",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source

    assert "request_estimate(" in source
    assert "stream_estimate(" in source


def test_streamlit_defines_backend_url_and_api_paths():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "BACKEND_URL" in source
    assert "/api/v1/estimate" in source
    assert "/api/v1/estimate/stream" in source
    assert "/metrics" in source


def test_streamlit_uses_requests_for_backend_calls():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "requests.post(" in source
    assert "requests.get(" in source
    assert "f\"{BACKEND_URL}{ESTIMATE_PATH}\"" in source
    assert "f\"{BACKEND_URL}{STREAM_PATH}\"" in source


def test_streamlit_does_not_use_local_streaming_cache_as_backend_cache():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "streaming_cache" not in source
    assert "make_streaming_cache_key" not in source
    assert "cache_key" not in source


def test_streamlit_streaming_mode_calls_backend_stream_function_directly():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "st.write_stream(" in source
    assert "stream_estimate(prompt, tier=tier, history=backend_history)" in source
    assert "st.write_stream(estimate_stream" not in source


def test_streamlit_sse_parser_preserves_token_leading_spaces():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "def parse_sse_data_line(" in source
    assert ".lstrip()" not in source


def test_streamlit_builds_backend_history_payload_from_chat_messages():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "def build_backend_history(" in source
    assert "backend_history = build_backend_history(messages_before_current_prompt)" in source
    assert '"history": history or []' in source
    assert '"max_history_turns": max_history_turns' in source


def test_streamlit_backend_history_excludes_current_prompt_before_send():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "messages_before_current_prompt" in source
    assert "build_backend_history(messages_before_current_prompt)" in source
