FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY deploy/eachat/requirements.generated.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes --requirement /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt \
    && useradd --create-home --uid 10001 eachat

COPY --chown=eachat:eachat app /app/app
COPY --chown=eachat:eachat docs/energy_chat_v2_demo.html /app/docs/energy_chat_v2_demo.html

USER eachat
EXPOSE 8000

CMD ["uvicorn", "app.energy_chat.production_app:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
