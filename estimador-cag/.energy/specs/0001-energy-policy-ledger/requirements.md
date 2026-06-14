# Requirements

spec_id: 0001-energy-policy-ledger
status: active
owner: Gonzalo / AI Engineer LIDR

## Objective

Create a deterministic CLI evaluator for Energy Aware Code candidate states.

## Functional requirements

1. Load an energy policy file.
2. Load a candidate state JSON file.
3. Load evidence records from JSONL.
4. Emit accept, repair, reject, or escalate.
5. Append every decision to a JSONL ledger.

## Out of scope

1. Provider calls.
2. IDE adapters.
3. Terminal adapters.
4. Chat product integration.
