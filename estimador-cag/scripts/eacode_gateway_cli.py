"""Generic stdin/file bridge from coding tools to the EACODE governance gateway.

No vendor SDK is required. A coding tool only needs to emit the normalized JSON
contract. Authentication is read from EACODE_SESSION_TOKEN so it is not exposed
in process arguments or persisted in the payload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _read_payload(path: str | None) -> bytes:
    if path:
        return Path(path).read_bytes()
    return sys.stdin.buffer.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a coding-tool proposal through EACODE governance")
    parser.add_argument("--input", help="JSON file; stdin is used when omitted")
    parser.add_argument(
        "--api-url",
        default=os.getenv("EACODE_API_URL", "http://127.0.0.1:8000/api/v1/eacode"),
        help="EACODE API root; defaults to EACODE_API_URL",
    )
    args = parser.parse_args()
    token = os.getenv("EACODE_SESSION_TOKEN", "").strip()
    if not token:
        print("EACODE_SESSION_TOKEN is required", file=sys.stderr)
        return 2

    raw = _read_payload(args.input)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid proposal JSON: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        args.api_url.rstrip("/") + "/gateway/proposals",
        data=encoded,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - explicit configurable API target
            sys.stdout.write(response.read().decode("utf-8"))
            sys.stdout.write("\n")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body, file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"EACODE gateway unavailable: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
