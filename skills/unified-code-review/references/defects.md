# Evidence-first defect review

## Scope

For PR reviews, compare requested base vs working tree, inspect target functions and their callers and tests, then verify the changed contract at each boundary. For deep reviews, index packages/modules, enumerate relevant entry points and functions, and retain coverage markers. Code that was never opened cannot be counted as reviewed.

## Review checklist by risk

- Invariants: null/Option, lengths, offset overflow, indices, invalid encodings, empty input, sentinel cases, exceptional arithmetic, ordering.
- Lifetime: ownership, allocations, file descriptors, locks, socket handles, cleanup during cancellation, errors and early returns.
- Concurrency: shared state, atomicity, racing state transitions, deadlocks, cancellation, task/worker lifetime, PID or handle reuse.
- Interfaces: ABI/API compatibility, visibility, generics, implicit conversions, exceptions, serialization and behavioral contracts.
- Security: input trust boundary, path handling, injection, information disclosure, permissions, credentials and unsafe FFI.
- Performance: demonstrably superlinear paths, repeated IO, accidental resource explosions, data copies, lock contention. Distinguish hypotheses from measurements.
- Tests: regression reproduction first, validity of assertions, negative cases, cleanup, platform-specific behavior and CI coverage.

## Evidence ladder

1. `reproduced`: minimal isolated input triggers a failing test against current code.
2. `static-proof`: exact branch/contract trace proves effect without execution.
3. `corroborated`: multiple independent code paths, invariants, documented API or runtime logs support conclusion but not full reproduction.
4. `unverified`: plausible hypothesis; **not** a confirmed bug. Keep separate or omit if not actionable.

A static proof should identify the reachable condition, the branch it takes and the resulting observable behavior. Beware unrelated mitigations elsewhere. Verify compiler/runtime behavior rather than importing rules from another language.

## Severity and reviewer discipline

- Severity measures impact and likelihood, **not reviewer certainty** or taste.
- Dedupe overlapping findings at the root cause, with all affected call sites referenced.
- Do not file every missing null check as a bug: establish whether null is possible at that trust boundary.
- Do not report an absent test as an error in behavior; distinguish test gaps.
- For speculative performance risks, derive the algorithm on realistic sizes and seek a benchmark before making performance claims.
- If environment is unavailable, report test `not run` and limit confidence; don't substitute imagined results.
