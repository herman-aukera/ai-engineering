FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS eacode-builder
WORKDIR /build
COPY requirements-eacode-runtime.txt ./
RUN uv venv /opt/eacode-venv \
    && uv pip install \
       --python /opt/eacode-venv/bin/python \
       --requirement requirements-eacode-runtime.txt

FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS full-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/full-venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS test-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/test-venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

FROM python:3.11.13-slim-bookworm AS test
ENV PATH="/opt/test-venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=test-builder /opt/test-venv /opt/test-venv
COPY . /app
CMD ["python", "-m", "pytest", "-q"]

FROM python:3.11.13-slim-bookworm AS full-runtime
ENV PATH="/opt/full-venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=full-builder /opt/full-venv /opt/full-venv
COPY --chown=appuser:appuser . /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11.13-slim-bookworm AS runtime
ENV PATH="/opt/eacode-venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EACODE_DEMO_DB_PATH="/data/eacode-demo.sqlite3"
RUN useradd --create-home --uid 10001 eacode \
    && mkdir -p /app/app/routers /data \
    && chown -R eacode:eacode /app /data
WORKDIR /app
COPY --from=eacode-builder /opt/eacode-venv /opt/eacode-venv
COPY --chown=eacode:eacode app/__init__.py /app/app/__init__.py
COPY --chown=eacode:eacode app/eacode_main.py /app/app/eacode_main.py
COPY --chown=eacode:eacode app/routers/__init__.py /app/app/routers/__init__.py
COPY --chown=eacode:eacode app/routers/eacode.py /app/app/routers/eacode.py
COPY --chown=eacode:eacode energy_core /app/energy_core
USER eacode
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["python", "-m", "uvicorn", "app.eacode_main:app", "--host", "0.0.0.0", "--port", "8000"]
