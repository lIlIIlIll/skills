# Skills

Reusable Codex and agent skills maintained by [lIlIIlIll](https://github.com/lIlIIlIll).

可复用的 Codex / Agent Skills，涵盖代码审查、代码度量，以及大型代码库的可维护性审计和行为保持重构。

## Available skills

### `unified-code-review`

Evidence-first code review across correctness, security, style, cleanup, maintainability, architecture, tests, and reproducible metrics. It supports `pr`, `style`, `metrics`, `deep`, `architecture`, and explicitly authorized `fix` modes. Review modes are read-only by default.

- Separate confirmed defects, maintainability issues, metrics-only hotspots, and unverified leads.
- Respect repository conventions, compiler/formatter results, and existing API contracts rather than enforcing generic preferences.
- Use optional language-native metrics tools. A bundled Cangjie (`.cj`) scanner reports line counts and **heuristic** function/branch/nesting estimates, **not** formal cyclomatic or cognitive complexity.
- Keep measurements reproducible and distinguish inventory coverage from semantic review coverage.

See [SKILL.md](skills/unified-code-review/SKILL.md) and [Cangjie scanner notes](skills/unified-code-review/references/cangjie.md).

### `clean-large-codebase`

Audits oversized files, functions, God objects, mixed responsibilities, deep control flow, and dependency hotspots. It separates analysis from execution and supports incremental code-size guards without treating line count as a design goal.

Key modes:

- `audit`: inventory and rank hotspots without modifying production code;
- `plan`: design responsibility boundaries and review-sized tasks;
- `execute`: perform one selected, behavior-preserving refactor;
- `verify`: review a refactor for semantic drift and real maintainability gains;
- `guard`: add or run an incremental file-size baseline.

The skill includes additional safeguards for the Axyndra Cangjie codebase.

## Install

Project-local Codex installation:

```bash
mkdir -p .agents/skills
cp -R skills/unified-code-review .agents/skills/
cp -R skills/clean-large-codebase .agents/skills/
```

User-level installation:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/unified-code-review "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -R skills/clean-large-codebase "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Invoke either as `$unified-code-review` / `$clean-large-codebase`, or let Codex select the matching skill automatically.

## Examples

```text
Use $unified-code-review in pr mode. Review the current branch against main
for confirmed defects, code-style issues and metric regressions. Read-only;
state verification evidence and tool limitations.
```

```text
Use $clean-large-codebase in audit mode.
Audit the current checkout for responsibility and control-flow hotspots.
Do not modify source, CI, dependencies, or baselines.
Write an evidence-backed audit and a reviewable refactoring roadmap.
```

## Validate

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
python -m unittest discover -s skills/unified-code-review/tests -v
```

The validation workflow runs on every push and pull request.
