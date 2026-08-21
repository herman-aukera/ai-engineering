#!/usr/bin/env sh
set -eu

COMPOSE_FILE="$(dirname "$0")/docker-compose.production.yml"

: "${EACODE_IMAGE:?Set EACODE_IMAGE to ghcr.io/...@sha256:<digest>}"
: "${PUBLIC_HOST:?Set PUBLIC_HOST to the public DNS name}"
: "${EACODE_DATABASE_URL:?Set EACODE_DATABASE_URL to durable PostgreSQL}"
: "${EACODE_SESSION_SIGNING_KEY:?Set EACODE_SESSION_SIGNING_KEY}"

case "$EACODE_IMAGE" in
  *@sha256:*) ;;
  *)
    echo "EACODE_IMAGE must use an immutable sha256 digest; refusing mutable tag." >&2
    exit 2
    ;;
esac

docker compose -f "$COMPOSE_FILE" config >/dev/null
docker compose -f "$COMPOSE_FILE" pull

if [ -z "${GIT_SHA:-}" ]; then
  GIT_SHA="$(
    docker image inspect "$EACODE_IMAGE" \
      --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' \
      2>/dev/null || true
  )"
  GIT_SHA="${GIT_SHA:-unknown}"
  export GIT_SHA
fi

# Schema evolution is explicit and versioned; application startup only verifies it.
docker compose -f "$COMPOSE_FILE" run --rm --no-deps eacode \
  python -m energy_core.postgres_beta_store migrate

docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

attempt=1
while [ "$attempt" -le 30 ]; do
  if docker compose -f "$COMPOSE_FILE" exec -T eacode \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"; then
    echo "Deployment ready: $EACODE_IMAGE (git_sha=$GIT_SHA)"
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
