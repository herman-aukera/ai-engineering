# Migration and Rollback

1. Freeze local product fixtures and source SHA.
2. Add a product-local adapter behind a disabled feature flag.
3. Dual-serialize local and EACORE records.
4. Compare normalized identity, evidence, energy, decision code, and trace ordering.
5. Keep the product policy authoritative.
6. Run full product regression and CI.
7. Revert by disabling the flag or reverting one adapter commit.
8. Never rewrite historical product ledgers in place.

No product adapter is part of Spec 0001.
