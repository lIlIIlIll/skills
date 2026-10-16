# Cangjie (`.cj`) specialization

## Repository and compiler context

- Start with repository `AGENTS.md` and build/test instructions. Record actual `cjc` / `cjfmt` version and target backend (e.g. cjnative), since behavior and APIs may vary by SDK and platform.
- Use `cjfmt` for supported formatting policy; don't invent a formatter policy from Python, Java or C++.
- Respect `package`, imports, visibility, generic constraints, extension methods, operator declarations, macros and source-generated declarations as language-specific features.
- For std/stdx code, pay special attention to API compatibility, exact type/overflow behavior, FFI ownership and error propagation, OS-dependent semantics, safety at trust boundaries, async/task cancellation, and resource cleanup.
- For JSON/Markdown/codegen tools, check deterministic output, Unicode, invalid input, overload resolution, AST/codegen symmetry, serialization/deserialization round trips and contracts documented by consumers.

## Metering caveats

The bundled `scripts/cj_metrics.py` is a **lexical heuristic** intended to rank functions worth reading, not a formal Cangjie parser.

It strips ordinary comments and strings, looks for `func`/`init` signatures and matching braces, counts selected keywords/operators, and estimates brace depth. It may miss or misattribute macro-generated declarations, overloaded operators, custom syntax, strings with interpolation, nested function/closure bodies, incomplete sources, and brace-like syntax. Never infer formal cyclomatic or cognitive complexity from these fields. Unknown or incomplete constructs should appear under `warnings`.

Use compiler/AST/CHIR tooling when available for authoritative symbol counts, inferred dispatch, declaration identities, and complexity. `lizard` support must be checked rather than assumed for `.cj`.

## Verifying a finding

- Write a minimal `.cj` regression when possible using the repository's existing test conventions.
- Record compiler version and platform as part of proof.
- Trace generated code and macro expansion when source-level expressions are misleading.
- When the SDK cannot be run, label any semantic claim contingent on compiler behavior `unverified` rather than asserting it.
- Distinguish API-level documented invariants from internal convenience assumptions. Avoid proposing additional `Option`/null checks when callers or types already make the state impossible.
