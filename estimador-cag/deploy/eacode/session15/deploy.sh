#!/usr/bin/env sh
set -eu

COMPOSE_FILE="$(dirname "$0")/docker-compose.production.yml"

: "${EACODE_IMAGE:?Set EACODE_IMAGE to ghcr.io/...@sha256:<digest>}"
: "${PUBLIC_HOST:?Set PUBLIC_HOST to the public DNS name}"

case "$EACODE_IMAGE" in
  *@sha256:*) ;;
  *)
    echo "EACODE_IMAGE must use an immutable sha256 digest; refusing mutable tag." >&2
    exit 2
    ;;
esac

docker compose -f "$COMPOSE_FILE" config >/dev/null
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

attempt=1
while [ "$attempt" -le 30 ]; do
  if docker compose -f "$COMPOSE_FILE" exec -T eacode \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"; then
    echo "Deployment ready: $EACODE_IMAGE"
    docker compose -f "$COMPOSE_FILE" ps
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 2
done

echo "Deployment failed readiness gate; leaving containers for inspection." >&2
docker compose -f "$COMPOSE_FILE" ps >&2 || true
docker compose -f "$COMPOSE_FILE" logs --tail=200 eacode >&2 || true
exit 1
