FROM ghcr.io/astral-sh/uv:0.8.3-python3.11-bookworm-slim AS builder
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

FROM python:3.11.13-slim-bookworm
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 eacode
WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --chown=eacode:eacode . /app
USER eacode
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
