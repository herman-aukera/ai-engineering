# Energy Aware Chat release snapshot

Status: helper guide for the final-project staging branch.

Use the release snapshot helper after both gates are green:

- `bash scripts/validate_energy_chat.sh`
- `bash scripts/check_energy_chat_ci.sh`

Then render a Markdown checkpoint with:

    uv run python scripts/render_energy_chat_release_snapshot.py \
      --commit-sha <sha> \
      --focused-tests <focused-count> \
      --full-tests <full-count> \
      --local-ref <local-proof-label> \
      --ci-ref <ci-proof-label> \
      --output docs/generated/energy_chat_release_snapshot.md

The snapshot is evidence bookkeeping only. It preserves the token:

    measurement_only_no_quality_claim

It should not replace the validation gate or the dedicated Energy Aware Chat CI proof.
