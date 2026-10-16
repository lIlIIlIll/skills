# Performance hotspot review

Metric-based scanning only produces places to inspect. Runtime performance claims require realistic inputs, appropriate benchmarks or profiler results.

1. Identify hot paths from benchmarks, production measurements or likely call frequencies; label assumptions if these sources are absent.
2. Check loops and containers: bound sizes, data structure semantics, exit conditions, sorting/search complexity, allocation and copying, IO per element, repeated deserialization, contention and blocking calls.
3. Distinguish nested loops over independent unbounded inputs from loops over small constants or partitioned disjoint inputs. A loop calling `contains` can be O(1) or O(n) depending on data type.
4. Inspect error paths and resource exhaustion (timeouts, cancellation, retries, buffering, backpressure). Avoid suggesting cached state without invalidation and memory cost analysis.
5. State asymptotic assumptions and expected input distribution. Prefer a focused benchmark before writing "performance regression confirmed".
6. With a measured regression, compare equal workloads/platform/compiler flags and report statistical variation. Do not alter performance baselines to pass CI.

A style refactor that improves readability but introduces extra allocation or hidden loops may have a legitimate tradeoff. Report it rather than assuming either dimension dominates.
