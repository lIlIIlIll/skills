# Style / Clean Code review

## Precedence and principles

Apply repository rules and `cjfmt` (or the language's own formatter) before generic style preferences. Do not ask an LLM to report spacing or semicolon minutiae already checked by deterministic tools. A review comment should target measurable comprehension burden, avoidable maintenance cost, inconsistency with accepted local rules, or a supported correctness risk.

## Categories

1. **Naming and API intent.** Prefer domain-specific, searchable, unambiguous names that reflect invariants. Don't rename established public APIs or short obvious locals for aesthetic reasons; consider backwards compatibility.
2. **Function design.** Identify high cognitive load, mixed levels of abstraction, hidden side effects or repeated state transitions. A long dispatch table or readable pattern-match is not necessarily bad.
3. **Comments and documentation.** Remove stale or contradictory claims. Explain why a surprising action is required, the contract, ownership or non-obvious limitation; preserve API docs and ABI obligations. Do not ban comments or enforce arbitrary two-line limits.
4. **Duplication.** Check for repeated **knowledge** (same rule / invariant), not merely similar text. Duplication in tests or across independently evolving domains may be deliberate. Prefer small existing utilities over new frameworks.
5. **Abstraction.** Flag single-use indirection, generic helpers with no demand, config knobs only supporting hypotheticals, and wrapper chains that obscure behavior. Do not insist on fewer types where types encode invariants.
6. **Defensive code.** Validate at trust boundaries, but avoid redundant validation of impossible internal states or catch-and-ignore branches that hide failures. Confirm invariants and threat model before removal.
7. **Errors and resources.** Clear ownership and predictable propagation. Don't simplify by dropping required cleanup, retaining references too long, or weakening diagnostics.
8. **Patterns and architecture.** Respect module boundaries, separation of concerns, test seam placement and repository neighbor symmetry without over-abstracting.
9. **Performance readability tradeoffs.** Only replace clear code with dense optimization when measured or an explicit asymptotic argument and realistic load justify it.

## Reporting criteria

An actionable style finding should include (a) actual confusing code or violated repo rule, (b) consequence, (c) smallest useful change, (d) countervailing benefit of existing design, (e) confidence. A preference not justified by (a)+(b) should be omitted.

### Anti-overengineering screen

Before suggesting any interface, helper, cache, guard, retry, fallback, or configuration option, answer:

- Which current requirement or real caller needs it?
- Is there a simpler change? Could it live at the boundary rather than in every function?
- What failure does it prevent? Is the state reachable?
- Does it increase testing or compatibility burden disproportionately?

Use metrics to prioritize source inspection, never as sole justification for a refactor. Check that extracting a method actually makes reasoning easier and doesn't split a cohesive algorithm into navigation overhead.
