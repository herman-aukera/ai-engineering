FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS runtime-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS test-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

FROM python:3.11.13-slim-bookworm AS test
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=test-builder /opt/venv /opt/venv
COPY . /app
CMD ["python", "-m", "pytest", "-q"]

FROM python:3.11.13-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EACODE_DEMO_DB_PATH="/data/eacode-demo.sqlite3"
RUN useradd --create-home --uid 10001 eacode \
    && mkdir -p /data \
    && chown eacode:eacode /data
WORKDIR /app
COPY --from=runtime-builder /opt/venv /opt/venv
COPY --chown=eacode:eacode app /app/app
COPY --chown=eacode:eacode energy_core /app/energy_core
COPY --chown=eacode:eacode docs /app/docs
COPY --chown=eacode:eacode data /app/data
COPY --chown=eacode:eacode .energy /app/.energy
USER eacode
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
