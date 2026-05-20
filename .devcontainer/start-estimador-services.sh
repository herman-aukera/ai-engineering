#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/workspaces/ai-engineering/estimador-cag"
cd "$PROJECT_DIR"

export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export ESTIMADOR_BACKEND_URL="${ESTIMADOR_BACKEND_URL:-http://localhost:8000}"

echo "[estimador] Starting Redis..."
docker compose up -d redis

echo "[estimador] Checking Redis..."
for attempt in {1..30}; do
  if docker compose exec -T redis redis-cli ping >/tmp/estimador-redis-ping.log 2>&1; then
    echo "[estimador] Redis is ready."
    break
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "[estimador] Redis did not become ready."
    cat /tmp/estimador-redis-ping.log || true
    exit 1
  fi

  sleep 1
done

echo "[estimador] Stopping stale FastAPI and Streamlit processes..."
pkill -f "uvicorn app.main:app" || true
pkill -f "streamlit run streamlit_app.py" || true
sleep 2

if ss -ltn | grep -q ':8000 '; then
  echo "[estimador] Port 8000 is already occupied by an unknown process."
  ss -ltnp | grep ':8000 ' || true
  exit 1
fi

if ss -ltn | grep -q ':8501 '; then
  echo "[estimador] Port 8501 is already occupied by an unknown process."
  ss -ltnp | grep ':8501 ' || true
  exit 1
fi

echo "[estimador] Starting FastAPI on port 8000..."
nohup env REDIS_URL="$REDIS_URL" uv run uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  > /tmp/estimador-fastapi.log 2>&1 &

echo "[estimador] Waiting for FastAPI..."
for attempt in {1..40}; do
  if curl -fsS http://localhost:8000/health >/tmp/estimador-health.json 2>/tmp/estimador-health.err; then
    echo "[estimador] FastAPI is ready."
    cat /tmp/estimador-health.json
    echo
    break
  fi

  if [ "$attempt" -eq 40 ]; then
    echo "[estimador] FastAPI did not become ready."
    echo "[estimador] FastAPI log:"
    tail -120 /tmp/estimador-fastapi.log || true
    exit 1
  fi

  sleep 1
done

echo "[estimador] Starting Streamlit on port 8501..."
nohup env ESTIMADOR_BACKEND_URL="$ESTIMADOR_BACKEND_URL" uv run streamlit run streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  > /tmp/estimador-streamlit.log 2>&1 &

echo "[estimador] Waiting for Streamlit..."
for attempt in {1..40}; do
  if curl -fsS http://localhost:8501 >/tmp/estimador-streamlit.html 2>/tmp/estimador-streamlit.err; then
    echo "[estimador] Streamlit is ready."
    break
  fi

  if [ "$attempt" -eq 40 ]; then
    echo "[estimador] Streamlit did not become ready."
    echo "[estimador] Streamlit log:"
    tail -120 /tmp/estimador-streamlit.log || true
    exit 1
  fi

  sleep 1
done

echo "[estimador] Services ready."
echo "[estimador] FastAPI log:   /tmp/estimador-fastapi.log"
echo "[estimador] Streamlit log: /tmp/estimador-streamlit.log"
