"""Runtime proofs for versioned minimal, balanced, and max context snapshots."""

from __future__ import annotations

from app.energy_chat.context_compaction import (
    build_context_snapshot,
    get_m18_runtime_status,
)
from app.energy_chat.conversation_models import ConversationTurnRequest
from app.energy_chat.conversation_service import (
    create_conversation,
    execute_conversation_turn,
)
from app.energy_chat.conversation_store import InMemoryConversationStore
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime


def _conversation_with_turns(count: int = 10):
    store = InMemoryConversationStore()
    runtime = EnergyChatApplicationRuntime()
    conversation_id = "conversation-context-runtime"
    create_conversation(store, conversation_id=conversation_id)
    for index in range(count):
        execute_conversation_turn(
            store=store,
            runtime=runtime,
            conversation_id=conversation_id,
            request=ConversationTurnRequest(
                turn_id=f"turn-{index + 1}",
                expected_revision=index,
                user_message=f"Visible context fact {index + 1}.",
                required_constraints=["preserve exact identifiers"],
            ),
        )
    return store, runtime, conversation_id


def test_context_profiles_produce_distinct_hash_linked_windows() -> None:
    store, _, conversation_id = _conversation_with_turns()
    record = store.get(conversation_id)

    minimal = build_context_snapshot(
        conversation_id=conversation_id,
        revision=record.revision,
        turns=record.turns,
        profile="minimal",
    )
    balanced = build_context_snapshot(
        conversation_id=conversation_id,
        revision=record.revision,
        turns=record.turns,
        profile="balanced",
    )
    maximum = build_context_snapshot(
        conversation_id=conversation_id,
        revision=record.revision,
        turns=record.turns,
        profile="max",
    )

    assert minimal.source_hash == balanced.source_hash == maximum.source_hash
    assert minimal.summary_hash != balanced.summary_hash
    assert balanced.summary_hash != maximum.summary_hash
    assert "Turn 9 ID turn-9" in minimal.summary_text
    assert "Turn 1 ID turn-1\n" not in minimal.summary_text
    assert "Turn 3 ID turn-3" in balanced.summary_text
    assert "Turn 1 ID turn-1\n" not in balanced.summary_text
    assert "Turn 1 ID turn-1\n" in maximum.summary_text
    assert minimal.hard_constraints == ["preserve exact identifiers"]
    assert minimal.ledger_entry_ids
    assert minimal.token_count_after < maximum.token_count_after


def test_conversation_turn_persists_snapshot_lineage_and_profile() -> None:
    store, runtime, conversation_id = _conversation_with_turns(count=2)

    response = execute_conversation_turn(
        store=store,
        runtime=runtime,
        conversation_id=conversation_id,
        request=ConversationTurnRequest(
            turn_id="turn-minimal",
            expected_revision=2,
            user_message="Use the minimal context profile.",
            context_profile="minimal",
        ),
    )

    snapshot = response.turn.context_snapshot
    assert snapshot is not None
    assert snapshot.profile == "minimal"
    assert snapshot.revision == 2
    assert snapshot.source_end_revision == 2
    assert response.turn.memory_message_count == 4
    assert snapshot.source_hash.startswith("sha256:")
    assert snapshot.summary_hash.startswith("sha256:")


def test_m18_truth_reports_context_runtime_but_not_committee_yet() -> None:
    status = get_m18_runtime_status()

    assert status.context_compaction == "implemented"
    assert status.active_context_profiles == ["minimal", "balanced", "max"]
    assert status.multi_agent_orchestration == "contract_only"
    assert status.active_orchestration_modes == ["critic"]
