#!/usr/bin/env sh
set -eu

: "${ROLLBACK_IMAGE:?Set ROLLBACK_IMAGE to the previous ghcr.io/...@sha256:<digest>}"

case "$ROLLBACK_IMAGE" in
  *@sha256:*) ;;
  *)
    echo "ROLLBACK_IMAGE must use an immutable sha256 digest." >&2
    exit 2
    ;;
esac

EACODE_IMAGE="$ROLLBACK_IMAGE" sh "$(dirname "$0")/deploy.sh"
