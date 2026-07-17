from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Strict immutable boundary model used by persisted EACORE records."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
