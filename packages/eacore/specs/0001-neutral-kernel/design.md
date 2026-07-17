# Design — Spec 0001 Neutral Kernel

Pure strict contracts live in `contracts`; deterministic pure functions live in
`engine`; framework-neutral protocols live in `ports`; bounded reference I/O
lives in `adapters`. Product adapters remain outside this package.

Energy sign convention:

    energy_delta = energy_after - energy_before

Negative means improvement. Product policies choose the exact decision;
EACORE verifies universal invariants and records neutral facts.
