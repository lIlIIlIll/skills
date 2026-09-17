---
name: clean-large-codebase
description: Audit, plan, execute, or guard responsibility-oriented refactoring of oversized files, functions, and modules. Use for maintainability work involving God objects, mixed abstraction levels, deep control flow, or code-size debt; do not use for ordinary feature work or mechanical line-count reduction.
---

# Clean Large Codebase

Reduce maintenance risk by improving responsibility boundaries while preserving behavior. Treat line counts as discovery signals, not design targets.

## Choose the mode

Infer the narrowest mode authorized by the request:

- **audit** — inspect and rank hotspots; do not modify production code.
- **plan** — design boundaries and reviewable refactoring tasks for selected hotspots; do not modify production code.
- **execute** — implement only the selected task or subsystem, with behavior-preserving verification.
- **verify** — review an existing refactor for semantic drift and actual maintainability improvement.
- **guard** — add or run an incremental size baseline; modify CI only when explicitly requested.

An ambiguous request such as “clean up this repository” defaults to **audit**. Do not turn analysis permission into permission to rewrite code, edit CI, commit, push, or open a pull request.

## Shared rules

1. Read applicable repository instructions, manifests, architecture documents, and validation entry points before judging boundaries.
2. Build a complete file inventory, then prioritize by size, change frequency, complexity, defect history, coupling, and responsibility count. State which factors were actually measured and which are reasoned estimates.
3. Fully read a hotspot and its important callers, tests, and collaborators before proposing or performing extraction.
4. Split by responsibility, ownership, lifecycle, or change reason. Never create `Part1`/`Part2` modules or trivial wrapper chains merely to reduce line counts.
5. Keep orchestration at one abstraction level. Separate parsing, validation, normalization, state ownership, persistence, execution, formatting, and error translation only when they are independently meaningful.
6. Preserve public APIs and observable behavior unless the task explicitly authorizes semantic change. This includes evaluation order, errors, cancellation, locking, transactions, authorization, events, cleanup, and recovery.
7. Prefer a small sequence of independently reviewable tasks over a repository-wide rewrite. Every task needs a verification method and rollback boundary.
8. Report evidence and uncertainty. Do not claim full semantic coverage from line-count scripts, regexes, or partial reading.

For **audit** or **plan**, read [references/audit-and-planning.md](references/audit-and-planning.md). Use the templates in `assets/` when producing repository reports.

For **execute** or **verify**, read [references/execution-and-review.md](references/execution-and-review.md).

For **guard**, or when using the bundled scripts, read [references/size-guard.md](references/size-guard.md).

When the target is Axyndra, read [references/axyndra.md](references/axyndra.md) before forming conclusions or changing code.

## Completion standard

Before declaring success:

- inspect the final diff and the complete resulting modules, not only edited hunks;
- run the most relevant available tests, build, lint, and type checks;
- distinguish passed, failed, and unavailable checks;
- state semantic-review coverage separately from inventory coverage;
- ensure the result reduced responsibility or control-flow complexity rather than only relocating code.

If critical verification cannot run, mark the task **implemented but unverified** rather than complete.
