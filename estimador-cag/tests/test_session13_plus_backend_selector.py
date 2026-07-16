from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "deepseek_api_key": "test",
        "kimi_api_key": "dummy",
    }
    values.update(overrides)
    return Settings(**values)


def test_estimation_backend_defaults_to_legacy() -> None:
    assert _settings().estimation_backend == "legacy"


def test_estimation_backend_accepts_graph() -> None:
    assert _settings(estimation_backend="graph").estimation_backend == "graph"


def test_estimation_backend_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        _settings(estimation_backend="shadow")


def test_graph_rollout_mode_defaults_to_off() -> None:
    assert _settings().graph_rollout_mode == "off"


@pytest.mark.parametrize("mode", ["off", "shadow", "serve"])
def test_graph_rollout_mode_accepts_explicit_policy(mode: str) -> None:
    assert _settings(graph_rollout_mode=mode).graph_rollout_mode == mode


def test_graph_rollout_mode_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        _settings(graph_rollout_mode="canary")
