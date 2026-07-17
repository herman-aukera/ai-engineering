from __future__ import annotations

import re
from typing import Self

from pydantic import field_validator

from .base import StrictModel
from .errors import UnsupportedMajorVersionError

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


class VersionIdentity(StrictModel):
    contract_name: str
    contract_version: str
    schema_version: str
    policy_version: str | None = None

    @field_validator("contract_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not re.fullmatch(r"[a-z][a-z0-9_.-]{1,79}", value):
            raise ValueError("contract_name must be a stable lowercase identifier")
        return value

    @field_validator("contract_version", "schema_version", "policy_version")
    @classmethod
    def validate_semver(cls, value: str | None) -> str | None:
        if value is not None and not _SEMVER.fullmatch(value):
            raise ValueError("version must use semantic version syntax")
        return value

    def require_supported_major(self, supported_major: int) -> Self:
        major = int(self.schema_version.split(".", 1)[0])
        if major != supported_major:
            raise UnsupportedMajorVersionError(
                f"unsupported {self.contract_name} schema major {major}; expected {supported_major}"
            )
        return self
