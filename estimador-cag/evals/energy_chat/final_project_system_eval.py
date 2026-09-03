"""Manual full-system EACHAT final-project evaluation with a real provider.

This evaluator is deliberately excluded from deterministic CI. It runs the fixed golden
set through the real support RAG, provider proposal, critic panel and disposition path,
then writes sanitized metrics without prompt or answer bodies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.energy_chat.api_v2_contracts import EnergyChatV2Request  # noqa: E402
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime  # noqa: E402

DEFAULT_CASES = Path("evals/energy_chat/final_project_golden.json")
DEFAULT_RESULTS_DIR = Path("evals/energy_chat/results")
_KEY_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "kimi": ("MOONSHOT_API_KEY", "KIMI_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the live EACHAT final-project golden set.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--provider", choices=tuple(_KEY_ENV), default="openai")
    parser.add_argument("--effort", choices=("fast", "balanced", "max"), default="balanced")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail unless every disposition matches the fixed golden set.",
    )
    args = parser.parse_args()

    if not args.live:
        raise RuntimeError("Full-system evaluation requires the explicit --live flag")
    if not _truthy(os.getenv("EACHAT_SUPPORT_RAG_ENABLED", "")):
        raise RuntimeError("EACHAT_SUPPORT_RAG_ENABLED must be true")
    if not any(_usable_secret(os.getenv(name, "")) for name in _KEY_ENV[args.provider]):
        raise RuntimeError(f"No usable credential configured for provider {args.provider}")

    payload = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = payload["cases"]
    runtime = EnergyChatApplicationRuntime()
    per_case: list[dict[str, object]] = []

    for case in cases:
        started = perf_counter()
        try:
            response = runtime.execute(
                EnergyChatV2Request(
                    user_message=case["query"],
                    mode="project",
                    k=5,
                    provider_preference=args.provider,
                    effort_profile=args.effort,
                    context_profile="balanced",
                    orchestration_mode="critic",
                    execution_profile="live_bounded",
                    allow_provider_fallback=False,
                ),
                "live_bounded",
            )
        except Exception as exc:
            per_case.append(
                {
                    "case_id": case["case_id"],
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "wall_latency_ms": _elapsed_ms(started),
                    "expected_disposition": case["expected_disposition"],
                }
            )
            continue

        expected_sources = set(case.get("expected_source_ids", []))
        graph_source_ids = {
            _source_id(ref)
            for ref in response.evidence_refs
            if isinstance(ref, str) and ref.startswith("source:")
        }
        retrieval_applicable = bool(expected_sources)
        retrieval_hit = bool(expected_sources.intersection(graph_source_ids)) if retrieval_applicable else None
        metrics = response.provider_metrics_summary
        per_case.append(
            {
                "case_id": case["case_id"],
                "status": "success",
                "expected_disposition": case["expected_disposition"],
                "actual_disposition": response.final_disposition,
                "disposition_correct": response.final_disposition == case["expected_disposition"],
                "expected_source_ids": sorted(expected_sources),
                "graph_source_ids": sorted(graph_source_ids),
                "retrieval_hit_at_5": retrieval_hit,
                "evidence_ref_present": bool(graph_source_ids),
                "provider": response.served_provider,
                "model": response.served_model,
                "provider_call_count": metrics.provider_call_count,
                "provider_latency_ms": metrics.total_latency_ms,
                "wall_latency_ms": _elapsed_ms(started),
                "estimated_cost_usd": metrics.total_cost_usd,
                "fallback_used": response.fallback_used,
                "answer_present": bool(response.final_answer),
                "answer_body_recorded": False,
                "prompt_body_recorded": False,
                "credential_recorded": False,
            }
        )

    report = _build_report(
        per_case=per_case,
        provider=args.provider,
        effort=args.effort,
        cases_path=args.cases,
        golden_schema_version=str(payload.get("schema_version", "unknown")),
    )
    output = args.output or _default_output_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"] != 0:
        return 1
    if args.strict and report["disposition_accuracy"] != 1.0:
        return 1
    return 0


def _build_report(
    *,
    per_case: list[dict[str, object]],
    provider: str,
    effort: str,
    cases_path: Path,
    golden_schema_version: str,
) -> dict[str, object]:
    successful = [case for case in per_case if case["status"] == "success"]
    retrieval_cases = [
        case for case in successful if case.get("retrieval_hit_at_5") is not None
    ]
    clarification_cases = [
        case for case in successful if case["expected_disposition"] == "clarify"
    ]
    escalation_cases = [
        case for case in successful if case["expected_disposition"] == "escalate"
    ]
    latencies = [int(case["wall_latency_ms"]) for case in successful]
    costs = [float(case["estimated_cost_usd"]) for case in successful]
    provider_calls = [int(case["provider_call_count"]) for case in successful]

    return {
        "schema_version": "1.0.0",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "git_sha": os.getenv("GIT_SHA", os.getenv("EXPECTED_HEAD_SHA", "unknown")),
        "provider": provider,
        "effort": effort,
        "golden_set": str(cases_path),
        "golden_schema_version": golden_schema_version,
        "cases_total": len(per_case),
        "cases_successful": len(successful),
        "errors": len(per_case) - len(successful),
        "error_rate": _rate(len(per_case) - len(successful), len(per_case)),
        "disposition_accuracy": _boolean_rate(successful, "disposition_correct"),
        "clarification_accuracy": _boolean_rate(clarification_cases, "disposition_correct"),
        "escalation_accuracy": _boolean_rate(escalation_cases, "disposition_correct"),
        "retrieval_hit_at_5": _boolean_rate(retrieval_cases, "retrieval_hit_at_5"),
        "evidence_ref_presence_rate": _boolean_rate(successful, "evidence_ref_present"),
        "answer_presence_rate": _boolean_rate(successful, "answer_present"),
        "mean_latency_ms": mean(latencies) if latencies else 0.0,
        "p95_latency_ms": _p95(latencies),
        "mean_provider_calls": mean(provider_calls) if provider_calls else 0.0,
        "provider_call_count": sum(provider_calls),
        "mean_cost_usd": mean(costs) if costs else 0.0,
        "total_estimated_cost_usd": sum(costs),
        "unsupported_claim_rate": "not_measured_without_external_judge",
        "claim_boundary": (
            "Disposition, retrieval/evidence-reference, latency, provider-call and cost metrics "
            "are measured directly. Semantic groundedness and unsupported-claim rate are not "
            "invented; they require a separate judge/manual review. Prompt and answer bodies "
            "are intentionally omitted from the saved artifact."
        ),
        "results": per_case,
    }


def _default_output_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"final_project_live_{stamp}.json"


def _boolean_rate(cases: list[dict[str, object]], field: str) -> float | None:
    if not cases:
        return None
    return sum(bool(case.get(field)) for case in cases) / len(cases)


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((0.95 * len(ordered) + 0.999999) - 1)))
    return ordered[index]


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _source_id(ref: str) -> str:
    parts = ref.split(":", 2)
    return parts[1] if len(parts) >= 2 else ref


def _usable_secret(value: str | None) -> bool:
    normalized = (value or "").strip().casefold()
    return bool(normalized) and normalized not in {"test", "dummy", "placeholder", "changeme"}


def _truthy(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
