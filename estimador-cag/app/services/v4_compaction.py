"""Deterministic context-compaction runtime for Session 13 Plus V4.

Compaction is a pure function: it reads a state dict, applies a compaction
level, and returns a compacted dict.  It never fabricates keys, never mutates
the input, and is idempotent — compacting an already-compacted state is a
no-op.
"""

from __future__ import annotations

import json
from copy import deepcopy

from app.schemas.v4_compaction import CompactionLevel, CompactionMetadata

COMPACTION_VERSION = "session13-v4-compaction-1.0.0"
_TRIM_LENGTH = 500
_MINIMAL_TRACE_LIMIT = 3
_MEDIUM_TRACE_LIMIT = 10

# Fields that carry the canonical compacted context (§8 of the policy doc).
_CANONICAL_MINIMAL_KEYS = frozenset(
    {
        "estimation_id",
        "graph_version",
        "status",
        "review_required",
        "transcript",
        "reformulated_request",
        "estimate",
        "critic_report",
        "boss_decision",
        "trace_events",
        "execution_budgets",
        "semantic_assessment",
        "v3_complexity",
        "arbitrated_assessment",
        "v3_route_plan",
        "compaction_metadata",
    }
)

# Fields dropped in minimal mode (component-level detail).
_MINIMAL_DROP_KEYS = frozenset(
    {
        "requirements",
        "components",
        "budget_matches",
        "component_estimates",
        "errors",
        "provider_metadata",
        "execution_metadata",
    }
)

# Fields whose text content is trimmed to _TRIM_LENGTH in minimal mode.
_TEXT_KEYS = frozenset({"transcript", "reformulated_request"})


def _estimate_tokens(state: dict[str, object]) -> int:
    """Rough token estimate: JSON length / 4 (English text heuristic)."""
    try:
        raw = json.dumps(state, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        raw = json.dumps(
            {k: str(v) for k, v in state.items()},
            ensure_ascii=False,
            sort_keys=True,
        )
    return max(1, len(raw) // 4)


def _already_compacted(state: dict[str, object]) -> bool:
    """Return True if the state already carries a compaction_metadata record."""
    return "compaction_metadata" in state


def _compact_minimal(state: dict[str, object]) -> dict[str, object]:
    """Aggressive compaction — canonical required fields only."""
    result: dict[str, object] = {}

    for key, value in state.items():
        if key in _MINIMAL_DROP_KEYS:
            continue

        if key == "trace_events" and isinstance(value, list):
            result[key] = deepcopy(value[-_MINIMAL_TRACE_LIMIT:])
            continue

        if key in _TEXT_KEYS and isinstance(value, str):
            result[key] = value[:_TRIM_LENGTH]
            continue

        if key == "estimate" and isinstance(value, dict):
            kept = {
                k: v
                for k, v in value.items()
                if k in {"total_hours", "total_cost_eur", "currency", "subtotal_hours",
                          "contingency_hours"}
            }
            result[key] = kept
            continue

        if key == "critic_report" and isinstance(value, dict):
            result[key] = {"verdict": value.get("verdict"), "summary": value.get("summary")}
            continue

        if key == "boss_decision" and isinstance(value, dict):
            result[key] = {"action": value.get("action"), "reason": value.get("reason")}
            continue

        if key == "semantic_assessment" and isinstance(value, dict):
            result[key] = {"level": value.get("level"), "classifier_version": value.get("classifier_version")}
            continue

        if key == "v3_complexity" and isinstance(value, dict):
            result[key] = {"level": value.get("level"), "score": value.get("score")}
            continue

        if key == "arbitrated_assessment" and isinstance(value, dict):
            result[key] = {
                "arbitrated_level": value.get("arbitrated_level"),
                "resolution": value.get("resolution"),
                "human_review_required": value.get("human_review_required"),
            }
            continue

        if key == "v3_route_plan" and isinstance(value, dict):
            result[key] = {"plan_id": value.get("plan_id"), "profile": value.get("profile")}
            continue

        if key == "execution_budgets" and isinstance(value, dict):
            kept = {
                k: v for k, v in value.items()
                if k in {"retry_count", "retry_limit", "fallback_count", "fallback_limit",
                          "cost_budget_usd", "latency_budget_ms"}
            }
            result[key] = kept
            continue

        result[key] = deepcopy(value)

    return result


def _compact_medium(state: dict[str, object]) -> dict[str, object]:
    """Balanced compaction — preserve structured data, limit trace events."""
    result: dict[str, object] = {}

    for key, value in state.items():
        if key == "trace_events" and isinstance(value, list):
            result[key] = deepcopy(value[-_MEDIUM_TRACE_LIMIT:])
            continue

        result[key] = deepcopy(value)

    return result


def _compact_max(state: dict[str, object]) -> dict[str, object]:
    """Max detail — preserve everything as-is."""
    return deepcopy(state)


_COMPACTORS = {
    "minimal": _compact_minimal,
    "medium": _compact_medium,
    "max": _compact_max,
}


def compact_context(
    state: dict[str, object],
    *,
    level: CompactionLevel = "medium",
) -> dict[str, object]:
    """Return a compacted state dict that preserves the canonical required fields.

    This is a deterministic pure function.  It never mutates the input and
    never fabricates keys that were absent.

    Idempotency: if *state* already carries a ``compaction_metadata`` record,
    it is returned unchanged.
    """
    if _already_compacted(state):
        return state

    original_tokens = _estimate_tokens(state)
    compacted = _COMPACTORS[level](state)
    compacted_tokens = _estimate_tokens(compacted)

    compacted["compaction_metadata"] = CompactionMetadata(
        original_token_estimate=original_tokens,
        compacted_token_estimate=compacted_tokens,
        compaction_level=level,
        compaction_version=COMPACTION_VERSION,
    ).model_dump(mode="json")

    return compacted
