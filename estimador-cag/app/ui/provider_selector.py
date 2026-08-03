"""Streamlit provider-selector component for Session 13 Plus readiness.

Run standalone with:

    uv run streamlit run app/ui/provider_selector.py

Or import into the control room:

    from app.ui.provider_selector import render_provider_selector
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.v5_provider_selection import ProviderSelection  # noqa: E402
from app.services.provider_readiness import (  # noqa: E402
    ProviderRouteUnavailableError,
    graph_stage_inventory,
)
from app.services.stage_routing_runtime import StageRoutingRuntime  # noqa: E402

COMPLEXITY_LEVELS = ("C0", "C1", "C2", "C3", "C4", "C5")

PROVIDER_LABELS = {
    "auto": "Auto (matched benchmark required)",
    "deepseek": "DeepSeek",
    "kimi": "Kimi / Moonshot product API",
    "openai": "OpenAI",
}

REASONING_LABELS = {
    "minimal": "Minimal (provider-specific lowest supported effort)",
    "medium": "Medium (balanced default)",
    "max": "Max (deepest analysis)",
}

CONTEXT_LABELS = {
    "minimal": "Minimal (aggressive compaction)",
    "medium": "Medium (balanced default)",
    "max": "Max (preserve detail)",
}


def render_provider_selector(key_prefix: str = "") -> ProviderSelection:
    """Render provider, reasoning, and context-detail controls."""

    st.subheader("Provider & Routing")
    col1, col2, col3 = st.columns(3)

    with col1:
        provider = st.selectbox(
            "Provider",
            options=list(PROVIDER_LABELS),
            format_func=lambda value: PROVIDER_LABELS[value],
            index=list(PROVIDER_LABELS).index("deepseek"),
            key=f"{key_prefix}provider",
        )

    with col2:
        reasoning = st.selectbox(
            "Reasoning",
            options=list(REASONING_LABELS),
            format_func=lambda value: REASONING_LABELS[value],
            index=list(REASONING_LABELS).index("medium"),
            key=f"{key_prefix}reasoning",
        )

    with col3:
        context_detail = st.selectbox(
            "Context detail",
            options=list(CONTEXT_LABELS),
            format_func=lambda value: CONTEXT_LABELS[value],
            index=list(CONTEXT_LABELS).index("medium"),
            key=f"{key_prefix}context_detail",
        )

    return ProviderSelection(
        provider=provider,
        reasoning=reasoning,
        context_detail=context_detail,
    )


def render_route_table(selection: ProviderSelection, key_prefix: str = "") -> None:
    """Render the exact runtime route for every graph leaf stage."""

    st.subheader("Runtime leaf-stage route map")
    complexity = st.selectbox(
        "Route-map complexity",
        options=list(COMPLEXITY_LEVELS),
        index=list(COMPLEXITY_LEVELS).index("C3"),
        key=f"{key_prefix}route_complexity",
    )
    runtime = StageRoutingRuntime.from_settings()
    state = {
        "provider_selection": selection.model_dump(mode="json"),
        "arbitrated_assessment": {"arbitrated_level": complexity},
    }
    rows: list[dict[str, str]] = []
    for stage in graph_stage_inventory():
        try:
            route = runtime.resolve(stage=stage, state=state)
            rows.append(
                {
                    "Stage": stage,
                    "Kind": route.execution_kind,
                    "Provider": route.provider,
                    "Model": route.model,
                    "Effort": route.effort,
                    "Source": route.source,
                }
            )
        except ProviderRouteUnavailableError as exc:
            rows.append(
                {
                    "Stage": stage,
                    "Kind": "model",
                    "Provider": "unavailable",
                    "Model": str(exc)[:120],
                    "Effort": "—",
                    "Source": "fail_closed",
                }
            )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stage": st.column_config.TextColumn(width="medium"),
            "Kind": st.column_config.TextColumn(width="small"),
            "Provider": st.column_config.TextColumn(width="small"),
            "Model": st.column_config.TextColumn(width="large"),
            "Effort": st.column_config.TextColumn(width="small"),
            "Source": st.column_config.TextColumn(width="small"),
        },
    )


def render_provider_selector_full(key_prefix: str = "") -> ProviderSelection:
    """Render the full provider-selector panel and current runtime route map."""

    selection = render_provider_selector(key_prefix=key_prefix)
    st.divider()
    render_route_table(selection, key_prefix=key_prefix)
    return selection


if __name__ == "__main__":
    st.set_page_config(page_title="Provider Selector — Session 13 Plus", layout="wide")
    st.title("Provider Selector")
    st.caption(
        "Explicit routes are operational for model-backed stages. Auto remains "
        "fail-closed until a complete matched benchmark snapshot is configured."
    )
    selected = render_provider_selector_full()
    st.divider()
    st.json(selected.model_dump(mode="json"), expanded=False)
