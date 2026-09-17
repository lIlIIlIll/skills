#!/usr/bin/env python3
"""Reject new code-size debt while allowing existing debt to shrink."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from inventory import (
    DEFAULT_EXCLUDED_DIRS,
    FileRecord,
    SOURCE_EXTENSIONS,
    is_source_path,
    matches_exclude,
    normalize_extensions,
    record_from_bytes,
    scan_repository,
)


class GateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Violation:
    path: str
    current: int
    baseline: int | None
    reason: str


def run_git(root: Path, *args: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", "replace").strip()
        raise GateError(f"git {' '.join(args)} failed: {detail}")
    return process.stdout


def verify_git_root(root: Path) -> None:
    top = Path(run_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root.resolve():
        raise GateError(f"--root must be the Git repository root ({top})")


def read_git_blobs(root: Path, sha_by_path: Mapping[str, str]) -> dict[str, bytes]:
    if not sha_by_path:
        return {}
    unique_shas = list(dict.fromkeys(sha_by_path.values()))
    request = b"".join(sha.encode("ascii") + b"\n" for sha in unique_shas)
    process = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input=request,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", "replace").strip()
        raise GateError(f"git cat-file --batch failed: {detail}")

    stream = io.BytesIO(process.stdout)
    blobs: dict[str, bytes] = {}
    for requested_sha in unique_shas:
        header = stream.readline().decode("ascii", "replace").rstrip("\n")
        parts = header.split()
        if len(parts) != 3 or parts[1] != "blob":
            raise GateError(f"unexpected git cat-file response for {requested_sha}: {header}")
        returned_sha, _, size_text = parts
        size = int(size_text)
        data = stream.read(size)
        terminator = stream.read(1)
        if len(data) != size or terminator != b"\n":
            raise GateError(f"truncated git blob response for {requested_sha}")
        blobs[returned_sha] = data

    return {path: blobs[sha] for path, sha in sha_by_path.items()}


def baseline_from_git(
    root: Path,
    base_ref: str,
    *,
    extensions: frozenset[str],
    exclude_patterns: Sequence[str],
) -> dict[str, FileRecord]:
    verify_git_root(root)
    raw = run_git(root, "ls-tree", "-r", "-z", base_ref)
    sha_by_path: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, object_type, sha = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GateError(f"cannot parse git tree entry: {exc}") from exc
        if mode == "120000" or object_type != "blob":
            continue
        if any(part in DEFAULT_EXCLUDED_DIRS for part in Path(path).parts):
            continue
        if matches_exclude(path, exclude_patterns) or not is_source_path(path, extensions):
            continue
        sha_by_path[path] = sha

    blobs = read_git_blobs(root, sha_by_path)
    records: dict[str, FileRecord] = {}
    for path, data in blobs.items():
        try:
            records[path] = record_from_bytes(path, data)
        except ValueError as exc:
            raise GateError(f"cannot measure {base_ref}:{path}: {exc}") from exc
    return records


def renames_from_git(root: Path, base_ref: str) -> dict[str, str]:
    raw = run_git(root, "diff", "--name-status", "-z", "-M", base_ref, "--")
    tokens = raw.split(b"\0")
    renames: dict[str, str] = {}
    index = 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index].decode("ascii", "replace")
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                raise GateError("truncated rename record from git diff")
            old = tokens[index].decode("utf-8")
            new = tokens[index + 1].decode("utf-8")
            index += 2
            if status.startswith("R"):
                renames[new] = old
        else:
            index += 1
    return renames


def baseline_from_json(path: Path) -> dict[str, FileRecord]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read baseline {path}: {exc}") from exc
    if document.get("schema_version") != 1 or not isinstance(document.get("files"), list):
        raise GateError(f"unsupported or malformed inventory baseline: {path}")

    records: dict[str, FileRecord] = {}
    try:
        for item in document["files"]:
            record = FileRecord(
                path=item["path"],
                lines=int(item["lines"]),
                nonblank_lines=int(item["nonblank_lines"]),
                bytes=int(item["bytes"]),
                sha256=item["sha256"],
            )
            records[record.path] = record
    except (KeyError, TypeError, ValueError) as exc:
        raise GateError(f"malformed file record in {path}: {exc}") from exc
    return records


def evaluate_gate(
    current: Mapping[str, FileRecord],
    baseline: Mapping[str, FileRecord],
    *,
    metric: str,
    max_lines: int,
    allowed_growth: int,
    renames: Mapping[str, str] | None = None,
) -> list[Violation]:
    renames = renames or {}
    violations: list[Violation] = []
    for path in sorted(current):
        current_value = int(getattr(current[path], metric))
        baseline_path = path if path in baseline else renames.get(path)
        baseline_record = baseline.get(baseline_path) if baseline_path else None
        if baseline_record is None:
            if current_value > max_lines:
                violations.append(
                    Violation(path, current_value, None, f"new file exceeds limit {max_lines}")
                )
            continue

        baseline_value = int(getattr(baseline_record, metric))
        if baseline_value <= max_lines:
            if current_value > max_lines:
                violations.append(
                    Violation(
                        path,
                        current_value,
                        baseline_value,
                        f"file crossed limit {max_lines}",
                    )
                )
        elif current_value > baseline_value + allowed_growth:
            violations.append(
                Violation(
                    path,
                    current_value,
                    baseline_value,
                    f"oversized file grew by {current_value - baseline_value}; "
                    f"allowed growth is {allowed_growth}",
                )
            )
    return violations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--baseline", type=Path, help="inventory JSON baseline")
    source.add_argument("--base-ref", help="Git revision used as the baseline")
    parser.add_argument("--metric", choices=("lines", "nonblank_lines"), default="lines")
    parser.add_argument("--max-lines", type=int, default=1500)
    parser.add_argument("--allowed-growth", type=int, default=0)
    parser.add_argument("--extension", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_lines < 1 or args.allowed_growth < 0:
        print("size-gate: --max-lines must be positive and --allowed-growth non-negative", file=sys.stderr)
        return 2

    root = args.root.resolve()
    extensions = normalize_extensions(args.extension)
    try:
        current_records, skipped = scan_repository(
            root,
            extensions=extensions,
            exclude_patterns=args.exclude,
        )
        if skipped:
            details = ", ".join(f"{item.path} ({item.reason})" for item in skipped[:5])
            raise GateError(f"recognized source paths were skipped: {details}")
        current = {item.path: item for item in current_records}

        if args.base_ref:
            baseline = baseline_from_git(
                root,
                args.base_ref,
                extensions=extensions,
                exclude_patterns=args.exclude,
            )
            renames = renames_from_git(root, args.base_ref)
        else:
            baseline = baseline_from_json(args.baseline)
            renames = {}

        violations = evaluate_gate(
            current,
            baseline,
            metric=args.metric,
            max_lines=args.max_lines,
            allowed_growth=args.allowed_growth,
            renames=renames,
        )
    except (GateError, ValueError, OSError) as exc:
        print(f"size-gate: {exc}", file=sys.stderr)
        return 2

    if violations:
        print(f"size-gate: {len(violations)} violation(s)", file=sys.stderr)
        for item in violations:
            baseline_text = "new" if item.baseline is None else str(item.baseline)
            print(
                f"  {item.path}: current={item.current}, baseline={baseline_text}: {item.reason}",
                file=sys.stderr,
            )
        return 1

    print(
        f"size-gate: pass ({len(current)} current files, {len(baseline)} baseline files, "
        f"metric={args.metric})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
