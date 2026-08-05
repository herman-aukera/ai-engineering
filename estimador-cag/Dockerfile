FROM ghcr.io/astral-sh/uv:0.12.1 AS uv-binary

FROM python:3.11.15-slim-bookworm AS builder-base
COPY --from=uv-binary /uv /uvx /bin/

FROM builder-base AS eacode-builder
WORKDIR /build
COPY requirements-eacode-runtime.txt ./
RUN uv venv /opt/eacode-venv \
    && uv pip install \
       --python /opt/eacode-venv/bin/python \
       --requirement requirements-eacode-runtime.txt

FROM builder-base AS full-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/full-venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM builder-base AS test-builder
ENV UV_PROJECT_ENVIRONMENT=/opt/test-venv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

FROM python:3.11.15-slim-bookworm AS hardened-python
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf \
       /usr/local/lib/python3.11/site-packages/pip* \
       /usr/local/lib/python3.11/site-packages/setuptools* \
       /usr/local/lib/python3.11/site-packages/wheel* \
       /usr/local/bin/pip*

FROM hardened-python AS test
ENV PATH="/opt/test-venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=test-builder /opt/test-venv /opt/test-venv
COPY . /app
CMD ["python", "-m", "pytest", "-q"]

FROM hardened-python AS full-runtime
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

FROM hardened-python AS runtime
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
