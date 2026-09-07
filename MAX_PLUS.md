# Agent Evolution MAX+

## Coordinator
The coordinator is the single writer for canonical merge telemetry. Shard workers are read-only with respect to `state.json` and produce isolated result files. A lock prevents overlapping coordinator runs. Duplicate agent ownership is rejected before merge.

## Learning
Causal telemetry is observational and explicitly avoids claiming causality without controlled experiments. Strategy trees are bounded to prevent runaway planning.

## Generations
Every cycle can produce an immutable, content-hashed generation snapshot. Lineage replay remains a compact explanation-oriented view.

## Immune system
State anomalies are written to `immune_system.json` with `clean` or `quarantine` status. Payment verification remains the source of truth for real money.

## Scaling path
1. Current: one GitHub runner + coordinator + isolated shard workers.
2. Next: GitHub matrix jobs produce artifact-only shard results.
3. Later: a durable artifact/object store becomes the shard result bus.

No layer fabricates money, customers, payment confirmations, or external success.
