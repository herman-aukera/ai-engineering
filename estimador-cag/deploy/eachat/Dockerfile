FROM python:3.11-slim@sha256:a630a63cdb314e2d138a2fca3e375e319e8568346ffafac5b980f888630ac4f1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.12.1 \
    && useradd --create-home --uid 10001 eachat

COPY deploy/eachat/pyproject.toml /tmp/eachat-runtime/pyproject.toml
COPY deploy/eachat/uv.lock /tmp/eachat-runtime/uv.lock
RUN uv export --project /tmp/eachat-runtime --frozen --no-dev \
      --format requirements-txt --output-file /tmp/requirements.txt \
    && python -m pip install --no-cache-dir --require-hashes --requirement /tmp/requirements.txt \
    && rm -rf /tmp/eachat-runtime /tmp/requirements.txt

COPY --chown=eachat:eachat app /app/app
COPY --chown=eachat:eachat docs/energy_chat_v2_demo.html /app/docs/energy_chat_v2_demo.html

USER eachat
EXPOSE 8000

CMD ["uvicorn", "app.energy_chat.production_app:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
