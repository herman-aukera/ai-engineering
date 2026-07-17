from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from energy_core.manifest import build_manifest, verify_manifest, write_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify a trusted file manifest.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--root", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("files", nargs="+")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "generate":
        manifest = build_manifest(
            args.files,
            root=args.root,
            generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
        write_manifest(args.output, manifest)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    report = verify_manifest(args.manifest, root=args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.fail_on_mismatch and not report["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
