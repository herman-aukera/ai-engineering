"""Strict PostgreSQL checkpoint serializer for the deployable EACHAT runtime."""

from __future__ import annotations

from typing import Final

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.energy_chat.checkpoint_postgres import (
    PostgresCheckpointer,
    _RedactingPostgresSaver,
)

STRICT_MSGPACK_ALLOWLIST: Final[list[tuple[str, str]]] = [
    ("app.energy_chat.audit_models", "DecisionLedgerEntry"),
    ("app.energy_chat.audit_models", "EnergyCardV2"),
    ("app.energy_chat.audit_models", "FinalAnswerProjection"),
    ("app.energy_chat.contracts", "CriticFinding"),
    ("app.energy_chat.contracts", "EnergyCard"),
    ("app.energy_chat.contracts", "ProjectRagChunk"),
    ("app.energy_chat.contracts", "ProjectRagResult"),
    ("app.energy_chat.contracts", "RequestPolicyAssessment"),
    ("app.energy_chat.contracts", "SourceNeedResult"),
    ("app.energy_chat.evidence_hardening", "CandidateCitationValidation"),
    ("app.energy_chat.evidence_hardening", "CitationValidationResult"),
    ("app.energy_chat.evidence_hardening", "EvidenceBodyMetadata"),
    ("app.energy_chat.graph_state", "CandidateVersion"),
    ("app.energy_chat.graph_state", "CostBudget"),
    ("app.energy_chat.graph_state", "CriticPanelRecord"),
    ("app.energy_chat.graph_state", "DecisionOutcome"),
    ("app.energy_chat.graph_state", "EnergyScoreRecord"),
    ("app.energy_chat.graph_state", "ErrorRecord"),
    ("app.energy_chat.graph_state", "ProviderMetrics"),
    ("app.energy_chat.graph_state", "RepairRequest"),
    ("app.energy_chat.graph_state", "RepairResultRecord"),
    ("app.energy_chat.graph_state", "RetryBudget"),
    ("app.energy_chat.graph_state", "TraceEvent"),
    ("app.energy_chat.human_gate", "HumanActionRequest"),
    ("app.energy_chat.human_gate", "HumanAdjustment"),
    ("app.energy_chat.observability", "NodeSpan"),
]


class StrictPostgresCheckpointer(PostgresCheckpointer):
    """PostgreSQL checkpointer that reconstructs only reviewed EACHAT types."""

    def open(self) -> StrictPostgresCheckpointer:
        if self._saver is not None:
            return self
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(
            conninfo=self._connection_string,
            min_size=self._pool_min_size,
            max_size=self._pool_max_size,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=True,
        )
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=STRICT_MSGPACK_ALLOWLIST,
        )
        self._saver = _RedactingPostgresSaver(
            self._pool,
            serde=serializer,
        )
        return self
