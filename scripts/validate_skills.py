#!/usr/bin/env python3
"""Perform dependency-free structural validation for every skill in this repo."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\[[^]]*]\(([^)]+)\)")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{display_path(skill_dir)}: missing SKILL.md"]

    text = skill_file.read_text(encoding="utf-8")
    if "TODO" in text or "[TODO" in text:
        errors.append(f"{display_path(skill_file)}: unfinished TODO")
    try:
        metadata = parse_frontmatter(text)
    except ValueError as exc:
        errors.append(f"{display_path(skill_file)}: {exc}")
        return errors

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if name != skill_dir.name:
        errors.append(f"{display_path(skill_file)}: name must equal directory name")
    if not NAME_PATTERN.fullmatch(name):
        errors.append(f"{display_path(skill_file)}: invalid skill name {name!r}")
    if not description:
        errors.append(f"{display_path(skill_file)}: description is required")

    for target in LINK_PATTERN.findall(text):
        if "://" in target or target.startswith("#"):
            continue
        candidate = (skill_dir / target.split("#", 1)[0]).resolve()
        try:
            candidate.relative_to(skill_dir.resolve())
        except ValueError:
            errors.append(f"{display_path(skill_file)}: link escapes skill directory: {target}")
            continue
        if not candidate.exists():
            errors.append(f"{display_path(skill_file)}: broken link: {target}")

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if openai_yaml.exists():
        interface = openai_yaml.read_text(encoding="utf-8")
        if f"${name}" not in interface:
            errors.append(
                f"{display_path(openai_yaml)}: default prompt must mention ${name}"
            )
    return errors


def main() -> int:
    if not SKILLS.is_dir():
        print("validation failed: skills directory is missing", file=sys.stderr)
        return 1

    skill_dirs = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    if not skill_dirs:
        print("validation failed: no skills found", file=sys.stderr)
        return 1

    errors = [error for skill in skill_dirs for error in validate_skill(skill)]
    if errors:
        print("validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"validated {len(skill_dirs)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
