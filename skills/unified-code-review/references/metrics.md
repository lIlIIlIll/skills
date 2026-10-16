# Code metrics: measured facts, heuristics and gates

## Metric inventory

| Metric | Preferred collection | Valid interpretation |
| --- | --- | --- |
| Physical LOC, blank, comment | `scc` or Cangjie text scanner | Inventory; not a quality score |
| Function length | AST/parsed function bounds; Cangjie scanner is heuristic | Investigation target only |
| Cyclomatic complexity (McCabe) | Supported-language parser / audited lizard extension | Count decision paths as defined by tool; language-specific |
| Cognitive complexity | Explicitly defined AST-aware implementation | Nesting- and flow-sensitive; not interchangeable with CC |
| Max nesting | Syntax tree if available; Cangjie uses brace nesting heuristic | Readability lead; object literals may skew estimates |
| Parameter count | Parser; Cangjie signature heuristic | Evaluate APIs and logical grouping, not just counts |
| Duplication | `jscpd`, language parser or tokens | Token duplicate != duplicate behavior or knowledge |
| Cohesion/LCOM, coupling | Dependable symbol graph / module dependency analysis | State definitions, graph boundaries and excluded edges |
| Maintainability index | Language-specific agreed formula/tool | Never compare cross-language values uncritically |
| Hotspot count | Tool-defined patterns plus source verification | A lead, not measured runtime slowness |

## Provenance contract

Every reported number has: `tool`, `version`, `language`, `metric_name`, `scope`, `exclusions`, `collection_method` (`measured`, `lexical`, `heuristic`, `estimated`), `coverage`, and `base_ref`/`baseline` when comparing. If a tool isn't installed or the parser doesn't support `.cj`, show `unavailable` rather than a fabricated zero. Preserve command line and raw result if possible.

When combining sources, do not silently sum inconsistent definitions. Do not mix exact AST metrics with heuristic regex-derived branch count under the label "cyclomatic complexity". Averages should always expose function count and distribution (e.g. median, p90, worst) to avoid hiding a few hotspots.

## Optional commands

```bash
scc .                               # verify scc supports project language/version
lizard src/                         # only supported languages / explicitly configured extensions
npx --no-install jscpd . --reporters json  # only if installed and configured for source language
python3 <skill-root>/scripts/cj_metrics.py . --format markdown
python3 <skill-root>/scripts/cj_metrics.py . --base main --format json
```

Use local versions and non-interactive commands, do not install third-party tools without user authorization. The bundled scanner has no third-party Python dependencies and does not invoke the compiler.

## Cangjie scanner outputs

- `physical_lines`: count of source text lines; exact by selected line-count convention, not equivalent to logical statements.
- `code_lines` / `comment_lines` / `blank_lines`: lexically classified; strings with comment markers are treated as code.
- `body_lines_estimate`: start/end of brace-delimited function definition identified by lexical pattern.
- `parameter_count_estimate`: comma-separated parameters in guessed declaration signature.
- `decision_tokens_heuristic`, `branch_score_heuristic`: simple keyword/operator counts; **not McCabe**.
- `brace_nesting_heuristic`: maximum nested `{}` depth in guessed function body; **not full cognitive complexity**.
- `coverage`: file/function statistics and warnings for unsupported or incomplete source shapes.

For true Cangjie McCabe/cognitive complexity, build an adapter on compiler AST or a verified grammar, define handling of `match`, `try`, expressions, short-circuit operators, macros, and closures, and compare a curated ground-truth fixture suite. Never claim the lexical approximation achieves that precision.

## Thresholds and CI policy

Optional starting **review prompts** (not portable quality standards): function length > 80, params > 5, brace nesting > 4, decision-token count > 12. Calibrate on repository distributions and agree on a baseline. Report delta only for compatible tools/settings. Measure and explain change impact; ignore intentionally generated code unless relevant.

**Do not fail CI solely on Cangjie heuristic branch/nesting counts.** Prefer a staged adoption: report-only -> ground-truth validation and baseline -> gates on trusted measures and new regressions. Do not reset the baseline to "pass" a PR, disable tests or change tool configuration to avoid findings.

## Performance caution

A nested loop is not necessarily O(n²); verify iteration bounds. A membership operation may be O(1) on a set and O(n) on an array. A sorting call in a loop may sort a bounded constant-sized collection. Mark hotspots as hypotheses until code/data evidence or benchmarking confirms a problem.
