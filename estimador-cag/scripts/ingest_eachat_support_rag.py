"""Ingest the curated EACHAT final-project technical-support corpus into pgvector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.energy_chat.support_pgvector import (  # noqa: E402
    build_pgvector_support_rag_service_from_env,
)

DEFAULT_MANIFEST = Path("docs/final_project/support_source_manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch, chunk, embed and persist the allowlisted EACHAT support corpus."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the curated support source manifest.",
    )
    args = parser.parse_args()

    service = build_pgvector_support_rag_service_from_env()
    report = service.ingest_manifest(args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
