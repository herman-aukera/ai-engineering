import pytest

from energy_core.schema_bundle import (
    build_schema_bundle,
    get_schema,
    list_schema_names,
)


def test_schema_bundle_lists_public_contracts() -> None:
    names = list_schema_names()

    assert names == [
        "candidate_state",
        "energy_decision",
        "energy_policy",
        "evidence_record",
        "violation",
    ]


def test_schema_bundle_contains_required_model_fields() -> None:
    bundle = build_schema_bundle()

    assert bundle["schema_bundle_version"] == "1.0.0"
    assert "models" in bundle
    assert "candidate_state" in bundle["models"]

    candidate = bundle["models"]["candidate_state"]
    evidence = bundle["models"]["evidence_record"]
    decision = bundle["models"]["energy_decision"]

    assert "candidate_id" in candidate["properties"]
    assert "spec_id" in candidate["properties"]
    assert "evidence_id" in evidence["properties"]
    assert "status" in evidence["properties"]
    assert "decision" in decision["properties"]
    assert "energy_after" in decision["properties"]


def test_unknown_schema_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown schema"):
        get_schema("executor_adapter")
