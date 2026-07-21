"""Streamlit provider-selector component for Session 13 Plus V5.

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
from app.services.v5_provider_selector import resolve_provider_route  # noqa: E402

COMPLEXITY_LEVELS = ("C0", "C1", "C2", "C3", "C4", "C5")
STAGES = ("complexity", "structure", "recovery", "reliability", "proposal")

PROVIDER_LABELS = {
    "auto": "Auto (policy preview; not live calibrated)",
    "deepseek": "DeepSeek",
    "kimi": "Kimi",
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
    """Render provider, reasoning, and context-detail dropdowns.

    Returns the user's current :class:`ProviderSelection`.
    """
    st.subheader("Provider & Routing")

    col1, col2, col3 = st.columns(3)

    with col1:
        provider = st.selectbox(
            "Provider",
            options=list(PROVIDER_LABELS),
            format_func=lambda v: PROVIDER_LABELS[v],
            index=list(PROVIDER_LABELS).index("deepseek"),
            key=f"{key_prefix}provider",
        )

    with col2:
        reasoning = st.selectbox(
            "Reasoning",
            options=list(REASONING_LABELS),
            format_func=lambda v: REASONING_LABELS[v],
            index=list(REASONING_LABELS).index("medium"),
            key=f"{key_prefix}reasoning",
        )

    with col3:
        context_detail = st.selectbox(
            "Context detail",
            options=list(CONTEXT_LABELS),
            format_func=lambda v: CONTEXT_LABELS[v],
            index=list(CONTEXT_LABELS).index("medium"),
            key=f"{key_prefix}context_detail",
        )

    return ProviderSelection(
        provider=provider,
        reasoning=reasoning,
        context_detail=context_detail,
    )


def render_route_table(selection: ProviderSelection) -> None:
    """Render a route-resolution table for all complexity levels and stages."""
    st.subheader("Resolved Routes")

    rows: list[dict[str, str]] = []
    for level in COMPLEXITY_LEVELS:
        for stage in STAGES:
            try:
                route = resolve_provider_route(
                    selection=selection,
                    complexity_level=level,
                    stage=stage,
                )
                rows.append(
                    {
                        "Complexity": level,
                        "Stage": stage,
                        "Provider": route["provider"],
                        "Model": route["model"],
                        "Effort": route["effort"],
                    }
                )
            except ValueError as exc:
                rows.append(
                    {
                        "Complexity": level,
                        "Stage": stage,
                        "Provider": "—",
                        "Model": str(exc)[:80],
                        "Effort": "—",
                    }
                )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Complexity": st.column_config.TextColumn(width="small"),
            "Stage": st.column_config.TextColumn(width="small"),
            "Provider": st.column_config.TextColumn(width="small"),
            "Model": st.column_config.TextColumn(width="medium"),
            "Effort": st.column_config.TextColumn(width="small"),
        },
    )


def render_provider_selector_full(key_prefix: str = "") -> ProviderSelection:
    """Render the full provider-selector panel and return the selection."""
    selection = render_provider_selector(key_prefix=key_prefix)
    st.divider()
    render_route_table(selection)
    return selection


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(page_title="Provider Selector — Session 13 Plus", layout="wide")
    st.title("Provider Selector")
    st.caption("Session 13 Plus routing preview. Selection persistence is implemented; live per-stage switching remains capability-gated.")

    sel = render_provider_selector_full()
    st.divider()
    st.json(sel.model_dump(mode="json"), expanded=False)
