# Execution and review

Use this reference for `execute` and `verify` modes.

## Before editing

- Confirm the selected roadmap task still matches the current revision.
- Read the entire target module plus important callers, tests, and state owners.
- Write down the observable behavior and architectural invariants being preserved.
- Run the narrowest meaningful pre-change checks. Add characterization tests first when behavior is not adequately protected.
- Keep unrelated cleanup out of the task.

## Safe extraction sequence

1. Establish or improve behavior-level tests.
2. Introduce the destination boundary with the smallest useful interface.
3. Move one coherent responsibility while preserving call order and ownership.
4. Re-run focused checks and inspect the diff.
5. Remove obsolete paths only after all callers have moved.
6. Run broader repository checks and inspect the complete resulting modules.

Avoid speculative frameworks, generic `Utils`/`Helper`/`Manager` dumping grounds, duplicated state, bidirectional dependencies, and wrappers that merely forward arguments.

## Behavioral review checklist

Check changes to:

- argument evaluation and side-effect order;
- exception/error types, messages, wrapping, and boundaries;
- cancellation, timeouts, retry, and partial progress;
- locks, atomics, thread affinity, and callback reentrancy;
- transactions, durability, idempotency, and recovery;
- authorization and tool/action ordering;
- ownership, cleanup, resource lifetime, and shutdown;
- event, logging, streaming, and user-visible output order;
- public symbols, serialization formats, and compatibility.

## Judge the result

A successful refactor should make at least one meaningful improvement: fewer responsibilities per module, clearer state ownership, simpler control flow, narrower dependencies, better test seams, or less duplicated policy.

Do not accept a refactor solely because files or functions became shorter. Compare navigation burden, number of indirections, public surface area, dependency direction, and the ease of explaining the main execution path.

In `verify` mode, report findings before offering follow-up changes. Do not silently repair issues unless the user also requested implementation.
