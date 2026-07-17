from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from eacore.contracts import CompatibilityError

Migration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class MigrationRegistry:
    _migrations: dict[tuple[str, str, str], Migration] = field(default_factory=dict)

    def register(self, contract_name: str, source: str, target: str, fn: Migration) -> None:
        key = (contract_name, source, target)
        if key in self._migrations:
            raise CompatibilityError(f"migration already registered: {key}")
        self._migrations[key] = fn

    def migrate(
        self, contract_name: str, source: str, target: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if source == target:
            return deepcopy(payload)
        key = (contract_name, source, target)
        try:
            migration = self._migrations[key]
        except KeyError as exc:
            raise CompatibilityError(f"no migration registered: {key}") from exc
        original = deepcopy(payload)
        result = migration(deepcopy(payload))
        if payload != original:
            raise CompatibilityError("migration mutated its input")
        return result
