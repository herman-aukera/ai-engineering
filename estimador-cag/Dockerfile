FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY deploy/estimator/requirements.generated.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY app ./app
COPY artifacts/provider-readiness/provider-benchmark-snapshot.json \
    ./artifacts/provider-readiness/provider-benchmark-snapshot.json

RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.estimator.production_app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
