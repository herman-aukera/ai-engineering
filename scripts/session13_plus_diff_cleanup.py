"""Restore source newline conventions while retaining validated semantic repairs."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "da0e2bf91569d1587a671bc598b285d5f4ecb3de"


def source_blob(relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{SOURCE_SHA}:{relative}"],
        cwd=ROOT,
    )


def newline_for(blob: bytes) -> str:
    return "\r\n" if b"\r\n" in blob else "\n"


def normalized(blob: bytes) -> str:
    return blob.decode("utf-8").replace("\r\n", "\n")


def write_with_source_newlines(relative: str, text: str, newline: str) -> None:
    payload = text.replace("\r\n", "\n")
    if newline == "\r\n":
        payload = payload.replace("\n", "\r\n")
    (ROOT / relative).write_bytes(payload.encode("utf-8"))


def cleanup_reviewed_build() -> None:
    relative = "estimador-cag/app/generation/graph/reviewed_build.py"
    blob = source_blob(relative)
    text = normalized(blob)
    edge = '    builder.add_edge("semantic_classify", "structure_phase")\n'
    if text.count(edge) != 1:
        raise RuntimeError("Expected one semantic classifier static edge in source")
    text = text.replace(edge, "", 1)
    write_with_source_newlines(relative, text, newline_for(blob))


def cleanup_reviewed_router() -> None:
    relative = "estimador-cag/app/routers/reviewed_graph_estimations.py"
    current = (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")
    safe_marker = "_SSE_ALLOWED_SCALAR_KEYS = frozenset(\n"
    if safe_marker not in current:
        raise RuntimeError("Validated safe SSE block is missing")
    safe_block = current[current.index(safe_marker):]

    blob = source_blob(relative)
    text = normalized(blob)
    text = text.replace("import json\nimport logging\n", "import asyncio\nimport json\nimport logging\n", 1)
    text = text.replace(
        "from collections.abc import AsyncIterator\nfrom typing import Any, cast\nfrom uuid import UUID\n",
        "from collections.abc import AsyncIterator, Mapping\nfrom typing import cast\nfrom uuid import UUID, uuid4\n",
        1,
    )
    structure_anchor = (
        "from app.generation.graph.nodes.structure_review import "
        "StaleStructureReviewError\n"
    )
    graph_imports = (
        "from app.generation.graph.review_state import ReviewedEstimationGraphState\n"
        "from app.generation.graph.state import new_estimation_graph_state\n"
    )
    if structure_anchor not in text:
        raise RuntimeError("Router graph import anchor is missing")
    text = text.replace(structure_anchor, structure_anchor + graph_imports, 1)

    schema_anchor = "from app.schemas.reviewed_graph_estimation import (\n"
    if schema_anchor not in text:
        raise RuntimeError("Router schema import anchor is missing")
    text = text.replace(
        schema_anchor,
        "from app.schemas.review_policy import ExecutionBudgetSnapshot\n" + schema_anchor,
        1,
    )

    audit_anchor = "from app.services.audit_export import build_estimation_audit_packet\n"
    if audit_anchor not in text:
        raise RuntimeError("Router service import anchor is missing")
    text = text.replace(
        audit_anchor,
        audit_anchor
        + "from app.services.graph_estimation import thread_id_from_estimation_id\n",
        1,
    )

    old_marker = '@router.post("/estimate/graph/reviewed/stream")\n'
    if old_marker not in text:
        raise RuntimeError("Original SSE endpoint is missing")
    text = text[: text.index(old_marker)] + safe_block
    write_with_source_newlines(relative, text, newline_for(blob))


def main() -> None:
    cleanup_reviewed_build()
    cleanup_reviewed_router()


if __name__ == "__main__":
    main()
