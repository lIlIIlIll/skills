# Skills

Reusable Codex and agent skills maintained by [lIlIIlIll](https://github.com/lIlIIlIll).

可复用的 Codex / Agent Skills。当前首个 Skill 专门用于大型代码库的可维护性审计与行为保持重构。

## Available skills

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
cp -R skills/clean-large-codebase .agents/skills/
```

User-level installation:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/clean-large-codebase "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Then invoke it as `$clean-large-codebase` or let Codex select it for a matching request.

## Example

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
```

The validation workflow runs on every push and pull request.
