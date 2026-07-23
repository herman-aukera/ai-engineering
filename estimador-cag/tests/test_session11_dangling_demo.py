import json
import subprocess
import sys
from pathlib import Path


def test_demo_verify_citations_s11_detects_planted_dangling_citation():
    script_path = Path("scripts/demo_verify_citations_s11.py")

    completed = subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["scenario"] == "session11_planted_dangling_citation"
    assert payload["retrieved_chunk_ids"] == ["chunk-001"]
    assert payload["citation_report"]["total_lines"] == 2
    assert payload["citation_report"]["grounded_lines"] == 1
    assert payload["citation_report"]["dangling_lines"] == 1
    assert payload["citation_report"]["insufficient_lines"] == 0
    assert payload["citation_report"]["verified_citations"] == 1
    assert payload["citation_report"]["dangling_citations"] == ["chunk-999"]
    assert payload["citation_report"]["has_dangling"] is True

    statuses = {
        line["component"]: line["status"]
        for line in payload["citation_report"]["lines"]
    }

    assert statuses["Payments module"] == "grounded"
    assert statuses["Invented reporting module"] == "dangling"
