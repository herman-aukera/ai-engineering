from __future__ import annotations

import argparse
import json

from energy_core.schema_bundle import build_schema_bundle, get_schema, list_schema_names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Energy Aware Code JSON schemas.")
    parser.add_argument(
        "--schema",
        choices=list_schema_names(),
        help="Export one named schema instead of the full bundle.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    payload = get_schema(args.schema) if args.schema else build_schema_bundle()

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if args.schema:
            print(f"Schema: {args.schema}")
            print(f"Title: {payload.get('title', args.schema)}")
            print("Fields:")
            for field_name in sorted(payload.get("properties", {})):
                print(f"- {field_name}")
        else:
            print("Energy Aware Code Schema Bundle")
            print(f"Version: {payload['schema_bundle_version']}")
            print("Schemas:")
            for name in sorted(payload["models"]):
                print(f"- {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
