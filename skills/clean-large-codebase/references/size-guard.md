# Incremental size guard

Use size checks as an anti-regression mechanism after architectural judgment, never as an automatic mandate to split code.

## Inventory

From the repository root:

```bash
python skills/clean-large-codebase/scripts/inventory.py \
  --root . \
  --format markdown \
  --output docs/refactoring/file-inventory.md
```

Use `--format json` for machine-readable baselines. The scanner records physical lines, non-blank lines, byte size, and SHA-256 for recognized source files. It skips symlinks and binary-looking files and reports all skips.

## Baseline gate

Compare the working tree to a Git revision:

```bash
python skills/clean-large-codebase/scripts/size_gate.py \
  --root . \
  --base-ref origin/main \
  --max-lines 1500
```

Or compare to an inventory JSON file:

```bash
python skills/clean-large-codebase/scripts/size_gate.py \
  --root . \
  --baseline docs/refactoring/file-inventory.json \
  --max-lines 1500
```

Default policy:

- a new file fails only when it exceeds `--max-lines`;
- an existing file at or below the limit may grow up to the limit;
- an existing oversized file may not grow beyond its baseline plus `--allowed-growth`;
- deleted files are ignored;
- Git-detected renames inherit the old path's baseline.

The gate fails closed if it cannot read the baseline or revision reliably. Use `--metric nonblank_lines` when that better matches repository policy.

Do not describe this as function-size enforcement. Function boundaries require language-aware AST/LSP/compiler analysis or manual inspection.
