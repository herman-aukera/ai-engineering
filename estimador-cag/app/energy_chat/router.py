"""FastAPI transport for deterministic and live Energy Aware Chat evaluation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.energy_chat import baseline, benchmark, fixed_benchmark, live_agent
from app.energy_chat.agent import run_energy_aware_chat_agent
from app.energy_chat.api_v2_contracts import (
    EnergyChatV2Request,
    EnergyChatV2Response,
    ExecutionProfile,
    ProviderUnavailableError,
    UnsupportedProfileError,
)
from app.energy_chat.candidate_provider import ProviderBudgetExceededError
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
    EnergyAwareChatAgentRequest,
    EnergyAwareChatAgentResult,
    EnergyChatRequest,
    EvaluationResult,
    EvidenceBundleRequest,
    EvidenceBundleResult,
    ProjectRagRequest,
    ProjectRagResult,
    RepairEvaluationResult,
    SourceNeedRequest,
    SourceNeedResult,
)
from app.energy_chat.evaluator import evaluate_answer, evaluate_with_one_pass_repair
from app.energy_chat.evidence import build_evidence_bundle
from app.energy_chat.fixed_benchmark import FixedBenchmarkRunResult
from app.energy_chat.graph_application import build_v2_error_detail, run_graph_chat_v2
from app.energy_chat.rag import retrieve_project_context
from app.energy_chat.settings import energy_chat_v2_enabled
from app.energy_chat.source_guard import classify_source_need

router = APIRouter()


@router.post("/evaluate", response_model=EvaluationResult)
def evaluate_energy_chat(request: EnergyChatRequest) -> EvaluationResult:
    """Evaluate a draft answer against deterministic energy policy."""

    return evaluate_answer(request)


@router.post("/evaluate/repair-once", response_model=RepairEvaluationResult)
def evaluate_energy_chat_with_one_pass_repair(
    request: EnergyChatRequest,
) -> RepairEvaluationResult:
    """Evaluate and apply one deterministic repair when repairable."""

    return evaluate_with_one_pass_repair(request)


@router.post("/source-needed", response_model=SourceNeedResult)
def classify_energy_chat_source_need(
    request: SourceNeedRequest,
) -> SourceNeedResult:
    """Classify whether the request needs current or project evidence."""

    return classify_source_need(request)


@router.post("/evidence/bundle", response_model=EvidenceBundleResult)
def build_energy_chat_evidence_bundle(
    request: EvidenceBundleRequest,
) -> EvidenceBundleResult:
    """Normalize supplied evidence references."""

    return build_evidence_bundle(request)


@router.post("/rag/search", response_model=ProjectRagResult)
def search_energy_chat_project_sources(
    request: ProjectRagRequest,
) -> ProjectRagResult:
    """Retrieve committed project-source evidence."""

    return retrieve_project_context(request)


@router.post("/chat", response_model=EnergyAwareChatAgentResult)
def chat_energy_aware_mvp(
    request: EnergyAwareChatAgentRequest,
) -> EnergyAwareChatAgentResult:
    """Run the deterministic legacy MVP path."""

    return run_energy_aware_chat_agent(request)


@router.post("/chat/live", response_model=EnergyAwareChatAgentResult)
def chat_energy_aware_live_provider(
    request: EnergyAwareChatAgentRequest,
) -> EnergyAwareChatAgentResult:
    """Run the legacy fallback-capable live path."""

    return live_agent.run_live_energy_aware_chat_agent(request)


@router.post("/draft/deepseek-baseline", response_model=DeepSeekBaselineResult)
def draft_deepseek_baseline(
    request: DeepSeekBaselineRequest,
) -> DeepSeekBaselineResult:
    """Generate one plain DeepSeek draft before evaluation."""

    return baseline.generate_deepseek_baseline_draft(request)


@router.post(
    "/benchmark/deepseek-energy-aware",
    response_model=DeepSeekBenchmarkRunResult,
)
def benchmark_deepseek_energy_aware(
    request: DeepSeekBenchmarkRequest,
) -> DeepSeekBenchmarkRunResult:
    """Run a measurement-only baseline plus Energy Aware evaluation."""

    return benchmark.run_deepseek_energy_benchmark(request)


@router.get("/benchmark/fixed", response_model=FixedBenchmarkRunResult)
def get_fixed_energy_chat_benchmark() -> FixedBenchmarkRunResult:
    """Return fixed deterministic benchmark evidence."""

    return fixed_benchmark.run_fixed_benchmark()


@router.get("/benchmark/fixed/report", response_class=PlainTextResponse)
def get_fixed_energy_chat_benchmark_report() -> str:
    """Return the fixed benchmark report as Markdown text."""

    return fixed_benchmark.render_fixed_benchmark_markdown(
        fixed_benchmark.run_fixed_benchmark()
    )


def _require_v2_enabled() -> None:
    if not energy_chat_v2_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "v2_disabled",
                "detail": "Energy Chat V2 is disabled by EACHAT_V2_ENABLED.",
            },
        )


def _bind_route_profile(
    request: EnergyChatV2Request,
    expected: ExecutionProfile,
) -> EnergyChatV2Request:
    if (
        request.execution_profile is not None
        and request.execution_profile != expected
    ):
        raise UnsupportedProfileError(
            field="execution_profile",
            value=request.execution_profile,
            detail=(
                f"Execution profile '{request.execution_profile}' conflicts with "
                f"this route, which requires '{expected}'."
            ),
        )
    return request.model_copy(update={"execution_profile": expected})


def _execute_v2(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
) -> EnergyChatV2Response:
    try:
        _require_v2_enabled()
        bound_request = _bind_route_profile(request, execution_profile)
        return run_graph_chat_v2(
            bound_request,
            execution_profile=execution_profile,
        )
    except HTTPException:
        raise
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_unavailable",
                exc.detail,
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except UnsupportedProfileError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                f"unsupported_{exc.field}",
                exc.detail,
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except ProviderBudgetExceededError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_budget_exceeded",
                str(exc),
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_v2_error_detail(
                "internal_error",
                "Graph execution failed. See server logs for details.",
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc


@router.post("/v2/chat", response_model=EnergyChatV2Response)
def chat_v2_deterministic(
    request: EnergyChatV2Request,
) -> EnergyChatV2Response:
    """Run exactly one keyless deterministic graph execution."""

    return _execute_v2(request, "deterministic")


@router.post("/v2/chat/live", response_model=EnergyChatV2Response)
def chat_v2_live(request: EnergyChatV2Request) -> EnergyChatV2Response:
    """Run exactly one bounded live graph execution."""

    return _execute_v2(request, "live_bounded")
