"""Prepare generated stabilization files for strict Ruff validation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "estimador-cag/app/routers/reviewed_graph_estimations.py"
    content = path.read_text(encoding="utf-8")
    content = content.replace("from typing import Any, cast\n", "from typing import cast\n", 1)

    anchor = "from app.generation.graph.nodes.structure_review import StaleStructureReviewError\n"
    imports = (
        "from app.generation.graph.review_state import ReviewedEstimationGraphState\n"
        "from app.generation.graph.state import new_estimation_graph_state\n"
    )
    if imports not in content:
        if anchor not in content:
            raise RuntimeError("Reviewed graph router import anchor is missing")
        content = content.replace(anchor, anchor + imports, 1)

    schema_anchor = "from app.schemas.reviewed_graph_estimation import (\n"
    budget_import = "from app.schemas.review_policy import ExecutionBudgetSnapshot\n"
    if budget_import not in content:
        if schema_anchor not in content:
            raise RuntimeError("Reviewed graph schema import anchor is missing")
        content = content.replace(schema_anchor, budget_import + schema_anchor, 1)

    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
