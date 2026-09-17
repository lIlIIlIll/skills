#!/usr/bin/env python3
"""Create a deterministic source-file size inventory.

This intentionally reports file-level text metrics only.  It does not attempt
to infer functions or architectural quality from regular expressions.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


SOURCE_EXTENSIONS = frozenset(
    {
        ".c",
        ".cc",
        ".cj",
        ".cpp",
        ".cxx",
        ".go",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".kts",
        ".m",
        ".mm",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".scala",
        ".swift",
        ".ts",
        ".tsx",
        ".zig",
    }
)

DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
    }
)


@dataclass(frozen=True)
class FileRecord:
    path: str
    lines: int
    nonblank_lines: int
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SkipRecord:
    path: str
    reason: str


def normalize_extensions(extra: Iterable[str] = ()) -> frozenset[str]:
    normalized = set(SOURCE_EXTENSIONS)
    for value in extra:
        value = value.strip().lower()
        if not value:
            continue
        normalized.add(value if value.startswith(".") else f".{value}")
    return frozenset(normalized)


def count_content(data: bytes) -> tuple[int, int]:
    lines = data.splitlines()
    return len(lines), sum(1 for line in lines if line.strip())


def record_from_bytes(path: str, data: bytes) -> FileRecord:
    if b"\x00" in data:
        raise ValueError("source file appears binary (contains NUL)")
    lines, nonblank = count_content(data)
    return FileRecord(
        path=path,
        lines=lines,
        nonblank_lines=nonblank,
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def is_source_path(relative_path: str, extensions: frozenset[str]) -> bool:
    return Path(relative_path).suffix.lower() in extensions


def matches_exclude(relative_path: str, patterns: Sequence[str]) -> bool:
    path = relative_path.replace(os.sep, "/")
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def scan_repository(
    root: Path,
    *,
    extensions: frozenset[str] = SOURCE_EXTENSIONS,
    exclude_patterns: Sequence[str] = (),
    excluded_dirs: frozenset[str] = DEFAULT_EXCLUDED_DIRS,
) -> tuple[list[FileRecord], list[SkipRecord]]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")

    records: list[FileRecord] = []
    skipped: list[SkipRecord] = []

    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in sorted(dirs):
            full = current_path / name
            rel = full.relative_to(root).as_posix()
            if name in excluded_dirs or matches_exclude(rel, exclude_patterns):
                continue
            if full.is_symlink():
                skipped.append(SkipRecord(rel, "symbolic-link directory"))
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in sorted(files):
            full = current_path / name
            rel = full.relative_to(root).as_posix()
            if matches_exclude(rel, exclude_patterns) or not is_source_path(rel, extensions):
                continue
            if full.is_symlink():
                skipped.append(SkipRecord(rel, "symbolic-link file"))
                continue
            try:
                records.append(record_from_bytes(rel, full.read_bytes()))
            except (OSError, ValueError) as exc:
                skipped.append(SkipRecord(rel, str(exc)))

    records.sort(key=lambda item: item.path)
    skipped.sort(key=lambda item: item.path)
    return records, skipped


def inventory_document(root: Path, records: list[FileRecord], skipped: list[SkipRecord]) -> dict:
    return {
        "schema_version": 1,
        "root": str(root.resolve()),
        "summary": {
            "file_count": len(records),
            "total_lines": sum(item.lines for item in records),
            "total_nonblank_lines": sum(item.nonblank_lines for item in records),
            "skipped_count": len(skipped),
        },
        "files": [asdict(item) for item in records],
        "skipped": [asdict(item) for item in skipped],
    }


def render_json(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown(document: dict) -> str:
    summary = document["summary"]
    rows = sorted(document["files"], key=lambda item: (-item["lines"], item["path"]))
    output = [
        "# Source-file inventory",
        "",
        f"- Files: {summary['file_count']}",
        f"- Physical lines: {summary['total_lines']}",
        f"- Non-blank lines: {summary['total_nonblank_lines']}",
        f"- Skipped entries: {summary['skipped_count']}",
        "",
        "| File | Lines | Non-blank | Bytes | SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for item in rows:
        safe_path = item["path"].replace("|", "\\|")
        output.append(
            f"| `{safe_path}` | {item['lines']} | {item['nonblank_lines']} | "
            f"{item['bytes']} | `{item['sha256'][:12]}` |"
        )

    if document["skipped"]:
        output.extend(["", "## Skipped", "", "| Path | Reason |", "|---|---|"])
        for item in document["skipped"]:
            safe_path = item["path"].replace("|", "\\|")
            safe_reason = item["reason"].replace("|", "\\|")
            output.append(f"| `{safe_path}` | {safe_reason} |")

    return "\n".join(output) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--extension",
        action="append",
        default=[],
        help="additional source extension; may be repeated",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="additional repository-relative glob to exclude; may be repeated",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="write to this path instead of stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return a failure status when a recognized source path is skipped",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records, skipped = scan_repository(
            args.root,
            extensions=normalize_extensions(args.extension),
            exclude_patterns=args.exclude,
        )
    except ValueError as exc:
        print(f"inventory: {exc}", file=sys.stderr)
        return 2

    document = inventory_document(args.root, records, skipped)
    rendered = render_json(document) if args.format == "json" else render_markdown(document)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    if args.strict and skipped:
        print(f"inventory: {len(skipped)} recognized source path(s) skipped", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
