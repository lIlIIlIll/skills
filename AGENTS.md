# Repository instructions

- Keep each skill self-contained under `skills/<skill-name>/`.
- Use lowercase kebab-case names and keep the folder name equal to the `name` in `SKILL.md`.
- Keep `SKILL.md` focused; route substantial mode-specific detail to `references/`.
- Do not add placeholders, generated caches, or duplicated documentation.
- Preserve automatic invocation unless a skill explicitly requires opt-in invocation.
- When changing a skill, run `python scripts/validate_skills.py` and `python -m unittest discover -s tests -v`.
- Run the upstream Skill Creator `quick_validate.py` as an additional check when it is available.
