from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "clean-large-codebase" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import inventory  # noqa: E402


class InventoryTests(unittest.TestCase):
    def test_count_content_handles_blank_and_unterminated_lines(self) -> None:
        self.assertEqual(inventory.count_content(b"one\n\nthree"), (3, 2))
        self.assertEqual(inventory.count_content(b""), (0, 0))

    def test_normalize_extensions_adds_dot(self) -> None:
        extensions = inventory.normalize_extensions(["foo", ".BAR"])
        self.assertIn(".foo", extensions)
        self.assertIn(".bar", extensions)
        self.assertIn(".cj", extensions)

    def test_scan_includes_source_and_excludes_default_build_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "build").mkdir()
            (root / "src" / "main.cj").write_text("a\n\nb\n", encoding="utf-8")
            (root / "src" / "note.txt").write_text("ignored", encoding="utf-8")
            (root / "build" / "generated.cj").write_text("ignored", encoding="utf-8")

            records, skipped = inventory.scan_repository(root)

            self.assertEqual([item.path for item in records], ["src/main.cj"])
            self.assertEqual(records[0].lines, 3)
            self.assertEqual(records[0].nonblank_lines, 2)
            self.assertEqual(skipped, [])

    def test_scan_applies_repository_relative_exclude(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "one.py").write_text("one", encoding="utf-8")
            (root / "src" / "two.py").write_text("two", encoding="utf-8")

            records, _ = inventory.scan_repository(root, exclude_patterns=["src/two.py"])

            self.assertEqual([item.path for item in records], ["src/one.py"])

    def test_binary_looking_source_is_reported_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.py").write_bytes(b"print\x00data")

            records, skipped = inventory.scan_repository(root)

            self.assertEqual(records, [])
            self.assertEqual(skipped[0].path, "bad.py")
            self.assertIn("binary", skipped[0].reason)

    def test_symlink_source_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.py"
            target.write_text("x", encoding="utf-8")
            (root / "link.py").symlink_to(target)

            records, skipped = inventory.scan_repository(root)

            self.assertEqual([item.path for item in records], ["target.py"])
            self.assertEqual([(item.path, item.reason) for item in skipped], [("link.py", "symbolic-link file")])

    def test_document_summary_and_json_are_deterministic(self) -> None:
        record = inventory.record_from_bytes("a.py", b"a\n")
        document = inventory.inventory_document(Path("."), [record], [])
        rendered = inventory.render_json(document)

        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["summary"]["total_lines"], 1)
        self.assertTrue(rendered.endswith("\n"))

    def test_markdown_orders_largest_file_first(self) -> None:
        small = inventory.record_from_bytes("small.py", b"x")
        large = inventory.record_from_bytes("large.py", b"a\nb\n")
        document = inventory.inventory_document(Path("."), [small, large], [])

        rendered = inventory.render_markdown(document)

        self.assertLess(rendered.index("large.py"), rendered.index("small.py"))

    def test_main_writes_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.cj").write_text("main", encoding="utf-8")
            output = root / "reports" / "inventory.json"

            status = inventory.main(["--root", str(root), "--output", str(output)])

            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.read_text())["summary"]["file_count"], 1)

    def test_strict_mode_fails_when_source_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.cj").write_bytes(b"bad\x00data")
            output = root / "inventory.json"

            status = inventory.main(
                ["--root", str(root), "--output", str(output), "--strict"]
            )

            self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
