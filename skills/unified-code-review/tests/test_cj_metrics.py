"""Behavior tests for the intentionally heuristic Cangjie metrics scanner."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "cj_metrics.py"
spec = importlib.util.spec_from_file_location("cj_metrics", MODULE)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class LexicalTests(unittest.TestCase):
    def test_comments_literals_nested_comments_and_newlines(self):
        code = ('// comment\n'
                'func foo(a: Int64, b: HashMap<String, Array<Int64>>) {\n'
                '  let x = "not // a comment or { brace }"\n'
                '  /* outer /* nested */ comment */\n'
                '  if (a > 0 && b.size > 0) { return 1 }\n'
                '}\n')
        result = metrics.analyze_file(code)
        self.assertEqual(result["stats"]["physical_lines"], 6)
        self.assertEqual(result["stats"]["comment_only_lines_lexical"], 2)
        self.assertEqual(result["stats"]["code_lines_lexical"], 4)
        self.assertEqual(len(result["functions"]), 1)
        fn = result["functions"][0]
        self.assertEqual(fn["name"], "foo")
        self.assertEqual(fn["parameter_count_estimate"], 2)
        self.assertEqual(fn["decision_tokens_heuristic"], 2)
        self.assertEqual(fn["brace_nesting_heuristic"], 1)
        self.assertEqual(fn["end_line"], 6)

    def test_unclosed_comment_warns(self):
        result = metrics.analyze_file("func foo() { /* unclosed\n if true { }\n")
        self.assertTrue(any("Unclosed block" in s for s in result["warnings"]))
        self.assertEqual(result["functions"], [])

    def test_abstract_declaration_does_not_steal_body(self):
        source = "interface Foo {\n func first(): Int64\n func second(): Int64 { return 1 }\n}\n"
        fns = metrics.analyze_file(source)["functions"]
        self.assertEqual([fn["name"] for fn in fns], ["second"])

    def test_nested_braces_and_ignored_literal(self):
        code = ('func choose(a: Int64) {\n'
                ' let s = """{ if while }"""\n'
                ' for (v in values) { if (v > 0) { return v } }\n'
                '}\n')
        fn = metrics.analyze_file(code)["functions"][0]
        self.assertEqual(fn["decision_tokens_heuristic"], 2)
        self.assertEqual(fn["brace_nesting_heuristic"], 2)

    def test_empty_and_single_line(self):
        self.assertEqual(metrics.analyze_file("")["stats"]["physical_lines"], 0)
        self.assertEqual(metrics.analyze_file("func f() {}")["functions"][0]["body_lines_estimate"], 1)

    def test_branches_with_macros_are_warnings(self):
        src = "macro Example { }\nfunc f() { match(a) { case 1 => 2; case 2 => 3 } }\n"
        result = metrics.analyze_file(src)
        self.assertTrue(any("Macro-generated" in x for x in result["warnings"]))
        self.assertEqual(result["functions"][0]["decision_tokens_heuristic"], 2)


class GitDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self._git("init", "-q")
        self._git("config", "user.name", "Test")
        self._git("config", "user.email", "test@example.invalid")
        (self.root / "src").mkdir()
        (self.root / "src" / "a.cj").write_text("func run() { return 1 }\n", encoding="utf-8")
        (self.root / "src" / "removed.cj").write_text("func old() { return 2 }\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        self.base = self._git("rev-parse", "HEAD").stdout.strip()

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True)

    def test_base_delta_includes_modified_added_and_deleted(self):
        (self.root / "src" / "a.cj").write_text("func run() { if x { return 1 } }\n", encoding="utf-8")
        (self.root / "src" / "removed.cj").unlink()
        (self.root / "src" / "added.cj").write_text("func added() { }\n", encoding="utf-8")
        self._git("add", "-A")
        report = metrics.scan(self.root, base=self.base, top=5)
        self.assertEqual(len(report["files"]), 3)
        self.assertEqual(report["base_commit"], self.base)
        self.assertEqual(report["delta"]["physical_lines"], 0)
        change = next(c for c in report["function_changes"] if c["name"] == "run")
        self.assertEqual(change["metric_delta_heuristic"]["decision_tokens_heuristic"], 1)
        self.assertEqual({f["status"] for f in report["files"]}, {"modified", "added", "deleted"})

    def test_untracked_opt_in(self):
        (self.root / "src" / "u.cj").write_text("func new() { }\n", encoding="utf-8")
        r1 = metrics.scan(self.root, base=self.base)
        r2 = metrics.scan(self.root, base=self.base, include_untracked=True)
        self.assertEqual(r1["summary"]["files"], 0)
        self.assertEqual(r2["summary"]["files"], 1)

    def test_subdirectory_scope_without_base_is_relative_to_repo(self):
        result = metrics.scan(self.root / "src")
        self.assertEqual(result["files"][0]["path"], "src/a.cj")

    def test_subdirectory_scope_and_no_mutations(self):
        (self.root / "src" / "a.cj").write_text("func run() { while x { } }\n", encoding="utf-8")
        (self.root / "outside.cj").write_text("func excluded() {}\n", encoding="utf-8")
        report = metrics.scan(self.root / "src", base=self.base)
        self.assertEqual(report["summary"]["files"], 1)
        self.assertEqual(report["files"][0]["path"], "src/a.cj")
        self.assertTrue((self.root / "outside.cj").exists())


if __name__ == "__main__":
    unittest.main()
