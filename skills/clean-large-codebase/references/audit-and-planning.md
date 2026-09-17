# Audit and planning

Use this reference for `audit` and `plan` modes.

## Establish scope

Record the current revision, included production roots, excluded generated/vendor/build paths, languages, and available validation commands. Do not silently omit unreadable files or unsupported languages.

Run `scripts/inventory.py` when a deterministic file-size inventory is useful. Its output is discovery data only; it does not identify functions, ownership, or architectural problems.

## Rank hotspots

Prefer evidence from several signals:

- physical and non-blank lines;
- change frequency and co-change patterns from version history;
- control-flow or cyclomatic complexity when trustworthy tooling exists;
- fan-in, fan-out, cross-layer imports, and shared mutable state;
- defects, regressions, and review churn;
- distinct responsibilities and abstraction levels found by reading the code.

A useful mental model is:

`priority ~= size × change frequency × complexity × defect risk × coupling`

Do not fabricate a numeric score when inputs are unavailable. A stable 2,000-line table may be safer than a frequently modified 300-line state coordinator.

## Size heuristics

These are prompts for inspection, not pass/fail design rules:

| Signal | Normal | Inspect | Priority candidate |
|---|---:|---:|---:|
| File lines | `< 500` | `500–1,500` | `> 1,500` |
| Function lines | `< 40` | `40–150` | `> 150` |
| Nesting depth | `≤ 3` | `4` | `≥ 5` |
| Parameters | `≤ 5` | `6–7` | `≥ 8` |

Generated code, protocol tables, declarative registries, parsers, state machines, and visitors may legitimately exceed these ranges. Explain exceptions rather than forcing extraction.

## Semantic inspection

For each serious candidate, identify:

1. The symbol and evidence location.
2. Its current responsibilities and owned state.
3. Callers, collaborators, and dependency direction.
4. Observable invariants that refactoring must preserve.
5. Why the current boundary makes changes or tests difficult.
6. A proposed boundary named by responsibility, not by implementation fragment.
7. Required characterization or regression tests.
8. Risk, dependencies, and a review-sized sequence of changes.

Use AST/LSP/compiler tooling for function boundaries when available. Otherwise inspect complete definitions manually and label measurements approximate. Never present regex-derived function metrics as exact.

## Outputs

For a repository-wide audit, prefer:

- `docs/refactoring/clean-code-audit.md`, based on `assets/audit-template.md`;
- `docs/refactoring/refactoring-roadmap.md`, based on `assets/roadmap-template.md`.

The audit must separate:

- **inventory coverage** — what deterministic scanning included;
- **semantic coverage** — which modules and symbols were actually read deeply;
- **validation coverage** — which commands ran successfully.

The roadmap should assign stable task IDs, dependencies, behavior invariants, verification commands, estimated risk, and explicit non-goals. Select a recommended first task, but do not execute it in audit or plan mode.
