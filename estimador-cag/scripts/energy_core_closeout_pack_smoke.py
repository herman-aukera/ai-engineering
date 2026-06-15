from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-m",
        "energy_core.closeout_pack_cli",
        "--project-root",
        str(project_root),
        "--format",
        "json",
        "--fail-on-incomplete",
    ]
    result = subprocess.run(
        command,
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    if payload["complete"] is not True:
        raise AssertionError("Closeout pack did not report complete output.")
    if payload["section_total"] != 5:
        raise AssertionError("Closeout pack should contain five closeout sections.")

    print("Energy Core closeout pack smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
