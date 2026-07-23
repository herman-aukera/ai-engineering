from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_DIR = (
    PROJECT_ROOT
    / "artifacts"
    / "session13"
    / "live_provider_smoke"
)

RESULTS_PATH = ARTIFACT_DIR / "results.csv"
REPORT_PATH = ARTIFACT_DIR / "REPORT.md"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"


def _passed(value: str) -> bool:
    return value == "True"


def test_session13_live_provider_smoke_artifact() -> None:
    assert RESULTS_PATH.is_file()
    assert REPORT_PATH.is_file()
    assert METADATA_PATH.is_file()

    with RESULTS_PATH.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))

    metadata = json.loads(
        METADATA_PATH.read_text(encoding="utf-8")
    )
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert len(rows) == 18

    assert {
        row["scenario"]
        for row in rows
    } == {
        "contradiction",
        "growing",
        "pivot",
    }

    assert {
        int(row["attachment_size_kb"])
        for row in rows
    } == {
        0,
        20,
        100,
    }

    assert {
        int(row["turn_index"])
        for row in rows
    } == {
        1,
        2,
    }

    assert {
        int(row["repeat"])
        for row in rows
    } == {
        1,
    }

    latency_passes = sum(
        _passed(row["latency_budget_passed"])
        for row in rows
    )
    cost_passes = sum(
        _passed(row["cost_budget_passed"])
        for row in rows
    )
    memory_passes = sum(
        _passed(row["memory_drift_passed"])
        for row in rows
    )

    latencies = [
        float(row["latency_ms"])
        for row in rows
    ]
    total_cost = sum(
        float(row["cost_usd"])
        for row in rows
    )
    tier_counts = Counter(
        row["last_resolved_tier"]
        for row in rows
    )

    assert latency_passes == 0
    assert cost_passes == 18
    assert memory_passes == 0
    assert median(latencies) == pytest.approx(9811.5)
    assert max(latencies) == pytest.approx(44457.0)
    assert total_cost == pytest.approx(0.038857)
    assert tier_counts == {
        "flash": 17,
        "pro": 1,
    }
    assert {
        row["cache_hit_kind"]
        for row in rows
    } == {
        "none",
    }

    assert metadata["schema_version"] == (
        "session13.live_provider_smoke.v1"
    )
    assert metadata["scope"] == (
        "auxiliary_session06_cag_stress"
    )

    assert metadata["workflow"] == {
        "name": "Live provider smoke - Estimador CAG",
        "run_id": 29439589612,
        "run_url": (
            "https://github.com/herman-aukera/"
            "ai-engineering/actions/runs/29439589612"
        ),
        "source_commit": (
            "720d9f034d60cbfc926974403a58056708a002e2"
        ),
        "conclusion": "success",
    }

    assert metadata["operational_gate"] == {
        "status": "passed",
        "rows_written": 18,
        "artifact_uploaded": True,
    }

    assert metadata["quality_observation"] == {
        "status": "failed_observed_thresholds",
        "latency_budget_passed_rows": 0,
        "cost_budget_passed_rows": 18,
        "memory_drift_passed_rows": 0,
        "median_latency_ms": 9811.5,
        "maximum_latency_ms": 44457.0,
        "total_cost_usd": 0.038857,
        "cache_hit_rows": 0,
        "flash_rows": 17,
        "pro_rows": 1,
    }

    assert metadata["session13_mandatory_gate_blocking"] is False

    assert "# Session 06 CAG stress report" in report
    assert "fact recall is 0.00%" in report

    serialized = json.dumps(
        metadata,
        sort_keys=True,
    )

    for forbidden_fragment in (
        "pylf_v1_",
        "Bearer ",
        "BEGIN " + "PRIVATE KEY",
        "DEEPSEEK_API_KEY=",
        "KIMI_API_KEY=",
    ):
        assert forbidden_fragment not in serialized
