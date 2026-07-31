# Spec 0011 design

`DeterministicHardGate` emits server-owned typed findings. `SemanticJudgeResult` carries rubric scores and evidence without authority. `SemanticJury` validates independent judge identities and records disagreement. `MetaJudgeResult` may recommend a semantic disposition but cannot alter hard findings or authorization. `ActionGovernor` deterministically combines these records and owns the disposition.

A provider-neutral `CodingProposal` remains inert data. `BetaDemoRunner` performs the deterministic fixture journey and appends typed timeline records. Execution is simulated unless the separately governed secure process boundary is explicitly enabled and authorized.
