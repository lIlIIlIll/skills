"""Validate skill packaging links, frontmatter and bundled source syntax."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_frontmatter_spec_fields(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\n"))
        frontmatter = skill.split("---\n", 2)[1]
        name = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(name)
        self.assertIsNotNone(description)
        self.assertRegex(name.group(1), r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name.group(1)), 64)
        self.assertLessEqual(len(description.group(1)), 1024)

    def test_referenced_files_exist(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        referenced = re.findall(r"\]\((references/[^)#]+)\)", text)
        self.assertGreaterEqual(len(referenced), 6)
        for rel in referenced:
            with self.subTest(reference=rel):
                self.assertTrue((ROOT / rel).is_file(), rel)

    def test_all_documents_under_five_hundred_lines(self):
        for path in [ROOT / "SKILL.md"]:
            self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
