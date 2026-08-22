FROM python:3.11-slim@sha256:a630a63cdb314e2d138a2fca3e375e319e8568346ffafac5b980f888630ac4f1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system eacode && useradd --system --gid eacode --home /app eacode

WORKDIR /app

COPY deploy/eacode/requirements.generated.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY app ./app
COPY energy_core ./energy_core
COPY data ./data

RUN chown -R eacode:eacode /app

USER eacode

EXPOSE 8000

CMD ["uvicorn", "app.eacode.production_app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
