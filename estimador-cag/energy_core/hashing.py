from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    """Return a labeled SHA-256 digest of the exact supplied bytes."""

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def sha256_text(payload: str) -> str:
    """Hash UTF-8 bytes without newline or whitespace normalization."""

    return sha256_bytes(payload.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    """Hash the exact bytes stored at path."""

    return sha256_bytes(Path(path).read_bytes())
