#!/usr/bin/env python3
"""Read-only, dependency-free *heuristic* source metrics for Cangjie (.cj).

This is a lexical scanner, not a Cangjie compiler or AST parser. Branch and
brace metrics MUST NOT be represented as formal CC / cognitive complexity.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

VERSION = "0.1.0"
EXCLUDE_DIRS = frozenset({
    ".git", ".cjpm", ".venv", "node_modules", "vendor", "third_party",
    "build", "dist", "target", "out", ".idea", ".vscode", "__pycache__",
})
DECISION_PATTERN = re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\|")
START_PATTERN = re.compile(r"\b(?:func|init)\b")
NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
DECL_BOUNDARY = re.compile(
    r"\b(?:func|init|class|struct|interface|enum|extension|macro|prop|package|import)\b"
)


def line_number(offset: int, newline_positions: list[int]) -> int:
    return bisect.bisect_left(newline_positions, offset) + 1


def lexical_mask(source: str) -> tuple[str, dict[str, int], list[str]]:
    """Mask ordinary comments/literals, retaining character and line offsets.

    Nested block comments are handled; unsupported interpolated and custom
    literal syntaxes may be misinterpreted and are reported as caveats.
    """
    chars = list(source)
    lines = source.splitlines()
    line_count = len(lines)
    is_code = [False] * line_count
    is_comment = [False] * line_count
    warnings: list[str] = []
    i = 0
    line = 0
    n = len(source)
    state = "normal"
    quote = ""
    triple = False
    escaped = False
    block_depth = 0
    has_interpolation = False

    def mask_one(pos: int, kind: str) -> None:
        nonlocal line
        ch = source[pos]
        if 0 <= line < line_count and ch != "\n":
            if kind == "comment":
                if not ch.isspace():
                    is_comment[line] = True
            elif kind == "code":
                is_code[line] = True
        if ch == "\n":
            line += 1
        else:
            chars[pos] = " "

    def emit_code(pos: int) -> None:
        nonlocal line
        ch = source[pos]
        if 0 <= line < line_count and not ch.isspace():
            is_code[line] = True
        if ch == "\n":
            line += 1

    while i < n:
        if state == "normal":
            if source.startswith("//", i):
                state = "line_comment"
                mask_one(i, "comment")
                mask_one(i + 1, "comment")
                i += 2
                continue
            if source.startswith("/*", i):
                state = "block_comment"
                block_depth = 1
                mask_one(i, "comment")
                mask_one(i + 1, "comment")
                i += 2
                continue
            if source[i] in ('"', "'"):
                quote = source[i]
                triple = source.startswith(quote * 3, i)
                state = "string"
                escaped = False
                length = 3 if triple else 1
                for p in range(i, i + length):
                    mask_one(p, "code")
                i += length
                continue
            if source.startswith('#"', i) or source.startswith('r#"', i):
                if "Custom/raw string delimiters may not be fully recognized" not in warnings:
                    warnings.append("Custom/raw string delimiters may not be fully recognized")
            emit_code(i)
            i += 1
            continue
        if state == "line_comment":
            if source[i] == "\n":
                state = "normal"
                emit_code(i)
            else:
                mask_one(i, "comment")
            i += 1
            continue
        if state == "block_comment":
            if source.startswith("/*", i):
                block_depth += 1
                for p in (i, i + 1):
                    mask_one(p, "comment")
                i += 2
                continue
            if source.startswith("*/", i):
                block_depth -= 1
                for p in (i, i + 1):
                    mask_one(p, "comment")
                i += 2
                if block_depth == 0:
                    state = "normal"
                continue
            mask_one(i, "comment")
            i += 1
            continue
        if state == "string":
            if (source.startswith("${", i) or source.startswith("$(", i)) and not has_interpolation:
                has_interpolation = True
            if triple and source.startswith(quote * 3, i):
                for p in range(i, i + 3):
                    mask_one(p, "code")
                state = "normal"
                i += 3
                continue
            ch = source[i]
            if not triple and ch == quote and not escaped:
                mask_one(i, "code")
                state = "normal"
                i += 1
                continue
            if ch == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
            mask_one(i, "code")
            i += 1
            continue

    if state == "block_comment":
        warnings.append("Unclosed block comment: subsequent code masked")
    elif state == "string":
        warnings.append("Unclosed string/character literal: subsequent code masked")
    if has_interpolation:
        warnings.append("Interpolated string expressions were not analyzed")

    code = sum(is_code)
    comments = sum(c and not is_code[idx] for idx, c in enumerate(is_comment))
    blanks = sum(not ln.strip() for ln in lines)
    classified = code + comments + blanks
    if classified != line_count:
        warnings.append(f"Line classification incomplete: {classified}/{line_count}")

    return "".join(chars), {
        "physical_lines": line_count,
        "code_lines_lexical": code,
        "comment_only_lines_lexical": comments,
        "blank_lines": blanks,
    }, warnings


def matching_delimiter(text: str, opening: int, left: str, right: str) -> int | None:
    depth = 0
    for i in range(opening, len(text)):
        if text[i] == left:
            depth += 1
        elif text[i] == right:
            depth -= 1
            if depth == 0:
                return i
    return None


def count_parameters(signature: str) -> int:
    if not signature.strip():
        return 0
    depths = {"<": 0, "(": 0, "[": 0, "{": 0}
    pairs = {">": "<", ")": "(", "]": "[", "}": "{"}
    commas = 0
    for ch in signature:
        if ch in depths:
            depths[ch] += 1
        elif ch in pairs:
            k = pairs[ch]
            depths[k] = max(0, depths[k] - 1)
        elif ch == "," and not any(depths.values()):
            commas += 1
    return commas + 1


def function_stats(masked: str, source: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    funcs: list[dict[str, Any]] = []
    nl = [i for i, char in enumerate(source) if char == "\n"]
    for m in START_PATTERN.finditer(masked):
        keyword = m.group()
        start = m.start()
        pos = m.end()
        while pos < len(masked) and masked[pos].isspace():
            pos += 1
        if keyword == "func":
            name_match = NAME_PATTERN.match(masked, pos)
            if name_match is None:
                # e.g. `func []` or operator syntax. Explicitly excluded.
                warnings.append(f"Unrecognized func name at line {line_number(start, nl)}")
                continue
            name = name_match.group()
            pos = name_match.end()
            while pos < len(masked) and masked[pos].isspace():
                pos += 1
            if pos < len(masked) and masked[pos] == "<":
                generic_end = matching_delimiter(masked, pos, "<", ">")
                if generic_end is None:
                    warnings.append(f"Generic signature not closed at line {line_number(start, nl)}")
                    continue
                pos = generic_end + 1
                while pos < len(masked) and masked[pos].isspace():
                    pos += 1
        else:
            name = "init"
        if pos >= len(masked) or masked[pos] != "(":
            continue
        params_end = matching_delimiter(masked, pos, "(", ")")
        if params_end is None:
            warnings.append(f"Function parameter list not closed at line {line_number(start, nl)}")
            continue
        params = count_parameters(masked[pos + 1:params_end])
        lookahead = masked[params_end + 1: params_end + 2001]
        open_pos = None
        # A declaration without a body must not borrow the next declaration's body.
        for relative, ch in enumerate(lookahead):
            if ch == "{":
                open_pos = params_end + 1 + relative
                break
            if ch in ";}":
                break
            if ch == "\n" and lookahead[:relative].count("\n") >= 24:
                break
            if relative > 0 and (b := DECL_BOUNDARY.match(lookahead, relative)) is not None:
                # The token may occur in a return type only rarely; conservatively stop.
                if b.group() not in ("import", "package"):
                    break
        if open_pos is None:
            continue
        end_pos = matching_delimiter(masked, open_pos, "{", "}")
        if end_pos is None:
            warnings.append(f"Function body not closed at line {line_number(start, nl)}")
            continue
        depth = 0
        max_depth = 0
        for ch in masked[open_pos:end_pos + 1]:
            if ch == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif ch == "}":
                depth -= 1
        decisions = len(DECISION_PATTERN.findall(masked[open_pos:end_pos + 1]))
        func = {
            "name": name,
            "start_line": line_number(start, nl),
            "body_start_line": line_number(open_pos, nl),
            "end_line": line_number(end_pos, nl),
            "body_lines_estimate": line_number(end_pos, nl) - line_number(open_pos, nl) + 1,
            "parameter_count_estimate": params,
            "decision_tokens_heuristic": decisions,
            "branch_score_heuristic": 1 + decisions,
            "brace_nesting_heuristic": max(0, max_depth - 1),
        }
        funcs.append(func)
    if re.search(r"\bmacro\b", masked):
        warnings.append("Macro-generated declarations are not available to lexical scanner")
    # Nested functions and overrides may be represented more than once.
    return funcs, warnings


def analyze_file(source: str) -> dict[str, Any]:
    masked, stats, warnings = lexical_mask(source)
    functions, func_warnings = function_stats(masked, source)
    return {"stats": stats, "functions": functions, "warnings": warnings + func_warnings}


def list_repository_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".cj" and not path.is_symlink() else []
    if not path.is_dir():
        raise ValueError(f"Path is not a source file or directory: {path}")
    files = []
    for root, dirs, filenames in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS and not (Path(root) / d).is_symlink())
        for filename in sorted(filenames):
            candidate = Path(root) / filename
            if candidate.suffix == ".cj" and not candidate.is_symlink():
                files.append(candidate)
    return sorted(files)


def git(repo: Path, *args: str, allowed_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if process.returncode and not allowed_failure:
        raise ValueError(process.stderr.decode("utf-8", errors="replace").strip() or f"git {args} failed")
    return process


def git_repo_root(path: Path) -> Path:
    # In --base mode, the target (and its containing directories) may be deleted.
    directory = path if path.is_dir() else path.parent
    while not directory.exists() and directory != directory.parent:
        directory = directory.parent
    root = git(directory, "rev-parse", "--show-toplevel")
    return Path(os.fsdecode(root.stdout.strip())).resolve()


def changed_files(target: Path, repo: Path, base: str, include_untracked: bool) -> list[Path]:
    # Disabling rename detection lets A/D pairs contribute correctly to total deltas.
    listed = git(repo, "diff", "--no-renames", "--name-only", "-z", base, "--", "*.cj")
    names = listed.stdout.split(b"\x00")
    if include_untracked:
        untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", "*.cj")
        names.extend(untracked.stdout.split(b"\x00"))
    found: list[Path] = []
    for name in names:
        if not name:
            continue
        relative = Path(os.fsdecode(name))
        if relative.suffix != ".cj" or any(p in EXCLUDE_DIRS for p in relative.parts):
            continue
        candidate = repo / relative
        if candidate.is_symlink():
            continue
        # lexical containment: includes deleted files while excluding other subtrees
        if target.is_dir() and (candidate == target or target in candidate.parents):
            found.append(candidate)
        elif candidate == target:
            found.append(candidate)
    return sorted(set(found))


def read_current(path: Path) -> tuple[str, list[str]] | None:
    if not path.is_file() or path.is_symlink():
        return None
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8"), []
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), ["Invalid UTF-8 replaced in current source"]


def read_baseline(repo: Path, base: str, relative: str) -> tuple[str, list[str]] | None:
    show = git(repo, "show", f"{base}:{relative}", allowed_failure=True)
    if show.returncode:
        return None  # New file (or absent in baseline tree).
    try:
        return show.stdout.decode("utf-8"), []
    except UnicodeDecodeError:
        return show.stdout.decode("utf-8", errors="replace"), ["Invalid UTF-8 replaced in baseline"]


def summarize(files: list[dict[str, Any]], key: str) -> dict[str, int]:
    selected = [f[key] for f in files if f.get(key) is not None]
    summary = {"files": len(selected), "functions": sum(len(s["functions"]) for s in selected)}
    for field in ("physical_lines", "code_lines_lexical", "comment_only_lines_lexical", "blank_lines"):
        summary[field] = sum(s["stats"][field] for s in selected)
    return summary


def changed_functions(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    for f in files:
        def keyed_functions(which: str) -> dict[tuple[str, int], dict[str, Any]]:
            side = f.get(which) or {"functions": []}
            counts: dict[str, int] = {}
            indexed = {}
            for fn in side["functions"]:
                counts[fn["name"]] = counts.get(fn["name"], 0) + 1
                indexed[(fn["name"], counts[fn["name"]])] = fn
            return indexed

        before, after = keyed_functions("baseline"), keyed_functions("current")
        names = sorted(set(before) | set(after))
        for name, ordinal in names:
            older, newer = before.get((name, ordinal)), after.get((name, ordinal))
            fields = ("body_lines_estimate", "parameter_count_estimate", "decision_tokens_heuristic", "brace_nesting_heuristic")
            delta = {field: (newer.get(field, 0) if newer else 0) - (older.get(field, 0) if older else 0) for field in fields}
            if older is not None and newer is not None and not any(delta.values()):
                continue
            changes.append({
                "file": f["path"], "name": name, "ordinal_in_file": ordinal,
                "status": "added" if older is None else "removed" if newer is None else "modified",
                "start_line": newer["start_line"] if newer is not None else None,
                "baseline_start_line": older["start_line"] if older is not None else None,
                "metric_delta_heuristic": delta,
            })
    return changes


def scan(target: Path, base: str | None = None, include_untracked: bool = False, top: int = 15) -> dict[str, Any]:
    if target.is_symlink():
        raise ValueError("Refusing to scan a symlink target directly")
    # A baseline comparison must accept a deleted .cj target. Without --base,
    # retain strict path validation; missing directories are not file targets.
    target = target.absolute().resolve(strict=base is None)
    if target.is_file() and target.suffix != ".cj":
        raise ValueError("Only .cj files can be directly scanned")
    if base is not None and not target.exists() and target.suffix != ".cj":
        raise ValueError("A missing target must be a .cj file in --base mode")
    base_commit: str | None = None
    head_commit: str | None = None
    if base is not None:
        repo = git_repo_root(target)
        base_commit = git(repo, "rev-parse", "--verify", f"{base}^{{commit}}").stdout.decode().strip()
        head_commit = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        paths = changed_files(target, repo, base, include_untracked)
        mode = "changed-files"
    else:
        try:
            repo = git_repo_root(target)
        except ValueError:
            repo = target if target.is_dir() else target.parent
        paths = list_repository_files(target)
        mode = "all-files-in-target"
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not paths:
        warnings.append("No changed .cj paths selected" if base is not None else "No .cj files discovered in target scope")
    for filepath in paths:
        try:
            relative = filepath.relative_to(repo).as_posix()
            current_text = read_current(filepath)
            base_text = read_baseline(repo, base, relative) if base is not None else None
            current = analyze_file(current_text[0]) if current_text is not None else None
            previous = analyze_file(base_text[0]) if base_text is not None else None
            if current is not None and current_text is not None:
                current["warnings"].extend(current_text[1])
            if previous is not None and base_text is not None:
                previous["warnings"].extend(base_text[1])
            if current is None and previous is None:
                continue
            if current is not None and previous is not None:
                status = "modified"
            elif current is not None:
                status = "added" if base is not None else "scanned"
            else:
                status = "deleted"
            record = {"path": relative, "status": status, "current": current, "baseline": previous}
            records.append(record)
            for label, side in (("current", current), ("baseline", previous)):
                if side:
                    for item in side["warnings"]:
                        if len(warnings) < 100:
                            warnings.append(f"{relative} ({label}): {item}")
        except (OSError, ValueError) as exc:
            warnings.append(f"{filepath}: file skipped: {exc}")
    summary = summarize(records, "current")
    baseline_summary = summarize(records, "baseline") if base is not None else None
    delta = {key: summary[key] - baseline_summary[key] for key in summary} if baseline_summary is not None else None
    functions = [
        {"file": f["path"], **fn}
        for f in records if f["current"] is not None
        for fn in f["current"]["functions"]
    ]
    functions.sort(key=lambda f: (
        f["decision_tokens_heuristic"], f["brace_nesting_heuristic"], f["body_lines_estimate"]
    ), reverse=True)
    result = {
        "schema_version": 1,
        "tool": {"name": "cj_metrics", "version": VERSION, "dependency": "python-stdlib", "read_only": True},
        "mode": mode,
        "target": str(target),
        "base_ref": base,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "metric_precision": {
            "physical_lines": "measured (text splitlines convention)",
            "code_comment_lines": "lexical estimate",
            "functions": "heuristic (func/init + brace matching)",
            "decision_tokens_heuristic": "heuristic: if/for/while/case/catch/&&/|| token counts; not McCabe CC",
            "brace_nesting_heuristic": "heuristic brace depth; not cognitive complexity",
            "parameter_count_estimate": "heuristic comma-separated signature",
        },
        "scope": {"excluded_directories": sorted(EXCLUDE_DIRS), "selected_file_paths": len(paths),
                  "analyzed_records": len(records), "changed_only": base is not None,
                  "includes_untracked": bool(include_untracked)},
        "summary": summary,
        "baseline_summary": baseline_summary,
        "delta": delta,
        "top_functions": functions[:max(0, top)],
        "function_changes": changed_functions(records) if base is not None else None,
        "files": records,
        "warnings": warnings,
        "limitations": [
            "Not an AST/compiler parser; heuristics may miss language features, closures, overloads and macros.",
            "Does not compute formal cyclomatic or cognitive complexity, duplication or runtime performance.",
            "Metrics by name+ordinal may mismatch same-named methods after reordering.",
            "Git base mode considers changed .cj paths only; deletion/rename shown as removed/added.",
        ],
    }
    return result


def render_markdown(report: dict[str, Any]) -> str:
    head = report["summary"]
    lines = [
        "# Cangjie source metrics (lexical / heuristic)", "",
        f"- Target: `{report['target']}`",
        f"- Scope: `{report['mode']}`; selected paths: {report['scope']['selected_file_paths']}",
        f"- Tool: `cj_metrics` {report['tool']['version']}; formal CC/cognitive metrics: **not measured**",
    ]
    if report["base_ref"] is not None:
        lines.append(f"- Base ref: `{report['base_ref']}` (`{report['base_commit'][:12]}`; changed `.cj` files only)")
    lines.extend([
        "", "## Current totals", "",
        "| Files | Functions recognized (heuristic) | Physical lines | Code lines (lexical) | Comment-only (lexical) | Blank |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {head['files']} | {head['functions']} | {head['physical_lines']} | {head['code_lines_lexical']} | {head['comment_only_lines_lexical']} | {head['blank_lines']} |",
    ])
    if report["delta"] is not None:
        d = report["delta"]
        lines.extend(["", "## Delta vs base (changed files only)", "",
                      "| Files | Functions | Physical lines | Code lines | Comment-only | Blank |",
                      "| ---: | ---: | ---: | ---: | ---: | ---: |",
                      f"| {d['files']:+} | {d['functions']:+} | {d['physical_lines']:+} | {d['code_lines_lexical']:+} | {d['comment_only_lines_lexical']:+} | {d['blank_lines']:+} |"])
    lines.extend(["", "## Top heuristic hotspots", "",
                  "| Function | Location | Branch tokens* | Brace nesting* | Body lines* | Params* |",
                  "| --- | --- | ---: | ---: | ---: | ---: |"])
    for f in report["top_functions"]:
        name = f["name"].replace("|", "\\|")
        lines.append(f"| `{name}` | `{f['file']}:{f['start_line']}` | {f['decision_tokens_heuristic']} | {f['brace_nesting_heuristic']} | {f['body_lines_estimate']} | {f['parameter_count_estimate']} |")
    if not report["top_functions"]:
        lines.append("| — | — | — | — | — | — |")
    lines.append("\n*All per-function values are lexical heuristics, **not** formal complexity measurements.*")
    if report["function_changes"] is not None:
        lines.extend(["", "## Changed function estimates", "",
                      "| Function | Status | Δ tokens* | Δ brace depth* | Δ body lines* |",
                      "| --- | --- | ---: | ---: | ---: |"])
        for change in report["function_changes"][:40]:
            d = change["metric_delta_heuristic"]
            lines.append(f"| `{change['file']}::{change['name']}#{change['ordinal_in_file']}` | {change['status']} | {d['decision_tokens_heuristic']:+} | {d['brace_nesting_heuristic']:+} | {d['body_lines_estimate']:+} |")
        if not report["function_changes"]:
            lines.append("| — | No recognized function metric changes | — | — | — |")
    if report["warnings"]:
        lines.extend(["", "## Scan warnings", ""])
        lines.extend(f"- {x}" for x in report["warnings"][:40])
        if len(report["warnings"]) > 40:
            lines.append(f"- …and {len(report['warnings']) - 40} more (see JSON)")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {x}" for x in report["limitations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help=".cj file or directory to inspect")
    parser.add_argument("--base", help="Git base ref; inspect only changed .cj paths, read base using git show")
    parser.add_argument("--include-untracked", action="store_true", help="Include untracked .cj files in --base mode")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--top", type=int, default=15, help="Number of top heuristic hotspot functions")
    parser.add_argument("--output", help="Write report to this path instead of stdout")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be nonnegative")
    try:
        report = scan(Path(args.path), base=args.base, include_untracked=args.include_untracked, top=args.top)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_markdown(report)
    if args.output:
        try:
            Path(args.output).write_text(content, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write report: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
