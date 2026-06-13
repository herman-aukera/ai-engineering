"""Deterministic critics for Energy Aware Chat Slice 1."""

from __future__ import annotations

import re

from app.energy_chat.contracts import CriticFinding, EnergyChatRequest, EnergyPolicy


ACTION_MARKERS = (
    "next action",
    "next step",
    "do this",
    "run ",
    "start by",
    "proceed with",
    "use this",
)

SCOPE_EXPANSION_MARKERS = (
    "also add rag",
    "add rag",
    "implement rag",
    "add streamlit",
    "add fastapi",
    "call deepseek",
    "call openai",
    "call kimi",
    "langgraph",
    "vector database",
    "production ready",
)

UNSAFE_MARKERS = (
    "commit your api key",
    "paste your api key",
    "disable the tests",
    "skip the secret scan",
    "force push",
    "ignore failing tests",
)

FABRICATED_CITATION_PATTERNS = (
    r"citeturn\d+\w+\d+",
    r"\[(?:source|citation) needed\]",
)


def run_chat_lite_critics(
    request: EnergyChatRequest, policy: EnergyPolicy
) -> list[CriticFinding]:
    """Run the deterministic Slice 1 critic pipeline."""

    critics = (
        _instruction_critic,
        _minimal_safety_critic,
        _scope_critic,
        _completeness_critic,
        _structure_critic,
    )
    findings: list[CriticFinding] = []
    for critic in critics:
        findings.extend(critic(request, policy))
    return findings


def _finding(
    policy: EnergyPolicy,
    *,
    critic: str,
    violation_id: str,
    constraint_type: str,
    evidence: str,
    repair_hint: str,
) -> CriticFinding:
    return CriticFinding(
        critic=critic,
        violation_id=violation_id,
        constraint_type=constraint_type,  # type: ignore[arg-type]
        penalty=policy.penalties[violation_id],
        evidence=evidence,
        repair_hint=repair_hint,
    )


def _instruction_critic(
    request: EnergyChatRequest, policy: EnergyPolicy
) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    draft = request.draft_answer.casefold()
    user = request.user_message.strip().casefold()

    if _is_vague_user_intent(user):
        findings.append(
            _finding(
                policy,
                critic="instruction_critic",
                violation_id="insufficient_user_intent",
                constraint_type="hard_repair",
                evidence="The user request is too vague to evaluate a useful answer safely.",
                repair_hint="Ask one focused clarification question before answering.",
            )
        )

    for constraint in request.required_constraints:
        normalized = constraint.casefold().strip()
        if normalized and normalized not in draft:
            findings.append(
                _finding(
                    policy,
                    critic="instruction_critic",
                    violation_id="missing_user_constraint",
                    constraint_type="hard_repair",
                    evidence=f"Required constraint not found in draft answer: {constraint}",
                    repair_hint=f"Revise the answer to explicitly satisfy: {constraint}",
                )
            )

    for section in request.required_sections:
        normalized = section.casefold().strip()
        if normalized and normalized not in draft:
            findings.append(
                _finding(
                    policy,
                    critic="instruction_critic",
                    violation_id="missing_mode_requirement",
                    constraint_type="hard_repair",
                    evidence=f"Required section not found in draft answer: {section}",
                    repair_hint=f"Add a clear section for: {section}",
                )
            )

    return findings


def _minimal_safety_critic(request: EnergyChatRequest, policy: EnergyPolicy) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    draft = request.draft_answer.casefold()
    user = request.user_message.casefold()

    if "chain of thought" in user and _appears_to_reveal_hidden_reasoning(draft):
        findings.append(
            _finding(
                policy,
                critic="minimal_safety_critic",
                violation_id="hidden_chain_of_thought_requested",
                constraint_type="hard_reject",
                evidence="The user requested hidden reasoning and the draft appears to reveal it.",
                repair_hint="Refuse hidden chain-of-thought and provide a concise reasoning summary.",
            )
        )

    if any(marker in draft for marker in UNSAFE_MARKERS):
        findings.append(
            _finding(
                policy,
                critic="minimal_safety_critic",
                violation_id="unsafe_answer",
                constraint_type="hard_reject",
                evidence="The draft recommends unsafe engineering behavior.",
                repair_hint="Replace unsafe instructions with a bounded, auditable workflow.",
            )
        )

    if "i ran the tests" in draft and not request.evidence_refs:
        findings.append(
            _finding(
                policy,
                critic="minimal_safety_critic",
                violation_id="executor_self_approved",
                constraint_type="hard_reject",
                evidence="The draft claims test execution without evidence references.",
                repair_hint="Remove the claim or attach trusted command output evidence.",
            )
        )

    if "private source" in draft or "leaked source" in draft:
        findings.append(
            _finding(
                policy,
                critic="minimal_safety_critic",
                violation_id="leaked_or_private_source_recommended",
                constraint_type="hard_reject",
                evidence="The draft recommends using leaked or private source material.",
                repair_hint="Use only public, licensed, or user-provided sources.",
            )
        )

    if _has_unbacked_citation(request):
        findings.append(
            _finding(
                policy,
                critic="minimal_safety_critic",
                violation_id="fabricated_citation",
                constraint_type="hard_reject",
                evidence="The draft contains citation-like markup without evidence references.",
                repair_hint="Remove fabricated citations or attach real evidence refs.",
            )
        )

    return findings


def _scope_critic(request: EnergyChatRequest, policy: EnergyPolicy) -> list[CriticFinding]:
    draft = request.draft_answer.casefold()
    user = request.user_message.casefold()

    if any(marker in draft for marker in SCOPE_EXPANSION_MARKERS) and "rag" not in user:
        return [
            _finding(
                policy,
                critic="scope_critic",
                violation_id="scope_explosion",
                constraint_type="hard_repair",
                evidence="The draft adds future-slice implementation scope not requested by the user.",
                repair_hint="Constrain the answer to the current slice and defer future components.",
            )
        ]
    return []


def _completeness_critic(
    request: EnergyChatRequest, policy: EnergyPolicy
) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    draft = request.draft_answer.casefold()
    user = request.user_message.casefold()

    if not any(marker in draft for marker in ACTION_MARKERS):
        findings.append(
            _finding(
                policy,
                critic="completeness_critic",
                violation_id="missing_next_action",
                constraint_type="hard_repair",
                evidence="The draft does not contain a concrete next action.",
                repair_hint="End with one concrete next action.",
            )
        )

    if _asks_for_comparison(user) and not _contains_comparison(draft):
        findings.append(
            _finding(
                policy,
                critic="completeness_critic",
                violation_id="missing_comparison",
                constraint_type="hard_repair",
                evidence="The user asks for a comparison but the draft does not compare options.",
                repair_hint="Compare the relevant options before recommending one.",
            )
        )

    if _asks_for_decision(user) and "tradeoff" not in draft and "trade-off" not in draft:
        findings.append(
            _finding(
                policy,
                critic="completeness_critic",
                violation_id="missing_tradeoffs",
                constraint_type="hard_repair",
                evidence="The user asks for a decision but the draft omits tradeoffs.",
                repair_hint="Add the main tradeoffs behind the recommendation.",
            )
        )

    return findings


def _structure_critic(request: EnergyChatRequest, policy: EnergyPolicy) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    draft = request.draft_answer.strip()
    word_count = len(draft.split())

    if word_count < 25:
        findings.append(
            _finding(
                policy,
                critic="structure_critic",
                violation_id="too_generic",
                constraint_type="soft",
                evidence="The draft is very short and likely too generic.",
                repair_hint="Add specific constraints, evidence, and next action.",
            )
        )

    if word_count > 80 and "#" not in draft and "\n- " not in draft and "\n1." not in draft:
        findings.append(
            _finding(
                policy,
                critic="structure_critic",
                violation_id="weak_structure",
                constraint_type="soft",
                evidence="The draft is long but lacks visible structure.",
                repair_hint="Add concise headings or bullets.",
            )
        )

    if word_count > 180:
        findings.append(
            _finding(
                policy,
                critic="structure_critic",
                violation_id="too_verbose",
                constraint_type="soft",
                evidence="The draft is verbose for a Slice 1 evaluation candidate.",
                repair_hint="Trim repeated claims and keep only decision-relevant details.",
            )
        )

    return findings


def _is_vague_user_intent(user: str) -> bool:
    if len(user.split()) > 4:
        return False
    return user in {"help", "fix it", "improve this", "make it better", "do it", "start"}


def _appears_to_reveal_hidden_reasoning(draft: str) -> bool:
    markers = (
        "chain of thought:",
        "my hidden reasoning",
        "here is my private reasoning",
        "step-by-step internal reasoning",
    )
    return any(marker in draft for marker in markers)


def _has_unbacked_citation(request: EnergyChatRequest) -> bool:
    if request.evidence_refs:
        return False
    return any(re.search(pattern, request.draft_answer) for pattern in FABRICATED_CITATION_PATTERNS)


def _asks_for_comparison(user: str) -> bool:
    return any(marker in user for marker in ("compare", "versus", " vs ", "which is better"))


def _contains_comparison(draft: str) -> bool:
    return any(marker in draft for marker in ("compared", "versus", "tradeoff", "trade-off"))


def _asks_for_decision(user: str) -> bool:
    return any(marker in user for marker in ("should i", "which", "decide", "recommend"))
