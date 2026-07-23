from __future__ import annotations

from app.ui.shadow_dashboard import summarize_shadow_comparisons


def test_shadow_dashboard_summary_reports_migration_metrics() -> None:
    summary = summarize_shadow_comparisons(
        [
            {
                "status": "completed",
                "latency_delta_ms": 120,
                "cost_delta_eur": 500.0,
                "shadow_review_required": False,
            },
            {
                "status": "completed",
                "latency_delta_ms": 80,
                "cost_delta_eur": -100.0,
                "shadow_review_required": True,
            },
            {
                "status": "failed",
                "latency_delta_ms": 30,
                "cost_delta_eur": None,
                "shadow_review_required": None,
            },
        ]
    )

    assert summary == {
        "total": 3,
        "completed": 2,
        "failed": 1,
        "success_rate_pct": 66.7,
        "median_latency_delta_ms": 100.0,
        "median_cost_delta_eur": 200.0,
        "graph_review_rate_pct": 50.0,
    }


def test_shadow_dashboard_summary_handles_no_evidence() -> None:
    assert summarize_shadow_comparisons([]) == {
        "total": 0,
        "completed": 0,
        "failed": 0,
        "success_rate_pct": None,
        "median_latency_delta_ms": None,
        "median_cost_delta_eur": None,
        "graph_review_rate_pct": None,
    }
