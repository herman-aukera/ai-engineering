# Energy Aware Chat demo narration script

Status: compact narration outline for a final-project walkthrough recording.

## Opening

This demo shows Energy Aware Chat, a deterministic proof layer for evaluating answer quality boundaries before claiming acceptance.

## Show the proof first

Open `docs/energy_aware_chat_final_submission_handoff.md` and show the two proof commands:

```text
bash scripts/validate_energy_chat.sh
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

State that the proof target is the exact branch, exact commit, and workflow `Energy Aware Chat CI`.

## Show the product path

Open `energy_chat_streamlit_app.py` and explain that the UI is a demo surface over deterministic Energy Chat contracts.

## Show the payloads

Open `demo_payloads/energy_chat/` and show:

1. `evaluate_accept.json`
2. `evaluate_repair_once.json`
3. `source_needed_project.json`
4. `evidence_bundle_project.json`
5. `benchmark_measurement.json`

## Show the claim boundary

Say clearly that this is not a production deployment, not RAG grounding, and not a model quality improvement claim.

Required benchmark wording:

```text
measurement_only_no_quality_claim
```

## Close

Point reviewers to `docs/energy_aware_chat_reviewer_index.md` as the stable navigation entry point.
