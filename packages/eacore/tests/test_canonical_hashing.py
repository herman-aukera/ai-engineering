import json

import pytest

from eacore.engine import candidate_fingerprint, canonical_hash, canonical_json


def test_canonical_output_is_key_order_independent() -> None:
    left = {"b": 2, "a": [3, 1]}
    right = {"a": [3, 1], "b": 2}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_hash(left) == canonical_hash(right)


def test_canonical_output_is_compact() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_nan_is_rejected() -> None:
    with pytest.raises(ValueError):
        canonical_json({"bad": float("nan")})


def test_candidate_fingerprint_is_deterministic() -> None:
    first = candidate_fingerprint(candidate_kind="answer", payload={"text": "hello"})
    second = candidate_fingerprint(candidate_kind="answer", payload={"text": "hello"})
    changed = candidate_fingerprint(candidate_kind="answer", payload={"text": "changed"})
    assert first == second
    assert first != changed
    assert len(first) == 64
