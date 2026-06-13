from app.energy_chat.contracts import EnergyChatRequest, EnergyPolicy


def test_request_defaults_to_chat_lite() -> None:
    request = EnergyChatRequest(user_message="Explain this", draft_answer="Next step: run tests.")

    assert request.mode == "chat_lite"
    assert request.required_constraints == []
    assert request.evidence_refs == []


def test_default_policy_contains_expected_thresholds() -> None:
    policy = EnergyPolicy()

    assert policy.accept_max_energy == 120
    assert policy.repair_min_energy == 121
    assert policy.reject_on_any_hard_reject is True
    assert policy.penalties["fabricated_citation"] == 1000
