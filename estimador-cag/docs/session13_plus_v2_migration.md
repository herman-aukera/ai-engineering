# V1 to unified V2 migration

## Current phase

The V2 API is available beside V1 and uses the reviewed graph as its durable
orchestrator. The existing `ESTIMATION_BACKEND` selector is retained only for
the older session product and rollback.

## Safe sequence

1. Keep all V1 routes operational.
2. Validate the canonical V2 projection and actions.
3. Build the unified Control Room against V2.
4. Add legacy structure/reformulation capabilities as graph nodes and canonical
   adapters rather than as a competing estimator.
5. Run V1/V2 shadow comparisons.
6. Promote V2 only after contract, persistence, browser, provider and CI gates.

No V1 deprecation date is claimed in this phase.
