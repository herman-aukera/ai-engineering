# EACORE research retention

**Historical source head:** `ace799087a24` (`EACORE`)  
**Retained on:** 2026-08-21  
**Authority:** historical research input only. Current product code and `docs/ENERGY_AWARE_PROTOCOL_V1.md` remain authoritative.

This record preserves the useful architectural conclusions from the unique EACORE branch before its branch head is removed during repository consolidation. The EACORE runtime package itself is intentionally **not** copied into a history directory: shared runtime extraction remains evidence-gated and Git is the source archive.

## Decisions worth retaining

The EACORE SDD converged on a framework-neutral shared kernel with these responsibilities:

- versioned neutral records;
- candidate/evidence references;
- constraint observations and critic findings;
- deterministic energy snapshots;
- neutral decision/repair envelopes;
- canonical serialization and hashing;
- append-only integrity/ledger behavior;
- compatibility, retention and migration contracts;
- cross-product evaluation hooks.

It explicitly rejected placing the following in a shared core:

- product graph topology or LangGraph runtime;
- FastAPI/Streamlit/UI concerns;
- provider SDKs, prompts or live calls;
- retrieval/storage implementations;
- project-estimation arithmetic;
- chat-specific answer/refusal semantics;
- shell/repository execution authority;
- IDE/coding-agent adapters;
- product-specific decision enums, weights or thresholds.

The critical dependency rule was:

```text
product -> neutral core
```

and never:

```text
neutral core -> product/framework/provider
```

The SDD approved a neutral-kernel pilot and standalone-ready package design, but rejected wholesale extraction of EACODE's historical `energy_core` package and rejected immediate migration of all products.

## Estimator-specific boundary retained

Project-hour and cost arithmetic stays in the estimator domain. A neutral core may govern observations such as reconciliation, evidence freshness, confidence and budget compliance, but must not own estimator formulas. This is why the current portfolio shares protocol contracts first rather than a universal runtime.

## Provider-routing research retained

The EACORE branch also separated five concepts that must not be collapsed into a single model-quality switch:

1. provider selection;
2. execution/model tier;
3. reasoning effort;
4. context-compaction profile;
5. multi-agent parallelism.

It required explicit capability evidence, explicit fallback, stable planned-vs-served provider identity and no silent provider substitution. Those principles remain valid in the current Energy-Aware protocol and product manifests.

Provider/model facts in that historical document were verified on **2026-07-19** and are not current authority. Current provider capabilities must come from each product's versioned capability registry and live/provider documentation evidence.

## Unique historical material represented by the removed branch

The branch contained standalone package research under `packages/eacore/`, including:

- `docs/EACORE_SDD.md`;
- `docs/EXTRACTION_DECISIONS.md`;
- `docs/COMPATIBILITY_MATRIX.md`;
- `docs/MIGRATION_AND_ROLLBACK.md`;
- `docs/SECURITY_MODEL.md`;
- `docs/RELEASE_CHECKLIST.md`;
- `docs/PROVIDER_ROUTING_CONTEXT_COMPACTION_AND_MULTI_AGENT.md`;
- `specs/0001-neutral-kernel/*`;
- `specs/0002-provider-routing-context-compaction/SPEC.md`;
- a prototype `src/eacore` neutral-kernel implementation and tests.

## Current disposition

The useful EACORE knowledge has been absorbed into the current portfolio through:

- `docs/ENERGY_AWARE_PROTOCOL_V1.md`;
- per-product `docs/energy_aware_product_manifest.json`;
- common reason-code and authority invariants;
- identical safe observability envelope;
- cross-product portfolio evaluation;
- repository-split contracts;
- the rule that shared code is extracted only after semantic equivalence is proven.

The historical prototype source is **DEFERRED/REJECTED as current runtime**, not lost by accident. Revisit a standalone EACORE repository only when at least two products have semantically identical stable contracts, conformance tests prove equivalence, and extraction lowers total coupling/maintenance energy.
