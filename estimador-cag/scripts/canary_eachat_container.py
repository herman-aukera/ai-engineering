"""Container canary for durable EACHAT health, restart recovery, and bounded load."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = os.environ.get("EACHAT_CANARY_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
EVIDENCE_DIR = Path(os.environ.get("EACHAT_CANARY_EVIDENCE", "/tmp/eachat-canary"))
CONVERSATION_FILE = EVIDENCE_DIR / "conversation-id.txt"


def request_json(path: str, *, method: str = "GET", payload: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            headers = {key.casefold(): value for key, value in response.headers.items()}
            return response.status, headers, data
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {path}: {detail}") from exc


def write_json(name: str, value: object) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / name).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def seed() -> None:
    status, _, created = request_json("/energy-chat/v2/conversations", method="POST")
    assert status == 201
    conversation_id = created["conversation_id"]
    first = request_json(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        method="POST",
        payload={
            "turn_id": "canary-turn-1",
            "expected_revision": 0,
            "user_message": "Remember the canary marker ORBIT-CONTAINER-17.",
        },
    )[2]
    second = request_json(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        method="POST",
        payload={
            "turn_id": "canary-turn-2",
            "expected_revision": 1,
            "user_message": "Use the prior visible turn as bounded context.",
        },
    )[2]
    assert first["revision"] == 1
    assert second["revision"] == 2
    assert first["turn"]["memory_message_count"] == 0
    assert second["turn"]["memory_message_count"] == 2
    assert first["turn"]["graph_thread_id"] != second["turn"]["graph_thread_id"]
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATION_FILE.write_text(conversation_id, encoding="utf-8")
    write_json("seed.json", {"created": created, "first": first, "second": second})


def verify() -> None:
    conversation_id = CONVERSATION_FILE.read_text(encoding="utf-8").strip()
    status, headers, health = request_json("/health")
    assert status == 200
    assert health["restart_persistent"] is True
    assert health["conversation_restart_persistent"] is True
    assert health["strict_msgpack"] is True
    assert headers.get("x-content-type-options") == "nosniff"
    history = request_json(f"/energy-chat/v2/conversations/{conversation_id}")[2]
    assert history["revision"] == 2
    assert len(history["turns"]) == 2
    assert history["turns"][1]["memory_message_count"] == 2
    assert all(turn["graph_response"]["energy_card_v2"] for turn in history["turns"])
    write_json("restart-verification.json", {"health": health, "history": history})


def load() -> None:
    def health_call(_: int) -> int:
        return request_json("/health")[0]

    def chat_call(index: int) -> int:
        return request_json(
            "/energy-chat/v2/chat",
            method="POST",
            payload={"user_message": f"Bounded canary request {index}."},
        )[0]

    with ThreadPoolExecutor(max_workers=12) as executor:
        health_statuses = list(executor.map(health_call, range(80)))
        chat_statuses = list(executor.map(chat_call, range(20)))
    assert set(health_statuses) == {200}
    assert set(chat_statuses) == {200}
    write_json(
        "load.json",
        {
            "health_requests": len(health_statuses),
            "chat_requests": len(chat_statuses),
            "max_workers": 12,
            "failures": 0,
        },
    )


def cleanup() -> None:
    conversation_id = CONVERSATION_FILE.read_text(encoding="utf-8").strip()
    status, _, deleted = request_json(
        f"/energy-chat/v2/conversations/{conversation_id}",
        method="DELETE",
    )
    assert status == 200
    assert deleted["deleted"] is True
    write_json("cleanup.json", deleted)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("seed", "verify", "load", "cleanup"))
    args = parser.parse_args()
    globals()[args.mode]()
    print(f"EACHAT_CONTAINER_CANARY_{args.mode.upper()}_OK")


if __name__ == "__main__":
    main()
