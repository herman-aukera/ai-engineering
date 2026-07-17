from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from energy_core.controlled_execution import CommandProposal, build_execution_plan
from energy_core.execution_authorization import (
    AuthorizationContext,
    ExecutionAuthorization,
    consume_execution_authorization,
    hash_nonce,
    scope_for_plan,
    verify_execution_authorization,
)


def _plan(tmp_path):
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-status",
            executable="git",
            arguments=["status", "--short"],
            working_directory=".",
            declared_paths=[],
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=512,
            environment_names=[],
            rollback_summary="Read-only status command; no repository mutation.",
        ),
        repository_root=tmp_path,
    )


def _authorization(plan, **overrides):
    now = datetime(2026, 7, 17, 20, 0, tzinfo=UTC)
    payload = {
        "authorization_id": "auth-1",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "expected_revision": 3,
        "accepted_revision": 3,
        "scope": scope_for_plan(plan),
        "created_at": now,
        "expires_at": now + timedelta(minutes=10),
        "nonce": "nonce-1234567890",
        "reason": "Review completed for the exact read-only execution plan.",
        "rollback_acknowledged": True,
        "consumed": False,
    }
    payload.update(overrides)
    return ExecutionAuthorization.model_validate(payload)


def _context(**overrides):
    payload = {
        "current_revision": 3,
        "trusted_actors": ["gonzalo"],
        "consumed_nonce_hashes": [],
        "now": datetime(2026, 7, 17, 20, 5, tzinfo=UTC),
    }
    payload.update(overrides)
    return AuthorizationContext.model_validate(payload)


def test_valid_authorization_verifies_and_consumes_once(tmp_path) -> None:
    plan = _plan(tmp_path)
    authorization = _authorization(plan)
    context = _context()

    decision = verify_execution_authorization(plan, authorization, context)
    consumed, updated_context, receipt = consume_execution_authorization(
        plan,
        authorization,
        context,
    )

    assert decision.authorized is True
    assert decision.reasons == []
    assert consumed.consumed is True
    assert hash_nonce(authorization.nonce) in updated_context.consumed_nonce_hashes
    assert receipt.authorization_id == authorization.authorization_id
    assert receipt.plan_hash == plan.plan_hash
    assert receipt.execution_performed is False


@pytest.mark.parametrize(
    ("authorization_overrides", "context_overrides", "expected_reason"),
    [
        ({"plan_hash": "0" * 64}, {}, "plan_hash_mismatch"),
        ({"expected_revision": 2, "accepted_revision": 2}, {}, "stale_expected_revision"),
        ({"actor": "unknown"}, {}, "untrusted_actor"),
        ({"rollback_acknowledged": False}, {}, "rollback_not_acknowledged"),
        ({"consumed": True}, {}, "authorization_already_consumed"),
    ],
)
def test_invalid_authorization_fails_closed(
    tmp_path,
    authorization_overrides,
    context_overrides,
    expected_reason,
) -> None:
    plan = _plan(tmp_path)
    decision = verify_execution_authorization(
        plan,
        _authorization(plan, **authorization_overrides),
        _context(**context_overrides),
    )

    assert decision.authorized is False
    assert expected_reason in decision.reasons


def test_expired_authorization_fails_closed(tmp_path) -> None:
    plan = _plan(tmp_path)
    now = datetime(2026, 7, 17, 20, 5, tzinfo=UTC)
    authorization = _authorization(
        plan,
        expires_at=now - timedelta(seconds=1),
    )

    decision = verify_execution_authorization(plan, authorization, _context(now=now))

    assert decision.authorized is False
    assert "authorization_expired" in decision.reasons


def test_replayed_nonce_fails_closed(tmp_path) -> None:
    plan = _plan(tmp_path)
    authorization = _authorization(plan)
    context = _context(consumed_nonce_hashes=[hash_nonce(authorization.nonce)])

    decision = verify_execution_authorization(plan, authorization, context)

    assert decision.authorized is False
    assert "nonce_already_consumed" in decision.reasons


def test_scope_mismatch_fails_closed(tmp_path) -> None:
    plan = _plan(tmp_path)
    scope = scope_for_plan(plan).model_copy(update={"timeout_seconds": 31})

    decision = verify_execution_authorization(
        plan,
        _authorization(plan, scope=scope),
        _context(),
    )

    assert decision.authorized is False
    assert "authorization_scope_mismatch" in decision.reasons


def test_authorization_is_rejected_for_non_human_gated_plan(tmp_path) -> None:
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-pytest",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            declared_paths=[],
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=512,
            environment_names=[],
        ),
        repository_root=tmp_path,
    )

    decision = verify_execution_authorization(plan, _authorization(plan), _context())

    assert decision.authorized is False
    assert "plan_does_not_require_human_authorization" in decision.reasons


def test_missing_authorization_cannot_be_consumed(tmp_path) -> None:
    plan = _plan(tmp_path)

    with pytest.raises(PermissionError, match="authorization required"):
        consume_execution_authorization(plan, None, _context())


def test_authorization_requires_timezone_aware_timestamps(tmp_path) -> None:
    plan = _plan(tmp_path)

    with pytest.raises(ValidationError):
        _authorization(
            plan,
            created_at=datetime(2026, 7, 17, 20, 0),
            expires_at=datetime(2026, 7, 17, 20, 10),
        )


def test_json_round_trip_preserves_consumed_and_replay_state(tmp_path) -> None:
    plan = _plan(tmp_path)
    consumed, updated_context, _ = consume_execution_authorization(
        plan,
        _authorization(plan),
        _context(),
    )

    reloaded_authorization = ExecutionAuthorization.model_validate_json(
        consumed.model_dump_json()
    )
    reloaded_context = AuthorizationContext.model_validate_json(
        updated_context.model_dump_json()
    )

    decision = verify_execution_authorization(
        plan,
        reloaded_authorization,
        reloaded_context,
    )
    assert decision.authorized is False
    assert "authorization_already_consumed" in decision.reasons
    assert "nonce_already_consumed" in decision.reasons
