# Session 13 Plus audit export

The reviewed-estimation API exposes a checkpoint-derived audit packet at:

```text
GET /api/v1/estimate/graph/reviewed/{estimation_id}/audit
```

The packet is assembled from an allow-list of checkpoint-safe domain fields. It
contains run and scenario lineage, the deterministic estimate, component
provenance, unresolved issues, Critic findings, Boss decisions, human decisions,
execution budgets, sanitized provider metadata, domain events, and limitations.

It intentionally excludes prompts, transcript bodies, attachment bodies, API
keys, and arbitrary state fields. The control room renders the packet and offers
a JSON export. This is an evidence bundle, not a replacement for protected logs
or a database backup.

Contract coverage lives in `tests/test_session13_plus_audit_export.py`.
