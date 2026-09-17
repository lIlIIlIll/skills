from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_skills.py"
SPEC = importlib.util.spec_from_file_location("validate_skills", MODULE_PATH)
assert SPEC and SPEC.loader
validate_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_skills)


class ValidateSkillsTests(unittest.TestCase):
    def test_parse_frontmatter(self) -> None:
        metadata = validate_skills.parse_frontmatter(
            "---\nname: example-skill\ndescription: Does a thing.\n---\n# Example\n"
        )
        self.assertEqual(metadata["name"], "example-skill")

    def test_broken_relative_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sample"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: sample\ndescription: Sample skill.\n---\n[missing](references/no.md)\n",
                encoding="utf-8",
            )

            errors = validate_skills.validate_skill(skill)

            self.assertTrue(any("broken link" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
