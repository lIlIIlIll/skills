from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "clean-large-codebase" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import inventory  # noqa: E402
import size_gate  # noqa: E402


def record(path: str, lines: int, nonblank: int | None = None) -> inventory.FileRecord:
    return inventory.FileRecord(
        path=path,
        lines=lines,
        nonblank_lines=lines if nonblank is None else nonblank,
        bytes=lines,
        sha256="0" * 64,
    )


class EvaluateGateTests(unittest.TestCase):
    def evaluate(
        self,
        current: dict[str, inventory.FileRecord],
        baseline: dict[str, inventory.FileRecord],
        **kwargs,
    ) -> list[size_gate.Violation]:
        return size_gate.evaluate_gate(
            current,
            baseline,
            metric=kwargs.pop("metric", "lines"),
            max_lines=kwargs.pop("max_lines", 100),
            allowed_growth=kwargs.pop("allowed_growth", 0),
            **kwargs,
        )

    def test_new_file_under_limit_passes(self) -> None:
        self.assertEqual(self.evaluate({"new.py": record("new.py", 100)}, {}), [])

    def test_new_file_over_limit_fails(self) -> None:
        violations = self.evaluate({"new.py": record("new.py", 101)}, {})
        self.assertEqual(violations[0].baseline, None)

    def test_existing_file_may_grow_to_limit(self) -> None:
        self.assertEqual(
            self.evaluate({"a.py": record("a.py", 100)}, {"a.py": record("a.py", 20)}),
            [],
        )

    def test_existing_file_may_not_cross_limit(self) -> None:
        violations = self.evaluate(
            {"a.py": record("a.py", 101)}, {"a.py": record("a.py", 20)}
        )
        self.assertIn("crossed", violations[0].reason)

    def test_oversized_file_may_stay_same_size(self) -> None:
        self.assertEqual(
            self.evaluate({"a.py": record("a.py", 150)}, {"a.py": record("a.py", 150)}),
            [],
        )

    def test_oversized_file_may_shrink(self) -> None:
        self.assertEqual(
            self.evaluate({"a.py": record("a.py", 120)}, {"a.py": record("a.py", 150)}),
            [],
        )

    def test_oversized_file_may_not_grow(self) -> None:
        violations = self.evaluate(
            {"a.py": record("a.py", 151)}, {"a.py": record("a.py", 150)}
        )
        self.assertIn("grew by 1", violations[0].reason)

    def test_allowed_growth_is_honored_for_existing_debt(self) -> None:
        self.assertEqual(
            self.evaluate(
                {"a.py": record("a.py", 152)},
                {"a.py": record("a.py", 150)},
                allowed_growth=2,
            ),
            [],
        )

    def test_deleted_files_are_ignored(self) -> None:
        self.assertEqual(self.evaluate({}, {"deleted.py": record("deleted.py", 500)}), [])

    def test_rename_inherits_old_baseline(self) -> None:
        violations = self.evaluate(
            {"new.py": record("new.py", 151)},
            {"old.py": record("old.py", 150)},
            renames={"new.py": "old.py"},
        )
        self.assertEqual(violations[0].baseline, 150)

    def test_nonblank_metric_can_be_selected(self) -> None:
        self.assertEqual(
            self.evaluate(
                {"a.py": record("a.py", 500, 80)},
                {},
                metric="nonblank_lines",
            ),
            [],
        )


class BaselineTests(unittest.TestCase):
    def test_load_inventory_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            document = {
                "schema_version": 1,
                "files": [
                    {
                        "path": "a.py",
                        "lines": 2,
                        "nonblank_lines": 1,
                        "bytes": 3,
                        "sha256": "a" * 64,
                    }
                ],
            }
            path.write_text(json.dumps(document), encoding="utf-8")

            loaded = size_gate.baseline_from_json(path)

            self.assertEqual(loaded["a.py"].nonblank_lines, 1)

    def test_malformed_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text("{}", encoding="utf-8")

            with self.assertRaises(size_gate.GateError):
                size_gate.baseline_from_json(path)

    def test_git_baseline_and_rename_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Skill Test"], check=True
            )
            (root / "old.py").write_text("one\ntwo\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "old.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
            subprocess.run(["git", "-C", str(root), "mv", "old.py", "new.py"], check=True)

            baseline = size_gate.baseline_from_git(
                root,
                "HEAD",
                extensions=inventory.SOURCE_EXTENSIONS,
                exclude_patterns=[],
            )
            renames = size_gate.renames_from_git(root, "HEAD")

            self.assertEqual(baseline["old.py"].lines, 2)
            self.assertEqual(renames, {"new.py": "old.py"})

    def test_main_rejects_invalid_thresholds(self) -> None:
        self.assertEqual(
            size_gate.main(["--baseline", "unused.json", "--max-lines", "0"]), 2
        )


if __name__ == "__main__":
    unittest.main()
