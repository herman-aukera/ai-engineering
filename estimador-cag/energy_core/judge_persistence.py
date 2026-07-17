from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver

from energy_core.judge_graph import build_judge_graph


@contextmanager
def sqlite_judge_graph(database_path: str | Path) -> Iterator[Any]:
    """Yield a judge graph backed by a create-or-migrate SQLite checkpointer."""

    database = Path(database_path).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(database)) as checkpointer:
        checkpointer.setup()
        yield build_judge_graph(checkpointer=checkpointer)
