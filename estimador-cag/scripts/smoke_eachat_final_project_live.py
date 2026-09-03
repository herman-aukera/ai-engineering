"""Bounded live proof for the EACHAT final-project RAG plus governed provider path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.energy_chat.api_v2_contracts import EnergyChatV2Request
from app.energy_chat.contracts import ProjectRagRequest
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.energy_chat.support_rag import build_support_rag_service_from_env

_KEY_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "kimi": ("MOONSHOT_API_KEY", "KIMI_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}

QUESTION = (
    "PostgreSQL connections are exhausted and the Spring Boot service cannot obtain a "
    "connection. Which server-side connection limits and active-session evidence should "
    "L2 support inspect before assigning a root cause?"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--provider", choices=("deepseek", "kimi", "openai"), default="openai")
    parser.add_argument("--effort", choices=("fast", "balanced", "max"), default="balanced")
    parser.add_argument("--output", default="/tmp/eachat-final-project-live.json")
    args = parser.parse_args()

    if not args.live:
        raise RuntimeError("Final-project live proof requires the explicit --live flag")
    if not _truthy(os.environ.get("EACHAT_SUPPORT_RAG_ENABLED", "")):
        raise RuntimeError("EACHAT_SUPPORT_RAG_ENABLED must be true for the live proof")
    if not any(_usable_secret(os.environ.get(name, "")) for name in _KEY_ENV[args.provider]):
        raise RuntimeError(f"No usable credential is configured for provider {args.provider}")

    rag_service = build_support_rag_service_from_env()
    rag = rag_service.retrieve(ProjectRagRequest(query=QUESTION, mode="project", k=5))
    if rag.retrieval_strategy != "openai_embedding_postgres_exact_cosine_support_rag":
        raise RuntimeError(f"Unexpected retrieval strategy: {rag.retrieval_strategy}")
    if not rag.results or not rag.evidence_refs:
        raise RuntimeError("Real support RAG returned no persisted evidence")

    runtime = EnergyChatApplicationRuntime()
    response = runtime.execute(
        EnergyChatV2Request(
            user_message=QUESTION,
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

    metrics = response.provider_metrics_summary
    if not response.final_answer:
        raise RuntimeError("Live final-project graph returned no visible final answer")
    if metrics.provider_call_count != 1:
        raise RuntimeError(
            f"Expected exactly one provider call, observed {metrics.provider_call_count}"
        )
    if response.fallback_used:
        raise RuntimeError("Live final-project proof unexpectedly used provider fallback")

    retrieved_refs = set(rag.evidence_refs)
    graph_refs = set(response.evidence_refs)
    retained_refs = sorted(retrieved_refs.intersection(graph_refs))
    if not retained_refs:
        raise RuntimeError("Retrieved support evidence did not survive into graph evidence")

    source_ids = sorted({_source_id(ref) for ref in retained_refs if ref.startswith("source:")})
    evidence = {
        "status": "success",
        "retrieval_strategy": rag.retrieval_strategy,
        "retrieval_result_count": len(rag.results),
        "retrieval_evidence_ref_count": len(rag.evidence_refs),
        "graph_retained_retrieval_ref_count": len(retained_refs),
        "retrieval_source_ids": source_ids,
        "provider": response.served_provider,
        "model": response.served_model,
        "requested_provider": response.requested_provider,
        "effort": args.effort,
        "provider_call_count": metrics.provider_call_count,
        "input_tokens": metrics.total_input_tokens,
        "output_tokens": metrics.total_output_tokens,
        "estimated_cost_usd": metrics.total_cost_usd,
        "provider_latency_ms": metrics.total_latency_ms,
        "fallback_used": response.fallback_used,
        "final_disposition": response.final_disposition,
        "energy_decision": (
            response.energy_card_v2.decision if response.energy_card_v2 else None
        ),
        "answer_present": True,
        "answer_body_recorded": False,
        "prompt_body_recorded": False,
        "credential_recorded": False,
        "checkpoint_id": response.checkpoint_id,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "EACHAT_FINAL_PROJECT_LIVE_OK "
        f"sources={','.join(source_ids)} provider={response.served_provider} "
        f"model={response.served_model} calls={metrics.provider_call_count}"
    )


def _source_id(ref: str) -> str:
    parts = ref.split(":", 2)
    return parts[1] if len(parts) >= 2 else ref


def _usable_secret(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized) and normalized not in {
        "test",
        "dummy",
        "placeholder",
        "changeme",
    }


def _truthy(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
